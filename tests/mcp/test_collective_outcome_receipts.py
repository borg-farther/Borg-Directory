import json

from borg.core import collective_learning as collective_module
from borg.integrations import mcp_server


def test_borg_rescue_records_intervention_and_outcome_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.delenv("BORG_TENANT_PSEUDONYM", raising=False)

    payload = json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        source="test",
        show_guidance=False,
        session_id="session-collective",
    ))

    assert payload["success"] is True
    assert payload["intervention_id"].startswith("intervention-sha256:")
    assert payload["value_receipt"]["intervention_id"] == payload["intervention_id"]

    receipt_payload = json.loads(mcp_server.borg_record_outcome(
        intervention_id=payload["intervention_id"],
        outcome="success",
        helpful=True,
        verified=True,
        verification_command="python -c 'import flask'",
        tenant_pseudonym="local",
        agent_id="agent-a",
        time_saved_minutes=3.0,
        tokens_saved=500,
        dead_ends_avoided=2,
    ))

    assert receipt_payload["success"] is True
    receipt = receipt_payload["receipt"]
    assert receipt["receipt_id"].startswith("outcome-sha256:")
    assert receipt["intervention_id"] == payload["intervention_id"]
    assert receipt["helpful"] is True
    assert receipt["verified"] is True


def test_borg_record_outcome_can_use_last_session_intervention(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.delenv("BORG_TENANT_PSEUDONYM", raising=False)
    json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        source="test",
        show_guidance=False,
        session_id="session-last",
    ))

    receipt_payload = json.loads(mcp_server.borg_record_outcome(
        outcome="partial",
        helpful=True,
        verified=True,
        verification_command="manual verification",
        tenant_pseudonym="local",
        agent_id="agent-b",
        session_id="session-last",
    ))

    assert receipt_payload["success"] is True
    assert receipt_payload["recorded"] is True


def test_borg_record_outcome_defaults_to_configured_tenant_env(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.setenv("BORG_TENANT_PSEUDONYM", "tenant-acme")
    session_id = "session-tenant-env"

    payload = json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        source="test",
        show_guidance=False,
        session_id=session_id,
    ))
    assert payload["success"] is True

    receipt_payload = json.loads(mcp_server.call_tool("borg_record_outcome", {
        "outcome": "success",
        "helpful": True,
        "verified": True,
        "verification_command": "python -c 'import flask'",
        "agent_id": "agent-env",
        "session_id": session_id,
    }))

    assert receipt_payload["success"] is True
    assert receipt_payload["recorded"] is True
    assert receipt_payload["receipt"]["tenant_pseudonym"].startswith("hmac-sha256:")


def test_borg_record_outcome_without_intervention_requires_explicit_session(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    with mcp_server._collective_intervention_lock:
        mcp_server._last_collective_intervention_by_session.clear()

    payload = json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        source="test",
        show_guidance=False,
    ))
    assert payload["success"] is True

    receipt_payload = json.loads(mcp_server.borg_record_outcome(
        outcome="success",
        helpful=True,
        verified=True,
        verification_command="python -c 'import flask'",
    ))

    assert receipt_payload["success"] is False
    assert "session_id is required" in receipt_payload["error"]

    call_payload = json.loads(mcp_server.call_tool("borg_record_outcome", {
        "outcome": "success",
        "helpful": True,
        "verified": True,
        "verification_command": "python -c 'import flask'",
    }))
    assert call_payload["success"] is False
    assert "session_id is required" in call_payload["error"]


def test_borg_record_outcome_rejects_unshown_atom_id(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    monkeypatch.delenv("BORG_TENANT_PSEUDONYM", raising=False)
    payload = json.loads(mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        source="test",
        show_guidance=False,
        session_id="session-unshown-atom",
    ))

    receipt_payload = json.loads(mcp_server.borg_record_outcome(
        intervention_id=payload["intervention_id"],
        outcome="success",
        helpful=True,
        verified=True,
        verification_command="python -c 'import flask'",
        atom_id="sha256:" + "e" * 64,
    ))

    assert receipt_payload["success"] is False
    assert "source_refs" in receipt_payload["error"]


def test_borg_collective_retrieve_returns_advisory_summary_not_raw_atom(monkeypatch):
    def fake_retrieve(query, limit=5):
        return [
            {
                "source": "learning_atom",
                "atom_id": "sha256:" + "a" * 64,
                "cluster_id": "cluster:debug:python",
                "score": 0.91,
                "score_reasons": ["text_match", "verified_quorum"],
                "verified_tenant_count": 3,
                "helpfulness_score": 0.8,
                "helpful_outcomes": 3,
                "unhelpful_outcomes": 1,
                "atom": {
                    "learning": {
                        "worked": "Install Flask in the active venv",
                        "avoid": ["Do not reinstall Python"],
                        "why": "Verified by outcomes",
                    },
                    "safety": {"retrieval_treatment": "untrusted_advisory"},
                    "trust": {"independent_tenant_count": 999, "verified_tenant_count": 3},
                },
            }
        ]

    monkeypatch.setattr(collective_module, "unified_collective_retrieve", fake_retrieve)

    payload = json.loads(mcp_server.borg_collective_retrieve("flask", limit=1))

    assert payload["success"] is True
    assert payload["matches"]
    match = payload["matches"][0]
    assert "atom" not in match
    assert match["retrieval_treatment"] == "untrusted_advisory"
    assert match["advisory"]["worked"] == "Install Flask in the active venv"
    assert match["advisory"]["avoid"] == ["Do not reinstall Python"]
    assert match["advisory"]["why"] == "Verified by outcomes"
