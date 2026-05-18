"""
Tests for guild/core/apply.py (T1.9)

Covers: action_start, action_checkpoint, action_complete,
action_resume, action_status, apply_handler dispatch.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from borg.core import apply as apply_mod
from borg.core import session as sess_mod
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_PACK_YAML = """
type: workflow
version: "1.0"
id: "test-pack-v1"
problem_class: testing
mental_model: "Test mental model"
phases:
  - name: phase_one
    description: "First test phase"
    checkpoint: "result is not None"
    anti_patterns: []
    prompts: []
  - name: phase_two
    description: "Second test phase"
    checkpoint: "len(result) > 0"
    anti_patterns: []
    prompts: []
provenance:
  confidence: tested
  evidence: "Unit tested"
  failure_cases: []
required_inputs: ["input1"]
escalation_rules: ["If stuck, retry"]
""".strip()


def make_pack_dir(agent_dir: Path, pack_name: str = "test-pack") -> Path:
    """Create a minimal pack directory with pack.yaml."""
    pack_dir = agent_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.yaml").write_text(MINIMAL_PACK_YAML, encoding="utf-8")
    return pack_dir


def parse_result(raw: str) -> dict:
    """Parse JSON from apply module responses."""
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_agent_dir():
    """Create a temporary BORG_DIR and patch apply module to use it."""
    original_agent_dir = apply_mod.BORG_DIR
    original_home = apply_mod.HERMES_HOME

    tmp = tempfile.mkdtemp(prefix="guild_test_")
    agent_dir = Path(tmp) / "guild"
    (agent_dir / "sessions").mkdir(parents=True)
    (agent_dir / "executions").mkdir(parents=True)

    apply_mod.BORG_DIR = agent_dir
    apply_mod.HERMES_HOME = Path(tmp)
    apply_mod.EXECUTIONS_DIR = agent_dir / "executions"

    # Also patch session module
    orig_sess_agent_dir = sess_mod.BORG_DIR
    orig_sess_home = sess_mod.HERMES_HOME
    orig_sess_exec = sess_mod.EXECUTIONS_DIR
    sess_mod.BORG_DIR = agent_dir
    sess_mod.HERMES_HOME = Path(tmp)
    sess_mod.EXECUTIONS_DIR = agent_dir / "executions"

    make_pack_dir(agent_dir)

    yield agent_dir

    # Restore
    apply_mod.BORG_DIR = original_agent_dir
    apply_mod.HERMES_HOME = original_home
    apply_mod.EXECUTIONS_DIR = original_agent_dir / "executions"
    sess_mod.BORG_DIR = orig_sess_agent_dir
    sess_mod.HERMES_HOME = orig_sess_home
    sess_mod.EXECUTIONS_DIR = orig_sess_exec

    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear active sessions and apply state before and after each test."""
    apply_mod._active_apply_state.clear()
    sess_mod._active_sessions.clear()
    yield
    apply_mod._active_apply_state.clear()
    sess_mod._active_sessions.clear()


# ---------------------------------------------------------------------------
# Tests: action_start
# ---------------------------------------------------------------------------

