"""
Tests for borg.core.v3_integration (BorgV3) and the V3 wiring in the MCP server.

Covers:
  - BorgV3.init / DB creation / schema
  - search() with and without task_context
  - record_outcome() and its side-effects
  - should_mutate() logic
  - get_dashboard() aggregation
  - run_maintenance()
  - record_feedback_signal()
  - Stub classes when real modules are unavailable
  - MCP server dispatch: borg_search with task_context, borg_dashboard, borg_feedback V3 params
  - Backward compatibility (V2 path still works when task_context absent)
"""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.integrations import mcp_server as mcp_module
from borg.core.v3_integration import BorgV3


# ============================================================================
# Helpers
# ============================================================================

def minimal_request(method: str, params: Dict[str, Any] = None, req_id: Any = 1) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": req_id,
    }


class _FakeSelector:
    """Fake contextual selector that records calls for assertions."""

    def __init__(self):
        self.outcomes: list = []
        self.select_called_with: list = []

    def record_outcome(self, pack_id, category, successful):
        self.outcomes.append((pack_id, category, successful))

    def record_outcomes(self, outcomes):
        for pack_id, category, successful in outcomes:
            self.record_outcome(pack_id, category, successful)

    def select(self, task_context, candidates, limit=1, seed=None):
        self.select_called_with.append((task_context, candidates, limit))
        return []


class _FakeMutationEngine:
    """Fake mutation engine that records calls."""

    def __init__(self, db=None):
        self.db = db
        self.outcomes: list = []
        self.ab_checked: int = 0
        self.drift_checked: bool = False
        self.mutations_suggested: list = []

    def record_outcome(self, pack_id, task_category, success, tokens_used=0, time_taken=0):
        self.outcomes.append((pack_id, task_category, success, tokens_used, time_taken))

    def check_ab_tests(self):
        self.ab_checked += 1
        return []

    def check_drift(self):
        self.drift_checked = True
        return []

    def suggest_mutations(self):
        return self.mutations_suggested


class _FakeFeedbackLoop:
    """Fake feedback loop that records calls."""

    def __init__(self, db=None):
        self.db = db
        self.records: list = []

    def record(self, pack_id, task_context, success, tokens_used=0, time_taken=0, agent_id=None):
        self.records.append((pack_id, task_context, success, tokens_used, time_taken, agent_id))

    def get_signals(self, pack_id=None):
        return []


# ============================================================================
# BorgV3 direct unit tests
# ============================================================================

