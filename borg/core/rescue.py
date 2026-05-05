"""Day-one rescue engine for agents and humans.

This module is intentionally small and dependency-light.  It wraps the existing
seed-pack classifier/guidance path into a product-shaped response that answers
three first-user questions immediately:

1. what should the agent do next?
2. what dead-end should it avoid?
3. how does the human see Borg's value?

The explicit CLI (`borg rescue`) and MCP tool (`borg_rescue`) both use this
same engine so manual and automated paths cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from borg.core.pack_taxonomy import (
    classify_error,
    debug_error,
    load_pack_by_problem_class,
)


@dataclass(frozen=True)
class RescueResult:
    """Machine-readable rescue contract used by CLI, MCP, and agents."""

    success: bool
    status: str
    problem_class: str
    confidence: str
    action: List[str]
    stop: List[str]
    verify: List[str]
    next_command: str
    agent_instruction: str
    human_receipt: str
    guidance: str
    automation_policy: Dict[str, Any]
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_actions(pack: Dict[str, Any], limit: int = 3) -> List[str]:
    """Extract the highest-signal next actions from a seed pack."""
    actions: List[str] = []
    for step in pack.get("resolution_sequence", []) or []:
        if isinstance(step, dict):
            action = _as_text(step.get("action"))
            cmd = _as_text(step.get("command"))
            if action and cmd:
                actions.append(f"{action} — run/check: {cmd}")
            elif action:
                actions.append(action)
            elif cmd:
                actions.append(f"run/check: {cmd}")
        elif isinstance(step, str):
            actions.append(step.strip())
        if len(actions) >= limit:
            break
    if actions:
        return actions

    # Fallback to investigation trail when a pack has diagnosis before repair.
    for step in pack.get("investigation_trail", []) or []:
        if isinstance(step, dict):
            what = _as_text(step.get("what"))
            where = _as_text(step.get("file"))
            if what and where:
                actions.append(f"inspect {where}: {what}")
            elif what:
                actions.append(what)
        if len(actions) >= limit:
            break
    return actions or ["capture the full failing command, stack trace, and environment before changing code"]


def _extract_stops(pack: Dict[str, Any], limit: int = 3) -> List[str]:
    """Extract dead-end warnings from anti-patterns."""
    stops: List[str] = []
    for item in pack.get("anti_patterns", []) or []:
        if isinstance(item, dict):
            action = _as_text(item.get("action"))
            why = _as_text(item.get("why_fails"))
            if action and why:
                stops.append(f"{action} — fails because {why}")
            elif action:
                stops.append(action)
        elif isinstance(item, str):
            stops.append(item.strip())
        if len(stops) >= limit:
            break
    return stops or ["do not make broad rewrites before reproducing and isolating the failing path"]


def _extract_verify(pack: Dict[str, Any], limit: int = 3) -> List[str]:
    """Extract proof steps from pack checkpoints / verification fields."""
    verify: List[str] = []
    for key in ("verification", "checkpoints", "success_criteria"):
        raw = pack.get(key)
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    text = _as_text(item.get("checkpoint") or item.get("description") or item.get("assertion"))
                else:
                    text = _as_text(item)
                if text:
                    verify.append(text)
                if len(verify) >= limit:
                    return verify
        elif isinstance(raw, str) and raw.strip():
            verify.append(raw.strip())
    return verify or ["rerun the exact failing command", "add or run the smallest regression test", "only then continue broader changes"]


def _evidence(pack: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not pack:
        return {"success_count": 0, "failure_count": 0, "uses": 0, "source": "none"}
    evidence = pack.get("evidence", {}) if isinstance(pack, dict) else {}
    if not isinstance(evidence, dict):
        evidence = {}
    return {
        "success_count": int(evidence.get("success_count", 0) or 0),
        "failure_count": int(evidence.get("failure_count", 0) or 0),
        "uses": int(evidence.get("uses", 0) or 0),
        "success_rate": evidence.get("success_rate", 0),
        "source": "seed_pack",
    }


def _confidence_from_evidence(pack: Optional[Dict[str, Any]]) -> str:
    if not pack:
        return "unknown"
    provenance = pack.get("provenance", {}) if isinstance(pack, dict) else {}
    if isinstance(provenance, dict) and provenance.get("confidence"):
        return str(provenance.get("confidence"))
    ev = _evidence(pack)
    successes = ev.get("success_count", 0)
    failures = ev.get("failure_count", 0)
    total = successes + failures
    if total >= 10 and successes / max(total, 1) >= 0.7:
        return "tested"
    if total > 0:
        return "observed"
    return "inferred"


def rescue(task_or_error: str, *, source: str = "cli", show_guidance: bool = True) -> RescueResult:
    """Return a complete first-user rescue packet.

    Args:
        task_or_error: error, failing command, agent transcript, or task text.
        source: provenance tag (`cli`, `mcp`, `agent-hook`, etc.).
        show_guidance: include the full legacy guidance block for humans.

    The result is safe for automation: `success=False` means Borg did not find
    a confident match and the agent should not pretend Borg helped.
    """
    text = _as_text(task_or_error)
    automation_policy = {
        "default": "automatic_for_agents",
        "call_when": [
            "technical task starts",
            "tool/command error appears",
            "same failure repeats",
            "agent says it is stuck or loops",
        ],
        "do_not_call_when": [
            "creative writing only",
            "pure preference question",
            "no technical action needed",
        ],
        "fail_closed": True,
        "human_visibility_required": True,
        "source": source,
    }

    if not text:
        return RescueResult(
            success=False,
            status="empty_input",
            problem_class="unknown",
            confidence="unknown",
            action=["paste the exact error, failing command, or agent transcript"],
            stop=["do not guess from an empty prompt"],
            verify=["rerun borg rescue with real failure text"],
            next_command="borg rescue '<paste exact failure>'",
            agent_instruction="NO_MATCH: ask for the exact error or failing command before changing code.",
            human_receipt="Borg did not run because no failure/task text was provided.",
            guidance="",
            automation_policy=automation_policy,
            evidence={"success_count": 0, "failure_count": 0, "uses": 0, "source": "none"},
        )

    problem_class = classify_error(text) or "unknown"
    pack = load_pack_by_problem_class(problem_class) if problem_class != "unknown" else None

    if not pack:
        guidance = debug_error(text, show_evidence=show_guidance) if show_guidance else ""
        return RescueResult(
            success=False,
            status="no_confident_match",
            problem_class="unknown",
            confidence="unknown",
            action=[
                "capture more context: exact command, full traceback/log, OS/runtime, and last changed file",
                "use normal debugging; do not attribute the next fix to Borg unless a match appears",
            ],
            stop=["do not force a Python/Django pack onto an unknown or non-Python error"],
            verify=["rerun borg rescue after adding the full failure text"],
            next_command="borg rescue '<full traceback or failing command output>'",
            agent_instruction=(
                "NO_MATCH: disclose that Borg checked and found no confident match. "
                "Do not blend weak retrieval into the answer. Ask for more evidence or proceed with ordinary debugging."
            ),
            human_receipt="Borg checked the cache but found no confident rescue path for this input.",
            guidance=guidance,
            automation_policy=automation_policy,
            evidence=_evidence(None),
        )

    actions = _extract_actions(pack)
    stops = _extract_stops(pack)
    verify = _extract_verify(pack)
    confidence = _confidence_from_evidence(pack)
    ev = _evidence(pack)
    guidance = debug_error(text, show_evidence=show_guidance) if show_guidance else ""

    action_line = actions[0]
    stop_line = stops[0]
    verify_line = verify[0]
    next_command = "borg feedback-v3 --pack {} --success yes".format(problem_class)

    return RescueResult(
        success=True,
        status="matched",
        problem_class=problem_class,
        confidence=confidence,
        action=actions,
        stop=stops,
        verify=verify,
        next_command=next_command,
        agent_instruction=(
            f"ACTION: {action_line}\n"
            f"STOP: avoid {stop_line}\n"
            f"VERIFY: {verify_line}\n"
            "SHOW HUMAN: say Borg found this rescue path and whether it worked."
        ),
        human_receipt=(
            f"Borg matched `{problem_class}` ({confidence}). "
            f"It gave the agent a next move, a dead-end to avoid, and a verification step."
        ),
        guidance=guidance,
        automation_policy=automation_policy,
        evidence=ev,
    )


def render_rescue_text(result: RescueResult) -> str:
    """Render a RescueResult into concise CLI text."""
    lines: List[str] = []
    lines.append("BORG RESCUE")
    lines.append("=" * 60)
    lines.append(f"status: {result.status}")
    lines.append(f"match: {result.problem_class} [{result.confidence}]")
    lines.append("")
    lines.append("ACTION")
    for item in result.action:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("STOP")
    for item in result.stop:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("VERIFY")
    for item in result.verify:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("AGENT INSTRUCTION")
    lines.append(result.agent_instruction)
    lines.append("")
    lines.append("HUMAN RECEIPT")
    lines.append(result.human_receipt)
    if result.guidance:
        lines.append("")
        lines.append("FULL GUIDANCE")
        lines.append(result.guidance)
    return "\n".join(lines)
