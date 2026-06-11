"""MCP-path tests for value-receipt schema v2 (gate #10): borg_rescue carries the
failure_count/trigger signal into the receipt, borg_suggest records the
2+-consecutive-failures rescue, and nothing raw-secret ever reaches disk."""

from __future__ import annotations

import json

from borg.integrations import mcp_server
from borg.core.value_receipts import _db_path, replayable_receipts, value_summary

_SECRET = "AKIAIOSFODNN7EXAMPLEKEY99"


def _home(tmp_path, monkeypatch):
    home = tmp_path / "borg-home"
    monkeypatch.setenv("BORG_HOME", str(home))
    monkeypatch.delenv("BORG_TENANT_PSEUDONYM", raising=False)
    return home


def test_borg_rescue_failure_count_records_after_n_failures(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path, monkeypatch)

    payload = json.loads(mcp_server.borg_rescue(
        input=f"TypeError: unsupported operand type(s) token={_SECRET}",
        show_guidance=False,
        failure_count=3,
    ))
    assert payload["success"] is True

    [receipt] = replayable_receipts(borg_home=home)
    assert receipt["trigger"] == "after_n_failures"
    assert receipt["trigger_n"] == 3
    assert _SECRET.encode() not in _db_path(home).read_bytes()
    assert value_summary(borg_home=home)["caught_after_stuck"] == 1


def test_borg_rescue_explicit_trigger_wins_over_failure_count(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path, monkeypatch)
    mcp_server.borg_rescue(
        input="PermissionError: [Errno 13] Permission denied",
        show_guidance=False,
        trigger="task_start",
    )
    summary = value_summary(borg_home=home)
    assert summary["by_trigger"] == {"task_start": 1}
    assert summary["caught_after_stuck"] == 0


def test_borg_rescue_default_trigger_is_unknown(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path, monkeypatch)
    mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask", show_guidance=False
    )
    assert value_summary(borg_home=home)["by_trigger"] == {"unknown": 1}


def test_dispatch_path_forwards_failure_count_and_trigger(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path, monkeypatch)
    out = json.loads(mcp_server._call_tool_impl("borg_rescue", {
        "input": "ModuleNotFoundError: No module named flask",
        "failure_count": 4,
    }))
    assert out["success"] is True
    [receipt] = replayable_receipts(borg_home=home)
    assert receipt["trigger"] == "after_n_failures"
    assert receipt["trigger_n"] == 4


def test_rescue_descriptor_advertises_failure_count_and_trigger() -> None:
    [descriptor] = [t for t in mcp_server.TOOLS if t["name"] == "borg_rescue"]
    props = descriptor["inputSchema"]["properties"]
    assert props["failure_count"]["type"] == "integer"
    assert "trigger" in props


def test_borg_suggest_records_caught_after_stuck_receipt(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path, monkeypatch)

    class _FakeV3:
        def search(self, context, task_context=None):
            return [{"name": "django-migration-rescue", "description": "fix desync", "score": 0.9}]

    monkeypatch.setattr(mcp_server, "_get_borg_v3", lambda: _FakeV3())

    payload = json.loads(mcp_server.borg_suggest(
        context=f"django migration keeps failing InconsistentMigrationHistory pwd={_SECRET}",
        failure_count=2,
    ))
    assert payload["has_suggestion"] is True

    [receipt] = replayable_receipts(borg_home=home)
    assert receipt["trigger"] == "after_n_failures"
    assert receipt["trigger_n"] == 2
    assert receipt["provenance"] == "pack_suggestion"
    assert _SECRET.encode() not in _db_path(home).read_bytes()
    assert value_summary(borg_home=home)["caught_after_stuck"] == 1


def test_borg_suggest_below_threshold_records_nothing(tmp_path, monkeypatch) -> None:
    home = _home(tmp_path, monkeypatch)
    mcp_server.borg_suggest(context="some mild frustration", failure_count=1)
    assert value_summary(borg_home=home)["rescues_fired"] == 0
    assert not _db_path(home).exists()
