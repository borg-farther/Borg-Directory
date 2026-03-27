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

from guild.core import apply as apply_mod
from guild.core import session as sess_mod


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


def make_pack_dir(guild_dir: Path, pack_name: str = "test-pack") -> Path:
    """Create a minimal pack directory with pack.yaml."""
    pack_dir = guild_dir / pack_name
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
def tmp_guild_dir():
    """Create a temporary GUILD_DIR and patch apply module to use it."""
    original_guild_dir = apply_mod.GUILD_DIR
    original_home = apply_mod.HERMES_HOME

    tmp = tempfile.mkdtemp(prefix="guild_test_")
    guild_dir = Path(tmp) / "guild"
    (guild_dir / "sessions").mkdir(parents=True)
    (guild_dir / "executions").mkdir(parents=True)

    apply_mod.GUILD_DIR = guild_dir
    apply_mod.HERMES_HOME = Path(tmp)
    apply_mod.EXECUTIONS_DIR = guild_dir / "executions"

    # Also patch session module
    orig_sess_guild_dir = sess_mod.GUILD_DIR
    orig_sess_home = sess_mod.HERMES_HOME
    orig_sess_exec = sess_mod.EXECUTIONS_DIR
    sess_mod.GUILD_DIR = guild_dir
    sess_mod.HERMES_HOME = Path(tmp)
    sess_mod.EXECUTIONS_DIR = guild_dir / "executions"

    make_pack_dir(guild_dir)

    yield guild_dir

    # Restore
    apply_mod.GUILD_DIR = original_guild_dir
    apply_mod.HERMES_HOME = original_home
    apply_mod.EXECUTIONS_DIR = original_guild_dir / "executions"
    sess_mod.GUILD_DIR = orig_sess_guild_dir
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
    def test_start_returns_success(self, tmp_guild_dir):
        result = apply_mod.action_start("test-pack", "My test task", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is True
        assert "session_id" in data
        assert data["session_id"].startswith("test-pack-")
        assert data["action_needed"] == "approve"
        assert "approval_summary" in data
        assert data["approval_summary"]["pack_name"] == "test-pack"
        assert len(data["phases"]) == 2

    def test_start_creates_session(self, tmp_guild_dir):
        result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        data = parse_result(result)
        session_id = data["session_id"]

        # Session should be registered in session module
        session = sess_mod.get_active_session(session_id)
        assert session is not None
        assert session["pack_name"] == "test-pack"
        assert session["task"] == "Task"
        assert session["approved"] is False

    def test_start_approval_summary_contains_confidence(self, tmp_guild_dir):
        result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        summary = data["approval_summary"]
        assert summary["confidence"] == "tested"
        assert "decay_warning" not in summary  # tested is not decayed

    def test_start_unknown_pack_returns_error(self, tmp_guild_dir):
        result = apply_mod.action_start("nonexistent-pack", "Task", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "Pack not found" in data["error"]

    def test_start_includes_instructions(self, tmp_guild_dir):
        result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert "instructions" in data
        assert "__approval__" in data["instructions"]
        assert "checkpoint" in data["instructions"]


# ---------------------------------------------------------------------------
# Tests: action_checkpoint
# ---------------------------------------------------------------------------

class TestActionCheckpoint:
    def test_checkpoint_approval_pass(self, tmp_guild_dir):
        # Start first
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        # Approve
        cp_result = apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["phase"] == "__approval__"
        assert data["status"] == "passed"
        assert data["next_action"] == "continue"

    def test_checkpoint_approval_fail_rejects(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        cp_result = apply_mod.action_checkpoint(
            session_id, "__approval__", "failed", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["status"] == "rejected"
        assert data["next_action"] == "stop"

    def test_checkpoint_blocked_before_approval(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is False
        assert "not yet approved" in data["error"]

    def test_checkpoint_phase_pass(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        # Approve first
        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )

        # Pass first phase
        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", evidence="Step 1 done", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["phase"] == "phase_one"
        assert data["status"] == "passed"
        assert data["next_action"] == "continue"
        assert data["phases_completed"] == 1

    def test_checkpoint_phase_fail_triggers_retry(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )

        # Fail first phase (first attempt)
        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", evidence="Not ready", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["next_action"] == "retry"
        assert "attempt 2" in data["guidance"]

    def test_checkpoint_phase_fail_after_retry_skips(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )

        # Fail first attempt
        apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", guild_dir=tmp_guild_dir
        )

        # Fail second attempt (retry exhausted)
        cp_result = apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is True
        assert data["next_action"] == "skip"

    def test_checkpoint_unknown_phase(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )

        cp_result = apply_mod.action_checkpoint(
            session_id, "nonexistent_phase", "passed", guild_dir=tmp_guild_dir
        )
        data = parse_result(cp_result)

        assert data["success"] is False
        assert "not found" in data["error"]


# ---------------------------------------------------------------------------
# Tests: action_complete
# ---------------------------------------------------------------------------

class TestActionComplete:
    def test_complete_flow(self, tmp_guild_dir):
        # Start
        start_result = apply_mod.action_start("test-pack", "My task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        # Approve and pass both phases
        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", guild_dir=tmp_guild_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_two", "passed", guild_dir=tmp_guild_dir
        )

        # Complete
        comp_result = apply_mod.action_complete(session_id, guild_dir=tmp_guild_dir)
        data = parse_result(comp_result)

        assert data["success"] is True
        assert "summary" in data
        assert data["summary"]["phases_passed"] == 2
        assert data["summary"]["phases_failed"] == 0
        assert data["summary"]["phases_total"] == 2
        assert "feedback_draft" in data
        assert "feedback_path" in data

    def test_complete_with_partial_failure(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", guild_dir=tmp_guild_dir
        )
        # After retry fails, phase_one is marked failed and skipped
        apply_mod.action_checkpoint(
            session_id, "phase_one", "failed", guild_dir=tmp_guild_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_two", "passed", guild_dir=tmp_guild_dir
        )

        comp_result = apply_mod.action_complete(session_id, guild_dir=tmp_guild_dir)
        data = parse_result(comp_result)

        assert data["success"] is True
        summary = data["summary"]
        assert summary["phases_passed"] == 1
        assert summary["phases_failed"] == 1

        # Feedback draft should mention failure
        fd = data["feedback_draft"]
        assert "what_changed" in fd
        assert "why_it_worked" in fd

    def test_complete_unknown_session(self, tmp_guild_dir):
        result = apply_mod.action_complete("nonexistent-session", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "No active session" in data["error"]

    def test_complete_cleans_up_session(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", guild_dir=tmp_guild_dir
        )

        apply_mod.action_complete(session_id, guild_dir=tmp_guild_dir)

        # Session should be gone from active store
        assert sess_mod.get_active_session(session_id) is None


# ---------------------------------------------------------------------------
# Tests: action_resume
# ---------------------------------------------------------------------------

class TestActionResume:
    def test_resume_from_persisted_session(self, tmp_guild_dir):
        # Start and approve
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )
        apply_mod.action_checkpoint(
            session_id, "phase_one", "passed", guild_dir=tmp_guild_dir
        )

        # Clear in-memory but keep disk
        apply_mod._active_apply_state.clear()
        sess_mod._active_sessions.clear()

        # Resume
        resume_result = apply_mod.action_resume("test-pack", guild_dir=tmp_guild_dir)
        data = parse_result(resume_result)

        assert data["success"] is True
        assert data["resumed_from"] == "persisted_session"
        assert data["phases_completed"] == 1
        assert data["phases_remaining"] == 1
        assert len(data["remaining_phases"]) == 1
        assert data["remaining_phases"][0]["name"] == "phase_two"

    def test_resume_from_log_file(self, tmp_guild_dir):
        # Simulate a session that was only in memory then lost
        # First create a pack dir and a fake log
        pack_dir = make_pack_dir(tmp_guild_dir)
        log_path = tmp_guild_dir / "executions" / "test-pack-v1-20260101T000000.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            json.dumps({"event": "execution_started", "task": "Old task", "phase_count": 2, "ts": "2026-01-01T00:00:00+00:00"}) + "\n"
            + json.dumps({"event": "checkpoint_passed", "phase": "phase_one", "evidence": "done", "attempt": 1, "ts": "2026-01-01T00:01:00+00:00"}) + "\n",
            encoding="utf-8",
        )

        resume_result = apply_mod.action_resume("test-pack", guild_dir=tmp_guild_dir)
        data = parse_result(resume_result)

        assert data["success"] is True
        assert data["phases_completed"] == 1
        assert data["phases_remaining"] == 1
        assert data["remaining_phases"][0]["name"] == "phase_two"

    def test_resume_pack_not_found(self, tmp_guild_dir):
        result = apply_mod.action_resume("nonexistent-pack", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "Pack not found" in data["error"]


# ---------------------------------------------------------------------------
# Tests: action_status
# ---------------------------------------------------------------------------

class TestActionStatus:
    def test_status_returns_session_state(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        status_result = apply_mod.action_status(session_id, guild_dir=tmp_guild_dir)
        data = parse_result(status_result)

        assert data["success"] is True
        assert data["session_id"] == session_id
        assert data["task"] == "Task"
        assert data["approved"] is False
        assert len(data["phases"]) == 2

    def test_status_unknown_session(self, tmp_guild_dir):
        result = apply_mod.action_status("nonexistent-session", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "No active session" in data["error"]

    def test_status_after_approval(self, tmp_guild_dir):
        start_result = apply_mod.action_start("test-pack", "Task", guild_dir=tmp_guild_dir)
        session_id = parse_result(start_result)["session_id"]

        apply_mod.action_checkpoint(
            session_id, "__approval__", "passed", guild_dir=tmp_guild_dir
        )

        status_result = apply_mod.action_status(session_id, guild_dir=tmp_guild_dir)
        data = parse_result(status_result)

        assert data["success"] is True
        assert data["approved"] is True


# ---------------------------------------------------------------------------
# Tests: apply_handler dispatch
# ---------------------------------------------------------------------------

class TestApplyHandler:
    def test_dispatch_start(self, tmp_guild_dir):
        result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="My task", guild_dir=tmp_guild_dir
        )
        data = parse_result(result)

        assert data["success"] is True
        assert "session_id" in data

    def test_dispatch_start_missing_pack_name(self, tmp_guild_dir):
        result = apply_mod.apply_handler(action="start", task="Task", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "pack_name" in data["error"]

    def test_dispatch_start_missing_task(self, tmp_guild_dir):
        result = apply_mod.apply_handler(action="start", pack_name="test-pack", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "task" in data["error"]

    def test_dispatch_checkpoint(self, tmp_guild_dir):
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", guild_dir=tmp_guild_dir
        )
        session_id = parse_result(start_result)["session_id"]

        cp_result = apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            guild_dir=tmp_guild_dir,
        )
        data = parse_result(cp_result)

        assert data["success"] is True

    def test_dispatch_checkpoint_missing_session_id(self, tmp_guild_dir):
        result = apply_mod.apply_handler(
            action="checkpoint", phase_name="phase_one", status="passed", guild_dir=tmp_guild_dir
        )
        data = parse_result(result)

        assert data["success"] is False
        assert "session_id" in data["error"]

    def test_dispatch_complete(self, tmp_guild_dir):
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", guild_dir=tmp_guild_dir
        )
        session_id = parse_result(start_result)["session_id"]

        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            guild_dir=tmp_guild_dir,
        )

        comp_result = apply_mod.apply_handler(
            action="complete", session_id=session_id, guild_dir=tmp_guild_dir
        )
        data = parse_result(comp_result)

        assert data["success"] is True

    def test_dispatch_resume(self, tmp_guild_dir):
        # Start + approve + checkpoint, then clear memory
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", guild_dir=tmp_guild_dir
        )
        session_id = parse_result(start_result)["session_id"]

        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            guild_dir=tmp_guild_dir,
        )

        # Clear memory
        apply_mod._active_apply_state.clear()
        sess_mod._active_sessions.clear()

        resume_result = apply_mod.apply_handler(
            action="resume", pack_name="test-pack", guild_dir=tmp_guild_dir
        )
        data = parse_result(resume_result)

        assert data["success"] is True

    def test_dispatch_status(self, tmp_guild_dir):
        start_result = apply_mod.apply_handler(
            action="start", pack_name="test-pack", task="Task", guild_dir=tmp_guild_dir
        )
        session_id = parse_result(start_result)["session_id"]

        status_result = apply_mod.apply_handler(
            action="status", session_id=session_id, guild_dir=tmp_guild_dir
        )
        data = parse_result(status_result)

        assert data["success"] is True
        assert data["session_id"] == session_id

    def test_dispatch_unknown_action(self, tmp_guild_dir):
        result = apply_mod.apply_handler(action="fly", guild_dir=tmp_guild_dir)
        data = parse_result(result)

        assert data["success"] is False
        assert "Unknown action" in data["error"]
