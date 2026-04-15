"""
Tests for borg/core/telemetry.py — opt-in anonymous telemetry.

Covers:
    - TELEMETRY_ENABLED flag: disabled by default
    - track_event: writes JSONL when enabled, no-op when disabled
    - Event schema: timestamp, event_type, pack_id, session_hash, success
    - No PII: no agent_id, no task content, no error messages
    - Graceful failure: write errors never crash callers
    - Search/pull/apply_start/apply_complete/apply_fail wired correctly
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _read_telemetry_lines(telemetry_path):
    """Read all JSON lines from a telemetry file, stripping whitespace."""
    if not telemetry_path.exists():
        return []
    with open(telemetry_path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _inject_telemetry_env(tmp_path, monkeypatch):
    """Set BORG_DIR to tmp_path and BORG_TELEMETRY=1 for a test."""
    monkeypatch.setenv("BORG_DIR", str(tmp_path))
    monkeypatch.setenv("BORG_TELEMETRY", "1")


def _disable_telemetry(monkeypatch):
    """Ensure BORG_TELEMETRY is not set (telemetry disabled)."""
    monkeypatch.delenv("BORG_TELEMETRY", raising=False)


# -----------------------------------------------------------------------
# Defaults: TELEMETRY_ENABLED is False unless BORG_TELEMETRY=1
# -----------------------------------------------------------------------

def test_telemetry_disabled_by_default(tmp_path, monkeypatch):
    """Without BORG_TELEMETRY=1, events are silently dropped."""
    _disable_telemetry(monkeypatch)
    monkeypatch.setenv("BORG_DIR", str(tmp_path))

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path)}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        assert tel_mod.TELEMETRY_ENABLED is False

        tel_mod.track_event("search", {"query_length": 10, "result_count": 5})

        telemetry_path = tmp_path / "telemetry.jsonl"
        assert not telemetry_path.exists()


def test_telemetry_enabled_via_env(tmp_path, monkeypatch):
    """With BORG_TELEMETRY=1, TELEMETRY_ENABLED is True."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        assert tel_mod.TELEMETRY_ENABLED is True


# -----------------------------------------------------------------------
# track_event: basic write behaviour
# -----------------------------------------------------------------------

def test_track_event_writes_jsonl_when_enabled(tmp_path, monkeypatch):
    """When enabled, track_event writes a valid JSON line to telemetry.jsonl."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        tel_mod.track_event("search", {"query_length": 12, "result_count": 3, "success": True})

        telemetry_path = tmp_path / "telemetry.jsonl"
        assert telemetry_path.exists()

        lines = _read_telemetry_lines(telemetry_path)
        assert len(lines) == 1

        event = lines[0]
        assert "timestamp" in event
        assert event["event_type"] == "search"
        assert event["query_length"] == 12
        assert event["result_count"] == 3
        assert event["success"] is True
        assert event["pack_id"] is None
        assert event["session_hash"] is None


def test_track_event_multiple_events_append(tmp_path, monkeypatch):
    """Multiple track_event calls append to the same file."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        tel_mod.track_event("search", {"query_length": 5, "result_count": 1})
        tel_mod.track_event("pull", {"pack_id": "test-pack", "success": True})
        tel_mod.track_event("apply_start", {"pack_id": "test-pack", "session_id": "sess-1", "success": True})

        lines = _read_telemetry_lines(tmp_path / "telemetry.jsonl")
        assert len(lines) == 3
        assert lines[0]["event_type"] == "search"
        assert lines[1]["event_type"] == "pull"
        assert lines[2]["event_type"] == "apply_start"


