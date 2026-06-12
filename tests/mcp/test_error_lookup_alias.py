"""First-user MCP surface contract for concrete error lookup.

The first alpha user should not have to infer that `borg_rescue` is the
user-facing error lookup tool.  Borg must expose the plain-English
`error_lookup` MCP alias and keep it behaviorally identical to `borg_rescue`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from borg.integrations import mcp_server

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _reset_mcp_rate_limit_state():
    """Keep these public dispatch checks from polluting rate-limit tests."""
    with mcp_server._rate_limit_lock:
        mcp_server._rate_requests.clear()
    with mcp_server._human_session_lock:
        mcp_server._human_session_state.clear()
    yield
    with mcp_server._rate_limit_lock:
        mcp_server._rate_requests.clear()
    with mcp_server._human_session_lock:
        mcp_server._human_session_state.clear()


def test_tools_list_exposes_plain_english_error_lookup_alias():
    resp = mcp_server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    })
    assert resp is not None
    tool_list = resp["result"]["tools"]
    names = [tool["name"] for tool in tool_list]
    assert len(names) == len(set(names)), f"duplicate MCP tool names confuse first-user tool discovery: {names}"
    tools = {tool["name"]: tool for tool in tool_list}

    assert "borg_rescue" in tools
    assert "error_lookup" in tools
    assert "alias" in tools["error_lookup"]["description"].lower()
    assert "borg_rescue" in tools["error_lookup"]["description"]
    assert tools["error_lookup"]["inputSchema"]["required"] == ["input"]
    assert "input" in tools["error_lookup"]["inputSchema"]["properties"]


def test_error_lookup_dispatch_matches_borg_rescue_contract():
    args = {
        "input": "ModuleNotFoundError: No module named flask",
        "source": "test-error-lookup-alias",
        "show_guidance": False,
    }

    alias = json.loads(mcp_server.call_tool("error_lookup", args))
    canonical = json.loads(mcp_server.call_tool("borg_rescue", args))

    assert alias["success"] is True
    assert alias["status"] == "matched"
    assert alias["problem_class"] == "missing_dependency"
    for key in ["action", "stop", "verify", "confidence", "evidence", "human_receipt", "automation_policy"]:
        assert alias[key] == canonical[key]


def test_error_lookup_is_not_auto_captured_as_user_trace(monkeypatch):
    """Do not persist first-user raw error text just because they used the alias."""
    session_id = "test-error-lookup-trace-skip"
    mcp_server.init_trace_capture(session_id, task="first-user rescue", agent_id="pytest")
    token = mcp_server._current_session_id.set(session_id)
    try:
        with mcp_server._trace_lock:
            capture = mcp_server._trace_captures[session_id]
            assert capture.tool_calls == 0

        monkeypatch.setattr(mcp_server, "_call_tool_impl", lambda name, args: json.dumps({"success": True, "tool": name}))

        mcp_server.call_tool("error_lookup", {"input": "ModuleNotFoundError: No module named flask"})
        with mcp_server._trace_lock:
            assert mcp_server._trace_captures[session_id].tool_calls == 0

        mcp_server.call_tool("non_internal_probe", {"input": "safe synthetic payload"})
        with mcp_server._trace_lock:
            assert mcp_server._trace_captures[session_id].tool_calls == 1
    finally:
        mcp_server._current_session_id.reset(token)
        with mcp_server._trace_lock:
            mcp_server._trace_captures.pop(session_id, None)


def test_error_lookup_json_rpc_call_returns_text_content_packet():
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "error_lookup",
            "arguments": {
                "input": "TypeError: unsupported operand type(s) for +: 'int' and 'str'",
                "show_guidance": False,
            },
        },
    }

    resp = mcp_server.handle_request(req)
    assert resp is not None
    assert resp["id"] == 2
    assert resp["result"]["isError"] is False
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["success"] is True
    assert payload["problem_class"] == "type_mismatch"
    assert payload["agent_instruction"].startswith("ACTION:")
    assert "structuredContent" in resp["result"]
    # Firing visibility (E-014): user_message carries the human_summary
    # moment-line — the channel clients actually surface to the human.
    assert resp["result"]["user_message"].startswith("🛟 Borg: found a known fix")
    assert "proven" not in resp["result"]["user_message"].lower()
    assert resp["result"]["structuredContent"]["borg_human"]["first_hit"] is True


def _assert_renderer_safe(line: str):
    # Single line, no box-drawing. Unicode is allowed: the human_summary
    # moment-line leads with the spec-mandated lifebuoy emoji.
    assert line == " ".join(line.split())
    assert not any("\u2500" <= ch <= "\u257f" for ch in line)


def test_error_lookup_human_badge_fires_once_per_session():
    args = {
        "input": "ModuleNotFoundError: No module named flask",
        "source": "test-human-comms",
        "show_guidance": False,
        "_meta": {"hermes_session_id": "human-session-1"},
    }

    first = json.loads(mcp_server.call_tool("error_lookup", args))
    second = json.loads(mcp_server.call_tool("error_lookup", args))

    assert first["user_message"].startswith("🛟 Borg: found a known fix for this missing dependency error")
    assert "proven" not in first["user_message"].lower()
    assert first["borg_human"]["first_hit"] is True
    assert "dead_ends_avoided" not in first["borg_human"]["state"]
    assert first["borg_human"]["state"]["stop_items_surfaced"] == 3
    # E-014 push rule: EVERY hit pushes the moment-line (was first-hit-only,
    # which meant a human whose agent hit twice never saw the second firing).
    assert second["user_message"] == first["user_message"]
    assert "dead_ends_avoided" not in second["borg_human"]["state"]
    assert second["borg_human"]["state"]["stop_items_surfaced"] == 6
    assert second["session_message"] == "Borg surfaced 2 matched hints, showed 6 STOP items, learned 0 new fixes; value remains unmeasured until VERIFY/outcome receipt."
    for line in [first["user_message"], first["session_message"], second["session_message"]]:
        _assert_renderer_safe(line)


def test_error_lookup_no_match_still_carries_session_line():
    result = json.loads(mcp_server.call_tool("error_lookup", {
        "input": "zzzz totally unrelated no technical thing",
        "source": "test-human-comms",
        "show_guidance": False,
        "_meta": {"hermes_session_id": "human-session-miss"},
    }))

    assert result["success"] is False
    assert "user_message" not in result
    assert result["session_message"] == "Borg had no prior memory for this one."
    assert result["borg_human"]["matched"] is False
    _assert_renderer_safe(result["session_message"])


def test_error_lookup_low_confidence_warning_does_not_consume_first_hit():
    payload = {
        "success": True,
        "status": "matched",
        "confidence": "low",
        "evidence": {"uses": 3},
        "stop": ["do not retry the same command"],
    }

    enriched = mcp_server._attach_human_comms(payload, session_id="weak-session")

    assert enriched["user_message"] == "Borg found a weak hint. Treating it cautiously."
    assert enriched["borg_human"]["first_hit"] is False
    with mcp_server._human_session_lock:
        assert mcp_server._human_session_state["weak-session"]["first_hit_shown"] is False


def test_first_user_docs_and_readiness_contract_name_error_lookup():
    docs = [
        ROOT / "README.md",
        ROOT / "docs" / "INSTALL.md",
        ROOT / "docs" / "QUICKSTART.md",
        ROOT / "docs" / "MCP_SETUP.md",
        ROOT / "docs" / "TRYING_BORG.md",
        ROOT / "docs" / "FIRST_10_BETA_READINESS.md",
        ROOT / "docs" / "TESTER_MESSAGE.md",
        ROOT / "examples" / "skills" / "borg" / "SKILL.md",
        ROOT / "examples" / "skills" / "guild-autopilot" / "SKILL.md",
        ROOT / "borg" / "seeds_data" / "borg" / "SKILL.md",
        ROOT / "borg" / "seeds_data" / "borg-autopilot" / "SKILL.md",
    ]
    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "error_lookup" in text, f"{path} must tell first users the plain-English MCP tool name"
        assert "borg_rescue" in text, f"{path} must preserve the canonical Borg tool name"

    packet = json.loads(mcp_server.borg_first_10())
    assert "error_lookup" in packet["priming_paragraph"]
    assert "error_lookup" in packet["mcp_first_call"]
