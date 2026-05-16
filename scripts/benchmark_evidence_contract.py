#!/usr/bin/env python3
"""Validate benchmark evidence before it can be used for frontier-value claims.

This contract is intentionally conservative. It permits honest artifacts that say
there is no valid evidence, but rejects benchmark JSON that tries to support a
frontier/better-than claim with zero-duration, zero-token, missing-delta, or
uncontrolled evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

UNAVAILABLE_MARKERS = {"unavailable", "not_available", "not_measured", "n/a", "na", "unknown"}
CLAIM_KEYS = (
    "frontier_better_than_proven",
    "better_than_frontier",
    "beats_frontier",
    "frontier_value_proven",
    "claim_frontier_lift",
)
CONTROLLED_EVIDENCE_KEYS = (
    "controlled_evidence",
    "controlled_ab",
    "randomized",
    "baseline_model",
    "frontier_baseline",
    "confidence_interval",
    "statistical_confidence",
    "matched_tasks",
)
DELTA_KEYS = (
    "success_delta",
    "delta",
    "success_rate_delta",
    "time_delta",
    "token_delta",
    "tokens_delta",
    "duration_delta",
)
DURATION_KEYS = ("duration_seconds", "latency_seconds", "elapsed_seconds", "wall_time_seconds", "runtime_seconds")
TOKEN_KEYS = ("tokens_used", "tokens_total", "total_tokens", "token_count", "tokens")
SUCCESS_KEYS = ("success", "success_rate", "verified_success", "completion_status")
PAIRED_ROW_KEYS = ("rows", "results", "task_results", "records", "pairs", "paired_rows")


class BenchmarkEvidenceError(ValueError):
    """Raised when an artifact violates the evidence contract."""


def _walk(obj: Any):
    yield obj
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk(value)


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _status(obj: Any) -> str | None:
    if isinstance(obj, dict):
        value = obj.get("status") or obj.get("evidence_status") or obj.get("verdict")
        if isinstance(value, str):
            return value.upper()
    return None


def _explicit_metric_unavailable(obj: Any, metric: str) -> bool:
    if not isinstance(obj, dict):
        return False
    candidates = [
        obj.get(f"{metric}_metric_status"),
        obj.get(f"{metric}_status"),
        obj.get(f"{metric}_availability"),
        obj.get(f"{metric}_unavailable_reason"),
    ]
    return any(isinstance(v, str) and v.strip().lower() in UNAVAILABLE_MARKERS for v in candidates)


def _has_positive_metric(obj: Any, keys: tuple[str, ...]) -> bool:
    for node in _walk(obj):
        if isinstance(node, dict):
            for key in keys:
                if key in node:
                    num = _as_number(node[key])
                    if num is not None and num > 0:
                        return True
    return False


def _has_key(obj: Any, keys: tuple[str, ...]) -> bool:
    return any(isinstance(node, dict) and any(key in node for key in keys) for node in _walk(obj))


def _has_top_level_key(obj: Any, keys: tuple[str, ...]) -> bool:
    return isinstance(obj, dict) and any(key in obj for key in keys)


def _has_non_null_delta(obj: Any) -> bool:
    for node in _walk(obj):
        if isinstance(node, dict):
            for key in DELTA_KEYS:
                if key in node and node[key] is not None:
                    return True
    return False


def _has_paired_rows(obj: Any) -> bool:
    for node in _walk(obj):
        if not isinstance(node, dict):
            continue
        for key in PAIRED_ROW_KEYS:
            rows = node.get(key)
            if isinstance(rows, list) and rows:
                arms_by_task: dict[str, set[str]] = {}
                for row in rows:
                    if isinstance(row, dict):
                        arm = row.get("arm") or row.get("experiment_arm") or row.get("condition")
                        task_id = row.get("task_id") or row.get("id")
                        if arm and task_id:
                            arms_by_task.setdefault(str(task_id), set()).add(str(arm).lower())
                for arms in arms_by_task.values():
                    if {"control", "treatment"}.issubset(arms) or {"baseline", "treatment"}.issubset(arms):
                        return True
    return False


def _claims_frontier(obj: Any) -> bool:
    text_claim = False
    explicit_claim = False
    for node in _walk(obj):
        if isinstance(node, dict):
            for key in CLAIM_KEYS:
                if node.get(key) is True:
                    explicit_claim = True
            claim = node.get("claim") or node.get("conclusion") or node.get("summary")
            if isinstance(claim, str):
                lower = claim.lower()
                if ("frontier" in lower and ("better" in lower or "beat" in lower or "outperform" in lower)):
                    text_claim = True
        elif isinstance(node, str):
            lower = node.lower()
            if "frontier" in lower and ("better than" in lower or "beats" in lower or "outperform" in lower):
                text_claim = True
    return explicit_claim or text_claim


def _has_controlled_evidence(obj: Any) -> bool:
    found = set()
    for node in _walk(obj):
        if isinstance(node, dict):
            for key in CONTROLLED_EVIDENCE_KEYS:
                value = node.get(key)
                if value not in (None, False, "", [], {}):
                    found.add(key)
    return {"randomized", "frontier_baseline", "matched_tasks"}.issubset(found) and (
        "confidence_interval" in found or "statistical_confidence" in found or "controlled_evidence" in found
    )


def validate_benchmark_evidence(data: Any) -> dict[str, Any]:
    """Return a machine-readable verdict; raise on invalid claimed evidence."""
    status = _status(data)
    if status == "NO_VALID_EVIDENCE":
        return {"valid": True, "status": "NO_VALID_EVIDENCE", "frontier_better_than_proven": False, "errors": []}

    errors: list[str] = []
    if not (_has_top_level_key(data, SUCCESS_KEYS) or _has_non_null_delta(data) or _has_paired_rows(data)):
        errors.append("missing success/success_delta/paired-row evidence")
    if not _has_positive_metric(data, DURATION_KEYS):
        errors.append("missing positive duration/time metric")
    if not (_has_positive_metric(data, TOKEN_KEYS) or _explicit_metric_unavailable(data if isinstance(data, dict) else {}, "tokens")):
        errors.append("missing positive token metric or explicit token-unavailable marker")
    if _has_key(data, DELTA_KEYS) and not _has_non_null_delta(data):
        errors.append("delta metrics are present but all null")

    claims_frontier = _claims_frontier(data)
    controlled = _has_controlled_evidence(data)
    if claims_frontier and not controlled:
        errors.append("frontier/better-than claim lacks controlled evidence fields")

    if errors:
        raise BenchmarkEvidenceError("; ".join(errors))
    return {
        "valid": True,
        "status": "VALID_EVIDENCE",
        "frontier_better_than_proven": bool(claims_frontier and controlled),
        "errors": [],
    }


def validate_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    verdict = validate_benchmark_evidence(data)
    verdict["path"] = str(path)
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    ok = True
    for path in args.paths:
        try:
            print(json.dumps(validate_file(path), sort_keys=True))
        except Exception as exc:  # noqa: BLE001 - CLI must report contract failures plainly.
            ok = False
            print(json.dumps({"path": str(path), "valid": False, "error": str(exc)}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
