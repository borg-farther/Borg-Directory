#!/usr/bin/env python3
"""
Comprehensive E2E Verification Harness for borg auto-trace system.

Tests the REAL user journey, not mocks:
1. TRACE CAPTURE: Verify tool calls are captured in traces.db
2. TRACE RETRIEVAL: Verify TraceMatcher.find_relevant() returns correct traces
3. PACK SEARCH: Verify borg_search works on real packs
4. FULL LOOP: Simulate agent task -> trace capture -> similar task -> trace retrieval
5. VALUE MEASUREMENT: Verify trace guidance would actually help

Mark broken functionality with @pytest.mark.xfail so progress is trackable.
"""

import json
import os
import re
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Ensure borg is on path
sys.path.insert(0, "/root/hermes-workspace/borg")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BORG_HOME = os.getenv("BORG_HOME", os.path.join(str(Path.home()), ".borg"))
TRACE_DB_PATH = os.path.join(BORG_HOME, "traces.db")
TEST_TRACE_DB = None  # Set per-test with tempfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db():
    """Create a temporary trace database for isolation."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


@pytest.fixture
def clean_trace_capture():
    """Reset trace capture state between tests (no-op if not wired in mcp_server)."""
    yield


# ---------------------------------------------------------------------------
# Test 1: TRACE CAPTURE
# ---------------------------------------------------------------------------

class TestTraceCapture:
    """Verify that tool calls are accumulated and saved as traces."""

    def test_trace_capture_accumulates_tool_calls(self, temp_db, clean_trace_capture):
        """
        PASS CRITERIA:
        - TraceCapture.on_tool_call() records tool_name, args, result
        - After 45+ calls, auto-extract saves a trace to DB
        - Trace contains: task_description, files_read, files_modified,
          errors_encountered, tool_calls count, technology, keywords
        """
        from borg.core.traces import TraceCapture, save_trace, _ensure_schema

        # Create a capture session
        capture = TraceCapture(
            task="Fix Django migration by editing models.py",
            agent_id="test-agent"
        )

        # Simulate a realistic sequence of tool calls
        # Dead end detection: read same file 3+ times WITHOUT ever modifying it
        tool_sequence = [
            ("search_files", {"path": "/testbed/django/db/models"}, "found models.py"),
            ("read_file", {"path": "/testbed/django/db/models/__init__.py"}, "class Model:"),
            ("read_file", {"path": "/testbed/django/db/models/fields/__init__.py"}, "class Field:"),
            ("read_file", {"path": "/testbed/django/db/models/fields/__init__.py"}, "class Field:"),
            ("read_file", {"path": "/testbed/django/db/models/fields/__init__.py"}, "class Field:"),
            # ^-- read 3 times but THEN modified below, so NOT a dead end
            ("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "class SQLCompiler:"),
            ("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "class SQLCompiler:"),
            ("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "class SQLCompiler:"),
            # ^-- read 3 times, NEVER modified = DEAD END
            ("search_files", {"path": "/testbed/django/db/migrations"}, "found 3 migration files"),
            ("read_file", {"path": "/testbed/django/db/migrations/0001_initial.py"}, "Migration class"),
            ("patch", {"path": "/testbed/django/db/models/fields/__init__.py"}, "patched: added null=True"),
            # ^-- this is the file we modify
            ("terminal", {}, "Error: ValueError: invalid literal for int()"),
            ("read_file", {"path": "/testbed/django/db/models/sql/query.py"}, "class Query"),
            ("terminal", {}, "OK\nRan 12 tests in 0.5s\nOK"),
        ]

        for tool_name, args, result in tool_sequence:
            capture.on_tool_call(tool_name, args, result)

        # Verify internal state
        assert capture.tool_calls == len(tool_sequence), \
            f"Expected {len(tool_sequence)} tool calls, got {capture.tool_calls}"
        assert len(capture.files_read) > 0, "Should have tracked file reads"
        assert "/testbed/django/db/models/fields/__init__.py" in capture.files_read

        # Extract trace
        trace = capture.extract_trace(
            outcome="success",
            root_cause="Field default was changed without proper migration",
            approach_summary="Added null=True to field definition in models.py"
        )

        # Verify trace structure
        assert "id" in trace
        assert trace["task_description"] == "Fix Django migration by editing models.py"
        assert trace["outcome"] == "success"
        assert trace["root_cause"] == "Field default was changed without proper migration"
        assert trace["approach_summary"] == "Added null=True to field definition in models.py"
        assert trace["tool_calls"] == len(tool_sequence)
        assert trace["technology"] == "django"
        assert trace["keywords"] != ""
        assert trace["created_at"] != ""

        # Verify files are tracked
        files_read = json.loads(trace["files_read"])
        files_modified = json.loads(trace["files_modified"])
        assert any("models" in f for f in files_read), "Should track relevant files read"
        assert any("models" in f for f in files_modified), "Should track modified files"

        # Verify key_files extracted
        key_files = json.loads(trace["key_files"])
        assert len(key_files) > 0, "Should extract key files from reads/modifies"

        # Verify dead ends detected (read same file 3x without ever modifying it)
        # We read /testbed/django/db/migrations/0001_initial.py twice without modifying
        dead_ends = json.loads(trace["dead_ends"])
        assert len(dead_ends) > 0, \
            f"Should detect the repeated file read as a dead end. files_read={files_read}"

        # Save to temp DB and verify persisted
        tid = save_trace(trace, temp_db)
        assert tid is not None

        # Verify can be retrieved from DB
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM traces WHERE id = ?", (tid,)).fetchone()
        conn.close()
        assert row is not None, "Trace should be persisted in DB"
        assert row["task_description"] == "Fix Django migration by editing models.py"

    def test_feed_trace_capture_accumulates_calls(self, temp_db, clean_trace_capture):
        """
        PASS CRITERIA:
        - _feed_trace_capture() accumulates tool calls correctly
        - The internal TraceCapture records the calls
        - After N calls, the capture has accumulated the right count
        """
        import borg.integrations.mcp_server as mcp_module
        from borg.core.traces import _ensure_schema

        # Reset global capture
        mcp_module._trace_capture = None

        # Initialize capture with a task
        task_desc = "Simulate a debugging session to test accumulation"
        mcp_module._trace_capture = mcp_module._trace_capture or \
            __import__('borg.core.traces', fromlist=['TraceCapture']).TraceCapture(
                task=task_desc, agent_id="test-agent"
            )

        # Simulate 10 tool calls (well before the 45-call auto-save)
        for i in range(10):
            mcp_module._feed_trace_capture(
                "read_file",
                {"path": f"/testbed/django/db/models/file_{i}.py"},
                f"content {i}"
            )

        # Verify the capture accumulated the calls
        assert mcp_module._trace_capture is not None
        assert mcp_module._trace_capture.tool_calls == 10, \
            f"Should have accumulated 10 calls, got {mcp_module._trace_capture.tool_calls}"
        assert len(mcp_module._trace_capture.files_read) == 10, \
            f"Should have tracked 10 file reads, got {len(mcp_module._trace_capture.files_read)}"

        # Verify we can extract a trace before auto-save threshold
        trace = mcp_module._trace_capture.extract_trace(outcome="unknown")
        assert trace is not None
        assert trace["tool_calls"] == 10
        assert "django" in trace["technology"].lower()


# ---------------------------------------------------------------------------
# Test 2: TRACE RETRIEVAL
# ---------------------------------------------------------------------------

class TestTraceRetrieval:
    """Verify TraceMatcher.find_relevant() returns correct prior traces."""

    @pytest.fixture
    def populated_db(self, temp_db):
        """Insert known traces into a temp DB."""
        from borg.core.traces import TraceCapture, save_trace

        # Trace 1: Django migration fix (SUCCESS)
        c1 = TraceCapture(task="Fix Django migration by editing models.py", agent_id="agent-1")
        c1.on_tool_call("read_file", {"path": "/testbed/django/db/models/__init__.py"}, "class Model")
        c1.on_tool_call("read_file", {"path": "/testbed/django/db/models/fields/__init__.py"}, "class Field")
        c1.on_tool_call("patch", {"path": "/testbed/django/db/models/fields/__init__.py"}, "patched")
        c1.on_tool_call("terminal", {}, "OK\nRan 12 tests\nOK")
        t1 = c1.extract_trace(
            outcome="success",
            root_cause="Field definition needed null=True",
            approach_summary="Added null=True to field in models.py after reading migration docs"
        )
        save_trace(t1, temp_db)
        self.trace1_id = t1["id"]

        # Trace 2: ASGI middleware issue (FAILURE)
        c2 = TraceCapture(task="ASGI middleware returns coroutine instead of response", agent_id="agent-2")
        c2.on_tool_call("read_file", {"path": "/testbed/django/utils/deprecation.py"}, "class MiddlewareMixin")
        c2.on_tool_call("read_file", {"path": "/testbed/django/middleware/security.py"}, "class Security")
        c2.on_tool_call("terminal", {}, "Error: RuntimeError: coroutine expected")
        t2 = c2.extract_trace(
            outcome="failure",
            root_cause="Middleware __init__ missing super() call causing _async_check to not run",
            approach_summary="Tried adding super().__init__() but failed to fix all cases"
        )
        save_trace(t2, temp_db)
        self.trace2_id = t2["id"]

        # Trace 3: Unrelated React task
        c3 = TraceCapture(task="Fix React useEffect not re-rendering", agent_id="agent-3")
        c3.on_tool_call("read_file", {"path": "/src/components/Button.tsx"}, "const Button")
        c3.on_tool_call("patch", {"path": "/src/components/Button.tsx"}, "patched")
        c3.on_tool_call("terminal", {}, "OK")
        t3 = c3.extract_trace(outcome="success", root_cause="missing dependency array", approach_summary="Added useEffect dependency")
        save_trace(t3, temp_db)
        self.trace3_id = t3["id"]

        return temp_db

    def test_find_relevant_returns_django_trace_for_django_query(self, populated_db):
        """
        PASS CRITERIA:
        - Query about Django migration returns the Django trace (not React)
        - The returned trace has the same root_cause/approach
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(populated_db)
        matches = matcher.find_relevant(
            task="Django migration error when editing models.py field",
            error="ValueError: invalid literal for int()",
            top_k=3
        )

        assert len(matches) > 0, "Should find at least one match for Django query"

        # The Django trace should be ranked higher than React trace
        ids = [m["id"] for m in matches]
        assert self.trace1_id in ids, f"Django trace should be returned; got {ids}"

        # Verify best match is actually relevant (has django in task_description or keywords)
        best = matches[0]
        searchable = f"{best.get('task_description','')} {best.get('keywords','')}"
        assert "django" in searchable.lower() or "migration" in searchable.lower(), \
            f"Best match should be Django-related; got: {best.get('task_description')}"

    def test_find_relevant_excludes_irrelevant_traces(self, populated_db):
        """
        PASS CRITERIA:
        - Query about React does NOT return Django trace
        - The match score for irrelevant trace is lower or zero
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(populated_db)
        matches = matcher.find_relevant(
            task="React useEffect dependency array not triggering re-render",
            error="",
            top_k=3
        )

        ids = [m["id"] for m in matches]
        assert self.trace3_id in ids, "React trace should be returned for React query"
        assert self.trace1_id not in ids or matches[-1]["id"] == self.trace1_id, \
            "Django trace should NOT be top result for React query"

    def test_find_relevant_returns_empty_for_nonsense(self, populated_db):
        """
        PASS CRITERIA:
        - Searching for completely unrelated nonsense returns empty or very low scores
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(populated_db)
        matches = matcher.find_relevant(
            task="zzzz_supercalifragilisticexpialidocious_12345_quantum_foo",
            error="",
            top_k=5
        )

        # Either empty, or if any results, they should have very low scores
        # (near zero since no actual matching)
        if matches:
            best_score = matches[0].get("match_score", 0)
            # Low score because no actual terms match
            assert best_score < 5.0, \
                f"Nonsense query should return very low scores; got {best_score}"

    def test_format_for_agent_produces_usable_guidance(self, populated_db):
        """
        PASS CRITERIA:
        - format_for_agent() produces a non-empty string
        - Contains root cause, key files, or approach summary
        - Is concise enough to be useful to an agent
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(populated_db)
        matches = matcher.find_relevant(
            task="Django field migration error",
            error="ValueError",
            top_k=1
        )

        assert len(matches) > 0, "Should find the Django trace"
        best = matches[0]

        formatted = matcher.format_for_agent(best)
        assert formatted != "", "format_for_agent should not return empty string"
        assert len(formatted) < 1000, "Should be concise (<1000 chars)"

        # Should contain useful information
        useful_markers = ["ROOT CAUSE", "CAUSE", "KEY FILES", "APPROACH", "FILES", "Solved"]
        assert any(marker in formatted.upper() for marker in useful_markers), \
            f"Formatted output should contain useful guidance; got: {formatted[:200]}"

    @pytest.mark.xfail(reason="TraceMatcher.find_relevant() is never called from borg_observe in the current code path — this is the known gap")
    def test_borg_observe_returns_prior_trace_guidance(self):
        """
        PASS CRITERIA:
        - Insert a known trace into the real traces.db
        - Call borg_observe() with a similar task description
        - The result should include guidance from the prior trace

        This test is expected to FAIL until find_relevant() is wired into borg_observe.
        """
        from borg.integrations.mcp_server import borg_observe
        from borg.core.traces import TraceCapture, save_trace, _get_db

        # Insert a trace about Django migrations
        task = "Fix Django migration for model field change"
        capture = TraceCapture(task=task, agent_id="test-e2e")
        capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/__init__.py"}, "class Model")
        capture.on_tool_call("patch", {"path": "/testbed/django/db/models/__init__.py"}, "patched")
        capture.on_tool_call("terminal", {}, "OK")
        trace = capture.extract_trace(
            outcome="success",
            root_cause="Field migration was missing null=True constraint",
            approach_summary="Added null=True to field definition after checking migration docs"
        )
        save_trace(trace)

        # Now call borg_observe with a similar task
        result = borg_observe(
            task="Django model field migration is failing with ValueError",
            context="django.db.utils.DatabaseError"
        )

        # The result should mention something from the prior trace
        # (either the pack guidance OR the trace guidance)
        # Since we're testing trace retrieval specifically, we check for trace-related content
        assert result != "", "borg_observe should return some guidance"
        # If traces are wired, result should include trace-derived content
        # Current code path: borg_observe searches packs, then falls back to find_relevant
        # So we check if any trace-related text appears
        trace_markers = ["prior agent", "investigation", "ROOT CAUSE", "APPROACH", "📋"]
        # Note: This may fail if pack search returns results before trace matching
        # or if the error message doesn't match well enough
        assert any(m.lower() in result.lower() for m in trace_markers), \
            f"Result should include trace guidance; got: {result[:300]}"


# ---------------------------------------------------------------------------
# Test 3: PACK SEARCH
# ---------------------------------------------------------------------------

class TestPackSearch:
    """Verify borg_search works on real local packs."""

    def test_search_finds_existing_packs(self):
        """
        PASS CRITERIA:
        - borg_search("github") returns results (at least one pack)
        - Results contain name, id, problem_class, tier
        - Result format is usable by an agent
        """
        from borg.core.search import borg_search

        result = borg_search("github", mode="text")
        parsed = json.loads(result)

        assert parsed.get("success") is True, f"Search should succeed; got: {result}"
        matches = parsed.get("matches", [])
        assert len(matches) > 0, f"Should find at least one 'github' pack; got {len(matches)}"

        # Verify result format is usable
        for match in matches[:3]:
            assert "name" in match or "id" in match, \
                f"Match should have name or id; got: {match}"
            # tier or confidence should be present
            assert "tier" in match or "confidence" in match, \
                f"Match should have tier or confidence; got: {match}"

    def test_search_returns_empty_for_nonsense(self):
        """
        PASS CRITERIA:
        - Searching nonsense returns empty matches list OR very few results
        """
        from borg.core.search import borg_search

        result = borg_search("xyzzy_nonsense_12345_superword", mode="text")
        parsed = json.loads(result)

        assert parsed.get("success") is True
        matches = parsed.get("matches", [])
        # Nonsense should return 0 matches (or at most 1 very low relevance match)
        assert len(matches) == 0, \
            f"Nonsense query should return 0 matches; got {len(matches)}: {[m.get('name') for m in matches]}"

    def test_search_with_empty_query_returns_all_packs(self):
        """
        PASS CRITERIA:
        - Empty query returns all available packs
        - At least 10 packs should be found (we know ~15 exist)
        """
        from borg.core.search import borg_search

        result = borg_search("", mode="text")
        parsed = json.loads(result)

        assert parsed.get("success") is True
        matches = parsed.get("matches", [])
        total = parsed.get("total", 0)
        # Should have many packs available
        assert len(matches) >= 10, \
            f"Should return all packs (at least 10); got {len(matches)}"
        assert total >= 10

    def test_search_result_format_is_agent_usable(self):
        """
        PASS CRITERIA:
        - Results can be parsed as JSON
        - Each match has 'name' or 'id' at minimum
        - tier, confidence, problem_class are useful for selection
        """
        from borg.core.search import borg_search

        result = borg_search("debug", mode="text")
        parsed = json.loads(result)

        assert parsed.get("success") is True
        matches = parsed.get("matches", [])

        for match in matches[:5]:
            # Must have an identifier
            assert match.get("name") or match.get("id"), \
                f"Match must have name or id: {match}"
            # Should have tier (even if "unknown")
            assert "tier" in match, f"Match should have tier: {match}"
            # Should have some classification
            has_info = any([
                match.get("problem_class"),
                match.get("confidence"),
                match.get("phase_names"),
            ])
            assert has_info, f"Match should have useful metadata: {match}"


# ---------------------------------------------------------------------------
# Test 4: FULL LOOP
# ---------------------------------------------------------------------------

class TestFullLoop:
    """
    The money test: simulate agent starts task -> borg observes ->
    agent works -> trace captured -> agent starts SIMILAR task ->
    borg returns previous trace.

    This is the core value proposition of borg.
    """

    @pytest.fixture
    def loop_db(self, temp_db):
        """Set up initial traces for the full loop test."""
        from borg.core.traces import TraceCapture, save_trace

        # First agent session: fixed a Django migration bug
        capture1 = TraceCapture(
            task="Fix Django migration for CharField max_length change",
            agent_id="agent-loop-1"
        )
        capture1.on_tool_call("read_file", {"path": "/testbed/django/db/models/fields/__init__.py"}, "class CharField")
        capture1.on_tool_call("read_file", {"path": "/testbed/django/db/models/fields/__init__.py"}, "class CharField")
        capture1.on_tool_call("read_file", {"path": "/testbed/django/db/migrations/0001_initial.py"}, "Migration")
        capture1.on_tool_call("patch", {"path": "/testbed/django/db/models/fields/__init__.py"}, "patched max_length")
        capture1.on_tool_call("terminal", {}, "Error: DatabaseError at position 0")
        capture1.on_tool_call("read_file", {"path": "/testbed/django/db/models/sql/compiler.py"}, "SQLCompiler")
        capture1.on_tool_call("patch", {"path": "/testbed/django/db/models/fields/__init__.py"}, "patched max_length=150")
        capture1.on_tool_call("terminal", {}, "OK\nRan 20 tests in 1.2s\nOK")

        trace1 = capture1.extract_trace(
            outcome="success",
            root_cause="CharField max_length=100 in model but migration generated max_length=150 in DB",
            approach_summary="Synchronized max_length between model definition and migration by adjusting the model field definition"
        )
        save_trace(trace1, temp_db)
        self.first_trace_id = trace1["id"]

        return temp_db

    def test_full_loop_similar_task_finds_prior_trace(self, loop_db):
        """
        PASS CRITERIA:
        1. First agent works on Django migration task -> trace is saved
        2. New agent starts SIMILAR (not identical) task
        3. borg_observe or find_relevant returns the prior trace
        4. The returned trace is relevant to the new task
        """
        from borg.core.trace_matcher import TraceMatcher

        # Step 1: Already done in loop_db fixture (trace saved)

        # Step 2: New agent asks about a similar problem
        similar_task = "Django migration failing because model field max_length doesn't match database"
        similar_error = "DatabaseError: column length mismatch"

        matcher = TraceMatcher(loop_db)
        matches = matcher.find_relevant(
            task=similar_task,
            error=similar_error,
            top_k=3
        )

        # Step 3: Should find the prior trace
        assert len(matches) > 0, \
            "Full loop FAIL: find_relevant returned no matches for similar task"

        # Step 4: The match should be the Django migration trace
        ids = [m["id"] for m in matches]
        assert self.first_trace_id in ids, \
            f"Full loop FAIL: prior trace not found. Expected {self.first_trace_id} in {ids}"

        # Verify the returned trace is actually relevant
        best = matches[0]
        trace_text = f"{best.get('task_description','')} {best.get('keywords','')} {best.get('root_cause','')}"

        # Should mention Django/migration/max_length related concepts
        assert any(term in trace_text.lower() for term in ["django", "migration", "max_length", "field"]), \
            f"Returned trace should be relevant to the similar task; got: {best.get('task_description')}"

    @pytest.mark.xfail(reason="Full loop requires find_relevant to be wired into borg_observe — currently not wired")
    def test_full_loop_via_mcp_server_observe(self, loop_db):
        """
        PASS CRITERIA:
        - Using the MCP server handle_request path
        - borg_observe returns prior trace guidance for a similar task
        """
        from borg.integrations.mcp_server import borg_observe
        from borg.core.traces import TraceCapture, save_trace

        # Ensure the trace exists in the real DB
        capture = TraceCapture(
            task="Fix Django model field max_length mismatch in migration",
            agent_id="agent-mcp-loop"
        )
        capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/__init__.py"}, "class Model")
        capture.on_tool_call("patch", {"path": "/testbed/django/db/models/__init__.py"}, "patched")
        capture.on_tool_call("terminal", {}, "OK")
        trace = capture.extract_trace(
            outcome="success",
            root_cause="max_length mismatch between model and migration",
            approach_summary="Adjusted model field to match migration generated length"
        )
        save_trace(trace)

        # Call borg_observe with a similar task
        result = borg_observe(
            task="Django migration error: model field max_length is 100 but DB column is 150",
            context="django.db.utils.DatabaseError"
        )

        assert result != "", "borg_observe should return guidance"
        # Should contain trace-derived content
        trace_indicators = ["prior agent", "📋", "ROOT CAUSE", "investigation"]
        assert any(ind.lower() in result.lower() for ind in trace_indicators), \
            f"borg_observe should return trace guidance; got: {result[:400]}"


# ---------------------------------------------------------------------------
# Test 5: VALUE MEASUREMENT
# ---------------------------------------------------------------------------

class TestValueMeasurement:
    """
    Measure whether having trace guidance actually helps an agent.

    Even if we can't run a full agent, we can verify:
    - Trace was returned and contained relevant info
    - The info is actionable (has root cause, files, approach)
    - The info is specific enough to be useful
    """

    @pytest.fixture
    def value_db(self, temp_db):
        """Set up traces for value measurement."""
        from borg.core.traces import TraceCapture, save_trace

        # A realistic debugging trace
        capture = TraceCapture(
            task="Fix pytest failing because of Django migration ordering issue",
            agent_id="agent-value"
        )
        capture.on_tool_call("search_files", {"path": "/testbed/django/db/migrations"}, "found migration files")
        capture.on_tool_call("read_file", {"path": "/testbed/django/db/migrations/0001_initial.py"}, "Migration")
        capture.on_tool_call("read_file", {"path": "/testbed/django/db/migrations/0002_auto.py"}, "Migration")
        capture.on_tool_call("read_file", {"path": "/testbed/django/db/migrations/0003_update.py"}, "Migration")
        capture.on_tool_call("terminal", {}, "FAILED: django.db.utils.IntegrityError: UNIQUE constraint failed")
        capture.on_tool_call("read_file", {"path": "/testbed/django/db/models/sql/query.py"}, "Query")
        capture.on_tool_call("patch", {"path": "/testbed/django/db/migrations/0003_update.py"}, "patched migration order")
        capture.on_tool_call("terminal", {}, "OK\nRan 8 tests in 0.3s\nOK")

        trace = capture.extract_trace(
            outcome="success",
            root_cause="Migration 0003 depended on 0002 but was numbered incorrectly, causing FK constraint failures",
            approach_summary="Renumbered migrations to respect foreign key dependency order, ensured each migration is self-contained"
        )
        save_trace(trace, temp_db)
        self.value_trace = trace

        return temp_db

    def test_trace_provides_actionable_root_cause(self, value_db):
        """
        PASS CRITERIA:
        - Trace root_cause is specific, not generic
        - A new agent seeing a similar error would understand the fix direction
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(value_db)
        matches = matcher.find_relevant(
            task="Django migration integrity error UNIQUE constraint failed",
            error="IntegrityError: UNIQUE constraint failed",
            top_k=1
        )

        assert len(matches) > 0, "Should find the migration trace"
        best = matches[0]

        # Root cause should be specific
        rc = best.get("root_cause", "")
        assert len(rc) > 20, f"Root cause should be specific, not generic; got: '{rc}'"

        # Root cause should mention migration/FK dependency issues
        assert any(word in rc.lower() for word in ["migration", "fk", "foreign", "dependency", "constraint"]), \
            f"Root cause should be about migration issues; got: '{rc}'"

    def test_trace_provides_specific_approach_guidance(self, value_db):
        """
        PASS CRITERIA:
        - approach_summary is concrete, not vague
        - An agent could take action based on it
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(value_db)
        matches = matcher.find_relevant(
            task="Django migration integrity error UNIQUE constraint failed",
            error="IntegrityError",
            top_k=1
        )

        assert len(matches) > 0
        best = matches[0]

        approach = best.get("approach_summary", "")
        assert len(approach) > 20, f"Approach should be specific; got: '{approach}'"

        # Approach should be actionable
        actionable_words = ["migration", "order", "renumber", "dependency", "check", "constraint", "foreign"]
        assert any(word in approach.lower() for word in actionable_words), \
            f"Approach should be actionable; got: '{approach}'"

    def test_formatted_trace_is_concise_and_agent_usable(self, value_db):
        """
        PASS CRITERIA:
        - Formatted trace is < 500 chars (concise for agent context)
        - Contains at least: root cause OR key files, and approach
        - Does NOT contain excessive boilerplate
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(value_db)
        matches = matcher.find_relevant(
            task="Django migration ordering integrity error",
            error="UNIQUE constraint",
            top_k=1
        )

        assert len(matches) > 0
        formatted = matcher.format_for_agent(matches[0])

        assert len(formatted) < 500, \
            f"Formatted trace should be concise (<500 chars); got {len(formatted)}: {formatted[:200]}"
        assert "migration" in formatted.lower(), \
            f"Formatted should mention migration; got: {formatted}"

    @pytest.mark.xfail(reason="Value measurement via full MCP round-trip requires trace retrieval to be wired")
    def test_agent_would_save_time_with_trace_guidance(self, value_db):
        """
        PASS CRITERIA:
        - Given a task, the trace guidance reduces search space
        - Agent gets: root cause, key files, approach — not just generic advice

        This is a meta-test: if find_relevant works end-to-end, this passes.
        We verify that the returned trace has the properties that would save time:
        - Specific root cause (not "something went wrong")
        - Specific files to examine (not "check the codebase")
        - Specific approach (not "try debugging")
        """
        from borg.core.trace_matcher import TraceMatcher

        matcher = TraceMatcher(value_db)
        matches = matcher.find_relevant(
            task="Django IntegrityError UNIQUE constraint during migration",
            error="IntegrityError: UNIQUE constraint failed",
            top_k=1
        )

        assert len(matches) > 0, "Should find relevant trace"

        best = matches[0]
        rc = best.get("root_cause", "")
        approach = best.get("approach_summary", "")
        key_files = best.get("key_files", "[]")

        # The three things that save agent time:
        assert len(rc) > 30, "Root cause must be specific"
        assert len(approach) > 30, "Approach must be specific"
        assert key_files not in ("[]", ""), "Key files must be specified"

        # These specific properties indicate time would be saved:
        # - Agent doesn't need to search for the root cause
        # - Agent has specific files to examine
        # - Agent has a concrete approach direction

        # If all three pass, the trace has value
        time_saving_indicators = [
            rc,  # Specific root cause
            approach,  # Specific approach
            key_files,  # Specific files
        ]
        assert all(indicator for indicator in time_saving_indicators), \
            "Trace must have all time-saving properties for full value measurement"


