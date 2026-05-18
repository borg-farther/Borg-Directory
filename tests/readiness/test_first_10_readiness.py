"""First-10 beta readiness contract tests.

These tests lock the launch-critical behavior AB requested before external
users: fail-closed retrieval, explicit confidence, ACTION/STOP/VERIFY shape,
truthful beta packet, and docs/security linkage.
"""

from __future__ import annotations

import json
from pathlib import Path

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

    assert "python3 -m pip install agent-borg" in commands
    assert "borg-doctor --json" in commands
    assert "borg rescue" in commands
    assert "borg setup-claude --scope user --verify --fix" in commands
    assert "borg first-10 --json" in commands
    assert "borg_rescue" in packet["priming_paragraph"]
    assert "borg_observe" in packet["priming_paragraph"]
    assert "borg_feedback" in packet["priming_paragraph"]
    assert "borg_record_failure" in packet["priming_paragraph"]
    assert "borg_rate" not in packet["priming_paragraph"]
    assert "did_it_prevent_a_dead_end" in packet["feedback_fields"]
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
    assert data["confidence"] in {"tested", "observed", "inferred", "unknown"}
    assert "source" in data["evidence"]
    assert data["human_receipt"]
    assert data["automation_policy"]["fail_closed"] is True


def test_docs_link_first_10_security_and_truthful_limitations():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    first_10 = (ROOT / "docs" / "FIRST_10_BETA_READINESS.md").read_text(encoding="utf-8")
    security = (ROOT / "docs" / "SECURITY_HARDENING_BASELINE.md").read_text(encoding="utf-8")

    assert "FIRST_10_BETA_READINESS.md" in readme
    assert "Statistically significant agent-level success lift" in readme
    assert "Security/privacy/prompt-injection surface" in readme
    assert "secret scan" in security.lower()
    assert "pip-audit" in security
    assert PRIMING_PARAGRAPH in first_10
    assert "do not paste API keys" in first_10


def test_cli_parser_exposes_first_10_command_by_source_contract():
    cli = (ROOT / "borg" / "cli.py").read_text(encoding="utf-8")

    assert 'sub.add_parser("first-10"' in cli
    assert "_cmd_first_10" in cli
    assert "first_10_readiness_packet" in cli


def test_mcp_exposes_first_10_contract():
    tool_names = {tool["name"] for tool in mcp_server.TOOLS}
    assert "borg_first_10" in tool_names

    raw = mcp_server.call_tool("borg_first_10", {})
    data = json.loads(raw)
    assert data["success"] is True
    assert data["status"] == "first_10_beta_contract"
    assert len(data["gates"]) == 7
