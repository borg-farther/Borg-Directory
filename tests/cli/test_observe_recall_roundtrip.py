"""observe -> recall roundtrip (confirmed broken pre-fix): an observed failure
was stored in traces.db (searchable) but `borg recall` read only the failure-
memory YAML store, which nothing on the observe path ever wrote — so recall
answered "No prior failures recorded" for an error the system knew about.

The fix is two-sided: observe (CLI + MCP trace save) now bridges errors into
failure memory, and recall (CLI + MCP) falls back across agent namespaces and
then to traces.db for observations recorded before the bridge."""

from __future__ import annotations

import json
import sys

import pytest

from borg.cli import main
from borg.core.failure_memory import FailureMemory


def _run(argv, borg_home, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(borg_home))
    monkeypatch.setattr(sys, "argv", ["borg", *argv])
    return main()


ERROR = "OperationalError: no such column: users.legacy_flag"


def test_cli_observe_then_recall_finds_the_failure(tmp_path, monkeypatch, capsys):
    _run(["observe", "migrate", "user", "schema", "--error", ERROR,
          "--context", "tried renaming the column in models only"], tmp_path, monkeypatch)
    capsys.readouterr()

    assert _run(["recall", ERROR], tmp_path, monkeypatch) == 0
    out = capsys.readouterr().out
    assert "No prior failures recorded" not in out
    assert "Wrong approaches" in out
    assert "renaming the column" in out


def test_failure_memory_resolves_borg_home_at_init(tmp_path, monkeypatch):
    # The class attribute froze BORG_HOME at import time; a late override
    # silently wrote to the wrong home. Init-time resolution fixes that.
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "late-home"))
    fm = FailureMemory()
    assert str(tmp_path / "late-home") in str(fm.memory_dir)


def test_recall_crosses_agent_namespaces(tmp_path, monkeypatch, capsys):
    # CLI observe records under 'cli'; a recall against another namespace must
    # still find it (the original mismatch: observe ns != recall ns).
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    FailureMemory(agent_id="some-agent").record_failure(
        error_pattern=ERROR, pack_id="observed", phase="observe",
        approach="blind retry", outcome="failure",
    )
    assert FailureMemory(agent_id="default").recall(ERROR) is None  # own ns: miss
    result = FailureMemory(agent_id="default").recall_across_agents(ERROR)
    assert result is not None
    assert result["wrong_approaches"][0]["approach"] == "blind retry"


def test_recall_falls_back_to_traces_for_pre_bridge_observations(tmp_path, monkeypatch, capsys):
    # Simulate a pre-fix observation: trace exists, failure memory is empty.
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.core.traces import TraceCapture, save_trace

    capture = TraceCapture(task="fix login migration", agent_id="cli")
    capture.on_tool_call("observe", {"task": "fix login migration"}, ERROR)
    trace = capture.extract_trace(outcome="observed", approach_summary="tried column rename")
    save_trace(trace)

    assert _run(["recall", ERROR], tmp_path, monkeypatch) == 0
    out = capsys.readouterr().out
    assert "No prior failures recorded" not in out
    assert "prior observed trace" in out
    assert "fix login migration" in out


def test_recall_still_honest_when_nothing_matches(tmp_path, monkeypatch, capsys):
    assert _run(["recall", "CompletelyUnknownError: never seen before xyzzy"], tmp_path, monkeypatch) == 0
    assert "No prior failures recorded" in capsys.readouterr().out


def test_mcp_observe_recall_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.integrations import mcp_server
    from borg.core.traces import TraceCapture

    capture = TraceCapture(task="deploy borg worker", agent_id="default")
    capture.on_tool_call("run", {"cmd": "deploy"}, ERROR)
    trace = capture.extract_trace(
        outcome="failure", root_cause="schema drift between envs",
        approach_summary="redeployed without migrating",
    )
    assert mcp_server._save_trace_if_meaningful(trace) is True

    payload = json.loads(mcp_server.borg_recall(error_message=ERROR))
    assert payload["success"] is True
    assert payload["found"] is True
    assert payload["source"] == "failure_memory"
    assert any(
        "redeployed without migrating" in entry.get("approach", "")
        for entry in payload["wrong_approaches"]
    )


def test_mcp_recall_traces_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    from borg.integrations import mcp_server
    from borg.core.traces import TraceCapture, save_trace

    capture = TraceCapture(task="configure redis cache", agent_id="cli")
    capture.on_tool_call("observe", {}, "ConnectionRefusedError: redis 6379 unreachable")
    save_trace(capture.extract_trace(outcome="observed", approach_summary="checked firewall"))

    payload = json.loads(
        mcp_server.borg_recall(error_message="ConnectionRefusedError: redis 6379 unreachable")
    )
    assert payload["success"] is True
    assert payload["found"] is True
    assert payload["source"] == "traces"
    assert payload["observed_traces"][0]["task"].startswith("configure redis")


def test_mcp_record_outcome_closes_value_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path))
    monkeypatch.delenv("BORG_TENANT_PSEUDONYM", raising=False)
    from borg.integrations import mcp_server
    from borg.core.value_receipts import replayable_receipts

    rescue = json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        show_guidance=False, failure_count=2,
    ))
    assert rescue["success"] is True

    outcome = json.loads(mcp_server.borg_record_outcome(
        intervention_id=rescue["intervention_id"], outcome="success",
        helpful=True, verified=True, verification_command="python -c 'import flask'",
        tenant_pseudonym="local", agent_id="agent-a",
    ))
    assert outcome["success"] is True
    assert outcome["value_receipt_outcome_id"] == 1

    [receipt] = replayable_receipts(borg_home=tmp_path)
    assert receipt["replay_context"]["outcome"] == "worked"
