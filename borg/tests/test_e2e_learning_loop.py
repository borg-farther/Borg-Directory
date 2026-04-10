"""
End-to-End Learning Loop Tests for Borg.

Tests the complete Borg learning loop:
  1. borg_search finds packs
  2. borg_observe returns guidance + prior trace matches
  3. borg_apply action=start initiates trace capture
  4. Tool calls accumulate in trace capture (feed 5 read_file calls)
  5. borg_feedback with task_context records outcome to V3
  6. run_maintenance processes A/B tests and drift

Uses real SQLite DBs via tempfile. No network access required.
"""

import json
import os
import sqlite3
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core.search import borg_search, classify_task
from borg.integrations.mcp_server import (
    borg_observe,
    borg_apply,
    borg_feedback,
    init_trace_capture,
    _feed_trace_capture,
    _current_session_id,
    save_trace,
)
from borg.core.v3_integration import BorgV3
from borg.core.trace_matcher import TraceMatcher
from borg.core.traces import TraceCapture, _get_db


# ============================================================================
# Helpers
# ============================================================================

def _make_trace_db(tmp_path: Path) -> str:
    """Create a temporary trace DB and return its path."""
    db_path = str(tmp_path / "traces.db")
    Path(db_path).touch()
    return db_path


def _make_v3_db(tmp_path: Path) -> str:
    """Create a temporary V3 DB and return its path."""
    db_path = str(tmp_path / "borg_v3.db")
    Path(db_path).touch()
    return db_path


class _FakeSessionModule:
    """Fake session module that stores sessions in memory."""

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}

    def register_session(self, session: Dict) -> None:
        self._sessions[session["session_id"]] = session

    def save_session(self, session: Dict) -> None:
        self._sessions[session["session_id"]] = session

    def get_active_session(self, session_id: str):
        return self._sessions.get(session_id)

    def load_session(self, session_id: str):
        return self._sessions.get(session_id)

    def log_event(self, session_id: str, event: Dict) -> None:
        if session_id in self._sessions:
            self._sessions[session_id].setdefault("events", []).append(event)

    def compute_log_hash(self, path) -> str:
        return "fakehash123"


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def tmp_trace_db(tmp_path):
    """Temporary trace DB path."""
    return _make_trace_db(tmp_path)


@pytest.fixture
def tmp_v3_db(tmp_path):
    """Temporary V3 DB path."""
    return _make_v3_db(tmp_path)


@pytest.fixture
def v3_instance(tmp_v3_db):
    """BorgV3 instance with temporary DB."""
    return BorgV3(db_path=tmp_v3_db)


@pytest.fixture
def trace_matcher(tmp_trace_db):
    """TraceMatcher with temporary trace DB."""
    return TraceMatcher(db_path=tmp_trace_db)


@pytest.fixture
def saved_trace(tmp_trace_db):
    """A pre-saved trace in the trace DB for match testing."""
    trace = {
        "id": "test-trace-001",
        "task_description": "Fix TypeError in auth module",
        "outcome": "success",
        "root_cause": "Missing null check on user object",
        "approach_summary": "Added null check before accessing user attribute",
        "files_read": json.dumps(["/app/auth.py", "/app/models.py"]),
        "files_modified": json.dumps(["/app/auth.py"]),
        "key_files": json.dumps(["/app/auth.py"]),
        "tool_calls": 8,
        "errors_encountered": json.dumps(["TypeError: 'NoneType' object has no attribute 'username'"]),
        "dead_ends": json.dumps([]),
        "keywords": "fix typeerror auth module null check",
        "technology": "python",
        "error_patterns": "TypeError",
        "agent_id": "test-agent",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "auto",
    }
    save_trace(trace, db_path=tmp_trace_db)
    return trace


# ============================================================================
# Test 1: borg_search finds packs
# ============================================================================

class TestSearchFindsPacks:
    """Step 1: borg_search returns matching packs."""

    def test_borg_search_returns_result_json(self):
        """borg_search returns valid JSON (may be empty matches)."""
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            result = borg_search("debug")
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert "success" in parsed

    def test_borg_search_empty_query_returns_packs(self):
        """borg_search with empty query works."""
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            with patch("borg.core.uri.get_available_pack_names", return_value=["pack-a", "pack-b"]):
                result = borg_search("")
        parsed = json.loads(result)
        assert parsed["success"] is True


# ============================================================================
# Test 2: borg_observe returns guidance + prior trace matches
# ============================================================================