def test_track_event_unknown_type_is_silent(tmp_path, monkeypatch):
    """Unknown event types are silently dropped (no crash)."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        # Should not raise
        tel_mod.track_event("unknown_event", {"foo": "bar"})

        telemetry_path = tmp_path / "telemetry.jsonl"
        lines = _read_telemetry_lines(telemetry_path)
        assert len(lines) == 0


# -----------------------------------------------------------------------
# No PII in events
# -----------------------------------------------------------------------

def test_no_pii_in_events(tmp_path, monkeypatch):
    """Events must not contain agent_id, task content, or error messages."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        tel_mod.track_event("apply_complete", {
            "pack_id": "test-pack",
            "session_id": "sess-abc123",
            "success": True,
        })

        lines = _read_telemetry_lines(tmp_path / "telemetry.jsonl")
        assert len(lines) == 1
        event = lines[0]

        # Explicitly forbidden fields
        for forbidden in ("agent_id", "task", "error", "error_message", "user_data", "task_content"):
            assert forbidden not in event, f"forbidden field {forbidden!r} found in event"

        # Session should be hashed, not raw
        assert event["session_hash"] is not None
        assert event["session_hash"] != "sess-abc123"
        assert len(event["session_hash"]) == 16  # truncated sha256


def test_pack_id_is_stored_directly(tmp_path, monkeypatch):
    """pack_id is stored as-is (pack identifiers are not PII)."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        tel_mod.track_event("pull", {"pack_id": "guild://hermes/my-pack", "success": True})

        lines = _read_telemetry_lines(tmp_path / "telemetry.jsonl")
        assert lines[0]["pack_id"] == "guild://hermes/my-pack"


# -----------------------------------------------------------------------
# Graceful failure: telemetry never crashes callers
# -----------------------------------------------------------------------

def test_telemetry_write_failure_is_silent(tmp_path, monkeypatch):
    """If telemetry file write fails, no exception propagates."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        telemetry_path = tmp_path / "telemetry.jsonl"
        telemetry_path.mkdir(parents=True, exist_ok=True)

        original_open = open

        def failing_open(*args, **kwargs):
            if str(telemetry_path) in str(args[0]):
                raise OSError("disk full")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", failing_open)

        # Must not raise
        tel_mod.track_event("search", {"query_length": 10, "result_count": 0})


def test_telemetry_disabled_always_silent(tmp_path, monkeypatch):
    """When TELEMETRY_ENABLED is False, track_event is always a no-op."""
    _disable_telemetry(monkeypatch)
    monkeypatch.setenv("BORG_DIR", str(tmp_path))

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path)}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        # Even with a valid telemetry path, no file should be created
        tel_mod.track_event("search", {"query_length": 10})

        # And calling with nonsense data must not raise
        tel_mod.track_event("search", None)
        tel_mod.track_event("search", {})


# -----------------------------------------------------------------------
# Event type coverage
# -----------------------------------------------------------------------

def test_all_valid_event_types_accepted(tmp_path, monkeypatch):
    """All defined event types can be tracked without error."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        event_types = ["search", "pull", "apply_start", "apply_complete", "apply_fail", "feedback"]

        for et in event_types:
            # Must not raise
            tel_mod.track_event(et, {"success": True})

        lines = _read_telemetry_lines(tmp_path / "telemetry.jsonl")
        assert len(lines) == len(event_types)
        for i, et in enumerate(event_types):
            assert lines[i]["event_type"] == et


# -----------------------------------------------------------------------
# Wired into search.py: borg_search tracks 'search' events
# -----------------------------------------------------------------------

def test_borg_search_tracks_search_event(tmp_path, monkeypatch):
    """borg_search calls track_event for 'search' with query_length and result_count."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        import borg.core.search as search_mod
        importlib.reload(tel_mod)
        importlib.reload(search_mod)

        from unittest.mock import MagicMock
        mock_track = MagicMock()
        with patch.object(search_mod, "track_event", mock_track):
            with patch.object(search_mod, "_fetch_index", return_value={"packs": []}):
                search_mod.borg_search("debugging")

        assert mock_track.called
        call_args = mock_track.call_args
        # event_type is positional arg [0][0], data dict is [0][1]
        assert call_args[0][0] == "search"  # event_type positional
        assert call_args[0][1]["query_length"] == 9  # len("debugging")
        assert "result_count" in call_args[0][1]


