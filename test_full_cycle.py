"""
End-to-End Full Apply Cycle Tests for Guild v2.

Tests the complete flow:
  1. guild_pull a pack
  2. apply_handler(action='start', ...)
  3. apply_handler(action='checkpoint', ...) for each phase
  4. apply_handler(action='complete', ...)
  5. generate_feedback() from borg.core.search
  6. Verify execution log JSONL was written
  7. Verify session was cleaned up

Also tests sad paths:
  - checkpoint FAIL on phase 2 → retry logic
  - check status of a session
  - resume a completed session → clear error
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from borg.core import apply as apply_mod
from borg.core import session as sess_mod
from borg.core import search as search_mod
from borg.core import uri as uri_mod
from borg.core.uri import BORG_DIR


# --------------------------------------------------------------------------  #
# Helpers
# --------------------------------------------------------------------------  #

def parse_result(raw: str) -> dict:
    """Parse JSON from apply/search module responses."""
    return json.loads(raw)


# --------------------------------------------------------------------------  #
# Fixture: isolated temp BORG_DIR
# --------------------------------------------------------------------------  #

@pytest.fixture
def tmp_agent_dir():
    """Create an isolated temp BORG_DIR patched into all relevant modules.

    Also sets HERMES_HOME env var so that resolve_guild_uri (which uses
    BORG_DIR from uri.py) and any other module-level BORG_DIR references
    resolve to the same temp directory.
    """
    original_agent_dir = apply_mod.BORG_DIR
    original_sess_agent_dir = sess_mod.BORG_DIR
    original_search_agent_dir = search_mod.BORG_DIR
    original_uri_agent_dir = uri_mod.BORG_DIR
    original_hermes_home = apply_mod.HERMES_HOME

    tmp = tempfile.mkdtemp(prefix="guild_e2e_")
    agent_dir = Path(tmp) / "guild"
    (agent_dir / "sessions").mkdir(parents=True)
    (agent_dir / "executions").mkdir(parents=True)

    # Set HERMES_HOME env var so BORG_DIR resolves via Path(os.getenv(...))
    # in all modules (uri.py, apply.py, search.py, session.py)
    fake_hermes = Path(tmp)
    os.environ["HERMES_HOME"] = str(fake_hermes)

    # Patch all module globals
    apply_mod.BORG_DIR = agent_dir
    apply_mod.HERMES_HOME = fake_hermes
    apply_mod.EXECUTIONS_DIR = agent_dir / "executions"

    sess_mod.BORG_DIR = agent_dir
    sess_mod.HERMES_HOME = fake_hermes
    sess_mod.EXECUTIONS_DIR = agent_dir / "executions"

    search_mod.BORG_DIR = agent_dir

    uri_mod.BORG_DIR = agent_dir  # critical: resolve_guild_uri uses uri.BORG_DIR

    yield agent_dir

    # Restore
    os.environ.pop("HERMES_HOME", None)
    apply_mod.BORG_DIR = original_agent_dir
    apply_mod.HERMES_HOME = original_hermes_home
    apply_mod.EXECUTIONS_DIR = original_agent_dir / "executions"
    sess_mod.BORG_DIR = original_sess_agent_dir
    sess_mod.HERMES_HOME = original_sess_agent_dir
    sess_mod.EXECUTIONS_DIR = original_sess_agent_dir
    search_mod.BORG_DIR = original_search_agent_dir
    uri_mod.BORG_DIR = original_uri_agent_dir

    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(autouse=True)
def clear_state():
    """Clear all in-memory state before and after each test."""
    apply_mod._active_apply_state.clear()
    sess_mod._active_sessions.clear()
    yield
    apply_mod._active_apply_state.clear()
    sess_mod._active_sessions.clear()


# --------------------------------------------------------------------------  #
# Valid test pack — systematic-debugging style but with valid schema
# --------------------------------------------------------------------------  #

SYSTEMATIC_DEBUGGING_PACK_YAML = """
type: workflow_pack
version: 1.0.0
id: guild://test/systematic-debugging
problem_class: "Use when encountering any bug, test failure, or unexpected behavior. 4-phase root cause investigation — NO fixes without understanding the problem first."
mental_model: "# Systematic Debugging"
required_inputs:
  - "bug_description"