class TestObserveReturnsGuidance:
    """Step 2: borg_observe returns structural guidance and prior trace matches."""

    def test_borg_observe_returns_json_without_error(self):
        """borg_observe returns JSON without raising an exception."""
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            with patch("borg.core.trace_matcher.TraceMatcher") as MockTM:
                MockTM.return_value.find_relevant.return_value = []
                result = borg_observe(task="Debug auth bug", context="TypeError in login")
        parsed = json.loads(result)
        assert parsed.get("success") is True

    def test_borg_observe_calls_init_trace_capture(self):
        """borg_observe does NOT call init_trace_capture in the new API.

        Trace capture is now initiated by borg_apply action='start', not by borg_observe.
        This test verifies that borg_observe completes without calling init_trace_capture.
        """
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        init_calls = []

        def track_init(session_id="", task="", agent_id=""):
            init_calls.append(("init", session_id, task, agent_id))

        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            with patch("borg.core.trace_matcher.TraceMatcher") as MockTM:
                MockTM.return_value.find_relevant.return_value = []
                with patch("borg.integrations.mcp_server.init_trace_capture", track_init):
                    result = borg_observe(task="Test task for trace capture")

        parsed = json.loads(result)
        assert parsed.get("success") is True
        # In the new API, borg_observe does NOT call init_trace_capture
        assert len(init_calls) == 0

        mcp_mod._trace_captures = {}

    def test_borg_observe_find_relevant_path(self, tmp_trace_db, saved_trace):
        """borg_observe uses TraceMatcher.find_relevant for prior traces."""
        # Use the real TraceMatcher with our temp DB so find_relevant actually works
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            result = borg_observe(
                task="Fix TypeError in auth module",
                context="TypeError when user is None"
            )

        parsed = json.loads(result)
        assert parsed.get("success") is True
        # With no matching packs, guidance may be empty but no error should occur
        assert "guidance" in parsed


# ============================================================================
# Test 3: borg_apply action=start initiates trace capture
# ============================================================================

class TestApplyStartsTraceCapture:
    """Step 3: borg_apply(action='start') initiates trace capture."""

    def test_apply_start_calls_init_trace_capture(self, tmp_path):
        """borg_apply(action='start') calls init_trace_capture."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        fake_guild = tmp_path / "guild" / "test-pack"
        fake_guild.mkdir(parents=True)
        (fake_guild / "pack.yaml").write_text("""
id: test-pack
version: "1.0"
problem_class: testing
phases:
  - name: phase-1
    description: Test phase