class TestBorgV3Init:
    """Test BorgV3 initialization and DB creation."""

    def test_init_creates_db_file(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        assert Path(db).exists()

    def test_init_creates_tables(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        with sqlite3.connect(db) as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = {r[0] for r in cur.fetchall()}
        assert "outcomes" in tables
        assert "feedback_signals" in tables
        assert "ab_tests" in tables
        assert "pack_versions" in tables

    def test_init_idempotent(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3a = BorgV3(db_path=db)
        v3b = BorgV3(db_path=db)  # should not raise
        assert Path(db).exists()

    def test_stub_selector_used_when_contextual_selector_unavailable(self, tmp_path):
        """When contextual_selector is unavailable, _StubContextualSelector is used."""
        import borg.core.v3_integration as v3mod
        # Test the stub directly
        stub = v3mod._StubContextualSelector()
        assert hasattr(stub, "record_outcome")
        assert hasattr(stub, "select")
        stub.record_outcome("p1", "debug", True)
        assert stub.outcomes == [("p1", "debug", True)]
        results = stub.select({}, [], limit=1)
        assert results == []


class TestBorgV3Search:
    """Test search() with and without task_context."""

    def test_search_without_task_context_falls_back_to_v2(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        # Without task_context, should call V2 search (which may return empty)
        results = v3.search("debug")
        assert isinstance(results, list)

    def test_search_with_task_context_calls_selector(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        fake_sel = _FakeSelector()
        v3._set_selector(fake_sel)

        ctx = {"task_type": "debug", "keywords": ["error"]}
        results = v3.search("debug", task_context=ctx)
        # FakeSelector.select returns [] so results is []
        assert fake_sel.select_called_with

    def test_search_with_empty_task_context_uses_v2(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        results = v3.search("test", task_context={})
        assert isinstance(results, list)


class TestBorgV3RecordOutcome:
    """Test record_outcome() and its side-effects."""

    def test_record_outcome_persists_to_db(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        v3.record_outcome("pack-1", {"task_type": "debug"}, success=True, tokens_used=100, time_taken=1.5)

        with sqlite3.connect(db) as conn:
            cur = conn.execute("SELECT pack_id, success, tokens_used, time_taken, task_category FROM outcomes")
            rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "pack-1"
        assert rows[0][1] == 1
        assert rows[0][2] == 100
        assert rows[0][3] == 1.5
        assert rows[0][4] == "debug"

    def test_record_outcome_feeds_selector(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        fake_sel = _FakeSelector()
        v3._set_selector(fake_sel)

        v3.record_outcome("pack-x", {"task_type": "test"}, success=False)
        assert ("pack-x", "test", False) in fake_sel.outcomes

    def test_record_outcome_feeds_mutation_engine(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        fake_mut = _FakeMutationEngine()
        v3._set_mutation(fake_mut)

        v3.record_outcome("pack-y", {"task_type": "refactor"}, success=True, tokens_used=50, time_taken=2.0)
        assert ("pack-y", "refactor", True, 50, 2.0) in fake_mut.outcomes

    def test_record_outcome_feeds_feedback_loop(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        fake_fb = _FakeFeedbackLoop()
        v3._set_feedback(fake_fb)

        ctx = {"task_type": "deploy", "agent_id": "agent-42"}
        v3.record_outcome("pack-z", ctx, success=True, agent_id="agent-42")
        assert ("pack-z", ctx, True, 0, 0.0, "agent-42") in fake_fb.records

    def test_record_outcome_multiple(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        for i in range(5):
            v3.record_outcome(f"pack-{i}", {"task_type": "other"}, success=(i % 2 == 0))
        with sqlite3.connect(db) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM outcomes")
            assert cur.fetchone()[0] == 5


class TestBorgV3ShouldMutate:
    """Test should_mutate() logic."""

    def test_should_mutate_false_when_few_outcomes(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        v3.record_outcome("pack-1", {"task_type": "debug"}, success=False)
        v3.record_outcome("pack-1", {"task_type": "debug"}, success=False)
        assert v3.should_mutate("pack-1") is False

    def test_should_mutate_false_when_high_success_rate(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        for _ in range(5):
            v3.record_outcome("pack-2", {"task_type": "debug"}, success=True)
        assert v3.should_mutate("pack-2") is False

    def test_should_mutate_true_when_low_success_rate(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        # 5 failures, 0 successes = 0% success rate
        for _ in range(5):
            v3.record_outcome("pack-3", {"task_type": "debug"}, success=False)
        assert v3.should_mutate("pack-3") is True

    def test_should_mutate_false_for_unknown_pack(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        assert v3.should_mutate("nonexistent-pack") is False


class TestBorgV3Dashboard:
    """Test get_dashboard() aggregation."""

    def test_dashboard_empty(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        dash = v3.get_dashboard()
        assert dash["total_outcomes"] == 0
        assert dash["total_packs"] == 0
        assert dash["success_rate"] == 0.0
        assert dash["quality_scores"] == {}
        assert dash["drift_alerts"] == []

    def test_dashboard_with_data(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        v3.record_outcome("pack-a", {"task_type": "debug"}, success=True, tokens_used=100, time_taken=1.0)
        v3.record_outcome("pack-a", {"task_type": "debug"}, success=False, tokens_used=80, time_taken=0.8)
        dash = v3.get_dashboard()
        assert dash["total_outcomes"] == 2
        assert dash["total_packs"] == 1
        assert dash["success_rate"] == 0.5
        assert dash["avg_tokens"] == 90.0
        assert dash["avg_time"] == 0.9
        assert "pack-a" in dash["quality_scores"]

    def test_dashboard_drift_alerts(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        # Record 5 failures for pack-b → should trigger drift alert
        for _ in range(5):
            v3.record_outcome("pack-b", {"task_type": "test"}, success=False)
        dash = v3.get_dashboard()
        pack_b_drifts = [d for d in dash["drift_alerts"] if d.get("pack_id") == "pack-b"]
        assert len(pack_b_drifts) >= 1

    def test_run_maintenance(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        fake_mut = _FakeMutationEngine()
        fake_mut.mutations_suggested = [{"pack_id": "pack-x", "reason": "low success"}]
        v3._set_mutation(fake_mut)

        result = v3.run_maintenance()
        assert result["ab_tests_checked"] >= 0
        assert fake_mut.ab_checked >= 1
        assert fake_mut.drift_checked is True


class TestBorgV3FeedbackSignals:
    """Test record_feedback_signal()."""

    def test_record_feedback_signal(self, tmp_path):
        from borg.core.v3_integration import BorgV3
        db = str(tmp_path / "test_v3.db")
        v3 = BorgV3(db_path=db)
        v3.record_feedback_signal("frustration", 0.8, agent_id="agent-1", pack_id="pack-1")

        with sqlite3.connect(db) as conn:
            cur = conn.execute("SELECT signal_type, value, agent_id, pack_id FROM feedback_signals")
            row = cur.fetchone()
        assert row[0] == "frustration"
        assert row[1] == 0.8
        assert row[2] == "agent-1"
        assert row[3] == "pack-1"


# ============================================================================
# MCP server V3 wiring tests
# ============================================================================

class TestMCPV3Search:
    """Test V3 wiring in borg_search."""

    def test_borg_search_with_task_context(self):
        """When task_context is provided, uses V3 search path."""
        fake_v3 = MagicMock()
        fake_v3.search.return_value = [
            {"pack_id": "debug-pack", "name": "debug-pack", "category": "debug", "score": 0.9}
        ]

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            result = mcp_module.borg_search(
                query="fix error",
                task_context={"task_type": "debug", "keywords": ["error"]},
            )
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["contextual"] is True
        assert parsed["matches"][0]["pack_id"] == "debug-pack"
        fake_v3.search.assert_called_once()

    def test_borg_search_without_task_context_uses_v2(self):
        """When task_context is absent, falls through to V2 search."""
        fake_v3 = MagicMock()
        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            with patch("borg.core.search.borg_search", return_value='{"success": true, "matches": []}'):
                result = mcp_module.borg_search(query="debug")
        fake_v3.search.assert_not_called()

    def test_borg_search_dispatches_task_context_from_mcp(self):
        """Integration: MCP tools/call with task_context reaches V3."""
        fake_v3 = MagicMock()
        fake_v3.search.return_value = [{"pack_id": "x", "name": "x", "score": 1.0}]

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            req = minimal_request("tools/call", {
                "name": "borg_search",
                "arguments": {
                    "query": "deploy",
                    "task_context": {"task_type": "deploy", "keywords": ["k8s"]},
                },
            })
            resp = mcp_module.handle_request(req)
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["contextual"] is True


class TestMCPV3Suggest:
    """Test V3 wiring in borg_suggest."""

    def test_borg_suggest_with_frustration_uses_v3(self):
        """failure_count >= 2 triggers V3 suggestion path."""
        fake_v3 = MagicMock()
        fake_v3.search.return_value = [{"pack_id": "smart-pack", "name": "smart-pack", "score": 0.95}]

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            result = mcp_module.borg_suggest(
                context="The deployment keeps failing with the same error",
                failure_count=2,
            )
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["has_suggestion"] is True
        assert parsed["contextual"] is True

    def test_borg_suggest_without_frustration_uses_v2(self):
        """Low failure_count and no frustration keywords → V2 path only."""
        fake_v3 = MagicMock()
        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            with patch("borg.core.search.check_for_suggestion", return_value='{"has_suggestion": false}'):
                result = mcp_module.borg_suggest(
                    context="How do I structure a new project?",
                    failure_count=0,
                )
        fake_v3.search.assert_not_called()

    def test_extract_keywords(self):
        """_extract_keywords splits text into lowercase words > 2 chars."""
        words = mcp_module._extract_keywords("Fix TypeError in auth module")
        assert "fix" in words
        assert "typeerror" in words
        assert "auth" in words
        assert "module" in words
        # Short words filtered
        assert "in" not in words


class TestMCPV3Dashboard:
    """Test borg_dashboard wiring."""

    def test_borg_dashboard_returns_stats(self):
        fake_dash = {
            "total_outcomes": 10,
            "total_packs": 3,
            "success_rate": 0.7,
            "avg_tokens": 150.0,
            "avg_time": 2.5,
            "quality_scores": {"pack-a": {"outcomes": 5, "success_rate": 80.0}},
            "drift_alerts": [],
            "mutation_stats": {"suggested": 1, "running": 0, "completed": 0, "failed": 0},
            "ab_tests": [],
            "mutation_suggestions": [],
        }
        fake_v3 = MagicMock()
        fake_v3.get_dashboard.return_value = fake_dash

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            result = mcp_module.borg_dashboard()
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["total_outcomes"] == 10
        assert parsed["success_rate"] == 0.7

    def test_borg_dashboard_via_mcp_dispatch(self):
        fake_v3 = MagicMock()
        fake_v3.get_dashboard.return_value = {"total_outcomes": 0, "total_packs": 0, "success_rate": 0.0, "avg_tokens": 0.0, "avg_time": 0.0, "quality_scores": {}, "drift_alerts": [], "mutation_stats": {"suggested": 0, "running": 0, "completed": 0, "failed": 0}, "ab_tests": [], "mutation_suggestions": []}

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            req = minimal_request("tools/call", {"name": "borg_dashboard", "arguments": {}})
            resp = mcp_module.handle_request(req)
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["success"] is True
        assert "total_outcomes" in content


class TestMCPV3Feedback:
    """Test borg_feedback V3 wiring."""

    def test_borg_feedback_calls_v3_record_outcome(self):
        """borg_feedback records outcome to V3 when session found."""
        fake_v3 = MagicMock()
        fake_session = {
            "pack_id": "test-pack",
            "pack_name": "test-pack",
            "pack_version": "1.0",
            "task": "fix bug",
            "problem_class": "debug",
            "execution_log_path": "",
            "phase_results": [{"phase": "phase-1", "status": "passed"}],
        }

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            with patch.object(mcp_module, "_get_core_modules") as mock_core:
                mock_session = MagicMock()
                mock_session.get_active_session.return_value = fake_session
                mock_session.load_session.return_value = None
                mock_session.compute_log_hash.return_value = "abc123"
                mock_core.return_value = (MagicMock(), MagicMock(), mock_session, MagicMock(), MagicMock())

                with patch("uuid.uuid4", return_value=MagicMock(hex="abc123")):
                    with patch.object(Path, "write_text"):
                        result = mcp_module.borg_feedback(
                            session_id="sess-1",
                            success=False,
                            tokens_used=200,
                            time_taken=3.5,
                            task_context={"task_type": "debug"},
                        )
        # record_outcome should have been called on the fake V3
        fake_v3.record_outcome.assert_called_once()
        call_kwargs = fake_v3.record_outcome.call_args
        assert call_kwargs.kwargs["pack_id"] == "test-pack"
        assert call_kwargs.kwargs["success"] is False
        assert call_kwargs.kwargs["tokens_used"] == 200
        assert call_kwargs.kwargs["time_taken"] == 3.5


class TestMCPToolsList:
    """Test that TOOLS list includes the new tools with updated schemas."""

    def test_borg_search_tool_has_task_context_param(self):
        req = minimal_request("tools/list", {}, req_id=1)
        resp = mcp_module.handle_request(req)
        tools = resp["result"]["tools"]
        search_tool = next(t for t in tools if t["name"] == "borg_search")
        props = search_tool["inputSchema"]["properties"]
        assert "task_context" in props

    def test_borg_feedback_tool_has_v3_params(self):
        req = minimal_request("tools/list", {}, req_id=2)
        resp = mcp_module.handle_request(req)
        tools = resp["result"]["tools"]
        fb_tool = next(t for t in tools if t["name"] == "borg_feedback")
        props = fb_tool["inputSchema"]["properties"]
        assert "success" in props
        assert "tokens_used" in props
        assert "time_taken" in props
        assert "task_context" in props

    def test_borg_dashboard_tool_exists(self):
        req = minimal_request("tools/list", {}, req_id=3)
        resp = mcp_module.handle_request(req)
        tools = resp["result"]["tools"]
        names = {t["name"] for t in tools}
        assert "borg_dashboard" in names

    def test_tools_count_includes_borg_dashboard(self):
        req = minimal_request("tools/list", {}, req_id=4)
        resp = mcp_module.handle_request(req)
        # Count tools from TOOLS list (borg_search, borg_pull, borg_try, borg_init,
        # borg_apply, borg_publish, borg_feedback, borg_suggest, borg_observe,
        # borg_convert, borg_generate x2, borg_context, borg_recall, borg_record_failure,
        # borg_delete_failure, borg_reputation, borg_analytics, borg_dashboard, borg_dojo)
        assert len(resp["result"]["tools"]) == 21


class TestBorgV3EndToEnd:
    """End-to-end test: search → select → record_outcome → run_maintenance → check results."""

    def test_e2e_learning_loop(self, tmp_path):
        """Full E2E flow through the V3 learning loop."""
        from borg.core.v3_integration import BorgV3

        db = str(tmp_path / "test_e2e.db")
        v3 = BorgV3(db_path=db)

        fake_sel = _FakeSelector()
        fake_mut = _FakeMutationEngine()
        fake_fb = _FakeFeedbackLoop()
        v3._set_selector(fake_sel)
        v3._set_mutation(fake_mut)
        v3._set_feedback(fake_fb)

        # Step 1: search returns candidate packs
        ctx = {"task_type": "debug", "keywords": ["error"]}
        fake_sel.select_called_with.clear()
        results = v3.search("fix error", task_context=ctx)
        # FakeSelector.select was called with task_context
        assert len(fake_sel.select_called_with) == 1

        # Step 2: record_outcome for a selected pack
        v3.record_outcome("pack-test", ctx, success=True, tokens_used=100, time_taken=1.5)

        # Verify DB persistence
        with sqlite3.connect(db) as conn:
            cur = conn.execute("SELECT pack_id, success, tokens_used, time_taken FROM outcomes")
            rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "pack-test"
        assert rows[0][1] == 1
        assert rows[0][2] == 100
        assert rows[0][3] == 1.5

        # Verify selector was fed
        assert ("pack-test", "debug", True) in fake_sel.outcomes

        # Verify feedback loop was fed
        assert any(r[0] == "pack-test" for r in fake_fb.records)

        # Step 3: record a failure
        v3.record_outcome("pack-test", ctx, success=False, tokens_used=50, time_taken=0.8)

        # Step 4: run_maintenance triggers mutation engine checks
        maint_result = v3.run_maintenance()
        assert maint_result["ab_tests_checked"] >= 0
        assert fake_mut.ab_checked >= 1
        assert fake_mut.drift_checked is True

        # Step 5: get_dashboard shows the data
        dash = v3.get_dashboard()
        assert dash["total_outcomes"] == 2
        assert dash["total_packs"] == 1
        assert "pack-test" in dash["quality_scores"]


class TestMaintenanceCounterPersistence:
    """Test that the maintenance counter persists across BorgV3 instances."""

    def test_maintenance_counter_persists(self, tmp_path):
        """Counter stored in DB survives instance restarts and resets correctly."""
        db_path = str(tmp_path / "test_v3.db")

        # Instance 1: increment counter 3 times
        v3_a = BorgV3(db_path=db_path)
        assert v3_a._get_maintenance_counter() == 0
        v3_a._inc_maintenance_counter()
        v3_a._inc_maintenance_counter()
        count = v3_a._inc_maintenance_counter()
        assert count == 3

        # Instance 2 (same DB): verify count = 3
        v3_b = BorgV3(db_path=db_path)
        assert v3_b._get_maintenance_counter() == 3

        # Instance 3: increment more
        v3_b._inc_maintenance_counter()
        assert v3_b._get_maintenance_counter() == 4

        # Reset and verify = 0
        v3_b._reset_maintenance_counter()
        assert v3_b._get_maintenance_counter() == 0

        # New instance after reset confirms 0
        v3_c = BorgV3(db_path=db_path)
        assert v3_c._get_maintenance_counter() == 0

    def test_maintenance_counter_default_zero_on_new_db(self, tmp_path):
        """Fresh DB with no counter entry returns 0."""
        db_path = str(tmp_path / "fresh.db")
        v3 = BorgV3(db_path=db_path)
        assert v3._get_maintenance_counter() == 0

    def test_maintenance_counter_after_many_increments(self, tmp_path):
        """Counter handles many increments correctly."""
        db_path = str(tmp_path / "many.db")
        v3 = BorgV3(db_path=db_path)

        for i in range(100):
            v3._inc_maintenance_counter()

        assert v3._get_maintenance_counter() == 100

        v3._reset_maintenance_counter()
        assert v3._get_maintenance_counter() == 0


class TestBackwardCompatibility:
    """Test that V2 (non-V3) paths still work without task_context."""

    def test_borg_search_empty_query_still_works(self):
        """Empty query with no task_context returns pack list via V2 path."""
        with patch("borg.core.uri.get_available_pack_names", return_value=["pack-a", "pack-b"]):
            result = mcp_module.borg_search(query="")
        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["total"] == 2

    def test_borg_feedback_backward_compatible_without_v3_params(self):
        """borg_feedback works with just session_id (existing behaviour)."""
        fake_v3 = MagicMock()
        fake_session = {
            "pack_id": "legacy-pack",
            "pack_name": "legacy-pack",
            "pack_version": "1.0",
            "task": "test",
            "problem_class": "testing",
            "phase_results": [{"phase": "phase-1", "status": "passed"}],
        }

        with patch.object(mcp_module, "_get_borg_v3", return_value=fake_v3):
            with patch.object(mcp_module, "_get_core_modules") as mock_core:
                mock_session = MagicMock()
                mock_session.get_active_session.return_value = fake_session
                mock_session.load_session.return_value = None
                mock_session.compute_log_hash.return_value = "abc"
                mock_core.return_value = (MagicMock(), MagicMock(), mock_session, MagicMock(), MagicMock())

                with patch("uuid.uuid4", return_value=MagicMock(hex="deadbeef")):
                    with patch.object(Path, "write_text"):
                        result = mcp_module.borg_feedback(session_id="sess-old")

        parsed = json.loads(result)
        assert parsed["success"] is True
        assert parsed["feedback_id"]  # feedback was generated
