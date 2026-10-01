"""First-10 beta readiness contract tests.

These tests lock the launch-critical behavior AB requested before external
users: fail-closed retrieval, explicit confidence, ACTION/STOP/VERIFY shape,
truthful beta packet, and docs/security linkage.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval import first_10_evidence as evidence
from borg.core.first_user_readiness import (
    FIRST_10_GATES,
    PRIMING_PARAGRAPH,
    first_10_readiness_packet,
    render_first_10_readiness_markdown,
)
from borg.integrations import mcp_server

ROOT = Path(__file__).resolve().parents[2]


def test_first_10_contract_has_all_seven_binary_gates():
    packet = first_10_readiness_packet()

    assert packet["success"] is True
    assert packet["status"] == "first_10_beta_contract"
    assert "6 of the first 10" in packet["success_metric"]
    assert len(packet["gates"]) == 7
    assert [gate["id"] for gate in packet["gates"]] == [f"G{i}" for i in range(1, 8)]
    for gate in packet["gates"]:
        assert gate["title"]
        assert gate["pass_criteria"]
        assert gate["proof"]


def test_first_10_packet_contains_install_mcp_feedback_and_priming():
    packet = first_10_readiness_packet()
    commands = "\n".join(packet["smoke_commands"])

    assert "python3 -m pip install agent-borg==" in commands
    assert "borg-doctor --json" in commands
    assert "borg rescue" in commands
    assert "BORGFIRST10_UNKNOWN_CONTROL_v1" in commands
    assert "borg agent-stack --json" in commands
    assert "borg setup-claude --scope user --verify --fix" in commands
    assert packet["study_protocol"]["protocol_id"] == "borg-rescue-first10-v1"
    assert packet["study_protocol"]["artifact"].startswith("agent-borg==")
    assert packet["study_protocol"]["unknown_control_expected_status"] == "no_confident_match"
    assert packet["study_protocol"]["failed_installs_remain_in_denominator"] is True
    assert "borg first-10 --json" in commands
    assert "borg collective summary --json" in commands
    stack = packet["minimum_capable_agent_stack"]
    assert stack["status"] == "minimum_capable_agent_stack"
    assert len(stack["levers"]) == 7
    assert stack["commands"]["inspect"] == "borg agent-stack --json"
    assert "borg_rescue" in packet["priming_paragraph"]
    assert "borg_observe" in packet["priming_paragraph"]
    assert "borg_record_outcome" in packet["priming_paragraph"]
    assert "borg_feedback" in packet["priming_paragraph"]
    assert "borg_record_failure" in packet["priming_paragraph"]
    assert "borg_rate" not in packet["priming_paragraph"]
    assert "did_it_prevent_a_dead_end" in packet["feedback_fields"]
    assert "baseline_minutes_without_borg" in packet["feedback_fields"]
    assert "actual_minutes_with_borg" in packet["feedback_fields"]
    assert "net_minutes_saved" in packet["feedback_fields"]
    assert "baseline_tokens_without_borg" in packet["feedback_fields"]
    assert "actual_tokens_with_borg" in packet["feedback_fields"]
    assert "net_tokens_saved" in packet["feedback_fields"]
    assert "savings_counterfactual_basis" in packet["feedback_fields"]
    assert "user_confirmed_value" in packet["feedback_fields"]
    assert "intervention_id" in packet["feedback_fields"]
    assert "outcome_receipt_id" in packet["feedback_fields"]
    assert "contribution_event_id" in packet["feedback_fields"]
    assert any("value_receipt" in item for gate in packet["gates"] for item in gate["pass_criteria"])
    mixes = "\n".join(packet["supported_mixes"])
    assert "Hermes" in mixes
    assert "ChatGPT/OpenAI" in mixes
    assert "Claude Code" in mixes
    assert "Human only" in mixes


def test_first_10_markdown_is_human_readable_and_not_theatre():
    md = render_first_10_readiness_markdown()

    assert "Borg First-10 Beta Readiness Contract" in md
    assert "NO-GO" in md
    assert "NO_CONFIDENT_MATCH" in md
    assert "ACTION/STOP/VERIFY" in md
    assert "Supported first-user mixes" in md
    assert "Minimum capable agent host stack" in md
    assert "borg agent-stack --json" in md
    assert "ChatGPT/OpenAI" in md
    assert "Hermes" in md
    assert "vanity" not in md.lower() or "test count" in md.lower()


def test_trace_match_confidence_rejects_weak_and_empty_hits():
    assert mcp_server._trace_match_is_confident({"similarity": 0.44, "approach_summary": "real fix"}) is False
    assert mcp_server._trace_match_is_confident({"similarity": 0.91}) is False
    assert mcp_server._trace_match_is_confident({"match_score": 0, "approach_summary": "real fix"}) is False
    assert mcp_server._trace_match_is_confident({"similarity": 0.91, "causal_intervention": "pin pydantic v2"}) is True


def test_pack_confidence_rejects_unrelated_permission_pack_for_readiness_question():
    permission_pack = {
        "name": "bash-permission-denied",
        "problem_class": "permission_denied",
        "tags": ["chmod", "eacces"],
    }

    assert mcp_server._pack_match_is_confident(
        "borg first 10 users readiness confidence retrieval docs security beta",
        permission_pack,
    ) is False
    assert mcp_server._pack_match_is_confident(
        "PermissionError EACCES chmod failing on deploy",
        permission_pack,
    ) is True


def test_no_confident_match_response_has_first_user_contract_shape():
    text = mcp_server._no_confident_match_response("rust")

    assert text.startswith("ACTION:")
    assert "STOP:" in text
    assert "VERIFY:" in text
    assert "CONFIDENCE:" in text
    assert "NO_CONFIDENT_MATCH" in text
    assert "do not force" in text.lower()


def test_rescue_json_contract_exposes_confidence_evidence_and_receipt():
    raw = mcp_server.borg_rescue(
        input="ModuleNotFoundError: No module named flask",
        source="first-10-test",
        show_guidance=False,
    )
    data = json.loads(raw)

    assert data["success"] is True
    assert data["action"]
    assert data["stop"]
    assert data["verify"]
    assert data["confidence"] == "seed-only"
    assert data["evidence"]["source"] == "seed_pack"
    assert data["evidence"]["verified_outcome_count"] == 0
    assert "zero verified outcome receipts" in data["human_summary"]
    assert data["human_receipt"]
    assert data["automation_policy"]["fail_closed"] is True


def test_docs_link_first_10_security_and_truthful_limitations():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    first_10 = (ROOT / "docs" / "FIRST_10_BETA_READINESS.md").read_text(encoding="utf-8")
    security = (ROOT / "docs" / "SECURITY_HARDENING_BASELINE.md").read_text(encoding="utf-8")

    assert "FIRST_10_BETA_READINESS.md" in readme
    assert "MINIMUM_CAPABLE_AGENT_STACK.md" in readme
    assert "Measured external agent success lift" in readme
    assert "Not yet claimed" in readme
    assert "Security/privacy/prompt-injection surface" in readme
    assert "secret scan" in security.lower()
    assert "pip-audit" in security
    assert PRIMING_PARAGRAPH in first_10
    assert "do not paste API keys" in first_10


def test_first_10_issue_form_captures_verification_safety_and_outcome_without_self_url() -> None:
    form = (ROOT / ".github" / "ISSUE_TEMPLATE" / "first-10-evidence.yml").read_text(encoding="utf-8")
    for field_id in [
        "artifact-version",
        "task-was-real-current-failure",
        "verification-status",
        "verification-evidence-redacted",
        "maintainer-help-before-first-value",
        "unknown-control-status",
        "false-confident-match",
        "harmful-guidance",
        "outcome-capture-method",
        "outcome-evidence-id",
    ]:
        assert f"id: {field_id}" in form
    assert "BORGFIRST10_UNKNOWN_CONTROL_v1" in form
    assert "id: external-user-evidence-uri" not in form
    assert "issue URL becomes the external evidence URI" in form


def test_preregistered_protocol_documents_denominator_and_hard_stops() -> None:
    protocol = (ROOT / "docs" / "FIRST_10_RESCUE_PROTOCOL.md").read_text(encoding="utf-8")

    assert "ENROLLMENT CLOSED" in protocol
    assert "Failed installs and unsuccessful rescues remain in the denominator" in protocol
    assert "BORGFIRST10_UNKNOWN_CONTROL_v1" in protocol
    assert "Pause enrollment on the first" in protocol
    assert "verified_useful_rescues + remaining_slots < 6" in protocol
    assert "no causal lift" in protocol


def test_cli_parser_exposes_first_10_command_by_source_contract():
    cli = (ROOT / "borg" / "cli.py").read_text(encoding="utf-8")

    assert 'sub.add_parser("first-10"' in cli
    assert "_cmd_first_10" in cli
    assert "first_10_readiness_packet" in cli


def test_mcp_exposes_first_10_contract():
    tool_names = {tool["name"] for tool in mcp_server.TOOLS}
    assert "borg_first_10" in tool_names
    assert "borg_capable_agent_stack" in tool_names

    raw = mcp_server.call_tool("borg_first_10", {})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["status"] == "first_10_beta_contract"
    assert len(data["gates"]) == 7

    stack_raw = mcp_server.call_tool("borg_capable_agent_stack", {})
    stack = json.loads(stack_raw)
    assert stack["success"] is True
    assert stack["status"] == "minimum_capable_agent_stack"
    assert len(stack["levers"]) == 7


def _first_10_value_row(
    idx: int,
    *,
    minutes_before: float | None = None,
    minutes_after: float | None = None,
    tokens_before: int | None = None,
    tokens_after: int | None = None,
    confirmed: bool = False,
) -> dict[str, object]:
    row: dict[str, object] = {
        "user_id_pseudonym": f"external-user-{idx:02d}",
        "enrollment_index": idx,
        "external_user_evidence_uri": f"https://github.com/borg-farther/Borg-Directory/issues/{idx}",
        "maintainer_validation_status": "verified",
        "maintainer_validation_evidence_uri": f"https://github.com/borg-farther/Borg-Directory/issues/{idx}#issuecomment-validated",
        "consent_confirmed": True,
        "artifact_version": "9.9.9",
        "install_method": "pipx install agent-borg==9.9.9",
        "install_success": True,
        "task_was_real_current_failure": True,
        "time_to_first_rescue_minutes": 4,
        "rescue_input_redacted": "ModuleNotFoundError: No module named flask",
        "rescue_returned_action_stop_verify": True,
        "rescue_useful": True,
        "guidance_relevant": True,
        "verification_status": "passed",
        "verification_evidence_redacted": "pytest target passed",
        "maintainer_help_before_first_value": False,
        "mcp_setup_attempted": True,
        "mcp_setup_success": True,
        "unknown_control_input_id": "unknown-control-v1",
        "unknown_control_status": "no_confident_match",
        "no_confident_match_when_unknown": True,
        "false_confident_match": False,
        "harmful_guidance": False,
        "blocker_category": "none",
        "blocker_notes_redacted": "none",
        "privacy_security_incident": False,
        "repeat_use_within_7_days": idx <= 2,
        "outcome_recorded": True,
        "outcome_capture_method": "github_evidence_issue",
        "outcome_evidence_id": f"issue-{idx}",
        "savings_counterfactual_basis": "randomized_control" if confirmed else "unknown",
        "dead_end_avoided_confirmed": confirmed,
        "user_confirmed_value": confirmed,
    }
    if minutes_before is not None:
        row["baseline_minutes_without_borg"] = minutes_before
    if minutes_after is not None:
        row["actual_minutes_with_borg"] = minutes_after
    if tokens_before is not None:
        row["baseline_tokens_without_borg"] = tokens_before
    if tokens_after is not None:
        row["actual_tokens_with_borg"] = tokens_after
    return row


def _first_10_value_scoreboard(rows: list[dict[str, object]]) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": 2,
        "protocol": {
            "protocol_id": "borg-rescue-first10-v1",
            "status": "complete" if len(rows) == 10 else ("enrollment_open" if not rows else "in_progress"),
            "enrollment_open": len(rows) < 10,
            "unknown_control": {
                "id": "unknown-control-v1",
                "input": "BORGFIRST10_UNKNOWN_CONTROL_v1: ZXQ-9199 proprietary scheduler quantum flux fault",
                "expected_status": "no_confident_match",
            },
            "artifact": {"package": "agent-borg", "version": "9.9.9", "wheel_sha256": "a" * 64},
        },
        "truth_policy": {
            "simulated_users_count_as_real": False,
            "internal_sessions_count_as_real": False,
            "maintainer_runs_count_as_real": False,
            "verified_external_users": 0,
            "public_self_serve_launch_allowed_before_thresholds": False,
        },
        "thresholds": {
            "min_install_successes_for_public_self_serve": 8,
            "min_useful_rescue_moments_for_public_self_serve": 6,
            "max_critical_privacy_security_failures": 0,
            "required_total_real_users": 10,
        },
        "columns": evidence.DEFAULT_COLUMNS,
        "rows": rows,
        "current_counts": {},
        "current_value_counts": {},
        "current_verdict": {},
    }
    return evidence.scoreboard_with_derived_fields(data)


def test_first_10_scoreboard_derives_human_value_savings_from_external_rows():
    rows = [_first_10_value_row(i) for i in range(1, 11)]
    rows[0].update(
        _first_10_value_row(
            1,
            minutes_before=30,
            minutes_after=10,
            tokens_before=9000,
            tokens_after=5000,
            confirmed=True,
        )
    )
    rows[1].update(
        _first_10_value_row(
            2,
            minutes_before=20,
            minutes_after=35,
            tokens_before=3000,
            tokens_after=4500,
            confirmed=True,
        )
    )
    data = _first_10_value_scoreboard(rows)

    result = evidence.evaluate_scoreboard(data)

    assert result["schema_valid"] is True
    assert result["derived_value"]["rows_with_measured_value"] == 2
    assert result["derived_value"]["net_minutes_saved"] == 5.0
    assert result["derived_value"]["positive_minutes_saved"] == 20.0
    assert result["derived_value"]["negative_minutes_cost"] == 15.0
    assert result["derived_value"]["net_tokens_saved"] == 2500
    assert result["derived_value"]["dead_ends_avoided_confirmed"] == 2
    assert result["stored_consistency"]["passed"] is True


def test_first_10_scoreboard_rejects_forged_or_inconsistent_savings_fields():
    rows = [_first_10_value_row(i) for i in range(1, 11)]
    rows[0].update(_first_10_value_row(1, minutes_before=30, minutes_after=10, confirmed=True))
    rows[0]["net_minutes_saved"] = 99
    data = _first_10_value_scoreboard(rows)

    result = evidence.evaluate_scoreboard(data)

    assert result["schema_valid"] is False
    assert result["public_self_serve_launch_gate"] == "BLOCKED"
    assert any(
        "net_minutes_saved does not match" in reason
        for item in result["invalid_rows"]
        for reason in item["reasons"]
    )