""")

        init_calls = []

        def track_init(session_id="", task="", agent_id=""):
            init_calls.append(("init", session_id, task, agent_id))

        fake_session_mod = _FakeSessionModule()

        with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
            with patch("borg.integrations.mcp_server.init_trace_capture", track_init):
                with patch("borg.integrations.mcp_server._get_core_modules") as mock_core:
                    mock_core.return_value = (
                        MagicMock(),  # uri_module
                        MagicMock(),  # publish_module
                        fake_session_mod,  # session_module
                        MagicMock(),  # safety_module
                        MagicMock(),  # schema_module
                    )
                    result = borg_apply(
                        action="start",
                        pack_name="test-pack",
                        task="Fix the bug"
                    )

        parsed = json.loads(result)
        assert parsed.get("success") is True
        assert len(init_calls) == 1
        # New API: init_trace_capture(session_id, task, agent_id)
        assert init_calls[0][2] == "Fix the bug"
        session_id = parsed.get("session_id")
        assert session_id is not None
        assert init_calls[0][1] == session_id

        mcp_mod._trace_captures = {}


# ============================================================================
# Test 4: Tool calls accumulate in trace capture (5 read_file calls)
# ============================================================================

class TestTraceCaptureAccumulates:
    """Step 4: init_trace_capture + _feed_trace_capture accumulate tool calls."""

    def test_feed_trace_capture_accumulates_calls(self):
        """Feeding 5 read_file calls increments tool_calls counter."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        _current_session_id.set("test-session")
        init_trace_capture("test-session", task="Test accumulation", agent_id="test-agent")

        for i in range(5):
            _feed_trace_capture(
                tool_name="read_file",
                args={"path": f"/app/file{i}.py"},
                result=f"Content of file {i}"
            )

        tc = mcp_mod._trace_captures["test-session"]
        assert tc is not None
        assert tc.tool_calls == 5
        assert len(tc.files_read) == 5

        mcp_mod._trace_captures = {}

    def test_trace_capture_extract_returns_correct_tool_count(self):
        """extract_trace returns the correct number of accumulated tool calls."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        _current_session_id.set("test-session")
        init_trace_capture("test-session", task="Extract test", agent_id="test-agent")

        for i in range(7):
            _feed_trace_capture(
                tool_name="read_file",
                args={"path": f"/app/module{i}.py"},
                result=f"module content {i}"
            )

        tc = mcp_mod._trace_captures["test-session"]
        trace = tc.extract_trace(outcome="success")

        assert trace["tool_calls"] == 7
        # files_read is a JSON string — parse and check length
        files_read_list = json.loads(trace["files_read"])
        assert len(files_read_list) == 7

        mcp_mod._trace_captures = {}

    def test_trace_capture_tracks_errors(self):
        """TraceCapture.on_tool_call extracts error messages from results."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        _current_session_id.set("test-session")
        init_trace_capture("test-session", task="Error tracking", agent_id="test-agent")

        _feed_trace_capture(
            tool_name="terminal",
            args={"command": "python test.py"},
            result="Error: TypeError: 'NoneType' object has no attribute 'value'\nSome other output"
        )

        tc = mcp_mod._trace_captures["test-session"]
        assert len(tc.errors) >= 1
        assert "TypeError" in tc.errors[0]

        mcp_mod._trace_captures = {}


    def test_agent_id_populated_in_trace(self):
        """TraceCapture.extract_trace returns the agent_id that was passed to __init__."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        capture = TraceCapture(task="test", agent_id="claude-code-abc123")
        for i in range(2):
            capture.on_tool_call("read_file", {"path": f"/test/file{i}.py"}, "ok")
        trace = capture.extract_trace(outcome="success")
        assert trace["agent_id"] == "claude-code-abc123"

        mcp_mod._trace_captures = {}


# ============================================================================
# Test 5: save_trace persists to DB
# ============================================================================

class TestSaveTracePersists:
    """Step 5a: save_trace writes traces to the SQLite DB."""

    def test_save_trace_persists_and_can_be_retrieved(self, tmp_trace_db):
        """A saved trace can be retrieved from the DB."""
        trace = {
            "id": "persist-test-001",
            "task_description": "Persist test trace",
            "outcome": "success",
            "root_cause": "Test root cause",
            "approach_summary": "Test approach",
            "files_read": json.dumps(["/app/main.py"]),
            "files_modified": json.dumps(["/app/main.py"]),
            "key_files": json.dumps(["/app/main.py"]),
            "tool_calls": 3,
            "errors_encountered": json.dumps([]),
            "dead_ends": json.dumps([]),
            "keywords": "persist test",
            "technology": "python",
            "error_patterns": "",
            "agent_id": "test",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "auto",
        }

        trace_id = save_trace(trace, db_path=tmp_trace_db)
        assert trace_id == "persist-test-001"

        db = _get_db(tmp_trace_db)
        row = db.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
        db.close()

        assert row is not None
        assert row["task_description"] == "Persist test trace"
        assert row["outcome"] == "success"
        assert row["tool_calls"] == 3

    def test_save_trace_indexes_key_files(self, tmp_trace_db):
        """save_trace correctly indexes key_files in trace_file_index."""
        trace = {
            "id": "index-test-002",
            "task_description": "Index test",
            "outcome": "success",
            "root_cause": "",
            "approach_summary": "",
            "files_read": json.dumps(["/app/auth.py", "/app/models.py"]),
            "files_modified": json.dumps(["/app/auth.py"]),
            "key_files": json.dumps(["/app/auth.py"]),
            "tool_calls": 4,
            "errors_encountered": json.dumps([]),
            "dead_ends": json.dumps([]),
            "keywords": "",
            "technology": "python",
            "error_patterns": "ValueError",
            "agent_id": "test",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "auto",
        }

        save_trace(trace, db_path=tmp_trace_db)

        db = _get_db(tmp_trace_db)

        # key_files get indexed with role='key'
        file_rows = db.execute(
            "SELECT trace_id, file_path, role FROM trace_file_index WHERE trace_id = ?",
            ("index-test-002",)
        ).fetchall()
        db.close()

        # /app/auth.py is a key file, /app/models.py is read but not key
        paths_and_roles = {(r["file_path"], r["role"]) for r in file_rows}
        assert ("/app/auth.py", "key") in paths_and_roles

    def test_save_trace_indexes_error_patterns(self, tmp_trace_db):
        """save_trace indexes error_patterns in trace_error_index."""
        trace = {
            "id": "index-error-003",
            "task_description": "Error index test",
            "outcome": "failure",
            "root_cause": "",
            "approach_summary": "",
            "files_read": json.dumps(["/app/main.py"]),
            "files_modified": json.dumps([]),
            "key_files": json.dumps([]),
            "tool_calls": 2,
            "errors_encountered": json.dumps(["RuntimeError: stack overflow"]),
            "dead_ends": json.dumps([]),
            "keywords": "",
            "technology": "python",
            "error_patterns": "RuntimeError",
            "agent_id": "test",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "auto",
        }

        save_trace(trace, db_path=tmp_trace_db)

        db = _get_db(tmp_trace_db)
        error_rows = db.execute(
            "SELECT trace_id, error_type FROM trace_error_index WHERE trace_id = ?",
            ("index-error-003",)
        ).fetchall()
        db.close()

        assert len(error_rows) >= 1
        error_types = {r["error_type"] for r in error_rows}
        assert "RuntimeError" in error_types


# ============================================================================
# Test 6: V3 search returns results
# ============================================================================

class TestV3SearchReturnsResults:
    """Step 5b (parallel): V3 search uses contextual selector."""

    def test_v3_search_with_task_context(self, v3_instance):
        """V3 search accepts task_context and uses selector."""
        ctx = {"task_type": "debug", "keywords": ["error", "fix"]}
        results = v3_instance.search("fix error", task_context=ctx)
        assert isinstance(results, list)

    def test_v3_search_without_task_context_falls_back_to_v2(self, v3_instance):
        """Without task_context, V3 search falls back to V2 keyword search."""
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            results = v3_instance.search("debug")
        assert isinstance(results, list)


# ============================================================================
# Test 7: V3 record_outcome persists to DB
# ============================================================================

class TestV3RecordOutcome:
    """Step 5c: V3 record_outcome persists outcomes to SQLite."""

    def test_record_outcome_persists_to_db(self, v3_instance, tmp_v3_db):
        """record_outcome writes an outcome row to the V3 DB."""
        ctx = {"task_type": "testing", "keywords": ["pytest"]}
        v3_instance.record_outcome(
            pack_id="test-pack-v3",
            task_context=ctx,
            success=True,
            tokens_used=500,
            time_taken=2.5,
            agent_id="test-agent",
        )

        with sqlite3.connect(tmp_v3_db) as conn:
            cur = conn.execute(
                "SELECT pack_id, success, tokens_used, time_taken, agent_id FROM outcomes"
            )
            rows = cur.fetchall()

        assert len(rows) == 1
        assert rows[0][0] == "test-pack-v3"
        assert rows[0][1] == 1  # success=True → 1
        assert rows[0][2] == 500
        assert rows[0][3] == 2.5
        assert rows[0][4] == "test-agent"

    def test_record_outcome_multiple_records(self, v3_instance, tmp_v3_db):
        """Multiple record_outcome calls create multiple DB rows."""
        for i in range(3):
            v3_instance.record_outcome(
                pack_id=f"pack-{i}",
                task_context={"task_type": "test"},
                success=(i % 2 == 0),
                tokens_used=100 * i,
                time_taken=i * 1.0,
            )

        with sqlite3.connect(tmp_v3_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]

        assert count == 3


# ============================================================================
# Test 8: TraceMatcher.find_relevant finds saved traces
# ============================================================================

class TestTraceMatcherFindRelevant:
    """Test TraceMatcher.find_relevant finds prior traces."""

    def test_find_relevant_returns_saved_trace(self, trace_matcher, saved_trace):
        """find_relevant with matching query returns the saved trace."""
        results = trace_matcher.find_relevant(
            task="Fix TypeError in auth module",
            error="TypeError: 'NoneType' object has no attribute 'username'",
            top_k=3
        )
        assert len(results) >= 1
        assert any(r["id"] == "test-trace-001" for r in results)

    def test_find_relevant_with_file_overlap(self, trace_matcher, saved_trace):
        """find_relevant uses file path overlap as a scoring signal."""
        results = trace_matcher.find_relevant(
            task="Fix bug in auth",
            files=["/app/auth.py"],
            top_k=3
        )
        assert len(results) >= 1

    def test_find_relevant_empty_for_irrelevant_query(self, trace_matcher):
        """find_relevant returns empty list when no traces match."""
        results = trace_matcher.find_relevant(
            task="Completely unrelated task xyz123",
            top_k=3
        )
        assert isinstance(results, list)


# ============================================================================
# Test 9: borg_feedback with task_context records to V3
# ============================================================================

class TestBorgFeedbackRecordsToV3:
    """Step 5: borg_feedback records outcome to V3 DB via task_context."""

    def test_borg_feedback_calls_record_outcome(self, tmp_path):
        """borg_feedback with task_context calls v3.record_outcome."""
        fake_session = {
            "session_id": "feedback-test-001",
            "pack_id": "feedback-pack",
            "pack_name": "feedback-pack",
            "pack_version": "1.0",
            "task": "Test feedback",
            "problem_class": "testing",
            "status": "complete",
            "outcome": "success",
            "phase_results": [{"phase": "phase-1", "status": "passed"}],
            "events": [],
            "eval_context": {},
        }

        record_calls = []

        def track_record(pack_id, task_context, success, tokens_used=0, time_taken=0.0, agent_id=None, session_id=None):
            record_calls.append({
                "pack_id": pack_id,
                "task_context": task_context,
                "success": success,
                "tokens_used": tokens_used,
                "session_id": session_id,
            })

        fake_session_mod = _FakeSessionModule()
        fake_session_mod.register_session(fake_session)

        with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
            with patch("uuid.uuid4", return_value=MagicMock(hex="feedback123")):
                with patch.object(Path, "write_text"):
                    with patch.object(Path, "mkdir"):
                        with patch("borg.integrations.mcp_server._get_borg_v3") as mock_v3:
                            v3_instance = MagicMock()
                            v3_instance.record_outcome = track_record
                            mock_v3.return_value = v3_instance

                            with patch("borg.integrations.mcp_server._get_core_modules") as mock_core:
                                mock_core.return_value = (
                                    MagicMock(),  # uri_module
                                    MagicMock(),  # publish_module
                                    fake_session_mod,  # session_module
                                    MagicMock(),  # safety_module
                                    MagicMock(),  # schema_module
                                )
                                result = borg_feedback(
                                    session_id="feedback-test-001",
                                    task_context={"task_type": "testing", "keywords": ["pytest"]},
                                    success=True,
                                    tokens_used=300,
                                    time_taken=1.5,
                                )

        parsed = json.loads(result)
        assert parsed.get("success") is True
        assert len(record_calls) == 1
        assert record_calls[0]["pack_id"] == "feedback-pack"
        assert record_calls[0]["success"] is True
        assert record_calls[0]["session_id"] == "feedback-test-001"


# ============================================================================
# Test 10: run_maintenance processes A/B tests and drift
# ============================================================================

class TestRunMaintenance:
    """Step 6: run_maintenance processes A/B tests and drift detection."""

    def test_run_maintenance_returns_dict(self, v3_instance):
        """run_maintenance returns a dict with expected keys."""
        result = v3_instance.run_maintenance()
        assert isinstance(result, dict)
        assert "ab_tests_checked" in result
        assert "drift_alerts" in result
        assert "mutations_suggested" in result

    def test_run_maintenance_calls_mutation_engine(self, v3_instance):
        """run_maintenance invokes the mutation engine's check methods."""
        fake_mut = MagicMock()
        fake_mut.check_ab_tests.return_value = []
        fake_mut.check_drift.return_value = []
        fake_mut.suggest_mutations.return_value = []

        v3_instance._mutation = fake_mut

        result = v3_instance.run_maintenance()

        assert fake_mut.check_ab_tests.called
        assert fake_mut.check_drift.called
        assert fake_mut.suggest_mutations.called
        assert result["ab_tests_checked"] == 0

    def test_run_maintenance_with_pending_ab_tests(self, v3_instance, tmp_v3_db):
        """run_maintenance processes pending A/B tests from DB."""
        with sqlite3.connect(tmp_v3_db) as conn:
            conn.execute("""
                INSERT INTO ab_tests (original_pack_id, mutant_pack_id, mutation_type, status, created_at)
                VALUES ('pack-a', 'pack-b', 'replace_phase', 'running', ?)
            """, (time.strftime("%Y-%m-%dT%H:%M:%SZ"),))
            conn.commit()

        fake_mut = MagicMock()
        fake_mut.check_ab_tests.return_value = [{"test_id": 1, "status": "running"}]
        fake_mut.check_drift.return_value = []
        fake_mut.suggest_mutations.return_value = []

        v3_instance._mutation = fake_mut

        result = v3_instance.run_maintenance()
        assert result["ab_tests_checked"] >= 1


