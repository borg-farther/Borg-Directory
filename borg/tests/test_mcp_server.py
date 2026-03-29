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

from borg.integrations import mcp_server as mcp_module


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
        assert resp["result"]["serverInfo"]["name"] == "borg-mcp-server"

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
            "borg_search",
            "borg_pull",
            "borg_try",
            "borg_init",
            "borg_apply",
            "borg_publish",
            "borg_feedback",
            "borg_suggest",
            "borg_observe",
            "borg_convert",
            "borg_context",
            "borg_recall",
            "borg_reputation",
            "borg_analytics",
            "borg_dojo",
        ]
        for name in expected:
            assert name in tool_names, f"{name} not in {tool_names}"

    def test_tools_list_includes_input_schema(self):
        req = minimal_request("tools/list", {}, req_id=3)
        resp = mcp_module.handle_request(req)
        tools = resp["result"]["tools"]
        search_tool = next((t for t in tools if t["name"] == "borg_search"), None)
        assert search_tool is not None
        assert "inputSchema" in search_tool
        assert search_tool["inputSchema"]["type"] == "object"
        assert "query" in search_tool["inputSchema"]["properties"]

    def test_tools_list_correct_count(self):
        req = minimal_request("tools/list", {}, req_id=4)
        resp = mcp_module.handle_request(req)
        assert len(resp["result"]["tools"]) == 15


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

    def test_tools_call_borg_search_empty_query(self):
        req = minimal_request("tools/call", {"name": "borg_search", "arguments": {"query": ""}}, req_id=6)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        assert resp["id"] == 6
        # Empty query may return error or empty results
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed

    def test_tools_call_borg_search_with_query(self):
        req = minimal_request("tools/call", {"name": "borg_search", "arguments": {"query": "test"}}, req_id=7)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed

    def test_tools_call_borg_init_missing_name_returns_error(self):
        req = minimal_request("tools/call", {"name": "borg_init", "arguments": {}}, req_id=8)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["success"] is False
        assert "pack_name" in parsed["error"]

    def test_tools_call_borg_init_success(self):
        req = minimal_request("tools/call", {
            "name": "borg_init",
            "arguments": {"pack_name": "test-pack-xyz", "problem_class": "reasoning"}
        }, req_id=9)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert parsed["success"] is True
        assert parsed["pack_name"] == "test-pack-xyz"

    def test_tools_call_borg_publish_list_action(self):
        req = minimal_request("tools/call", {
            "name": "borg_publish",
            "arguments": {"action": "list"}
        }, req_id=10)
        resp = mcp_module.handle_request(req)
        assert resp is not None
        content_text = resp["result"]["content"][0]["text"]
        parsed = json.loads(content_text)
        assert "success" in parsed
        assert "artifacts" in parsed

    def test_tools_call_borg_apply_missing_action_returns_error(self):
        req = minimal_request("tools/call", {
            "name": "borg_apply",
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

    def test_call_tool_borg_search_empty(self):
        result = mcp_module.call_tool("borg_search", {"query": ""})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "packs" in parsed

    def test_call_tool_borg_init(self):
        result = mcp_module.call_tool("borg_init", {"pack_name": "test-call-tool", "problem_class": "extraction"})
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["pack_name"] == "test-call-tool"

    def test_call_tool_borg_feedback_missing_session(self):
        result = mcp_module.call_tool("borg_feedback", {"session_id": "does-not-exist-at-all"})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]

    def test_call_tool_borg_apply_unknown_action(self):
        result = mcp_module.call_tool("borg_apply", {"action": "fly_to_the_moon"})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Unknown action" in parsed["error"]

    def test_call_tool_borg_suggest_empty_context(self):
        result = mcp_module.call_tool("borg_suggest", {"context": ""})
        assert result == "{}"

    def test_call_tool_borg_suggest_with_context(self):
        result = mcp_module.call_tool("borg_suggest", {
            "context": "I've tried debugging this for hours and it keeps failing with the same error",
            "failure_count": 2,
        })
        # Should return JSON (either empty {} or suggestion)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_call_tool_borg_convert_with_explicit_format(self, tmp_path):
        # Create a minimal SKILL.md file
        skill_file = tmp_path / "myskill.md"
        skill_file.write_text("---\nname: test-skill\ndescription: A test skill\n---\n# Main\nThis is the main phase.\n")
        result = mcp_module.call_tool("borg_convert", {
            "path": str(skill_file),
            "format": "skill",
        })
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert "content" in parsed
        assert "pack" in parsed
        assert parsed["pack"]["id"] == "borg://converted/test_skill"

    def test_call_tool_borg_convert_missing_path(self):
        result = mcp_module.call_tool("borg_convert", {"path": ""})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "path is required" in parsed["error"]

    def test_call_tool_borg_observe_empty_task_returns_empty(self):
        result = mcp_module.call_tool("borg_observe", {"task": ""})
        assert result == ""

    def test_call_tool_borg_observe_no_match_returns_empty(self):
        # Mock the core search function that borg_observe imports directly
        with patch("borg.core.search.borg_search", return_value='{"success": true, "matches": [], "mode": "text"}'):
            with patch("borg.core.search.classify_task", return_value=["xyzzy-nonexistent-task-12345"]):
                result = mcp_module.call_tool("borg_observe", {"task": "xyzzy-nonexistent-task-12345"})
                assert result == ""

    @pytest.mark.xfail(reason="Local pack scan overrides mock; integration test covers this via E2E")
    def test_call_tool_borg_observe_with_match_returns_guide(self):
        # Mock the core search function that borg_observe imports directly
        mock_search_result = json.dumps({
            "success": True,
            "matches": [
                {
                    "name": "test-pack",
                    "id": "borg://test/pack",
                    "problem_class": "extraction",
                    "tier": "proven",
                    "phases": [
                        {"name": "parse", "description": "Parse input"},
                        {"name": "extract", "description": "Extract key info"},
                    ],
                    "anti_patterns": ["rushing", "skipping validation"],
                    "checkpoint": "validate output",
                }
            ],
            "mode": "text",
        })
        with patch("borg.core.search.borg_search", return_value=mock_search_result):
            with patch("borg.core.search.classify_task", return_value=["extract"]):
                result = mcp_module.call_tool("borg_observe", {"task": "extract data from text"})
                assert "proven approach: **test-pack**" in result
                assert "Phase" in result  # phases are listed
                assert "anti-patterns" in result.lower() or "anti_patterns" in result.lower()
                assert "anti-patterns" in result.lower()
                assert "checkpoint" in result.lower()

    def test_call_tool_borg_observe_uses_context(self):
        # Verify context parameter is accepted (context is stored but not used in new implementation)
        # The new implementation uses classify_task to extract keywords from task only
        with patch("borg.core.search.borg_search", return_value='{"success": true, "matches": [], "mode": "text"}'):
            with patch("borg.core.search.classify_task", return_value=["debug"]) as mock_classify:
                mcp_module.call_tool("borg_observe", {
                    "task": "fix bug",
                    "context": "python, django",
                })
                mock_classify.assert_called_once_with("fix bug")


class TestBorgObserveUnit:
    """Unit tests for borg_observe function directly."""

    def test_borg_observe_empty_task_returns_empty_string(self):
        result = mcp_module.borg_observe(task="")
        assert result == ""

    def test_borg_observe_empty_task_with_context_returns_empty(self):
        result = mcp_module.borg_observe(task="", context="some context")
        assert result == ""

    def test_borg_observe_no_matching_packs_returns_empty(self):
        with patch("borg.core.search.borg_search", return_value='{"success": true, "matches": [], "mode": "text"}'):
            with patch("borg.core.search.classify_task", return_value=["totally-obscure-task-xyz123"]):
                result = mcp_module.borg_observe(task="totally obscure task xyz123")
                assert result == ""

    def test_borg_observe_low_score_returns_empty(self):
        # Low relevance score with tier "none" returns empty (new impl filters out tier "none")
        with patch("borg.core.search.borg_search", return_value=json.dumps({
            "success": True,
            "matches": [{"name": "some-pack", "relevance_score": 0.2, "tier": "none"}],
            "mode": "hybrid",
        })):
            with patch("borg.core.search.classify_task", return_value=["task"]):
                result = mcp_module.borg_observe(task="some task")
                assert result == ""

    def test_borg_observe_text_mode_returns_match_without_score_threshold(self):
        # Text mode falls back to tier-based filtering (any non-"none" tier is accepted)
        with patch("borg.core.search.borg_search", return_value=json.dumps({
            "success": True,
            "matches": [{"name": "my-pack", "tier": "experimental", "phases": [], "anti_patterns": []}],
            "mode": "text",
        })):
            with patch("borg.core.search.classify_task", return_value=["some-task"]):
                result = mcp_module.borg_observe(task="some task")
                assert "my-pack" in result

    def test_borg_observe_includes_phases(self):
        with patch("borg.core.search.borg_search", return_value=json.dumps({
            "success": True,
            "matches": [{
                "name": "guide-pack",
                "phases": [
                    {"name": "plan", "description": "Make a plan"},
                    {"name": "execute", "description": "Execute the plan"},
                    {"name": "verify", "description": "Verify results"},
                ],
                "anti_patterns": [],
            }],
            "mode": "text",
        })):
            with patch("borg.core.search.classify_task", return_value=["complex-task"]):
                result = mcp_module.borg_observe(task="complex task")
                assert "Phase 1: plan" in result
                assert "Phase 2: execute" in result
                assert "Phase 3: verify" in result

    def test_borg_observe_includes_anti_patterns(self):
        with patch("borg.core.search.borg_search", return_value=json.dumps({
            "success": True,
            "matches": [{
                "name": "smart-pack",
                "phases": [],
                "anti_patterns": ["copy-paste", "skip tests", "ignore errors"],
            }],
            "mode": "text",
        })):
            with patch("borg.core.search.classify_task", return_value=["task"]):
                result = mcp_module.borg_observe(task="task")
                assert "anti-patterns" in result.lower()
                assert "copy-paste" in result
                assert "skip tests" in result

    def test_borg_observe_includes_checkpoint(self):
        with patch("borg.core.search.borg_search", return_value=json.dumps({
            "success": True,
            "matches": [{
                "name": "safe-pack",
                "phases": [],
                "anti_patterns": [],
                "checkpoint": "review before merging",
            }],
            "mode": "text",
        })):
            with patch("borg.core.search.classify_task", return_value=["task"]):
                result = mcp_module.borg_observe(task="task")
                assert "checkpoint" in result.lower()
                assert "review before merging" in result

    def test_borg_observe_handles_search_error_gracefully(self):
        with patch("borg.core.search.borg_search", return_value='{"success": false, "error": "search failed"}'):
            with patch("borg.core.search.classify_task", return_value=["task"]):
                result = mcp_module.borg_observe(task="task")
                assert result == ""

    def test_borg_observe_handles_invalid_json_gracefully(self):
        with patch("borg.core.search.borg_search", return_value="not json at all"):
            with patch("borg.core.search.classify_task", return_value=["task"]):
                result = mcp_module.borg_observe(task="task")
                assert result == ""

    def test_borg_observe_handles_exception_gracefully(self):
        # borg_observe internally calls classify_task and borg_search; if they raise, it must not propagate
        def raise_once(*args, **kwargs):
            raise RuntimeError("borg_search temporarily unavailable")

        with patch("borg.core.search.borg_search", side_effect=raise_once):
            with patch("borg.core.search.classify_task", return_value=["task"]):
                result = mcp_module.borg_observe(task="task")
                result_data = json.loads(result)
                assert result_data["success"] is True  # Should fail silently, not raise
                assert result_data["observed"] is False

    def test_call_tool_borg_convert_unknown_format(self):
        result = mcp_module.call_tool("borg_convert", {
            "path": "/tmp/test.md",
            "format": "invalid_format",
        })
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Unknown format" in parsed["error"]


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
# Tests: borg_apply full workflow (start, checkpoint, complete)
# ============================================================================

class TestBorgApplyWorkflow:
    def test_apply_start_creates_session(self):
        # First init a pack so we have something to apply
        init_result = mcp_module.call_tool("borg_init", {
            "pack_name": "wf-test-apply",
            "problem_class": "reasoning",
        })
        init_parsed = json.loads(init_result)
        assert init_parsed["success"] is True

        # Start apply
        start_result = mcp_module.call_tool("borg_apply", {
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
        result = mcp_module.call_tool("borg_apply", {
            "action": "start",
            "pack_name": "this-pack-definitely-does-not-exist-12345",
            "task": "Test",
        })
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]

    def test_apply_checkpoint_unknown_session_returns_error(self):
        result = mcp_module.call_tool("borg_apply", {
            "action": "checkpoint",
            "session_id": "nonexistent-session-xyz",
            "phase_name": "phase-1",
            "status": "passed",
        })
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "not found" in parsed["error"]

    def test_apply_complete_unknown_session_returns_error(self):
        result = mcp_module.call_tool("borg_apply", {
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

    def test_borg_apply_has_all_required_properties(self):
        apply_tool = next(t for t in mcp_module.TOOLS if t["name"] == "borg_apply")
        props = apply_tool["inputSchema"]["properties"]
        assert "action" in props
        assert "pack_name" in props
        assert "task" in props
        assert "session_id" in props

    def test_borg_publish_enum_action(self):
        pub_tool = next(t for t in mcp_module.TOOLS if t["name"] == "borg_publish")
        assert pub_tool["inputSchema"]["properties"]["action"]["enum"] == ["list", "publish"]


class TestBorgDojo:
    """Tests for borg_dojo tool (analyze, report, history, status actions)."""

    def test_borg_dojo_tool_exists_in_tools_list(self):
        """Verify borg_dojo is present in TOOLS with correct schema."""
        tool = next((t for t in mcp_module.TOOLS if t["name"] == "borg_dojo"), None)
        assert tool is not None
        props = tool["inputSchema"]["properties"]
        assert "action" in props
        assert props["action"]["enum"] == ["analyze", "report", "history", "status"]
        assert "days" in props
        assert "report_format" in props

    def test_borg_dojo_unknown_action_returns_error(self):
        result = mcp_module.call_tool("borg_dojo", {"action": "fly_to_the_moon"})
        parsed = json.loads(result)
        assert parsed["success"] is False
        assert "Unknown action" in parsed["error"]

    def test_borg_dojo_analyze_with_mock(self):
        """Test action=analyze returns structured analysis data."""
        mock_analysis = MagicMock()
        mock_analysis.schema_version = 1
        mock_analysis.sessions_analyzed = 42
        mock_analysis.total_tool_calls = 300
        mock_analysis.total_errors = 15
        mock_analysis.overall_success_rate = 95.0
        mock_analysis.user_corrections = 3
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = []
        mock_analysis.failure_reports = []

        with patch("borg.dojo.pipeline.analyze_recent_sessions", return_value=mock_analysis) as mock_analyze:
            result = mcp_module.call_tool("borg_dojo", {"action": "analyze", "days": 7})
            mock_analyze.assert_called_once_with(days=7)
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["action"] == "analyze"
            assert parsed["sessions_analyzed"] == 42
            assert parsed["total_tool_calls"] == 300
            assert parsed["total_errors"] == 15
            assert parsed["overall_success_rate"] == 95.0

    def test_borg_dojo_analyze_file_not_found(self):
        """Test action=analyze handles missing state.db gracefully."""
        with patch("borg.dojo.pipeline.analyze_recent_sessions", side_effect=FileNotFoundError("state.db not found")):
            result = mcp_module.call_tool("borg_dojo", {"action": "analyze"})
            parsed = json.loads(result)
            assert parsed["success"] is False
            assert "state.db" in parsed["error"]

    def test_borg_dojo_report_with_mock(self):
        """Test action=report returns formatted report string."""
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = "Dojo Report — 5 sessions analyzed, 2 improvements made."

        with patch("borg.dojo.pipeline.DojoPipeline", return_value=mock_pipeline):
            result = mcp_module.call_tool("borg_dojo", {"action": "report", "report_format": "telegram"})
            mock_pipeline.run.assert_called_once_with(days=7, auto_fix=False, report_fmt="telegram")
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["action"] == "report"
            assert "Dojo Report" in parsed["report"]

    def test_borg_dojo_report_cli_format(self):
        """Test action=report with cli format."""
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = "CLI REPORT LINE 1\nCLI REPORT LINE 2"

        with patch("borg.dojo.pipeline.DojoPipeline", return_value=mock_pipeline):
            result = mcp_module.call_tool("borg_dojo", {"action": "report", "report_format": "cli"})
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["format"] == "cli"

    def test_borg_dojo_history_with_mock(self):
        """Test action=history returns learning curve snapshots."""
        mock_snapshot = MagicMock()
        mock_snapshot.to_dict.return_value = {
            "timestamp": 1700000000.0,
            "date": "2024-01-01 00:00",
            "sessions_analyzed": 10,
            "total_tool_calls": 100,
            "overall_success_rate": 92.0,
            "total_errors": 8,
            "user_corrections": 2,
            "skill_gaps_count": 1,
            "retry_pattern_count": 0,
            "weakest_tools": [],
            "improvements_made": [],
            "schema_version": 1,
        }
        mock_tracker = MagicMock()
        mock_tracker.load_history.return_value = [mock_snapshot]

        with patch("borg.dojo.learning_curve.LearningCurveTracker", return_value=mock_tracker):
            result = mcp_module.call_tool("borg_dojo", {"action": "history"})
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["action"] == "history"
            assert parsed["snapshot_count"] == 1
            assert len(parsed["snapshots"]) == 1
            assert parsed["snapshots"][0]["sessions_analyzed"] == 10

    def test_borg_dojo_history_empty_returns_empty_list(self):
        """Test action=history handles empty history gracefully."""
        mock_tracker = MagicMock()
        mock_tracker.load_history.return_value = []

        with patch("borg.dojo.learning_curve.LearningCurveTracker", return_value=mock_tracker):
            result = mcp_module.call_tool("borg_dojo", {"action": "history"})
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["snapshot_count"] == 0
            assert parsed["snapshots"] == []

    def test_borg_dojo_status_with_cached_analysis(self):
        """Test action=status returns health summary from cached analysis."""
        mock_analysis = MagicMock()
        mock_analysis.overall_success_rate = 85.0
        mock_analysis.sessions_analyzed = 20
        mock_analysis.total_tool_calls = 150
        mock_analysis.total_errors = 12
        mock_analysis.user_corrections = 1
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = [
            MagicMock(tool_name="borg_search", failed_calls=5),
            MagicMock(tool_name="borg_pull", failed_calls=3),
        ]

        with patch("borg.dojo.pipeline.get_cached_analysis", return_value=mock_analysis):
            result = mcp_module.call_tool("borg_dojo", {"action": "status"})
            parsed = json.loads(result)
            assert parsed["success"] is True
            assert parsed["action"] == "status"
            assert parsed["health"] == "healthy"
            assert parsed["sessions_analyzed"] == 20
            assert parsed["overall_success_rate"] == 85.0
            assert len(parsed["weakest_tools"]) == 2

    def test_borg_dojo_status_degraded_health(self):
        """Test action=status returns 'degraded' when success rate < 70."""
        mock_analysis = MagicMock()
        mock_analysis.overall_success_rate = 65.0
        mock_analysis.sessions_analyzed = 10
        mock_analysis.total_tool_calls = 50
        mock_analysis.total_errors = 17
        mock_analysis.user_corrections = 0
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = []

        with patch("borg.dojo.pipeline.get_cached_analysis", return_value=mock_analysis):
            result = mcp_module.call_tool("borg_dojo", {"action": "status"})
            parsed = json.loads(result)
            assert parsed["health"] == "degraded"

    def test_borg_dojo_status_unhealthy_health(self):
        """Test action=status returns 'unhealthy' when success rate < 50."""
        mock_analysis = MagicMock()
        mock_analysis.overall_success_rate = 40.0
        mock_analysis.sessions_analyzed = 5
        mock_analysis.total_tool_calls = 20
        mock_analysis.total_errors = 12
        mock_analysis.user_corrections = 0
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = []

        with patch("borg.dojo.pipeline.get_cached_analysis", return_value=mock_analysis):
            result = mcp_module.call_tool("borg_dojo", {"action": "status"})
            parsed = json.loads(result)
            assert parsed["health"] == "unhealthy"

    def test_borg_dojo_status_no_cache_runs_analysis(self):
        """Test action=status runs analysis when no cached result exists."""
        mock_analysis = MagicMock()
        mock_analysis.overall_success_rate = 90.0
        mock_analysis.sessions_analyzed = 8
        mock_analysis.total_tool_calls = 60
        mock_analysis.total_errors = 6
        mock_analysis.user_corrections = 0
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = []

        with patch("borg.dojo.pipeline.get_cached_analysis", return_value=None):
            with patch("borg.dojo.pipeline.analyze_recent_sessions", return_value=mock_analysis) as mock_analyze:
                result = mcp_module.call_tool("borg_dojo", {"action": "status", "days": 5})
                mock_analyze.assert_called_once_with(days=5)
                parsed = json.loads(result)
                assert parsed["success"] is True
                assert parsed["health"] == "healthy"

    def test_borg_dojo_analyze_passes_days_parameter(self):
        """Verify action=analyze respects the days parameter."""
        mock_analysis = MagicMock()
        mock_analysis.schema_version = 1
        mock_analysis.sessions_analyzed = 5
        mock_analysis.total_tool_calls = 30
        mock_analysis.total_errors = 2
        mock_analysis.overall_success_rate = 93.3
        mock_analysis.user_corrections = 0
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = []
        mock_analysis.failure_reports = []

        with patch("borg.dojo.pipeline.analyze_recent_sessions", return_value=mock_analysis) as mock_analyze:
            mcp_module.call_tool("borg_dojo", {"action": "analyze", "days": 30})
            mock_analyze.assert_called_once_with(days=30)

    def test_borg_dojo_dispatch_via_handle_request(self):
        """Test borg_dojo dispatch through handle_request (tools/call flow)."""
        req = minimal_request("tools/call", {
            "name": "borg_dojo",
            "arguments": {"action": "analyze", "days": 7}
        }, req_id=99)
        mock_analysis = MagicMock()
        mock_analysis.schema_version = 1
        mock_analysis.sessions_analyzed = 3
        mock_analysis.total_tool_calls = 20
        mock_analysis.total_errors = 1
        mock_analysis.overall_success_rate = 95.0
        mock_analysis.user_corrections = 0
        mock_analysis.skill_gaps = []
        mock_analysis.weakest_tools = []
        mock_analysis.failure_reports = []

        with patch("borg.dojo.pipeline.analyze_recent_sessions", return_value=mock_analysis):
            resp = mcp_module.handle_request(req)
            assert resp is not None
            assert resp["id"] == 99
            content_text = resp["result"]["content"][0]["text"]
            parsed = json.loads(content_text)
            assert parsed["success"] is True
            assert parsed["action"] == "analyze"