class TestActionStart:
    def test_start_returns_success(self, tmp_agent_dir):
        result = apply_mod.action_start("test-pack", "My test task", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is True
        assert "session_id" in data
        assert data["session_id"].startswith("test-pack-")
        assert data["action_needed"] == "approve"
        assert "approval_summary" in data
        assert data["approval_summary"]["pack_name"] == "test-pack"
        assert len(data["phases"]) == 2

    def test_start_creates_session(self, tmp_agent_dir):
        result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        data = parse_result(result)
        session_id = data["session_id"]

        # Session should be registered in session module
        session = sess_mod.get_active_session(session_id)
        assert session is not None
        assert session["pack_name"] == "test-pack"
        assert session["task"] == "Task"
        assert session["approved"] is False

    def test_start_approval_summary_contains_confidence(self, tmp_agent_dir):
        result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        summary = data["approval_summary"]
        assert summary["confidence"] == "tested"
        assert "decay_warning" not in summary  # tested is not decayed

    def test_start_unknown_pack_returns_error(self, tmp_agent_dir):
        result = apply_mod.action_start("nonexistent-pack", "Task", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "Pack not found" in data["error"]

    def test_start_includes_instructions(self, tmp_agent_dir):
        result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert "instructions" in data
        assert "__approval__" in data["instructions"]
        assert "checkpoint" in data["instructions"]


# ---------------------------------------------------------------------------
# Tests: action_checkpoint
# ---------------------------------------------------------------------------

class TestActionCheckpoint:
    def test_checkpoint_approval_pass(self, tmp_agent_dir):
        # Start first
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        # Approve
        cp_result = apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["phase"] == "__approval__"
        assert data["status"] == "passed"
        assert data["next_action"] == "continue"

    def test_checkpoint_approval_fail_rejects(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        cp_result = apply_mod.action_checkpoint(
            session_id, "__approval__", "failed", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["status"] == "rejected"
        assert data["next_action"] == "stop"

    def test_checkpoint_blocked_before_approval(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is False
        assert "not yet approved" in data["error"]

    def test_checkpoint_phase_pass(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        # Approve first
        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        # Pass first phase
        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", evidence="Step 1 done", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["phase"] == "phase_one"
        assert data["status"] == "passed"
        assert data["next_action"] == "continue"
        assert data["phases_completed"] == 1

    def test_checkpoint_phase_fail_triggers_retry(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        # Fail first phase (first attempt)
        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", evidence="Not ready", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["next_action"] == "retry"
        assert "attempt 2" in data["guidance"]

    def test_checkpoint_phase_fail_after_retry_skips(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        # Fail first attempt
        apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", agent_dir=tmp_agent_dir
        )

        # Fail second attempt (retry exhausted)
        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["next_action"] == "skip"

    def test_checkpoint_unknown_phase(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        cp_result = apply_mod.action_checkpoint(
            session_id, "nonexistent_phase", "passed", agent_dir=tmp_agent_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is False
        assert "not found" in data["error"]


# ---------------------------------------------------------------------------
# Tests: action_complete
# ---------------------------------------------------------------------------

class TestActionComplete:
    def test_complete_flow(self, tmp_agent_dir):
        # Start
        start_result = apply_mod.action_start("test-pack", "My task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        # Approve and pass both phases
        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", agent_dir=tmp_agent_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_two", "passed", agent_dir=tmp_agent_dir
        )

        # Complete
        comp_result = apply_mod.action_complete(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(comp_result)

        assert data["success"] is True
        assert "summary" in data
        assert data["summary"]["phases_passed"] == 2
        assert data["summary"]["phases_failed"] == 0
        assert data["summary"]["phases_total"] == 2
        assert "feedback_draft" in data
        assert "feedback_path" in data

    def test_complete_with_partial_failure(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", agent_dir=tmp_agent_dir
        )
        # After retry fails, phase_one is marked failed and skipped
        apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", agent_dir=tmp_agent_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_two", "passed", agent_dir=tmp_agent_dir
        )

        comp_result = apply_mod.action_complete(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(comp_result)

        assert data["success"] is True
        summary = data["summary"]
        assert summary["phases_passed"] == 1
        assert summary["phases_failed"] == 1

        # Feedback draft should mention failure
        fd = data["feedback_draft"]
        assert "what_changed" in fd
        assert "why_it_worked" in fd

    def test_complete_unknown_session(self, tmp_agent_dir):
        result = apply_mod.action_complete("nonexistent-session", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "No active session" in data["error"]

    def test_complete_cleans_up_session(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", agent_dir=tmp_agent_dir
        )

        apply_mod.action_complete(session_id, agent_dir=tmp_agent_dir)

        # Session should be gone from active store
        assert sess_mod.get_active_session(session_id) is None


# ---------------------------------------------------------------------------
# Tests: action_resume
# ---------------------------------------------------------------------------

class TestActionResume:
    def test_resume_from_persisted_session(self, tmp_agent_dir):
        # Start and approve
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", agent_dir=tmp_agent_dir
        )

        # Clear in-memory but keep disk
        apply_mod._active_apply_state.clear()
        sess_mod._active_sessions.clear()

        # Resume
        resume_result = apply_mod.action_resume("test-pack", agent_dir=tmp_agent_dir)
        data = parse_result(resume_result)

        assert data["success"] is True
        assert data["resumed_from"] == "persisted_session"
        assert data["phases_completed"] == 1
        assert data["phases_remaining"] == 1
        assert len(data["remaining_phases"]) == 1
        assert data["remaining_phases"][0]["name"] == "phase_two"

    def test_resume_from_log_file(self, tmp_agent_dir):
        # Simulate a session that was only in memory then lost
        # First create a pack dir and a fake log
        pack_dir = make_pack_dir(tmp_agent_dir)
        log_path = tmp_agent_dir / "executions" / "test-pack-v1-20260101T000000.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            json.dumps({"event": "execution_started", "task": "Old task", "phase_count": 2, "ts": "2026-01-01T00:00:00+00:00"}) + "\n"
            + json.dumps({"event": "checkpoint_passed", "phase": "phase_one", "evidence": "done", "attempt": 1, "ts": "2026-01-01T00:01:00+00:00"}) + "\n",
            encoding="utf-8",
        )

        resume_result = apply_mod.action_resume("test-pack", agent_dir=tmp_agent_dir)
        data = parse_result(resume_result)

        assert data["success"] is True
        assert data["phases_completed"] == 1
        assert data["phases_remaining"] == 1
        assert data["remaining_phases"][0]["name"] == "phase_two"

    def test_resume_pack_not_found(self, tmp_agent_dir):
        result = apply_mod.action_resume("nonexistent-pack", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "Pack not found" in data["error"]


# ---------------------------------------------------------------------------
# Tests: action_status
# ---------------------------------------------------------------------------

class TestActionStatus:
    def test_status_returns_session_state(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        status_result = apply_mod.action_status(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(status_result)

        assert data["success"] is True
        assert data["session_id"] == session_id
        assert data["task"] == "Task"
        assert data["approved"] is False
        assert len(data["phases"]) == 2

    def test_status_unknown_session(self, tmp_agent_dir):
        result = apply_mod.action_status("nonexistent-session", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "No active session" in data["error"]

    def test_status_after_approval(self, tmp_agent_dir):
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        status_result = apply_mod.action_status(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(status_result)

        assert data["success"] is True
        assert data["approved"] is True


# ---------------------------------------------------------------------------
# Tests: apply_handler dispatch
# ---------------------------------------------------------------------------

class TestApplyHandler:
    def test_dispatch_start(self, tmp_agent_dir):
        result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="My task", agent_dir=tmp_agent_dir
        )
        data = parse_result(result)

        assert data["success"] is True
        assert "session_id" in data

    def test_dispatch_start_missing_pack_name(self, tmp_agent_dir):
        result = apply_mod.apply_handler(action="start", task="Task", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "pack_name" in data["error"]

    def test_dispatch_start_missing_task(self, tmp_agent_dir):
        result = apply_mod.apply_handler(action="start", pack_name="test-pack", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "task" in data["error"]

    def test_dispatch_checkpoint(self, tmp_agent_dir):
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", agent_dir=tmp_agent_dir
        )
        session_id = parse_result(start_result)["session_id"]

        cp_result = apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )
        data = parse_result(cp_result)

        assert data["success"] is True

    def test_dispatch_checkpoint_missing_session_id(self, tmp_agent_dir):
        result = apply_mod.apply_handler(
            action="checkpoint", phase_name="phase_one", status="passed", agent_dir=tmp_agent_dir
        )
        data = parse_result(result)

        assert data["success"] is False
        assert "session_id" in data["error"]

    def test_dispatch_complete(self, tmp_agent_dir):
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", agent_dir=tmp_agent_dir
        )
        session_id = parse_result(start_result)["session_id"]

        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        comp_result = apply_mod.apply_handler(
            action="complete", session_id=session_id, agent_dir=tmp_agent_dir
        )
        data = parse_result(comp_result)

        assert data["success"] is True

    def test_dispatch_resume(self, tmp_agent_dir):
        # Start + approve + checkpoint, then clear memory
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", agent_dir=tmp_agent_dir
        )
        session_id = parse_result(start_result)["session_id"]

        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        # Clear memory
        apply_mod._active_apply_state.clear()
        sess_mod._active_sessions.clear()

        resume_result = apply_mod.apply_handler(
            action="resume", pack_name="test-pack", agent_dir=tmp_agent_dir
        )
        data = parse_result(resume_result)

        assert data["success"] is True

    def test_dispatch_status(self, tmp_agent_dir):
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", agent_dir=tmp_agent_dir
        )
        session_id = parse_result(start_result)["session_id"]

        status_result = apply_mod.apply_handler(
            action="status", session_id=session_id, agent_dir=tmp_agent_dir
        )
        data = parse_result(status_result)

        assert data["success"] is True
        assert data["session_id"] == session_id

    def test_dispatch_unknown_action(self, tmp_agent_dir):
        result = apply_mod.apply_handler(action="fly", agent_dir=tmp_agent_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "Unknown action" in data["error"]


# --------------------------------------------------------------------------
# Tests: reputation store logging (mocked)
# --------------------------------------------------------------------------


class TestReputationLogging:
    """Tests that action_complete logs execution events to the store."""

    def test_complete_calls_record_execution_on_store(self, tmp_agent_dir, monkeypatch):
        """action_complete calls store.record_execution() after success."""
        mock_store = MagicMock()
        monkeypatch.setattr(apply_mod, "AgentStore", lambda: mock_store)

        # Start + approve + phase checkpoint
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        # Complete the session
        comp_result = apply_mod.action_complete(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(comp_result)
        assert data["success"] is True

        # Verify record_execution was called
        mock_store.record_execution.assert_called_once()
        call_kwargs = mock_store.record_execution.call_args.kwargs
        assert call_kwargs["pack_id"] == "test-pack-v1"
        assert call_kwargs["session_id"] == session_id
        assert call_kwargs["status"] == "completed"
        mock_store.close.assert_called_once()

    def test_complete_store_failure_does_not_break_flow(self, tmp_agent_dir, monkeypatch):
        """If store.record_execution raises, action_complete still returns success."""
        mock_store = MagicMock()
        mock_store.record_execution.side_effect = Exception("DB unavailable")
        monkeypatch.setattr(apply_mod, "AgentStore", lambda: mock_store)

        # Start + approve + phase checkpoint
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        # Complete should still succeed despite store failure
        comp_result = apply_mod.action_complete(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(comp_result)
        assert data["success"] is True

    def test_complete_works_when_guildstore_is_none(self, tmp_agent_dir, monkeypatch):
        """action_complete works when AgentStore import fails (store unavailable)."""
        monkeypatch.setattr(apply_mod, "AgentStore", None)

        # Start + approve + phase checkpoint
        start_result = apply_mod.action_start("test-pack", "Task", agent_dir=tmp_agent_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", agent_dir=tmp_agent_dir
        )

        comp_result = apply_mod.action_complete(session_id, agent_dir=tmp_agent_dir)
        data = parse_result(comp_result)
        assert data["success"] is True