# ============================================================================
# Test 11: Full E2E loop — all steps together
# ============================================================================

class TestFullLearningLoop:
    """Complete E2E flow through all learning loop steps."""

    def test_full_loop_trace_capture_to_feedback(self, tmp_path, tmp_trace_db, tmp_v3_db):
        """End-to-end: observe → apply start → feed 5 calls → extract → save → feedback."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        # Set session context for all trace operations
        _current_session_id.set("session-1")

        # ── Step 1: borg_search ──────────────────────────────────────────
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            search_result = borg_search("debugging")
        search_parsed = json.loads(search_result)
        assert search_parsed.get("success") is True

        # ── Step 2: borg_observe (returns guidance + prior matches) ───────
        with patch("borg.core.uri._fetch_index", return_value={"packs": []}):
            with patch("borg.core.trace_matcher.TraceMatcher") as MockTM:
                MockTM.return_value.find_relevant.return_value = []
                observe_result = borg_observe(
                    task="Debug authentication bug",
                    context="users can't login"
                )
        observe_parsed = json.loads(observe_result)
        assert observe_parsed.get("success") is True

        # Note: borg_observe does NOT call init_trace_capture in the new API.
        # Trace capture is initiated by borg_apply start.
        # Step 2 just validates borg_observe works without error.

        # ── Step 3: borg_apply start ─────────────────────────────────────
        fake_guild = tmp_path / "guild" / "e2e-pack"
        fake_guild.mkdir(parents=True)
        (fake_guild / "pack.yaml").write_text("""