# ---------------------------------------------------------------------------
# Summary test: Overall system health
# ---------------------------------------------------------------------------

class TestSystemHealth:
    """Overall health checks for the borg trace system."""

    def test_traces_db_exists_and_readable(self):
        """PASS: traces.db exists at the expected path."""
        assert os.path.exists(TRACE_DB_PATH), \
            f"traces.db should exist at {TRACE_DB_PATH}"

        # Should be readable as SQLite
        conn = sqlite3.connect(TRACE_DB_PATH)
        conn.row_factory = sqlite3.Row
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        conn.close()

        table_names = [t[0] for t in tables]
        assert "traces" in table_names, \
            f"traces table should exist; found tables: {table_names}"
        assert "trace_file_index" in table_names
        assert "trace_error_index" in table_names

    def test_mcp_server_handle_request_is_callable(self):
        """PASS: MCP server handle_request can be called programmatically."""
        from borg.integrations.mcp_server import handle_request

        # Simulate a tools/list request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        response = handle_request(request)
        assert response is not None, "Should return a response"
        assert response.get("id") == 1
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

    def test_call_tool_round_trip(self):
        """PASS: call_tool can be called directly and returns structured result."""
        from borg.integrations.mcp_server import call_tool

        # Call borg_search directly (simple, no side effects)
        result = call_tool("borg_search", {"query": "github"})

        parsed = json.loads(result)
        assert parsed.get("success") is True, \
            f"call_tool(borg_search) should succeed; got: {result[:200]}"
        assert "matches" in parsed


# ---------------------------------------------------------------------------
# Run with: pytest tests/test_e2e_verify.py -v
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