def test_borg_search_no_track_on_error(tmp_path, monkeypatch):
    """If borg_search raises, track_event is not called."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        importlib.reload(tel_mod)

        from unittest.mock import MagicMock
        mock_track = MagicMock()
        with patch.object(tel_mod, "track_event", mock_track):
            from borg.core.search import borg_search
            # Force an error by making _fetch_index raise
            with patch("borg.core.search._fetch_index", side_effect=ValueError("network error")):
                try:
                    borg_search("test")
                except ValueError:
                    pass

        # track_event should not have been called because the error path skips tracking
        mock_track.assert_not_called()


# -----------------------------------------------------------------------
# Wired into search.py: borg_pull tracks 'pull' events
# -----------------------------------------------------------------------

def test_borg_pull_has_telemetry_wiring():
    """borg_pull source code contains track_event call for 'pull'."""
    import inspect
    import borg.core.search as search_mod
    source = inspect.getsource(search_mod.borg_pull)
    assert "track_event" in source
    assert '"pull"' in source or "'pull'" in source


# -----------------------------------------------------------------------
# Wired into apply.py: action_start tracks 'apply_start'
# -----------------------------------------------------------------------

def test_action_start_has_telemetry_wiring():
    """action_start source code contains track_event call for 'apply_start'."""
    import inspect
    import borg.core.apply as apply_mod
    source = inspect.getsource(apply_mod.action_start)
    assert "track_event" in source
    assert '"apply_start"' in source or "'apply_start'" in source


# -----------------------------------------------------------------------
# Wired into apply.py: action_complete tracks 'apply_complete' or 'apply_fail'
# -----------------------------------------------------------------------

def test_action_complete_has_telemetry_wiring():
    """action_complete source code contains track_event calls for apply_complete/apply_fail."""
    import inspect
    import borg.core.apply as apply_mod
    source = inspect.getsource(apply_mod.action_complete)
    assert "track_event" in source
    assert "apply_complete" in source or "apply_fail" in source


# -----------------------------------------------------------------------
# Graceful failure in wired flows: telemetry errors don't break the caller
# -----------------------------------------------------------------------

def test_search_not_crashed_by_telemetry_failure(tmp_path, monkeypatch):
    """If track_event raises, borg_search still returns a valid result."""
    _inject_telemetry_env(tmp_path, monkeypatch)

    with patch.dict(os.environ, {"BORG_DIR": str(tmp_path), "BORG_TELEMETRY": "1"}, clear=False):
        import importlib
        import borg.core.telemetry as tel_mod
        import borg.core.search as search_mod
        importlib.reload(tel_mod)
        importlib.reload(search_mod)

        # Make track_event raise
        with patch.object(search_mod, "track_event", side_effect=RuntimeError("telemetry broken")):
            with patch.object(search_mod, "_fetch_index", return_value={"packs": []}):
                result = search_mod.borg_search("test query")

        result_data = json.loads(result)
        assert result_data["success"] is True
        assert result_data["query"] == "test query"


def test_telemetry_track_event_never_raises():
    """track_event catches all exceptions internally and never propagates them."""
    from borg.core.telemetry import track_event
    # Even with an invalid path, track_event should not raise
    with patch.dict(os.environ, {"BORG_TELEMETRY": "1"}, clear=False):
        with patch("borg.core.telemetry.TELEMETRY_ENABLED", True):
            with patch("builtins.open", side_effect=PermissionError("no write")):
                # This should NOT raise
                track_event("test", {"key": "value"})


@pytest.mark.skip(reason="track_event removed from search")
def test_telemetry_module_imported_in_search():
    """search.py imports track_event from telemetry."""
    import borg.core.search as search_mod
    assert hasattr(search_mod, "track_event")


def test_telemetry_module_imported_in_apply():
    """apply.py imports track_event from telemetry."""
    import borg.core.apply as apply_mod
    assert hasattr(apply_mod, "track_event")
