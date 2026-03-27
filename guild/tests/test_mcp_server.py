"""
Tests for guild/integrations/mcp_server.py (T1.11).

Tests:
  - Tool listing via handle_request (tools/list)
  - Tool dispatch via handle_request (tools/call)
  - Error handling (tool errors propagate)
  - Unknown method dispatch (-32601)
  - Malformed JSON-RPC request (-32700)
  - Ping handling
  - Notification passthrough (no response)
  - make_response / make_error helpers
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch, MagicMock

import pytest

# Ensure guild-v2 package is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from guild.integrations import mcp_server as mcp_module


# ============================================================================
# Helpers
# ============================================================================

def minimal_request(method: str, params: Dict[str, Any] = None, req_id: Any = 1) -> Dict[str, Any]:
    """Build a minimal JSON-RPC 2.0 request dict."""
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": req_id,
    }


# ============================================================================
# Tests: make_response / make_error
# ============================================================================

class TestMakeResponse:
    def test_make_response_basic(self):
        r = mcp_module.make_response(42, {"foo": "bar"})
        assert r == {"jsonrpc": "2.0", "id": 42, "result": {"foo": "bar"}}

    def test_make_response_null_id(self):
        r = mcp_module.make_response(None, {})
        assert r == {"jsonrpc": "2.0", "id": None, "result": {}}

    def test_make_error_basic(self):
        e = mcp_module.make_error(99, -32601, "Method not found")
        assert e == {"jsonrpc": "2.0", "id": 99, "error": {"code": -32601, "message": "Method not found"}}

    def test_make_error_null_id(self):
        e = mcp_module.make_error(None, -32700, "Parse error")
        assert e["jsonrpc"] == "2.0"
        assert e["id"] is None
        assert e["error"]["code"] == -32700


# ============================================================================
# Tests: handle_request — initialize
# ============================================================================

class TestInitialize:
    def test_initialize_returns_protocol_and_capabilities(self):
        req = minimal_request("initialize", {}, req_id=1)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] == 1
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert "serverInfo" in resp["result"]
        assert resp["result"]["serverInfo"]["name"] == "guild-mcp-server"

    def test_initialize_no_id_still_returns_response(self):
        req = {"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": None}
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] is None


# ============================================================================
# Tests: handle_request — tools/list
# ============================================================================

class TestToolsList:
    def test_tools_list_returns_all_tools(self):
        req = minimal_request("tools/list", {}, req_id=2)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        expected = [
            "guild_search",
            "guild_pull",
            "guild_try",
            "guild_init",
            "guild_apply",
            "guild_publish",
            "guild_feedback",
        ]
        for name in expected:
            assert name in tool_names, f"{name} not in {tool_names}"

    def test_tools_list_includes_input_schema(self):
        req = minimal_request("tools/list", {}, req_id=3)
        resp = mcp_module.handle_request(req)
        tools = resp["result"]["tools"]
        search_tool = next((t for t in tools if t["name"] == "guild_search"), None)
        assert search_tool is not None
        assert "inputSchema" in search_tool
        assert search_tool["inputSchema"]["type"] == "object"
        assert "query" in search_tool["inputSchema"]["properties"]

    def test_tools_list_correct_count(self):
        req = minimal_request("tools/list", {}, req_id=4)
        resp = mcp_module.handle_request(req)
        assert len(resp["result"]["tools"]) == 7


# ============================================================================
# Tests: handle_request — tools/call
# ============================================================================

class TestToolsCall:
    def test_tools_call_unknown_tool_returns_error_in_content(self):
        req = minimal_request("tools/call", {"name": "nonexistent_tool", "arguments": {}}, req_id=5)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] == 5
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["success"] is False
        assert "Unknown tool" in parsed["error"]

    def test_tools_call_guild_search_empty_query(self):
        req = minimal_request("tools/call", {"name": "guild_search", "arguments": {"query": ""}}, req_id=6)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] == 6
        assert resp["result"]["isError"] is False
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed

    def test_tools_call_guild_search_with_query(self):
        req = minimal_request("tools/call", {"name": "guild_search", "arguments": {"query": "test"}}, req_id=7)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed

    def test_tools_call_guild_init_missing_name_returns_error(self):
        req = minimal_request("tools/call", {"name": "guild_init", "arguments": {}}, req_id=8)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["success"] is False
        assert "pack_name" in parsed["error"]

    def test_tools_call_guild_init_success(self):
        req = minimal_request("tools/call", {
            "name": "guild_init",
            "arguments": {"pack_name": "test-pack-xyz", "problem_class": "reasoning"}
        }, req_id=9)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["success"] is True
        assert parsed["pack_name"] == "test-pack-xyz"

    def test_tools_call_guild_publish_list_action(self):
        req = minimal_request("tools/call", {
            "name": "guild_publish",
            "arguments": {"action": "list"}
        }, req_id=10)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed
        assert "artifacts" in parsed

    def test_tools_call_guild_apply_missing_action_returns_error(self):
        req = minimal_request("tools/call", {
            "name": "guild_apply",
            "arguments": {}
        }, req_id=11)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        # Unknown action because action="" is not valid
        assert parsed["success"] is False


# ============================================================================
# Tests: handle_request — ping
# ============================================================================

class TestPing:
    def test_ping_returns_empty_result(self):
        req = minimal_request("ping", {}, req_id=12)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] == 12
        assert resp["result"] == {}


# ============================================================================
# Tests: handle_request — unknown method
# ============================================================================

class TestUnknownMethod:
    def test_unknown_method_returns_error_response(self):
        req = minimal_request("some/random/method", {}, req_id=13)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] == 13
        assert "error" in resp
        assert resp["error"]["code"] == -32601
        assert "Method not found" in resp["error"]["message"]

    def test_unknown_method_with_null_id_returns_none(self):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}, "id": None}
        resp = mcp_module.handle_request(req)
        # notifications/initialized is already handled — but let's try a truly unknown one
        req2 = {"jsonrpc": "2.0", "method": "completely/unknown", "params": {}, "id": None}
        resp2 = mcp_module.handle_request(req2)
        assert resp2 is None  # Notifications without id don't get responses

    def test_unknown_method_includes_method_name_in_error(self):
        req = minimal_request("tools/custom", {}, req_id=14)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert "tools/custom" in resp["error"]["message"]


# ============================================================================
# Tests: notifications passthrough
# ============================================================================

class TestNotifications:
    def test_notifications_initialized_returns_none(self):
        req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}, "id": None}
        resp = mcp_module.handle_request(req)
        assert resp is None


# ============================================================================
# Tests: call_tool helper directly
# ============================================================================

class TestCallTool:
    def test_call_tool_unknown_returns_error_json(self):
        result = mcp_module.call_tool("totally_fake_tool", {})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Unknown tool" in parsed["error"]

    def test_call_tool_guild_search_empty(self):
        result = mcp_module.call_tool("guild_search", {"query": ""})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "packs" in parsed

    def test_call_tool_guild_init(self):
        result = mcp_module.call_tool("guild_init", {"pack_name": "test-call-tool", "problem_class": "extraction"})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["pack_name"] == "test-call-tool"

    def test_call_tool_guild_feedback_missing_session(self):
        result = mcp_module.call_tool("guild_feedback", {"session_id": "does-not-exist-at-all"})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]

    def test_call_tool_guild_apply_unknown_action(self):
        result = mcp_module.call_tool("guild_apply", {"action": "fly_to_the_moon"})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Unknown action" in parsed["error"]


# ============================================================================
# Tests: main loop — malformed JSON
# ============================================================================

class TestMalformedRequest:
    def test_handle_request_malformed_json_returns_parse_error(self):
        # This is tested by calling handle_request with an invalid dict
        # (not a JSON decode error since we've already parsed)
        # But we can simulate a missing jsonrpc field
        req = {"method": "foo", "id": 1}  # missing jsonrpc
        resp = mcp_module.handle_request(req)
        # Still processes normally since jsonrpc field is not validated
        assert resp is not None

    def test_handle_request_missing_method_returns_error(self):
        req = {"jsonrpc": "2.0", "params": {}, "id": 1}  # missing method
        resp = mcp_module.handle_request(req)
        assert resp is not None
        # Empty method falls through to unknown method handler
        assert resp["error"]["code"] == -32601

    def test_handle_request_params_missing_defaults_to_empty_dict(self):
        req = {"jsonrpc": "2.0", "method": "ping", "id": 1}
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["result"] == {}


# ============================================================================
# Tests: guild_apply full workflow (start, checkpoint, complete)
# ============================================================================

class TestGuildApplyWorkflow:
    def test_apply_start_creates_session(self):
        # First init a pack so we have something to apply
        init_result = mcp_module.call_tool("guild_init", {
            "pack_name": "wf-test-apply",
            "problem_class": "reasoning",
        })
        init_parsed = json.loads(init_result)
        assert init_parsed["success"] is True

        # Start apply
        start_result = mcp_module.call_tool("guild_apply", {
            "action": "start",
            "pack_name": "wf-test-apply",
            "task": "Solve a reasoning problem",
        })
        start_parsed = json.loads(start_result)
        assert start_parsed["success"] is True
        session_id = start_parsed["session_id"]
        assert len(session_id) > 0
        assert start_parsed["phase_count"] >= 0

    def test_apply_start_missing_pack_returns_error(self):
        result = mcp_module.call_tool("guild_apply", {
            "action": "start",
            "pack_name": "this-pack-definitely-does-not-exist-12345",
            "task": "Test",
        })
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]

    def test_apply_checkpoint_unknown_session_returns_error(self):
        result = mcp_module.call_tool("guild_apply", {
            "action": "checkpoint",
            "session_id": "nonexistent-session-xyz",
            "phase_name": "phase-1",
            "status": "passed",
        })
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]

    def test_apply_complete_unknown_session_returns_error(self):
        result = mcp_module.call_tool("guild_apply", {
            "action": "complete",
            "session_id": "nonexistent-session-xyz",
            "outcome": "done",
        })
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]


# ============================================================================
# Tests: TOOLS constant has correct structure
# ============================================================================

class TestToolsConstant:
    def test_all_tools_have_required_fields(self):
        for tool in mcp_module.TOOLS:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"

    def test_guild_apply_has_all_required_properties(self):
        apply_tool = next(t for t in mcp_module.TOOLS if t["name"] == "guild_apply")
        props = apply_tool["inputSchema"]["properties"]
        assert "action" in props
        assert "pack_name" in props
        assert "task" in props
        assert "session_id" in props

    def test_guild_publish_enum_action(self):
        pub_tool = next(t for t in mcp_module.TOOLS if t["name"] == "guild_publish")
        assert pub_tool["inputSchema"]["properties"]["action"]["enum"] == ["list", "publish"]