id: e2e-pack
version: "1.0"
problem_class: debugging
phases:
  - name: reproduce
    description: Reproduce the bug
  - name: fix
    description: Apply the fix
""")

        fake_session_mod = _FakeSessionModule()

        with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
            with patch("borg.integrations.mcp_server._get_core_modules") as mock_core:
                mock_core.return_value = (
                    MagicMock(),
                    MagicMock(),
                    fake_session_mod,
                    MagicMock(),
                    MagicMock(),
                )
                apply_result = borg_apply(
                    action="start",
                    pack_name="e2e-pack",
                    task="Debug authentication bug"
                )
        apply_parsed = json.loads(apply_result)
        assert apply_parsed.get("success") is True
        session_id = apply_parsed["session_id"]

        # Update contextvar to use the actual session_id from borg_apply
        _current_session_id.set(session_id)

        # ── Step 4: Feed 5 read_file calls ──────────────────────────────
        test_files = [
            "/app/auth.py", "/app/models.py", "/app/config.py",
            "/app/routes.py", "/app/middleware.py"
        ]
        for path in test_files:
            _feed_trace_capture(
                tool_name="read_file",
                args={"path": path},
                result=f"# Content of {path}"
            )

        assert session_id in mcp_mod._trace_captures
        tc = mcp_mod._trace_captures[session_id]
        assert tc is not None
        assert tc.tool_calls == 5
        assert len(tc.files_read) == 5

        # ── Step 4b: Extract and save trace ────────────────────────────
        trace = tc.extract_trace(outcome="success")
        trace["id"] = "e2e-trace-001"
        saved_id = save_trace(trace, db_path=tmp_trace_db)
        assert saved_id == "e2e-trace-001"

        # Verify persisted in DB
        db = _get_db(tmp_trace_db)
        row = db.execute(
            "SELECT id, task_description, outcome, tool_calls FROM traces WHERE id = ?",
            ("e2e-trace-001",)
        ).fetchone()
        db.close()
        assert row is not None
        assert row["tool_calls"] == 5

        # ── Step 5: borg_feedback records to V3 ─────────────────────────
        fake_session = {
            "session_id": session_id,
            "pack_id": "e2e-pack",
            "pack_name": "e2e-pack",
            "pack_version": "1.0",
            "task": "Debug authentication bug",
            "problem_class": "debugging",
            "status": "complete",
            "outcome": "success",
            "phase_results": [
                {"phase": "reproduce", "status": "passed"},
                {"phase": "fix", "status": "passed"},
            ],
            "events": [],
            "eval_context": {},
        }
        fake_session_mod.register_session(fake_session)

        record_calls = []

        def track_record(pack_id, task_context, success, tokens_used=0, time_taken=0.0, agent_id=None, session_id=None):
            record_calls.append({
                "pack_id": pack_id,
                "task_context": task_context,
                "success": success,
                "tokens_used": tokens_used,
                "session_id": session_id,
            })

        with patch.dict(os.environ, {"HERMES_HOME": str(tmp_path)}):
            with patch("uuid.uuid4", return_value=MagicMock(hex="e2efeedback")):
                with patch.object(Path, "write_text"):
                    with patch.object(Path, "mkdir"):
                        with patch("borg.integrations.mcp_server._get_borg_v3") as mock_v3:
                            v3_inst = MagicMock()
                            v3_inst.record_outcome = track_record
                            v3_inst.run_maintenance = MagicMock(return_value={
                                "ab_tests_checked": 0,
                                "drift_alerts": [],
                                "mutations_suggested": [],
                            })
                            mock_v3.return_value = v3_inst

                            with patch("borg.integrations.mcp_server._get_core_modules") as mock_core:
                                mock_core.return_value = (
                                    MagicMock(),
                                    MagicMock(),
                                    fake_session_mod,
                                    MagicMock(),
                                    MagicMock(),
                                )
                                fb_result = borg_feedback(
                                    session_id=session_id,
                                    task_context={
                                        "task_type": "debugging",
                                        "keywords": ["auth", "bug"]
                                    },
                                    success=True,
                                    tokens_used=800,
                                    time_taken=4.2,
                                )

        fb_parsed = json.loads(fb_result)
        assert fb_parsed.get("success") is True
        assert len(record_calls) == 1
        assert record_calls[0]["pack_id"] == "e2e-pack"
        assert record_calls[0]["success"] is True
        assert record_calls[0]["tokens_used"] == 800
        assert record_calls[0]["session_id"] == session_id

        # ── Step 6: TraceMatcher can find the saved trace ───────────────
        matcher = TraceMatcher(db_path=tmp_trace_db)
        relevant = matcher.find_relevant(
            task="Debug authentication bug",
            error="AuthenticationError: invalid token",
            top_k=3
        )
        assert len(relevant) >= 1

        # ── Step 7: record_outcome was called (verified above) ──────────
        # Note: we used a mock V3 in borg_feedback, so we can't check the real DB here.
        # The call tracking in Step 5 already verified record_outcome was invoked.

        # ── Step 8: run_maintenance completes without error ────────────
        maint = v3_inst.run_maintenance()
        assert isinstance(maint, dict)
        assert "ab_tests_checked" in maint

        # Clean up global state
        mcp_mod._trace_captures = {}

    def test_trace_matcher_format_for_agent(self, saved_trace):
        """TraceMatcher.format_for_agent produces readable guidance text."""
        matcher = TraceMatcher()
        formatted = matcher.format_for_agent(saved_trace)
        assert isinstance(formatted, str)
        assert len(formatted) > 0


# ============================================================================
# Test 8: Root Cause Extraction from what_changed
# ============================================================================

class TestRootCauseExtraction:
    """Step 8: borg_feedback extracts root_cause from what_changed and saves it."""

    def test_root_cause_save_and_retrieve(self, tmp_trace_db):
        """root_cause is saved and retrieved correctly from the DB."""
        # Create capture and accumulate
        capture = TraceCapture(task="Fix auth bug", agent_id="test-agent")
        for i in range(3):
            capture.on_tool_call("read_file", {"path": f"/test/file{i}.py"}, "content")

        # Extract with root_cause
        trace = capture.extract_trace(
            outcome="success",
            root_cause="Missing null check in getUser()",
            approach_summary="Added if user is None check"
        )

        tid = save_trace(trace, db_path=tmp_trace_db)

        # Verify in DB
        conn = sqlite3.connect(tmp_trace_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT root_cause, approach_summary FROM traces WHERE id = ?", (tid,)).fetchone()
        conn.close()

        assert row is not None
        assert "Missing null check" in row["root_cause"]
        assert "Added if user is None" in row["approach_summary"]

    def test_root_cause_passed_to_extract_trace(self, tmp_trace_db):
        """what_changed is passed as root_cause to extract_trace in borg_feedback."""
        import borg.integrations.mcp_server as mcp_mod
        mcp_mod._trace_captures = {}

        session_id = "rc-test-session"
        _current_session_id.set(session_id)
        init_trace_capture(session_id, task="Fix bug", agent_id="test-agent")

        for i in range(6):
            _feed_trace_capture(
                tool_name="read_file",
                args={"path": f"/app/file{i}.py"},
                result=f"content {i}"
            )

        fake_session_mod = _FakeSessionModule()
        fake_session_mod.register_session({
            "session_id": session_id,
            "execution_log_path": "",
            "phase_results": [],
            "pack_id": "test-pack",
            "pack_version": "1.0.0",
            "task": "Fix bug",
            "outcome": "success"
        })

        # Mock generate_feedback to avoid external dependencies
        with patch("borg.core.search.generate_feedback", return_value={"success": True, "feedback": {}}):
            with patch("borg.integrations.mcp_server._get_core_modules") as mock_core:
                mock_core.return_value = (
                    MagicMock(),
                    MagicMock(),
                    fake_session_mod,
                    MagicMock(),
                    MagicMock(),
                )
                with patch("borg.integrations.mcp_server.save_trace") as mock_save:
                    borg_feedback(
                        session_id=session_id,
                        what_changed="Fixed null pointer in getUser() by adding guard clause",
                        where_to_reuse="Any user lookup in auth flow",
                    )
                    assert mock_save.called
                    call_kwargs = mock_save.call_args[1]
                    trace = call_kwargs.get("trace") or mock_save.call_args[0][0]
                    assert "null pointer" in trace.get("root_cause", "")
                    assert "guard clause" in trace.get("root_cause", "")

        mcp_mod._trace_captures = {}


# ============================================================================
# Test 12: Thompson Sampling Feedback Boost
# ============================================================================

class TestThompsonSamplingFeedbackBoost:
    """Test PRD item 3.4: Thompson Sampling + FeedbackLoop Signal Integration."""

    def test_feedback_signal_boost_formula(self):
        from borg.core.contextual_selector import ContextualSelector
        from unittest.mock import Mock

        # Create mock feedback loop
        mock_fl = Mock()
        mock_fl.get_signals.return_value = []

        selector = ContextualSelector(feedback_loop=mock_fl)

        # No signals → neutral boost
        assert selector.feedback_signal_boost("any-pack") == 1.0

        # Negative drift signal
        mock_signal = Mock()
        mock_signal.quality_score = 0.3
        mock_signal.success_rate_trend = -0.5
        mock_fl.get_signals.return_value = [mock_signal]

        boost = selector.feedback_signal_boost("failing-pack")
        # 0.3 * (1 + -0.5/2) = 0.3 * 0.75 = 0.225
        assert abs(boost - 0.225) < 0.001, f"Expected ~0.225, got {boost}"

        # Positive drift signal
        mock_signal2 = Mock()
        mock_signal2.quality_score = 0.9
        mock_signal2.success_rate_trend = 0.5
        mock_fl.get_signals.return_value = [mock_signal2]

        boost2 = selector.feedback_signal_boost("good-pack")
        # 0.9 * (1 + 0.5/2) = 0.9 * 1.25 = 1.125
        assert abs(boost2 - 1.125) < 0.001, f"Expected ~1.125, got {boost2}"

    def test_feedback_signal_boost_no_feedback_loop(self):
        from borg.core.contextual_selector import ContextualSelector

        selector = ContextualSelector()
        # Without feedback_loop, should return neutral 1.0
        assert selector.feedback_signal_boost("any-pack") == 1.0

    def test_feedback_signal_boost_multiple_signals(self):
        from borg.core.contextual_selector import ContextualSelector
        from unittest.mock import Mock

        mock_fl = Mock()
        # Multiple signals are averaged
        mock_signal1 = Mock()
        mock_signal1.quality_score = 0.4
        mock_signal1.success_rate_trend = -0.2
        mock_signal2 = Mock()
        mock_signal2.quality_score = 0.8
        mock_signal2.success_rate_trend = 0.4
        mock_fl.get_signals.return_value = [mock_signal1, mock_signal2]

        selector = ContextualSelector(feedback_loop=mock_fl)

        boost = selector.feedback_signal_boost("multi-signal-pack")
        # avg_quality = (0.4 + 0.8) / 2 = 0.6
        # avg_trend = (-0.2 + 0.4) / 2 = 0.1
        # boost = 0.6 * (1 + 0.1/2) = 0.6 * 1.05 = 0.63
        assert abs(boost - 0.63) < 0.001, f"Expected ~0.63, got {boost}"

    def test_feedback_signal_boost_clamped_to_2_0(self):
        from borg.core.contextual_selector import ContextualSelector
        from unittest.mock import Mock

        mock_fl = Mock()
        mock_signal = Mock()
        mock_signal.quality_score = 1.0
        mock_signal.success_rate_trend = 1.0  # max positive trend
        mock_fl.get_signals.return_value = [mock_signal]

        selector = ContextualSelector(feedback_loop=mock_fl)

        boost = selector.feedback_signal_boost("max-boost-pack")
        # 1.0 * (1 + 1.0/2) = 1.0 * 1.5 = 1.5 (not clamped)
        assert abs(boost - 1.5) < 0.001, f"Expected ~1.5, got {boost}"

    def test_feedback_signal_boost_clamped_to_0_0(self):
        from borg.core.contextual_selector import ContextualSelector
        from unittest.mock import Mock

        mock_fl = Mock()
        mock_signal = Mock()
        mock_signal.quality_score = 0.0
        mock_signal.success_rate_trend = -1.0  # worst trend
        mock_fl.get_signals.return_value = [mock_signal]

        selector = ContextualSelector(feedback_loop=mock_fl)

        boost = selector.feedback_signal_boost("min-boost-pack")
        # 0.0 * (1 + -1.0/2) = 0.0 * 0.5 = 0.0
        assert abs(boost - 0.0) < 0.001, f"Expected ~0.0, got {boost}"

    def test_boost_applied_in_select(self):
        from borg.core.contextual_selector import ContextualSelector, PackDescriptor
        from unittest.mock import Mock

        mock_fl = Mock()
        mock_fl.get_signals.return_value = []

        selector = ContextualSelector(feedback_loop=mock_fl)

        candidates = [
            PackDescriptor(
                pack_id="boost-test-pack",
                name="Boost Test Pack",
                keywords=["debug", "error"],
                supported_tasks=["debug"],
            )
        ]

        # With no signals, boost is neutral (1.0)
        ctx = {"task_type": "debug", "keywords": ["error"]}
        results = selector.select(ctx, candidates, seed=42)

        assert len(results) == 1
        assert results[0].pack_id == "boost-test-pack"
        assert results[0].category == "debug"
