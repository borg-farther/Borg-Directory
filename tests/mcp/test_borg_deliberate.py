from __future__ import annotations

import json

from borg import deliberate as public_deliberate
from borg.core import epistemic_guardrail
from borg.integrations import mcp_server


def no_memory(*args):
    return []


def test_mcp_schema_exposes_bounded_deliberation_contract() -> None:
    tool = next(item for item in mcp_server.TOOLS if item["name"] == "borg_deliberate")
    schema = tool["inputSchema"]
    assert schema["required"] == ["task"]
    assert schema["properties"]["mode"]["enum"] == ["auto", "standard", "deep"]
    assert schema["properties"]["stage"]["enum"] == ["preflight", "review"]
    assert "memory_items" not in schema["properties"]
    assert "session_id" in schema["properties"]
    assert "chain-of-thought" in tool["description"]


def test_mcp_deliberate_records_intervention_and_returns_packet(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)

    raw = mcp_server.borg_deliberate(
        task="review the production release",
        mode="deep",
        agent_id="test-agent",
        session_id="session-1",
    )
    payload = json.loads(raw)
    assert payload["success"] is True
    packet = payload["epistemic_packet"]
    assert packet["mode_selected"] == "deep"
    assert packet["memory_status"] == "no_confident_match"
    assert packet["outcome_capture"]["status"] == "recorded_local"
    assert packet["outcome_capture"]["intervention_id"].startswith("intervention-sha256:")
    assert packet["outcome_capture"]["cluster_id"]
    assert "NO_CONFIDENT_MATCH" in payload["text"]


def test_mcp_high_risk_unsupported_claim_blocks(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    raw = mcp_server.borg_deliberate(
        task="approve production release",
        stage="review",
        risk_level="high",
        claims=[{"id": "c1", "text": "The release is safe", "material": True}],
    )
    packet = json.loads(raw)["epistemic_packet"]
    assert packet["decision"] == "block_pending_verification"
    assert packet["unsupported_claims"] == ["c1"]


def test_dispatch_routes_all_structured_inputs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    raw = mcp_server._call_tool_impl(
        "borg_deliberate",
        {
            "task": "review release",
            "stage": "review",
            "risk_level": "medium",
            "claims": [{"id": "c1", "text": "Tests pass", "evidence_refs": ["e1"]}],
            "evidence": [{"id": "e1", "type": "test_result", "source": "ci://1", "verified": True}],
            "_hermes_session_id": "hermes-session-1",
        },
    )
    packet = json.loads(raw)["epistemic_packet"]
    assert packet["decision"] == "proceed"
    assert packet["claims"][0]["support_status"] == "verified_evidence_present"
    assert packet["outcome_capture"]["intervention_id"]


def test_python_api_and_mcp_share_core_semantics(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    direct = public_deliberate("rename a local variable", mode="auto").to_dict()
    via_mcp = json.loads(
        mcp_server.borg_deliberate(task="rename a local variable", mode="auto")
    )["epistemic_packet"]
    for field in (
        "schema_version",
        "packet_id",
        "status",
        "mode_requested",
        "mode_selected",
        "decision",
        "memory_status",
        "verification_plan",
        "claim_boundaries",
    ):
        assert via_mcp[field] == direct[field]


def test_empty_task_is_structured_invalid_input(monkeypatch) -> None:
    monkeypatch.setattr(epistemic_guardrail, "_default_memory_provider", no_memory)
    payload = json.loads(mcp_server.borg_deliberate(task=""))
    assert payload["success"] is False
    assert payload["epistemic_packet"]["decision"] == "invalid_input"
    assert "intervention_id" not in payload["epistemic_packet"]["outcome_capture"]
