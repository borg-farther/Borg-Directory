"""
Borg Aggregator — self-improving pack intelligence.

Collects execution logs and feedback, computes metrics, suggests improvements,
and promotes confidence tiers.

Stdlib + json only. No ML, no embeddings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------
# Confidence tier promotion thresholds
# -----------------------------------------------------------------------

PROMOTION_MIN_EXECUTIONS = 10
PROMOTION_MIN_SUCCESS_RATE = 0.70

# Tier order (lowest → highest)
CONFIDENCE_TIER_ORDER = ["guessed", "inferred", "tested", "validated"]


# -----------------------------------------------------------------------
# PackAggregator
# -----------------------------------------------------------------------

class PackAggregator:
    """Aggregate execution data for a pack and generate improvements."""

    def __init__(self, pack_id: str) -> None:
        self.pack_id = pack_id
        self._executions: List[Dict[str, Any]] = []   # ingested execution dicts
        self._feedbacks: List[Dict[str, Any]] = []    # ingested feedback dicts

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_execution(self, log_path: Path) -> Dict[str, Any]:
        """Parse one JSONL execution log and store it.

        Expected JSONL event types (from session.log_event):
            execution_started, checkpoint_pass, checkpoint_fail,
            execution_completed.

        Returns a summary dict with keys:
            session_id, success, phases (list of phase results),
            total_duration_s, error (or "").
        """
        events = _read_jsonl(log_path)

        # Extract session_id from first event or filename
        session_id = ""
        if events:
            session_id = str(events[0].get("session_id", log_path.stem))

        # Determine overall success from execution_completed event
        success = False
        error = ""
        for ev in events:
            if ev.get("type") == "execution_completed":
                success = ev.get("status") == "completed"
                error = ev.get("error", "")
                break

        # Build per-phase results from checkpoint events
        phases: List[Dict[str, Any]] = []
        phase_results: Dict[str, Dict[str, Any]] = {}
        total_duration_s = 0.0

        for ev in events:
            ev_type = ev.get("type", "")
            if ev_type in ("checkpoint_pass", "checkpoint_fail"):
                phase_name = ev.get("phase", ev.get("checkpoint", "unknown"))
                status = "passed" if ev_type == "checkpoint_pass" else "failed"
                phase_results[phase_name] = {
                    "phase": phase_name,
                    "status": status,
                    "checkpoint_result": ev.get("checkpoint_result", ""),
                    "error": ev.get("error", ""),
                    "duration_s": ev.get("duration_s", 0.0),
                }
            elif ev_type == "execution_started":
                total_duration_s += ev.get("duration_s", 0.0)

        phases = list(phase_results.values())

        # Detect overall success: execution_completed status == completed
        # OR all checkpoints passed (partial fallback)
        if not any(ev.get("type") == "execution_completed" for ev in events):
            success = all(p["status"] == "passed" for p in phases)

        summary = {
            "session_id": session_id,
            "success": success,
            "phases": phases,
            "total_duration_s": total_duration_s,
            "error": error,
        }
        self._executions.append(summary)
        return summary

    def ingest_feedback(self, feedback: Dict[str, Any]) -> None:
        """Store one feedback artifact dict (from search.generate_feedback)."""
        if not isinstance(feedback, dict):
            return
        if feedback.get("type") != "feedback":
            return
        self._feedbacks.append(feedback)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def compute_metrics(self) -> Dict[str, Any]:
        """Compute aggregated metrics across all ingested executions.

        Returns:
            dict with keys:
                pack_id, total_executions, success_count, failure_count,
                success_rate (0.0-1.0), avg_iterations, phase_metrics,
                common_failures (list of "phase_name" strings).
        """
        executions = self._executions
        total = len(executions)

        if total == 0:
            return {
                "pack_id": self.pack_id,
                "total_executions": 0,
                "success_count": 0,
                "failure_count": 0,
                "success_rate": 0.0,
                "avg_iterations": 0.0,
                "phase_metrics": {},
                "common_failures": [],
            }

        success_count = sum(1 for e in executions if e.get("success"))
        failure_count = total - success_count
        success_rate = success_count / total

        # avg_iterations: mean of total_duration_s across executions
        durations = [e.get("total_duration_s", 0.0) for e in executions]
        avg_iterations = sum(durations) / total if total else 0.0

        # Per-phase metrics: count passed/failed per phase name
        phase_pass: Dict[str, int] = {}
        phase_fail: Dict[str, int] = {}
        for e in executions:
            for p in e.get("phases", []):
                name = p.get("phase", "unknown")
                if p.get("status") == "passed":
                    phase_pass[name] = phase_pass.get(name, 0) + 1
                else:
                    phase_fail[name] = phase_fail.get(name, 0) + 1

        phase_metrics: Dict[str, Dict[str, Any]] = {}
        all_phase_names = set(phase_pass) | set(phase_fail)
        for name in all_phase_names:
            p_total = phase_pass.get(name, 0) + phase_fail.get(name, 0)
            p_pass = phase_pass.get(name, 0)
            phase_metrics[name] = {
                "passed": p_pass,
                "failed": phase_fail.get(name, 0),
                "total": p_total,
                "success_rate": p_pass / p_total if p_total else 0.0,
            }

        # Common failures: phases with >1 failure and success_rate below 70%,
        # sorted by fail count descending.  This catches chronic failure patterns
        # even when overall pack success_rate is acceptable.
        common_failures: List[str] = []
        for name, m in phase_metrics.items():
            if m["failed"] >= 2 and m["success_rate"] < 0.7:
                common_failures.append(name)

        common_failures.sort(
            key=lambda n: phase_metrics[n].get("failed", 0), reverse=True
        )

        return {
            "pack_id": self.pack_id,
            "total_executions": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_rate,
            "avg_iterations": avg_iterations,
            "phase_metrics": phase_metrics,
            "common_failures": common_failures,
        }

    # ------------------------------------------------------------------
    # Suggestions
    # ------------------------------------------------------------------

    def suggest_improvements(self) -> List[str]:
        """Return concrete improvement suggestions.

        Each suggestion is a string of the form:
            "add anti-pattern X to phase Y"
        based on failure patterns in executions and feedback.

        Returns empty list if no clear improvement is found.
        """
        metrics = self.compute_metrics()
        suggestions: List[str] = []

        # 1. Suggest adding anti-patterns to commonly-failing phases
        for phase_name in metrics.get("common_failures", []):
            pm = metrics["phase_metrics"].get(phase_name, {})
            fail_count = pm.get("failed", 0)
            if fail_count >= 1:
                # Derive a generic anti-pattern description from failure patterns
                suggestion = (
                    f"add common failure handling to phase {phase_name} "
                    f"({fail_count} failures detected)"
                )
                suggestions.append(suggestion)

        # 2. Consult feedback suggestions for phase-specific improvements
        for fb in self._feedbacks:
            fb_suggestions = fb.get("suggestions", "")
            failure_cases = fb.get("failure_cases", [])
            if fb_suggestions:
                suggestions.append(fb_suggestions)
            for fc in failure_cases:
                # Try to extract phase name from failure case
                # Format: "Phase 'X' failed: Y"
                if "'" in fc:
                    suggestions.append(f"address failure: {fc}")

        # Deduplicate while preserving order
        seen: set = set()
        unique: List[str] = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)

        return unique

    # ------------------------------------------------------------------
    # Confidence promotion
    # ------------------------------------------------------------------

    def should_promote_confidence(self) -> Optional[str]:
        """Check if the pack's confidence tier should be promoted.

        Promotion rules (all must be true):
            - At least PROMOTION_MIN_EXECUTIONS (10) executions ingested
            - success_rate >= PROMOTION_MIN_SUCCESS_RATE (0.70)

        Returns the new confidence tier string, or None if no promotion.
        """
        metrics = self.compute_metrics()
        total = metrics.get("total_executions", 0)
        success_rate = metrics.get("success_rate", 0.0)

        if total < PROMOTION_MIN_EXECUTIONS:
            return None
        if success_rate < PROMOTION_MIN_SUCCESS_RATE:
            return None

        # Current tier is inferred → promote to tested
        return "tested"

    # ------------------------------------------------------------------
    # Pack improvement
    # ------------------------------------------------------------------

    def generate_improved_pack(self, current_pack: Dict[str, Any]) -> Dict[str, Any]:
        """Apply aggregated improvements to the current pack.

        Creates a shallow copy and adds:
            - New anti_patterns entries to phases that commonly fail
            - Updated provenance with promoted confidence if warranted

        Does NOT modify the input dict.

        Returns the updated pack dict.
        """
        import copy

        improved = copy.deepcopy(current_pack)

        suggestions = self.suggest_improvements()
        metrics = self.compute_metrics()

        # Build a map: phase_name -> phase dict
        phase_map: Dict[str, Dict[str, Any]] = {}
        for i, phase in enumerate(improved.get("phases", [])):
            if isinstance(phase, dict):
                name = phase.get("name", f"phase_{i}")
                phase_map[name] = phase

        # Apply anti-patterns to commonly failing phases
        for phase_name in metrics.get("common_failures", []):
            if phase_name not in phase_map:
                continue
            phase = phase_map[phase_name]
            existing = set(str(ap) for ap in phase.get("anti_patterns", []))

            # Generate a descriptive anti-pattern from failure data
            new_ap = (
                f"Avoid common failure in {phase_name}: "
                f"ensure checkpoint validation before proceeding. "
                f"Consider fallback behavior on validation failure."
            )
            if new_ap not in existing:
                anti_patterns = phase.get("anti_patterns", [])
                anti_patterns.append(new_ap)
                phase["anti_patterns"] = anti_patterns

        # Promote confidence tier if warranted
        new_tier = self.should_promote_confidence()
        if new_tier:
            provenance = improved.get("provenance", {})
            old_confidence = provenance.get("confidence", "inferred")
            provenance["confidence"] = new_tier
            provenance["promoted_from"] = old_confidence
            provenance["promotion_executions"] = metrics.get("total_executions", 0)
            provenance["promotion_success_rate"] = metrics.get("success_rate", 0.0)
            improved["provenance"] = provenance

        return improved


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Read a JSONL file and return a list of event dicts."""
    events: List[Dict[str, Any]] = []
    if not path.exists():
        return events
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return events
