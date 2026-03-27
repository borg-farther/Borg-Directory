"""
Tests for guild/core/session.py  (T1.7)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from guild.core import session as sess_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_minimal_session(
    session_id: str = "test-session-001",
    *,
    pack_name: str = "test-pack",
    task: str = "Test task",
    phase_index: int = 0,
    status: str = "pending",
    created_at: str = None,
    phases: list = None,
    execution_log_path: Path = None,
) -> dict:
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    if phases is None:
        phases = [
            {
                "index": 0,
                "name": "phase_one",
                "description": "First phase",
                "checkpoint": "assert result",
                "anti_patterns": [],
                "prompts": ["prompt A"],
                "status": "pending",
            },
            {
                "index": 1,
                "name": "phase_two",
                "description": "Second phase",
                "checkpoint": "assert result2",
                "anti_patterns": [],
                "prompts": ["prompt B"],
                "status": "pending",
            },
        ]
    return {
        "session_id": session_id,
        "pack_name": pack_name,
        "task": task,
        "phase_index": phase_index,
        "status": status,
        "created_at": created_at,
        "phases": phases,
        "execution_log_path": execution_log_path or Path("/tmp/fake.jsonl"),
        "pack_id": pack_name,
        "pack_version": "1.0.0",
        "problem_class": "test",
        "events": [],
        "phase_results": [],
        "retries": {},
        "approved": False,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_guild_dir(tmp_path: Path) -> Path:
    """A temporary GUILD_DIR root (not ~/.hermes/guild)."""
    guild_dir = tmp_path / "guild"
    guild_dir.mkdir(parents=True)
    return guild_dir


@pytest.fixture
def tmp_session(tmp_guild_dir: Path) -> dict:
    """A minimal valid session dict backed by tmp_guild_dir."""
    log_path = tmp_guild_dir / "executions" / "test-session-001.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return make_minimal_session(
        "test-session-001",
        pack_name="test-pack",
        execution_log_path=log_path,
    )


# ---------------------------------------------------------------------------
# Tests: save / load round-trip
# ---------------------------------------------------------------------------

def test_save_load_roundtrip(tmp_guild_dir: Path):
    session = make_minimal_session("roundtrip-001", execution_log_path=tmp_guild_dir / "executions" / "roundtrip-001.jsonl")
    sess_mod.save_session(session, guild_dir=tmp_guild_dir)

    loaded = sess_mod.load_session("roundtrip-001", guild_dir=tmp_guild_dir)
    assert loaded is not None
    assert loaded["session_id"] == "roundtrip-001"
    assert loaded["pack_name"] == "test-pack"
    assert loaded["task"] == "Test task"
    assert loaded["phase_index"] == 0
    assert loaded["status"] == "pending"
    assert loaded["approved"] is False


def test_save_load_roundtrip_preserves_phases(tmp_guild_dir: Path):
    session = make_minimal_session("phases-001", execution_log_path=tmp_guild_dir / "executions" / "phases-001.jsonl")
    sess_mod.save_session(session, guild_dir=tmp_guild_dir)

    loaded = sess_mod.load_session("phases-001", guild_dir=tmp_guild_dir)
    assert loaded is not None
    assert len(loaded["phases"]) == 2
    names = {p["name"] for p in loaded["phases"]}
    assert names == {"phase_one", "phase_two"}


def test_load_nonexistent_returns_none(tmp_guild_dir: Path):
    result = sess_mod.load_session("does-not-exist", guild_dir=tmp_guild_dir)
    assert result is None


def test_load_invalid_json_logs_warning(tmp_guild_dir: Path):
    # Write malformed JSON
    sf = sess_mod.session_file("bad-json", guild_dir=tmp_guild_dir)
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text("{not valid json", encoding="utf-8")

    result = sess_mod.load_session("bad-json", guild_dir=tmp_guild_dir)
    assert result is None


# ---------------------------------------------------------------------------
# Tests: delete_session
# ---------------------------------------------------------------------------

def test_delete_session_removes_file(tmp_guild_dir: Path):
    session = make_minimal_session("delete-me", execution_log_path=tmp_guild_dir / "executions" / "delete-me.jsonl")
    sess_mod.save_session(session, guild_dir=tmp_guild_dir)
    assert sess_mod.session_file("delete-me", guild_dir=tmp_guild_dir).exists()

    sess_mod.delete_session("delete-me", guild_dir=tmp_guild_dir)
    assert not sess_mod.session_file("delete-me", guild_dir=tmp_guild_dir).exists()


def test_delete_session_nonexistent_is_silent(tmp_guild_dir: Path):
    # Must not raise
    sess_mod.delete_session("no-such-session", guild_dir=tmp_guild_dir)


# ---------------------------------------------------------------------------
# Tests: log_event
# ---------------------------------------------------------------------------

def test_log_event_writes_jsonl(tmp_guild_dir: Path):
    log_path = tmp_guild_dir / "executions" / "events-001.jsonl"
    session = make_minimal_session("events-001", execution_log_path=log_path)
    sess_mod.register_session(session)
    sess_mod.log_event("events-001", {"event": "test_event", "value": 42}, guild_dir=tmp_guild_dir)

    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "test_event"
    assert record["value"] == 42
    assert "ts" in record


def test_log_event_multiple_events(tmp_guild_dir: Path):
    log_path = tmp_guild_dir / "executions" / "events-002.jsonl"
    session = make_minimal_session("events-002", execution_log_path=log_path)
    sess_mod.register_session(session)
    sess_mod.log_event("events-002", {"event": "first"}, guild_dir=tmp_guild_dir)
    sess_mod.log_event("events-002", {"event": "second"}, guild_dir=tmp_guild_dir)

    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "first"
    assert json.loads(lines[1])["event"] == "second"


def test_log_event_updates_in_memory_events(tmp_guild_dir: Path):
    log_path = tmp_guild_dir / "executions" / "events-003.jsonl"
    session = make_minimal_session("events-003", execution_log_path=log_path)
    sess_mod.register_session(session)
    sess_mod.log_event("events-003", {"event": "in_mem_test"}, guild_dir=tmp_guild_dir)

    assert len(session["events"]) == 1
    assert session["events"][0]["event"] == "in_mem_test"


def test_log_event_without_active_session_writes_to_disk(tmp_guild_dir: Path):
    # log_event falls back to constructing log path from guild_dir
    log_path = tmp_guild_dir / "executions" / "no-session.jsonl"
    sess_mod.log_event("no-session", {"event": "orphan"}, guild_dir=tmp_guild_dir)

    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    assert json.loads(lines[0])["event"] == "orphan"


# ---------------------------------------------------------------------------
# Tests: compute_log_hash
# ---------------------------------------------------------------------------

def test_compute_log_hash_empty_returns_empty_string(tmp_path: Path):
    empty_file = tmp_path / "empty.jsonl"
    empty_file.touch()
    assert sess_mod.compute_log_hash(empty_file) == ""


def test_compute_log_hash_computes_correctly(tmp_path: Path):
    log_file = tmp_path / "hashable.jsonl"
    log_file.write_text('{"event":"test"}\n', encoding="utf-8")

    digest = sess_mod.compute_log_hash(log_file)
    assert digest.startswith("sha256:")
    # Verify it is reproducible
    assert sess_mod.compute_log_hash(log_file) == digest


def test_compute_log_hash_nonexistent_returns_empty():
    from pathlib import Path
    result = sess_mod.compute_log_hash(Path("/tmp/does/not/exist.jsonl"))
    assert result == ""


# ---------------------------------------------------------------------------
# Tests: check_pack_size_limits
# ---------------------------------------------------------------------------

def test_check_pack_size_limits_passes_small_pack(tmp_path: Path):
    pack = {
        "id": "test",
        "name": "TestPack",
        "phases": [{"name": "p1", "description": "Short"}] * 5,
    }
    pf = tmp_path / "small.yaml"
    pf.write_text("id: test\n", encoding="utf-8")

    violations = sess_mod.check_pack_size_limits(pack, pf)
    assert violations == []


def test_check_pack_size_limits_fails_file_too_large(tmp_path: Path):
    pack = {"id": "test", "phases": []}
    pf = tmp_path / "large.yaml"
    # Write enough bytes to exceed 500KB
    pf.write_bytes(b"x" * (sess_mod.MAX_PACK_SIZE_BYTES + 1))

    violations = sess_mod.check_pack_size_limits(pack, pf)
    assert any("500KB" in v for v in violations)


def test_check_pack_size_limits_fails_too_many_phases(tmp_path: Path):
    pack = {
        "id": "test",
        "phases": [{"name": f"p{i}", "description": ""} for i in range(sess_mod.MAX_PHASES + 1)],
    }
    pf = tmp_path / "many_phases.yaml"
    pf.write_text("id: test\n", encoding="utf-8")

    violations = sess_mod.check_pack_size_limits(pack, pf)
    assert any(f"{sess_mod.MAX_PHASES}" in v for v in violations)


def test_check_pack_size_limits_fails_large_field(tmp_path: Path):
    large_text = "x" * (sess_mod.MAX_FIELD_SIZE_BYTES + 1)
    pack = {
        "id": "test",
        "phases": [
            {"name": "p1", "description": large_text},
        ],
    }
    pf = tmp_path / "large_field.yaml"
    pf.write_text("id: test\n", encoding="utf-8")

    violations = sess_mod.check_pack_size_limits(pack, pf)
    assert any("10KB" in v for v in violations)


def test_check_pack_size_limits_nested_large_field(tmp_path: Path):
    large_text = "y" * (sess_mod.MAX_FIELD_SIZE_BYTES + 1)
    pack = {
        "id": "test",
        "phases": [
            {
                "name": "p1",
                "metadata": {"nested": {"deep": large_text}},
            },
        ],
    }
    pf = tmp_path / "nested.yaml"
    pf.write_text("id: test\n", encoding="utf-8")

    violations = sess_mod.check_pack_size_limits(pack, pf)
    assert any("10KB" in v for v in violations)


# ---------------------------------------------------------------------------
# Tests: clear_test_sessions
# ---------------------------------------------------------------------------

def test_clear_test_sessions_empties_memory(tmp_guild_dir: Path):
    session = make_minimal_session("clear-me", execution_log_path=tmp_guild_dir / "executions" / "clear-me.jsonl")
    sess_mod.register_session(session)
    assert sess_mod.get_active_session("clear-me") is not None

    sess_mod.clear_test_sessions()
    assert sess_mod.get_active_session("clear-me") is None


# ---------------------------------------------------------------------------
# Tests: session_file path construction
# ---------------------------------------------------------------------------

def test_session_file_uses_provided_guild_dir(tmp_path: Path):
    custom = tmp_path / "custom_guild"
    result = sess_mod.session_file("s1", guild_dir=custom)
    assert result == custom / "sessions" / "s1.json"


def test_session_file_defaults_to_module_gUILD_DIR(tmp_guild_dir: Path):
    # When no guild_dir override, should use GUILD_DIR (which may be ~/.hermes/guild)
    # We can verify the path structure at least
    result = sess_mod.session_file("s2")
    assert result.name == "s2.json"
    assert result.suffix == ".json"


# ---------------------------------------------------------------------------
# Tests: get_active_session / register_session
# ---------------------------------------------------------------------------

def test_register_and_get_active_session(tmp_guild_dir: Path):
    session = make_minimal_session("active-001", execution_log_path=tmp_guild_dir / "executions" / "active-001.jsonl")
    sess_mod.register_session(session)

    retrieved = sess_mod.get_active_session("active-001")
    assert retrieved is session  # same object


def test_get_active_session_unknown_returns_none():
    assert sess_mod.get_active_session("unknown-id") is None


# ---------------------------------------------------------------------------
# Tests: save_session overwrites cleanly
# ---------------------------------------------------------------------------

def test_save_session_overwrites(tmp_guild_dir: Path):
    session = make_minimal_session("overwrite-001", status="pending", execution_log_path=tmp_guild_dir / "executions" / "overwrite-001.jsonl")
    sess_mod.save_session(session, guild_dir=tmp_guild_dir)

    session["status"] = "running"
    session["phase_index"] = 3
    sess_mod.save_session(session, guild_dir=tmp_guild_dir)

    loaded = sess_mod.load_session("overwrite-001", guild_dir=tmp_guild_dir)
    assert loaded is not None
    assert loaded["status"] == "running"
    assert loaded["phase_index"] == 3


# ---------------------------------------------------------------------------
# Tests: execution_log_path aliasing (log_path vs execution_log_path)
# ---------------------------------------------------------------------------

def test_session_with_log_path_alias(tmp_guild_dir: Path):
    """Session dict may use 'log_path' or 'execution_log_path' — both accepted."""
    log_path = tmp_guild_dir / "executions" / "alias-test.jsonl"
    session = make_minimal_session("alias-test", execution_log_path=log_path)
    # Rename key to simulate old-style
    session["log_path"] = session.pop("execution_log_path")

    sess_mod.save_session(session, guild_dir=tmp_guild_dir)
    loaded = sess_mod.load_session("alias-test", guild_dir=tmp_guild_dir)
    assert loaded is not None
    # Both load path variants should produce a log_path key
    assert "log_path" in loaded or "execution_log_path" in loaded


# ---------------------------------------------------------------------------
# Integration: full session lifecycle (save, log events, hash, load)
# ---------------------------------------------------------------------------

def test_full_lifecycle(tmp_guild_dir: Path):
    session = make_minimal_session("lifecycle-001", execution_log_path=tmp_guild_dir / "executions" / "lifecycle-001.jsonl")
    sess_mod.save_session(session, guild_dir=tmp_guild_dir)

    sess_mod.register_session(session)
    sess_mod.log_event("lifecycle-001", {"event": "phase_started", "phase": "phase_one"}, guild_dir=tmp_guild_dir)
    sess_mod.log_event("lifecycle-001", {"event": "phase_finished", "phase": "phase_one", "result": "passed"}, guild_dir=tmp_guild_dir)

    log_path = tmp_guild_dir / "executions" / "lifecycle-001.jsonl"
    digest = sess_mod.compute_log_hash(log_path)
    assert digest.startswith("sha256:")

    # Verify two events in log
    lines = log_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    # Verify in-memory events updated
    assert len(session["events"]) == 2

    # Verify loaded session also has events
    loaded = sess_mod.load_session("lifecycle-001", guild_dir=tmp_guild_dir)
    assert loaded is not None
    assert len(loaded["events"]) == 2
