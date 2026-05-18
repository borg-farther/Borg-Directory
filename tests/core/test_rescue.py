"""Tests for the day-one Borg rescue engine."""

from __future__ import annotations

import json

from borg.core.rescue import rescue, render_rescue_text
from borg.integrations import mcp_server


def test_rescue_returns_agent_contract_for_known_error():
    result = rescue("ModuleNotFoundError: No module named flask", source="test", show_guidance=False)

    assert result.success is True
    assert result.status == "matched"
    assert result.problem_class == "missing_dependency"
    assert result.action
    assert result.stop
    assert result.verify
    assert "ACTION:" in result.agent_instruction
    assert "STOP:" in result.agent_instruction
    assert "VERIFY:" in result.agent_instruction
    assert result.automation_policy["default"] == "automatic_for_agents"
    assert result.automation_policy["fail_closed"] is True
    assert "Borg matched" in result.human_receipt


def test_rescue_fails_closed_on_unknown_or_non_python_error():
    result = rescue("error[E0382]: borrow of moved value: `x`", source="test", show_guidance=False)

    assert result.success is False
    assert result.status == "no_confident_match"
    assert result.problem_class == "unknown"
    assert "NO_MATCH" in result.agent_instruction
    assert "Do not" in result.agent_instruction or "do not" in result.agent_instruction
    assert result.automation_policy["fail_closed"] is True


def test_rescue_fails_closed_on_empty_input():
    result = rescue("", source="test", show_guidance=False)

    assert result.success is False
    assert result.status == "empty_input"
    assert result.action == ["paste the exact error, failing command, or agent transcript"]


def test_render_rescue_text_has_visible_human_value_sections():
    result = rescue("PermissionError: [Errno 13] permission denied", source="test", show_guidance=False)
    text = render_rescue_text(result)

    assert "BORG RESCUE" in text
    assert "ACTION" in text
    assert "STOP" in text
    assert "VERIFY" in text
    assert "AGENT INSTRUCTION" in text
    assert "HUMAN RECEIPT" in text


def test_mcp_borg_rescue_returns_json_contract():
    raw = mcp_server.borg_rescue(
        input="TypeError: unsupported operand type(s) for +: 'int' and 'str'",
        source="test-mcp",
        show_guidance=False,
    )
    data = json.loads(raw)

    assert data["success"] is True
    assert data["status"] == "matched"
    assert data["problem_class"] == "type_mismatch"
    assert data["automation_policy"]["default"] == "automatic_for_agents"


def test_mcp_call_tool_dispatches_borg_rescue():
    raw = mcp_server.call_tool(
        "borg_rescue",
        {"input": "ModuleNotFoundError: No module named yaml", "show_guidance": False},
    )
    data = json.loads(raw)

    assert data["success"] is True
    assert data["problem_class"] == "missing_dependency"