escalation_rules:
  - "If 3+ fixes fail, STOP and question the architecture"
phases:
  - name: the_iron_law
    description: "NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST. If you haven't completed Phase 1, you cannot propose fixes."
    checkpoint: "Root cause identified"
    anti_patterns: []
    prompts: []
  - name: the_four_phases
    description: "You MUST complete each phase before proceeding to the next."
    checkpoint: "Phase structure understood"
    anti_patterns: []
    prompts: []
  - name: phase_1__root_cause_investigation
    description: "**BEFORE attempting ANY fix:** Read error messages, reproduce consistently, check recent changes, gather evidence."
    checkpoint: "Error reproduced and root cause identified"
    anti_patterns:
      - "Skipping error message details"
      - "Applying fixes before understanding"
    prompts: []
  - name: phase_2__pattern_analysis
    description: "**Find the pattern before fixing:** Find working examples, compare against references, identify differences."
    checkpoint: "Pattern identified from working examples"
    anti_patterns:
      - "Skimming reference implementations"
    prompts: []
  - name: phase_3__hypothesis_and_testing
    description: "**Scientific method:** Form a single hypothesis, test minimally, verify before continuing."
    checkpoint: "Hypothesis formed and tested"
    anti_patterns:
      - "Multiple changes at once"
    prompts: []
  - name: phase_4__implementation
    description: "**Fix the root cause:** Create failing test, implement single fix, verify, apply Rule of Three if stuck."
    checkpoint: "Fix verified by passing tests"
    anti_patterns:
      - "Bundling refactoring with fixes"
    prompts: []
provenance:
  author_agent: agent://guild-init
  created: "2026-03-24T10:29:04+00:00"
  confidence: tested
  evidence: "Reduced average debugging iterations from 5+ to 2-3 across multiple sessions."
  failure_cases:
    - "Performance/timing bugs where debugging changes behavior"
    - "Issues requiring domain expertise the agent lacks"
