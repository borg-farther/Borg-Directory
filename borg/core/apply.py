"""
Guild Apply Module (T1.9) — Bundled execution engine for Guild v2.

Multi-action handler:
  action="start"      — Load pack, safety-scan, create execution session, return approval summary
  action="checkpoint"  — Log a phase checkpoint result (pass/fail/skip)
  action="complete"    — Finalize execution, write summary, generate feedback draft
  action="resume"      — Resume an interrupted execution from the last completed phase
  action="status"      — Check current session state

Session persistence: {GUILD_DIR}/sessions/{session_id}.json
Execution logs:      {GUILD_DIR}/executions/{session_id}.jsonl

Zero imports from tools.* or guild_mcp.* — uses borg.core.* sibling modules.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from borg.core import safety as _safety_mod
from borg.core import schema as _schema_mod
from borg.core import session as _session_mod
from borg.core.uri import resolve_guild_uri, fetch_with_retry
from borg.core.privacy import privacy_redact
from borg.core.proof_gates import check_confidence_decay

try:
    from borg.db.store import GuildStore
except ImportError:
    GuildStore = None

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (mirror PRD §4.3)
# ---------------------------------------------------------------------------

HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
GUILD_DIR = HERMES_HOME / "guild"
EXECUTIONS_DIR = GUILD_DIR / "executions"

MAX_PHASES = 20
MAX_PACK_SIZE_BYTES = 500 * 1024  # 500 KB
MAX_FIELD_SIZE_BYTES = 10 * 1024  # 10 KB

# In-memory overlay for apply-specific session fields not stored in core session
_active_apply_state: Dict[str, Dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# V1/V2 pack normalization
# ---------------------------------------------------------------------------

def _normalize_phases(pack: dict) -> List[dict]:
    """Normalize V1 (phases[]) or V2 (structure[]) to a phases list.

    V2 packs use ``structure: [{phase_name, description, guidance,
    checkpoint, anti_patterns}]`` instead of V1's
    ``phases: [{name, description, checkpoint, anti_patterns, prompts}]``.

    This function converts V2 ``structure`` entries to the V1 ``phase``
    format so the rest of the apply engine works unchanged.
    """
    # V2: structure[] without phases[]
    if "structure" in pack and "phases" not in pack:
        result: List[dict] = []
        for i, p in enumerate(pack.get("structure", [])):
            if not isinstance(p, dict):
                continue
            # guidance in V2 may be a string or list; normalise to list
            guidance = p.get("guidance", "")
            prompts: List[str]
            if isinstance(guidance, list):
                prompts = guidance
            elif guidance:
                prompts = [guidance]
            else:
                prompts = []

            result.append({
                "name": p.get("phase_name", p.get("name", f"phase_{i}")),
                "description": p.get("description", ""),
                "checkpoint": p.get("checkpoint", ""),
                "anti_patterns": p.get("anti_patterns", []),
                "prompts": prompts,
                "status": "pending",
            })
        return result
    # V1: phases[]
    return pack.get("phases", [])


# ---------------------------------------------------------------------------
# Feedback generation (inline minimal implementation)
# ---------------------------------------------------------------------------

def _generate_feedback(
    pack_id: str,
    pack_version: str,
    execution_log: List[dict],
    task_description: str,
    outcome: str,
) -> dict:
    """Generate a minimal PRD-compliant feedback draft.

    Returns a dict with schema_version, type, before, after, evidence fields.
    """
    phases_passed = sum(1 for r in execution_log if r.get("status") == "passed")
    phases_failed = sum(1 for r in execution_log if r.get("status") == "failed")

    # Build "before" from the task
    before = []
    if task_description:
        before.append(f"Task: {task_description}")

    # Build "after" from outcomes
    after = {}
    if phases_passed > 0:
        after["phases_passed"] = phases_passed
    if phases_failed > 0:
        after["phases_failed"] = phases_failed
    if outcome:
        after["outcome"] = outcome

    # Evidence: aggregate checkpoint results
    evidence_parts = []
    for r in execution_log:
        ev = r.get("evidence", "").strip()
        if ev and ev.lower() not in ("passed", "done", "ok", "success", ""):
            evidence_parts.append(f"{r.get('phase', '?')}: {ev}")
    evidence = "; ".join(evidence_parts) if evidence_parts else ""

    return {
        "schema_version": "1.0",
        "type": "feedback",
        "before": before,
        "after": after,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Action: start
# ---------------------------------------------------------------------------

def action_start(pack_name: str, task: str, *, guild_dir: Optional[Path] = None) -> str:
    """Load a pulled pack, safety-scan it, and create an execution session.

    Returns JSON with session_id and approval_summary.
    Does NOT log execution_started until operator approves via __approval__ checkpoint.
    """
    base = guild_dir if guild_dir is not None else GUILD_DIR

    # Find the pack
    pack_file = base / pack_name / "pack.yaml"
    if not pack_file.exists():
        candidates = list(base.glob("*/pack.yaml"))
        matches = [c for c in candidates if pack_name in c.parent.name]
        if matches:
            pack_file = matches[0]
        else:
            return json.dumps({
                "success": False,
                "error": f"Pack not found: {pack_name}. Pull it first with borg_pull.",
                "available": [c.parent.name for c in candidates],
            })

    try:
        pack_text = pack_file.read_text(encoding="utf-8")
        pack = yaml.safe_load(pack_text)
    except (yaml.YAMLError, OSError) as e:
        return json.dumps({"success": False, "error": f"Failed to load pack: {e}"})

    if not isinstance(pack, dict):
        return json.dumps({"success": False, "error": "Pack is not a valid YAML mapping"})

    # --- CRITICAL: Safety scan at apply time ---
    threats = _safety_mod.scan_pack_safety(pack)
    if threats:
        return json.dumps({
            "success": False,
            "error": "Safety scan failed — pack contains threats.",
            "threats": threats,
        })

    # --- MEDIUM: Schema validation ---
    schema_errors = _schema_mod.validate_pack(pack)
    if schema_errors:
        return json.dumps({
            "success": False,
            "error": "Pack validation failed.",
            "violations": schema_errors,
        })

    # --- MEDIUM: YAML size limits ---
    size_violations = _safety_mod.check_pack_size_limits(pack, pack_file)
    if size_violations:
        return json.dumps({
            "success": False,
            "error": "Pack exceeds size limits.",
            "violations": size_violations,
        })

    # Create session
    pack_id = pack.get("id", pack_name)
    ts = datetime.now(timezone.utc)
    session_id = f"{pack_name}-{ts.strftime('%Y%m%d-%H%M%S')}"

    safe_id = pack_id.replace("://", "-").replace("/", "-")
    log_filename = f"{safe_id}-{ts.strftime('%Y%m%dT%H%M%S')}.jsonl"
    log_path = (base / "executions" / log_filename)

    # Build phase plan (handles both V1 phases[] and V2 structure[])
    phases = _normalize_phases(pack)
    phase_plan = []
    for i, phase in enumerate(phases):
        if not isinstance(phase, dict):
            continue
        phase_plan.append({
            "index": i,
            "name": phase.get("name", f"phase_{i}"),
            "description": phase.get("description", ""),
            "checkpoint": phase.get("checkpoint", ""),
            "anti_patterns": phase.get("anti_patterns", []),
            "prompts": phase.get("prompts", []),
            "status": "pending",
        })

    # Build core session dict (uses field names expected by session.py)
    session: Dict[str, Any] = {
        "session_id": session_id,
        "pack_id": pack_id,
        "pack_version": pack.get("version", "unknown"),
        "pack_name": pack_name,
        "task": task,
        "problem_class": pack.get("problem_class", ""),
        "mental_model": pack.get("mental_model", ""),
        "phases": phase_plan,
        "phase_index": 0,
        "status": "pending",
        "created_at": ts.isoformat(),
        "log_path": log_path,
        "execution_log_path": log_path,
        "events": [],
        "phase_results": [],
        "retries": {},
        "approved": False,
    }

    # Persist via session.py
    _session_mod.save_session(session, guild_dir=base)
    _session_mod.register_session(session)

    # Track apply-specific state (approved flag)
    _active_apply_state[session_id] = {"approved": False}

    # Do NOT log execution_started yet — wait for approval checkpoint

    # Build approval summary
    provenance = pack.get("provenance", {})
    decay_status = check_confidence_decay(pack)

    approval_summary = {
        "pack_name": pack_name,
        "pack_id": pack_id,
        "problem_class": pack.get("problem_class", ""),
        "phase_count": len(phase_plan),
        "confidence": provenance.get("confidence", "unknown"),
        "evidence": provenance.get("evidence", ""),
        "failure_cases": provenance.get("failure_cases", []),
        "confidence_status": decay_status,
    }
    if decay_status.get("decayed"):
        approval_summary["decay_warning"] = decay_status["warning"]

    return json.dumps({
        "success": True,
        "session_id": session_id,
        "action_needed": "approve",
        "approval_summary": approval_summary,
        "mental_model": pack.get("mental_model", ""),
        "phases": [
            {"name": p["name"], "checkpoint": p["checkpoint"], "status": p["status"]}
            for p in phase_plan
        ],
        "instructions": (
            "Present the approval_summary to the operator. "
            "To approve, call apply_handler(action='checkpoint', session_id=..., "
            "phase_name='__approval__', status='passed'). "
            "After approval, execute each phase in order. After completing each phase, "
            "call apply_handler(action='checkpoint') with the phase name and result. "
            "Use anti_patterns as guidance on what to avoid. "
            "If a checkpoint fails, retry the phase once. "
            "After all phases, call apply_handler(action='complete')."
        ),
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Action: checkpoint
# ---------------------------------------------------------------------------

def action_checkpoint(
    session_id: str,
    phase_name: str,
    status: str,
    evidence: str = "",
    attempt: int = 1,
    *,
    guild_dir: Optional[Path] = None,
) -> str:
    """Log a phase checkpoint result.

    status: 'passed' or 'failed'
    Special phase_name '__approval__' with status='passed' approves execution.
    Returns guidance on next step (retry, continue, or skip).
    """
    base = guild_dir if guild_dir is not None else GUILD_DIR

    # Try in-memory first, then load from disk via session.py
    session = _session_mod.get_active_session(session_id)
    if not session:
        session = _session_mod.load_session(session_id, guild_dir=base)
        if not session:
            return json.dumps({
                "success": False,
                "error": f"No active session: {session_id}",
            })

    # Get apply-specific state
    apply_state = _active_apply_state.get(session_id, {})
    approved = apply_state.get("approved", session.get("approved", False))

    # --- MEDIUM: Handle approval gate ---
    if phase_name == "__approval__":
        if status == "passed":
            approved = True
            _active_apply_state[session_id] = {"approved": True}
            session["approved"] = True

            _session_mod.log_event(session_id, {
                "event": "execution_started",
                "artifact": session["pack_id"],
                "task": session["task"],
                "phase_count": len(session["phases"]),
            }, guild_dir=base)
            _session_mod.save_session(session, guild_dir=base)

            return json.dumps({
                "success": True,
                "phase": "__approval__",
                "status": "passed",
                "next_action": "continue",
                "guidance": "Execution approved. Proceed with phase execution.",
                "next_phase": session["phases"][0] if session["phases"] else None,
                "phases_completed": 0,
                "phases_total": len(session["phases"]),
            }, ensure_ascii=False)
        else:
            # Rejected — clean up
            _active_apply_state.pop(session_id, None)
            _session_mod.delete_session(session_id, guild_dir=base)
            return json.dumps({
                "success": True,
                "phase": "__approval__",
                "status": "rejected",
                "next_action": "stop",
                "guidance": "Execution rejected by operator. Session discarded.",
                "phases_completed": 0,
                "phases_total": 0,
            }, ensure_ascii=False)

    # Block phase checkpoints until approved
    if not approved:
        return json.dumps({
            "success": False,
            "error": (
                "Execution not yet approved. Call checkpoint with "
                "phase_name='__approval__' and status='passed' first."
            ),
        })

    # Find the phase
    phase_match = None
    for p in session["phases"]:
        if p["name"] == phase_name:
            phase_match = p
            break

    if not phase_match:
        return json.dumps({
            "success": False,
            "error": f"Phase '{phase_name}' not found in session",
            "available_phases": [p["name"] for p in session["phases"]],
        })

    # Privacy scan on evidence
    sanitized_evidence = privacy_redact(evidence)

    # Track retries
    retry_key = phase_name
    current_retries = session["retries"].get(retry_key, 0)

    # Determine action based on status
    if status == "passed":
        phase_match["status"] = "passed"
        event_type = "checkpoint_passed"
        next_action = "continue"
        guidance = "Phase passed. Proceed to the next phase."
    elif status == "failed":
        if current_retries < 1:
            session["retries"][retry_key] = current_retries + 1
            event_type = "checkpoint_failed"
            next_action = "retry"
            guidance = (
                f"Phase '{phase_name}' checkpoint failed. "
                f"Retry this phase once more (attempt 2). "
                f"Checkpoint assertion: {phase_match.get('checkpoint', '')}"
            )
        else:
            phase_match["status"] = "failed"
            event_type = "checkpoint_failed"
            next_action = "skip"
            guidance = (
                f"Phase '{phase_name}' failed after retry. "
                f"Skipping this phase and continuing to the next one."
            )
    else:
        return json.dumps({
            "success": False,
            "error": f"Invalid status: {status}. Must be 'passed' or 'failed'.",
        })

    # Log the event
    _session_mod.log_event(session_id, {
        "event": event_type,
        "phase": phase_name,
        "evidence": sanitized_evidence,
        "attempt": current_retries + 1,
        "reason": sanitized_evidence if status == "failed" else "",
    }, guild_dir=base)

    # Record phase result
    if next_action != "retry":
        session["phase_results"].append({
            "phase": phase_name,
            "status": phase_match["status"],
            "evidence": sanitized_evidence,
            "attempts": current_retries + 1,
            "duration_s": 0,
            "checkpoint_result": sanitized_evidence,
        })

    # Persist updated session
    _session_mod.save_session(session, guild_dir=base)

    # Find next phase
    next_phase = None
    if next_action in ("continue", "skip"):
        current_idx = phase_match["index"]
        for p in session["phases"]:
            if p["index"] > current_idx and p["status"] == "pending":
                next_phase = p
                break

    return json.dumps({
        "success": True,
        "phase": phase_name,
        "status": status,
        "next_action": next_action,
        "guidance": guidance,
        "next_phase": next_phase,
        "phases_completed": sum(
            1 for p in session["phases"] if p["status"] != "pending"
        ),
        "phases_total": len(session["phases"]),
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Action: complete
# ---------------------------------------------------------------------------

def action_complete(session_id: str, outcome: str = "", *, guild_dir: Optional[Path] = None) -> str:
    """Finalize execution session. Write summary and generate feedback draft.

    Returns the execution summary + auto-generated PRD-compliant feedback draft.
    """
    base = guild_dir if guild_dir is not None else GUILD_DIR

    session = _session_mod.get_active_session(session_id)
    if not session:
        session = _session_mod.load_session(session_id, guild_dir=base)
        if not session:
            return json.dumps({
                "success": False,
                "error": f"No active session: {session_id}",
            })

    # Count results
    phases_passed = sum(1 for r in session["phase_results"] if r["status"] == "passed")
    phases_failed = sum(1 for r in session["phase_results"] if r["status"] == "failed")
    phases_total = len(session["phases"])

    # Calculate duration
    started_at = session.get("started_at") or session.get("created_at", "")
    if started_at:
        try:
            started = datetime.fromisoformat(started_at)
        except ValueError:
            started = datetime.now(timezone.utc)
    else:
        started = datetime.now(timezone.utc)
    ended = datetime.now(timezone.utc)
    duration_seconds = int((ended - started).total_seconds())

    # Log completion event
    _session_mod.log_event(session_id, {
        "event": "execution_completed",
        "phases_passed": phases_passed,
        "phases_failed": phases_failed,
        "phases_total": phases_total,
        "duration_seconds": duration_seconds,
        "outcome": outcome,
    }, guild_dir=base)

    # Compute log hash
    log_path = session.get("execution_log_path") or session.get("log_path", Path(base) / "executions" / f"{session_id}.jsonl")
    log_hash = _session_mod.compute_log_hash(Path(log_path))

    # Generate feedback
    raw_feedback = _generate_feedback(
        pack_id=session["pack_id"],
        pack_version=session["pack_version"],
        execution_log=session["phase_results"],
        task_description=session["task"],
        outcome=outcome or f"{phases_passed}/{phases_total} phases passed",
    )

    # Build evidence summary
    passed_phases = [r for r in session["phase_results"] if r["status"] == "passed"]
    failed_phases = [r for r in session["phase_results"] if r["status"] == "failed"]
    problem_class = session.get("problem_class", "workflow")

    # Synthesize why_it_worked
    why_it_worked = ""
    if phases_passed > 0:
        evidence_parts = []
        for r in passed_phases:
            ev = r.get("evidence", "").strip()
            if ev and ev.lower() not in ("passed", "done", "ok", "success", ""):
                evidence_parts.append(ev)

        if evidence_parts:
            if len(evidence_parts) == 1:
                why_it_worked = (
                    f"The pack guided the task effectively. "
                    f"Key evidence: {evidence_parts[0]}"
                )
            else:
                intro = (
                    f"The pack's {len(passed_phases)}-phase structure "
                    f"provided clear progression. "
                )
                narrative_mid = " Building on that, ".join(evidence_parts[:4])
                why_it_worked = f"{intro}{narrative_mid}."
        else:
            why_it_worked = (
                f"All {phases_passed} phases passed their checkpoints, "
                f"indicating the pack's phase structure matched the task requirements."
            )

    if phases_failed > 0 and why_it_worked:
        why_it_worked += (
            f" However, {phases_failed} phase(s) failed, "
            f"suggesting some steps need refinement."
        )

    # Determine what_changed
    if outcome and outcome != f"{phases_passed}/{phases_total} phases passed":
        what_changed = outcome
    elif phases_passed == phases_total:
        what_changed = (
            f"Task completed successfully through all {phases_total} phases. "
            f"The {problem_class} workflow was fully executed as structured."
        )
    elif phases_passed > 0:
        passed_names = [r["phase"] for r in passed_phases]
        failed_names = [r["phase"] for r in failed_phases]
        what_changed = (
            f"Partially completed: {phases_passed}/{phases_total} phases succeeded "
            f"({', '.join(passed_names)}). "
            f"Failed phases: {', '.join(failed_names)}."
        )
    else:
        what_changed = (
            f"Execution did not produce the intended result. "
            f"All {phases_total} phases failed their checkpoints."
        )

    # Build where_to_reuse
    task_desc = session["task"]
    where_parts = []
    if problem_class and problem_class != "workflow":
        where_parts.append(f"Best suited for '{problem_class}' tasks")
    else:
        where_parts.append("Applicable to structured workflow tasks")

    if phases_passed == phases_total:
        where_parts.append(
            f"Validated end-to-end on: \"{task_desc}\". "
            f"Reuse confidently on similar-scope tasks"
        )
    elif phases_passed > 0:
        passed_names = [r["phase"] for r in passed_phases]
        where_parts.append(
            f"The phases [{', '.join(passed_names)}] worked well and "
            f"can be reused. Tested on: \"{task_desc}\""
        )
    else:
        where_parts.append(
            f"Needs iteration before reuse. "
            f"Tested (unsuccessfully) on: \"{task_desc}\""
        )
    where_to_reuse = ". ".join(where_parts)

    # Generate suggestions
    suggestions = []
    for r in failed_phases:
        ev = r.get("evidence", "").strip()
        phase_name = r["phase"]
        if r.get("attempts", 1) > 1:
            suggestions.append(
                f"Phase '{phase_name}' failed after retry — "
                f"consider breaking it into smaller steps or clarifying its checkpoint"
            )
        elif ev:
            suggestions.append(
                f"Phase '{phase_name}' failed ({ev}) — "
                f"review whether the checkpoint is realistic for this task type"
            )
        else:
            suggestions.append(
                f"Phase '{phase_name}' failed with no evidence — "
                f"add clearer checkpoint criteria so failures are diagnosable"
            )

    # Check for vague evidence on passed phases
    for r in passed_phases:
        ev = r.get("evidence", "").strip()
        if not ev or ev.lower() in ("passed", "done", "ok", "success"):
            suggestions.append(
                f"Phase '{r['phase']}' passed but with no meaningful evidence — "
                f"consider adding more specific checkpoint assertions"
            )

    # Check for phases without anti_patterns
    phases_without_anti = [
        p["name"] for p in session["phases"]
        if not p.get("anti_patterns")
    ]
    if phases_without_anti:
        suggestions.append(
            f"Phases [{', '.join(phases_without_anti[:3])}] have no anti_patterns — "
            f"adding common mistakes to watch for would improve guidance"
        )

    failure_cases = []
    for r in failed_phases:
        failure_cases.append(f"{r['phase']}: {r.get('evidence', 'failed')}")

    # Build final feedback draft
    feedback_draft = {
        "schema_version": "1.0",
        "type": "feedback",
        "id": f"{session['pack_id']}/feedback/{ended.strftime('%Y%m%dT%H%M%S')}",
        "parent_artifact": session["pack_id"],
        "version": session["pack_version"],
        "before": raw_feedback.get("before", []),
        "after": raw_feedback.get("after", {}),
        "what_changed": what_changed,
        "why_it_worked": why_it_worked,
        "where_to_reuse": where_to_reuse,
        "suggestions": suggestions,
        "evidence": raw_feedback.get("evidence", ""),
        "provenance": {
            "confidence": "guessed",
            "author_agent": "guild-v2",
            "generated": datetime.now(timezone.utc).isoformat(),
            "failure_cases": failure_cases,
        },
        "execution_log_hash": log_hash,
    }

    # Write feedback draft to disk
    feedback_path = base / "feedback" / f"{session['pack_name']}-{ended.strftime('%Y%m%d')}.yaml"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(
        yaml.dump(feedback_draft, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    # Build execution summary
    summary = {
        "session_id": session_id,
        "pack_id": session["pack_id"],
        "task": session["task"],
        "phases_passed": phases_passed,
        "phases_failed": phases_failed,
        "phases_total": phases_total,
        "duration_seconds": duration_seconds,
        "execution_log": str(log_path),
        "execution_log_hash": log_hash,
        "phase_results": session["phase_results"],
    }

    # Log execution to reputation store (optional — store may not exist)
    if GuildStore is not None:
        try:
            _store = GuildStore()
            _store.record_execution(
                execution_id=f"{session['pack_id']}-{session_id}",
                session_id=session_id,
                pack_id=session["pack_id"],
                agent_id="guild-v2",  # agent_id not available in session context
                task=session.get("task"),
                status="completed",
                phases_completed=phases_passed,
                phases_failed=phases_failed,
                started_at=session.get("created_at"),
                completed_at=ended.isoformat(),
                log_hash=log_hash,
            )
            _store.close()
        except Exception:
            pass  # Store is optional — never break core flow

    # Clean up
    _active_apply_state.pop(session_id, None)
    _session_mod.delete_session(session_id, guild_dir=base)

    return json.dumps({
        "success": True,
        "summary": summary,
        "feedback_draft": feedback_draft,
        "feedback_path": str(feedback_path),
        "instructions": (
            "Review the auto-generated feedback draft above. "
            "You can approve it as-is, edit it, or discard it. "
            "To publish, use the publish module when ready."
        ),
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Action: resume
# ---------------------------------------------------------------------------

def action_resume(pack_name: str, task: str = "", *, guild_dir: Optional[Path] = None) -> str:
    """Resume an interrupted execution from the last completed phase.

    Reads the most recent JSONL log for the pack, rebuilds session state,
    and returns remaining phases.
    """
    base = guild_dir if guild_dir is not None else GUILD_DIR

    # Check for persisted sessions matching the pack name
    sessions_dir = base / "sessions"
    if sessions_dir.exists():
        for sf in sorted(sessions_dir.glob(f"{pack_name}-*.json"), reverse=True):
            try:
                meta = json.loads(sf.read_text(encoding="utf-8"))
                sid = meta.get("session_id", "")
                if sid and sid not in _session_mod._active_sessions:
                    restored = _session_mod.load_session(sid, guild_dir=base)
                    if restored:
                        remaining = [p for p in restored["phases"] if p["status"] == "pending"]
                        completed_count = sum(1 for p in restored["phases"] if p["status"] != "pending")
                        if remaining:
                            _active_apply_state[sid] = {"approved": restored.get("approved", True)}
                            return json.dumps({
                                "success": True,
                                "session_id": sid,
                                "resumed_from": "persisted_session",
                                "phases_completed": completed_count,
                                "phases_remaining": len(remaining),
                                "remaining_phases": remaining,
                                "mental_model": restored.get("mental_model", ""),
                                "instructions": (
                                    "Execution resumed from persisted session. "
                                    "Continue with the remaining phases listed above. "
                                    "After completing each phase, call apply_handler(action='checkpoint') "
                                    "with the phase name and result. "
                                    "After all phases, call apply_handler(action='complete')."
                                ),
                            }, ensure_ascii=False)
            except (OSError, json.JSONDecodeError):
                continue

    # Find the most recent execution log for this pack
    pack_file = base / pack_name / "pack.yaml"
    if not pack_file.exists():
        candidates = list(base.glob("*/pack.yaml"))
        matches = [c for c in candidates if pack_name in c.parent.name]
        if matches:
            pack_file = matches[0]
        else:
            return json.dumps({
                "success": False,
                "error": f"Pack not found: {pack_name}. Pull it first with borg_pull.",
            })

    try:
        pack_text = pack_file.read_text(encoding="utf-8")
        pack = yaml.safe_load(pack_text)
    except (yaml.YAMLError, OSError) as e:
        return json.dumps({"success": False, "error": f"Failed to load pack: {e}"})

    pack_id = pack.get("id", pack_name)
    safe_id = pack_id.replace("://", "-").replace("/", "-")

    # Find the most recent log file for this pack
    exec_dir = base / "executions"
    log_files = sorted(exec_dir.glob(f"{safe_id}-*.jsonl"), reverse=True)
    if not log_files:
        return json.dumps({
            "success": False,
            "error": f"No execution logs found for pack '{pack_name}'. Use action='start' instead.",
        })

    log_path = log_files[0]

    # Read events from the log
    events = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except (OSError, json.JSONDecodeError) as e:
        return json.dumps({"success": False, "error": f"Failed to read execution log: {e}"})

    # Check if already completed
    for ev in events:
        if ev.get("event") == "execution_completed":
            return json.dumps({
                "success": False,
                "error": "Execution already completed. Use action='start' for a new execution.",
            })

    # Rebuild completed phases from events
    completed_phases: Dict[str, str] = {}
    phase_results = []
    original_task = task

    for ev in events:
        if ev.get("event") == "execution_started":
            original_task = original_task or ev.get("task", "")
        elif ev.get("event") == "checkpoint_passed":
            phase_nm = ev.get("phase", "")
            completed_phases[phase_nm] = "passed"
            phase_results.append({
                "phase": phase_nm,
                "status": "passed",
                "evidence": ev.get("evidence", ""),
                "attempts": ev.get("attempt", 1),
                "duration_s": 0,
                "checkpoint_result": ev.get("evidence", ""),
            })
        elif ev.get("event") == "checkpoint_failed":
            phase_nm = ev.get("phase", "")
            attempt = ev.get("attempt", 1)
            if attempt >= 2:
                completed_phases[phase_nm] = "failed"
                phase_results.append({
                    "phase": phase_nm,
                    "status": "failed",
                    "evidence": ev.get("evidence", ""),
                    "attempts": attempt,
                    "duration_s": 0,
                    "checkpoint_result": ev.get("evidence", ""),
                })

    # Build phase plan from pack (handles both V1 phases[] and V2 structure[])
    phases = _normalize_phases(pack)
    phase_plan = []
    for i, phase in enumerate(phases):
        if not isinstance(phase, dict):
            continue
        name = phase.get("name", f"phase_{i}")
        ph_status = completed_phases.get(name, "pending")
        phase_plan.append({
            "index": i,
            "name": name,
            "description": phase.get("description", ""),
            "checkpoint": phase.get("checkpoint", ""),
            "anti_patterns": phase.get("anti_patterns", []),
            "prompts": phase.get("prompts", []),
            "status": ph_status,
        })

    remaining_phases = [p for p in phase_plan if p["status"] == "pending"]

    if not remaining_phases:
        return json.dumps({
            "success": False,
            "error": "All phases already completed. Use action='complete' to finalize.",
        })

    # Create a new session for the resumed execution
    ts = datetime.now(timezone.utc)
    session_id = f"{pack_name}-{ts.strftime('%Y%m%d-%H%M%S')}-resumed"

    session: Dict[str, Any] = {
        "session_id": session_id,
        "pack_id": pack_id,
        "pack_version": pack.get("version", "unknown"),
        "pack_name": pack_name,
        "task": original_task,
        "problem_class": pack.get("problem_class", ""),
        "mental_model": pack.get("mental_model", ""),
        "phases": phase_plan,
        "phase_index": len(completed_phases),
        "status": "in_progress",
        "created_at": ts.isoformat(),
        "log_path": log_path,
        "execution_log_path": log_path,
        "events": events,
        "phase_results": phase_results,
        "retries": {},
        "approved": True,
    }

    _session_mod.save_session(session, guild_dir=base)
    _session_mod.register_session(session)
    _active_apply_state[session_id] = {"approved": True}

    return json.dumps({
        "success": True,
        "session_id": session_id,
        "resumed_from_log": str(log_path),
        "phases_completed": len(completed_phases),
        "phases_remaining": len(remaining_phases),
        "remaining_phases": remaining_phases,
        "mental_model": pack.get("mental_model", ""),
        "instructions": (
            "Execution resumed. Continue with the remaining phases listed above. "
            "After completing each phase, call apply_handler(action='checkpoint') "
            "with the phase name and result. "
            "After all phases, call apply_handler(action='complete')."
        ),
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Action: status
# ---------------------------------------------------------------------------

def action_status(session_id: str, *, guild_dir: Optional[Path] = None) -> str:
    """Check current execution session state."""
    base = guild_dir if guild_dir is not None else GUILD_DIR

    session = _session_mod.get_active_session(session_id)
    if not session:
        session = _session_mod.load_session(session_id, guild_dir=base)
        if not session:
            return json.dumps({
                "success": False,
                "error": f"No active session: {session_id}",
            })

    apply_state = _active_apply_state.get(session_id, {})
    approved = apply_state.get("approved", session.get("approved", False))

    return json.dumps({
        "success": True,
        "session_id": session_id,
        "pack_id": session["pack_id"],
        "task": session["task"],
        "approved": approved,
        "current_phase": session.get("phase_index", 0),
        "phases": session["phases"],
        "phase_results": session["phase_results"],
        "started_at": session.get("started_at") or session.get("created_at", ""),
    }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def apply_handler(
    action: str,
    pack_name: str = "",
    task: str = "",
    session_id: str = "",
    phase_name: str = "",
    status: str = "",
    evidence: str = "",
    outcome: str = "",
    *,
    guild_dir: Optional[Path] = None,
) -> str:
    """Main entry point for guild apply.

    Dispatches to action_start, action_checkpoint, action_complete,
    action_resume, or action_status based on the ``action`` argument.
    """
    try:
        if action == "start":
            if not pack_name:
                return json.dumps({"success": False, "error": "pack_name is required for action='start'"})
            if not task:
                return json.dumps({"success": False, "error": "task is required for action='start'"})
            return action_start(pack_name, task, guild_dir=guild_dir)

        elif action == "checkpoint":
            if not session_id:
                return json.dumps({"success": False, "error": "session_id is required for action='checkpoint'"})
            if not phase_name:
                return json.dumps({"success": False, "error": "phase_name is required for action='checkpoint'"})
            if not status:
                return json.dumps({"success": False, "error": "status is required for action='checkpoint'"})
            return action_checkpoint(session_id, phase_name, status, evidence, guild_dir=guild_dir)

        elif action == "complete":
            if not session_id:
                return json.dumps({"success": False, "error": "session_id is required for action='complete'"})
            return action_complete(session_id, outcome, guild_dir=guild_dir)

        elif action == "resume":
            if not pack_name:
                return json.dumps({"success": False, "error": "pack_name is required for action='resume'"})
            return action_resume(pack_name, task, guild_dir=guild_dir)

        elif action == "status":
            if not session_id:
                return json.dumps({"success": False, "error": "session_id is required for action='status'"})
            return action_status(session_id, guild_dir=guild_dir)

        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown action: {action}. Must be 'start', 'checkpoint', 'complete', 'resume', or 'status'.",
            })

    except Exception as e:
        logger.exception("apply_handler error")
        return json.dumps({"success": False, "error": str(e)})
