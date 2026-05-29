"""Deterministic scoring for Borg local pack optimizer candidates."""

from __future__ import annotations

from typing import Any

from borg.core.pack_optimizer_schemas import SelectionScore


WEIGHTS = {
    "verified_success": 0.30,
    "action_stop_verify_relevance": 0.20,
    "dead_ends_avoided": 0.15,
    "no_confident_match_precision": 0.15,
    "verification_quality": 0.10,
    "token_or_tool_efficiency": 0.10,
}


def _metric(metrics: dict[str, Any], key: str) -> float:
    try:
        return max(0.0, min(1.0, float(metrics.get(key, 0.0))))
    except (TypeError, ValueError):
        return 0.0


def weighted_verified_guidance_score(metrics: dict[str, Any]) -> float:
    """Compute the PRD weighted score from normalized metric components."""
    if "weighted_score" in metrics:
        return _metric(metrics, "weighted_score")
    return round(sum(weight * _metric(metrics, key) for key, weight in WEIGHTS.items()), 6)


def hard_failures(taskset: dict[str, Any], baseline_metrics: dict[str, Any], candidate_metrics: dict[str, Any]) -> list[str]:
    """Return hard-gate failures that override aggregate score."""
    failures = [str(item) for item in taskset.get("hard_failures", []) if str(item)]
    controls = taskset.get("controls") or {}
    if controls.get("unrelated_task_regression"):
        failures.append("unrelated_task_regression")
    if controls.get("no_confident_match_regression"):
        failures.append("no_confident_match_regression")
    if controls.get("unsafe_command_regression"):
        failures.append("unsafe_command_regression")
    if _metric(candidate_metrics, "no_confident_match_precision") < _metric(baseline_metrics, "no_confident_match_precision"):
        failures.append("no_confident_match_regression")
    if _metric(candidate_metrics, "verified_success") <= _metric(baseline_metrics, "verified_success"):
        failures.append("selection_score_not_strictly_better")
    return sorted(set(failures))


def compare_baseline_candidate(taskset: dict[str, Any], candidate_id: str) -> SelectionScore:
    baseline_metrics = taskset.get("baseline_metrics") or {}
    candidate_metrics = taskset.get("candidate_metrics") or {}
    baseline = weighted_verified_guidance_score(baseline_metrics)
    candidate = weighted_verified_guidance_score(candidate_metrics)
    failures = hard_failures(taskset, baseline_metrics, candidate_metrics)
    if candidate <= baseline and "selection_score_not_strictly_better" not in failures:
        failures.append("selection_score_not_strictly_better")
    failures = sorted(set(failures))
    recommendation = "eligible_for_manual_review" if not failures and candidate > baseline else "reject"
    return SelectionScore(
        candidate_id=candidate_id,
        baseline_score=baseline,
        candidate_score=candidate,
        score_delta=round(candidate - baseline, 6),
        primary_metric="weighted_verified_guidance_score",
        hard_failures=tuple(failures),
        recommendation=recommendation,
    )