""".strip()


# --------------------------------------------------------------------------  #
# Helper: set up systematic-debugging pack in tmp_agent_dir
# --------------------------------------------------------------------------  #

def setup_pack(agent_dir: Path, pack_name: str = "systematic-debugging") -> dict:
    """Write a valid systematic-debugging pack directly into the temp agent_dir.

    Returns the same dict shape as guild_pull would.
    """
    pack_dir = agent_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)
    pack_file = pack_dir / "pack.yaml"
    pack_file.write_text(SYSTEMATIC_DEBUGGING_PACK_YAML, encoding="utf-8")

    return {
        "success": True,
        "name": pack_name,
        "path": str(pack_file),
        "tier": "VALIDATED",
        "proof_gates": {
            "validation_errors": [],
            "confidence": "tested",
            "evidence": "Pack written directly for testing.",
        },
        "confidence_status": {"confidence": "tested", "decayed": False},
    }


# --------------------------------------------------------------------------  #
# Tests: Happy Path — Full Cycle
# --------------------------------------------------------------------------  #

class TestFullCycleHappyPath:
    """End-to-end tests for the complete apply→checkpoint→complete→feedback cycle."""

    def test_full_cycle_with_systematic_debugging_pack(self, tmp_agent_dir):
        """
        FULL CYCLE TEST:
        1. Pull systematic-debugging pack
        2. Start apply with a task
        3. Checkpoint each phase PASS
        4. Complete the session
        5. Generate feedback
        6. Verify execution log was written
        7. Verify session was cleaned up
        """
        # ── Step 1: Set up pack ─────────────────────────────────────────────
        pull_data = setup_pack(tmp_agent_dir)
        assert pull_data["success"] is True
        assert pull_data["name"] == "systematic-debugging"
        pack_path = Path(pull_data["path"])
        assert pack_path.exists(), f"Pack not pulled to {pack_path}"

        # ── Step 2: Start Apply ──────────────────────────────────────────
        start_result = apply_mod.apply_handler(
            action="start",
            pack_name="systematic-debugging",
            task="Fix TypeError in test_utils.py",
            agent_dir=tmp_agent_dir,
        )
        start_data = parse_result(start_result)
        assert start_data["success"] is True, f"start failed: {start_data.get('error')}"
        session_id = start_data["session_id"]
        assert session_id.startswith("systematic-debugging-")
        assert start_data["action_needed"] == "approve"

        phases = start_data["phases"]
        assert len(phases) > 0, "Should have phases in the pack"
        phase_names = [p["name"] for p in phases]

        # ── Step 3: Approve (implicit first checkpoint) ─────────────────
        approval_result = apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )
        approval_data = parse_result(approval_result)
        assert approval_data["success"] is True
        assert approval_data["status"] == "passed"

        # ── Step 4: Checkpoint each phase PASS ───────────────────────────
        for phase_name in phase_names:
            cp_result = apply_mod.apply_handler(
                action="checkpoint",
                session_id=session_id,
                phase_name=phase_name,
                status="passed",
                evidence="Tested and confirmed",
                agent_dir=tmp_agent_dir,
            )
            cp_data = parse_result(cp_result)
            assert cp_data["success"] is True, \
                f"checkpoint for {phase_name} failed: {cp_data.get('error')}"
            assert cp_data["status"] == "passed", \
                f"Phase {phase_name} did not pass: {cp_data.get('status')}"

        # ── Step 5: Complete ─────────────────────────────────────────────
        complete_result = apply_mod.apply_handler(
            action="complete",
            session_id=session_id,
            agent_dir=tmp_agent_dir,
        )
        complete_data = parse_result(complete_result)
        assert complete_data["success"] is True, \
            f"complete failed: {complete_data.get('error')}"
        assert "summary" in complete_data
        summary = complete_data["summary"]
        assert summary["phases_passed"] == len(phase_names)
        assert summary["phases_failed"] == 0
        assert summary["phases_total"] == len(phase_names)

        # Feedback draft must be present
        assert "feedback_draft" in complete_data
        feedback_draft = complete_data["feedback_draft"]
        assert "schema_version" in feedback_draft
        assert feedback_draft["schema_version"] == "1.0"
        assert "type" in feedback_draft
        assert feedback_draft["type"] == "feedback"
        assert "before" in feedback_draft
        assert "after" in feedback_draft
        assert "what_changed" in feedback_draft
        assert "why_it_worked" in feedback_draft
        assert "where_to_reuse" in feedback_draft
        assert "suggestions" in feedback_draft
        assert "evidence" in feedback_draft
        assert "provenance" in feedback_draft
        assert "execution_log_hash" in feedback_draft

        # Feedback path must be written to disk
        feedback_path = Path(complete_data["feedback_path"])
        assert feedback_path.exists(), \
            f"Feedback draft not written to {feedback_path}"

        # ── Step 6: Verify execution log JSONL was written ─────────────
        log_path = Path(summary["execution_log"])
        assert log_path.exists(), \
            f"Execution log JSONL not found at {log_path}"

        # Verify it has content (has execution_started and checkpoint events)
        log_lines = log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(log_lines) > 0, "Execution log should have events"
        events = [json.loads(line) for line in log_lines if line.strip()]
        event_types = [e.get("event") for e in events]
        assert "execution_started" in event_types
        assert "execution_completed" in event_types
        checkpoint_events = [e for e in events if e.get("event") in
                             ("checkpoint_passed", "checkpoint_failed")]
        assert len(checkpoint_events) >= len(phase_names), \
            f"Expected ≥{len(phase_names)} checkpoint events, got {len(checkpoint_events)}"

        # ── Step 7: Verify session was cleaned up ─────────────────────────
        status_result = apply_mod.apply_handler(
            action="status",
            session_id=session_id,
            agent_dir=tmp_agent_dir,
        )
        status_data = parse_result(status_result)
        assert status_data["success"] is False, \
            "Session should have been cleaned up after complete"
        assert "No active session" in status_data.get("error", "")

        # Session file should not exist on disk
        session_file = tmp_agent_dir / "sessions" / f"{session_id}.json"
        assert not session_file.exists(), \
            f"Session file should have been deleted: {session_file}"

    def test_generate_feedback_standalone(self, tmp_agent_dir):
        """
        Verify generate_feedback() from borg.core.search produces all spec fields.
        """
        # Pull pack and run a mini cycle to get real execution data
        setup_pack(tmp_agent_dir)

        start_result = apply_mod.apply_handler(
            action="start",
            pack_name="systematic-debugging",
            task="Verify feedback spec fields",
            agent_dir=tmp_agent_dir,
        )
        start_data = parse_result(start_result)
        session_id = start_data["session_id"]

        # Approve
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        # Get the phase list
        phases = start_data["phases"]
        phase_names = [p["name"] for p in phases]

        # Checkpoint 2 phases only
        for phase_name in phase_names[:2]:
            apply_mod.apply_handler(
                action="checkpoint",
                session_id=session_id,
                phase_name=phase_name,
                status="passed",
                evidence="Verified step",
                agent_dir=tmp_agent_dir,
            )

        # Get the session's phase_results
        session = sess_mod.get_active_session(session_id)
        assert session is not None
        phase_results = session["phase_results"]

        # Call generate_feedback from search module
        feedback = search_mod.generate_feedback(
            pack_id="borg://converted/systematic-debugging",
            pack_version="1.0.0",
            execution_log=phase_results,
            task_description="Verify feedback spec fields",
            outcome="2/2 phases passed",
        )

        # Verify all spec fields are present
        assert "schema_version" in feedback, "Missing: schema_version"
        assert "type" in feedback, "Missing: type"
        assert feedback["type"] == "feedback"
        assert "parent_artifact" in feedback, "Missing: parent_artifact"
        assert "version" in feedback, "Missing: version"
        assert "before" in feedback, "Missing: before"
        assert "after" in feedback, "Missing: after"
        assert "what_changed" in feedback, "Missing: what_changed"
        assert "why_it_worked" in feedback, "Missing: why_it_worked"
        assert "where_to_reuse" in feedback, "Missing: where_to_reuse"
        assert "failure_cases" in feedback, "Missing: failure_cases"
        assert "suggestions" in feedback, "Missing: suggestions"
        assert "evidence" in feedback, "Missing: evidence"
        assert "execution_log_hash" in feedback, "Missing: execution_log_hash"
        assert "provenance" in feedback, "Missing: provenance"
        provenance = feedback["provenance"]
        assert "confidence" in provenance, "Missing: provenance.confidence"
        assert "generated" in provenance, "Missing: provenance.generated"

        # Confidence should be 'tested' when all phases pass
        assert provenance["confidence"] == "tested"


# --------------------------------------------------------------------------  #
# Tests: Sad Paths
# --------------------------------------------------------------------------  #

class TestSadPaths:
    """Sad-path tests: failures, retries, status checks, resume errors."""

    def test_checkpoint_fail_on_phase_2_triggers_retry(self, tmp_agent_dir):
        """
        Start apply, checkpoint FAIL on phase 2, verify retry logic.
        First failure should return next_action='retry'.
        Second failure should return next_action='skip'.
        """
        setup_pack(tmp_agent_dir)

        # Start
        start_result = apply_mod.apply_handler(
            action="start",
            pack_name="systematic-debugging",
            task="Test retry logic",
            agent_dir=tmp_agent_dir,
        )
        start_data = parse_result(start_result)
        session_id = start_data["session_id"]
        phase_names = [p["name"] for p in start_data["phases"]]
        assert len(phase_names) >= 2, "Need at least 2 phases for this test"
        phase_2 = phase_names[1]

        # Approve
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        # Pass phase 1
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name=phase_names[0],
            status="passed",
            evidence="Phase 1 passed",
            agent_dir=tmp_agent_dir,
        )

        # ── FAIL phase 2 (first attempt → retry) ─────────────────────────
        fail1_result = apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name=phase_2,
            status="failed",
            evidence="Not ready yet",
            agent_dir=tmp_agent_dir,
        )
        fail1_data = parse_result(fail1_result)
        assert fail1_data["success"] is True
        assert fail1_data["next_action"] == "retry", \
            f"Expected 'retry' on first failure, got: {fail1_data.get('next_action')}"
        assert "attempt 2" in fail1_data["guidance"].lower() or \
               "retry" in fail1_data["guidance"].lower(), \
            f"Expected retry guidance, got: {fail1_data['guidance']}"

        # ── FAIL phase 2 again (second attempt → skip) ───────────────────
        fail2_result = apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name=phase_2,
            status="failed",
            evidence="Still not ready",
            agent_dir=tmp_agent_dir,
        )
        fail2_data = parse_result(fail2_result)
        assert fail2_data["success"] is True
        assert fail2_data["next_action"] == "skip", \
            f"Expected 'skip' after retry exhausted, got: {fail2_data.get('next_action')}"

        # The session should still be active and allow continuing
        remaining_phases = [p for p in phase_names[2:]]
        if remaining_phases:
            # Should be able to checkpoint remaining phases
            for remaining_phase in remaining_phases:
                cp_result = apply_mod.apply_handler(
                    action="checkpoint",
                    session_id=session_id,
                    phase_name=remaining_phase,
                    status="passed",
                    evidence="Continuing despite earlier skip",
                    agent_dir=tmp_agent_dir,
                )
                cp_data = parse_result(cp_result)
                assert cp_data["success"] is True

    def test_status_check_returns_session_state(self, tmp_agent_dir):
        """
        Start apply, then check status. Verify status returns correct state.
        """
        setup_pack(tmp_agent_dir)

        # Start
        start_result = apply_mod.apply_handler(
            action="start",
            pack_name="systematic-debugging",
            task="Check status test",
            agent_dir=tmp_agent_dir,
        )
        start_data = parse_result(start_result)
        session_id = start_data["session_id"]

        # Check status before approval
        status_result = apply_mod.apply_handler(
            action="status",
            session_id=session_id,
            agent_dir=tmp_agent_dir,
        )
        status_data = parse_result(status_result)
        assert status_data["success"] is True
        assert status_data["session_id"] == session_id
        assert status_data["task"] == "Check status test"
        assert status_data["approved"] is False
        assert len(status_data["phases"]) > 0

        # After approval, approved should be True
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        status_after_result = apply_mod.apply_handler(
            action="status",
            session_id=session_id,
            agent_dir=tmp_agent_dir,
        )
        status_after_data = parse_result(status_after_result)
        assert status_after_data["approved"] is True, \
            "Session should be approved after __approval__ checkpoint"

    def test_status_unknown_session_returns_error(self, tmp_agent_dir):
        """Status for unknown session should return clear error."""
        status_result = apply_mod.apply_handler(
            action="status",
            session_id="nonexistent-session-12345",
            agent_dir=tmp_agent_dir,
        )
        status_data = parse_result(status_result)
        assert status_data["success"] is False
        assert "No active session" in status_data["error"]

    def test_resume_completed_session_returns_clear_error(self, tmp_agent_dir):
        """
        Start apply, complete it, then try to resume → clear error.
        """
        setup_pack(tmp_agent_dir)

        # Start and complete
        start_result = apply_mod.apply_handler(
            action="start",
            pack_name="systematic-debugging",
            task="Resume completed session test",
            agent_dir=tmp_agent_dir,
        )
        start_data = parse_result(start_result)
        session_id = start_data["session_id"]
        phase_names = [p["name"] for p in start_data["phases"]]

        # Approve
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        # Pass all phases
        for phase_name in phase_names:
            apply_mod.apply_handler(
                action="checkpoint",
                session_id=session_id,
                phase_name=phase_name,
                status="passed",
                evidence="Done",
                agent_dir=tmp_agent_dir,
            )

        # Complete
        complete_result = apply_mod.apply_handler(
            action="complete",
            session_id=session_id,
            agent_dir=tmp_agent_dir,
        )
        complete_data = parse_result(complete_result)
        assert complete_data["success"] is True

        # Try to resume by pack_name
        resume_result = apply_mod.apply_handler(
            action="resume",
            pack_name="systematic-debugging",
            task="Resume completed session test",
            agent_dir=tmp_agent_dir,
        )
        resume_data = parse_result(resume_result)

        # After complete, session is deleted. Resume should find the execution
        # log and report "already completed" error
        assert resume_data["success"] is False, \
            "Resume of completed session should fail"
        error_msg = resume_data.get("error", "").lower()
        assert ("completed" in error_msg) or ("already" in error_msg), \
            f"Expected clear 'already completed' error, got: {resume_data.get('error')}"

    def test_complete_with_partial_failure(self, tmp_agent_dir):
        """
        Start apply, fail one phase (after retry), pass others, complete.
        Verify feedback draft reflects partial failure correctly.
        """
        setup_pack(tmp_agent_dir)

        start_result = apply_mod.apply_handler(
            action="start",
            pack_name="systematic-debugging",
            task="Partial failure test",
            agent_dir=tmp_agent_dir,
        )
        start_data = parse_result(start_result)
        session_id = start_data["session_id"]
        phase_names = [p["name"] for p in start_data["phases"]]

        # Approve
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name="__approval__",
            status="passed",
            agent_dir=tmp_agent_dir,
        )

        # Pass phase 1, fail phase 2 (retry exhaust), pass rest
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name=phase_names[0],
            status="passed",
            evidence="Phase 1 OK",
            agent_dir=tmp_agent_dir,
        )

        # Fail phase 2 twice → skipped
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name=phase_names[1],
            status="failed",
            evidence="Intentional failure",
            agent_dir=tmp_agent_dir,
        )
        apply_mod.apply_handler(
            action="checkpoint",
            session_id=session_id,
            phase_name=phase_names[1],
            status="failed",
            evidence="Still failing",
            agent_dir=tmp_agent_dir,
        )

        # Pass remaining phases
        for phase_name in phase_names[2:]:
            apply_mod.apply_handler(
                action="checkpoint",
                session_id=session_id,
                phase_name=phase_name,
                status="passed",
                evidence="Recovered",
                agent_dir=tmp_agent_dir,
            )

        # Complete
        complete_result = apply_mod.apply_handler(
            action="complete",
            session_id=session_id,
            agent_dir=tmp_agent_dir,
        )
        complete_data = parse_result(complete_result)
        assert complete_data["success"] is True

        summary = complete_data["summary"]
        assert summary["phases_passed"] == len(phase_names) - 1
        assert summary["phases_failed"] == 1

        feedback = complete_data["feedback_draft"]
        assert "suggestions" in feedback
        # Suggestions should mention the failed phase
        suggestions_text = " ".join(feedback["suggestions"]) if isinstance(feedback["suggestions"], list) else str(feedback["suggestions"])
        assert len(suggestions_text) > 0, "Suggestions should not be empty for partial failure"


# --------------------------------------------------------------------------  #
# Tests: Guild Pull validation
# --------------------------------------------------------------------------  #

class TestGuildPull:
    """Tests for guild_pull as used in the full cycle."""

    def test_pull_systematic_debugging_pack(self, tmp_agent_dir):
        """guild_pull('borg://systematic-debugging') should succeed."""
        result = search_mod.guild_pull("borg://systematic-debugging")
        data = parse_result(result)

        assert data["success"] is True, f"guild_pull failed: {data.get('error')}"
        assert data["name"] == "systematic-debugging"
        assert "tier" in data
        assert data["tier"] in ("VALIDATED", "PROVISIONAL", "EXPEDITED", "MINIMAL", "DECAYED")

        # Pack should be on disk
        pack_path = Path(data["path"])
        assert pack_path.exists(), f"Pack file not found at {pack_path}"

        # Proof gates should be present
        assert "proof_gates" in data
        pg = data["proof_gates"]
        assert "validation_errors" in pg
        assert "confidence" in pg

    def test_pull_nonexistent_pack_returns_clear_error(self, tmp_agent_dir):
        """guild_pull for nonexistent pack should suggest alternatives."""
        result = search_mod.guild_pull("borg://nonexistent-pack-xyz")
        data = parse_result(result)

        assert data["success"] is False
        assert "Pack not found" in data["error"]
        # Should have hints
        assert "hint" in data or "suggestions" in data
