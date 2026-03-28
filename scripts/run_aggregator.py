#!/usr/bin/env python3
"""
Automated Borg Aggregator Cron Job

Reads feedback from AgentStore and telemetry from BORG_DIR/telemetry.jsonl,
groups by pack, identifies patterns, and generates improvement suggestions.

Run: python scripts/run_aggregator.py
Output: BORG_DIR/aggregator_report.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add borg to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from borg.core.aggregator import PackAggregator
from borg.core.dirs import get_borg_dir
from borg.db.store import AgentStore


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file and return a list of event dicts."""
    events: list[dict[str, Any]] = []
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


def _load_telemetry(borg_dir: Path) -> list[dict[str, Any]]:
    """Load telemetry events from telemetry.jsonl if it exists."""
    telemetry_path = borg_dir / "telemetry.jsonl"
    return _read_jsonl(telemetry_path)


def _group_feedback_by_pack(feedbacks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group feedback entries by pack_id."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for fb in feedbacks:
        pack_id = fb.get("pack_id")
        if pack_id:
            if pack_id not in grouped:
                grouped[pack_id] = []
            grouped[pack_id].append(fb)
    return grouped


def _group_telemetry_by_pack(telemetry: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group telemetry events by pack_id."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in telemetry:
        pack_id = event.get("pack_id")
        if pack_id:
            if pack_id not in grouped:
                grouped[pack_id] = []
            grouped[pack_id].append(event)
    return grouped


def _identify_negative_feedback(feedbacks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter to only negative/outcome=failure feedback."""
    negative: list[dict[str, Any]] = []
    for fb in feedbacks:
        outcome = fb.get("outcome", "").lower()
        if outcome in ("failure", "partial"):
            negative.append(fb)
    return negative


def _compute_pack_report(
    pack_id: str,
    feedbacks: list[dict[str, Any]],
    telemetry: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute a report for a single pack using PackAggregator."""
    agg = PackAggregator(pack_id)

    # Ingest feedback
    for fb in feedbacks:
        if fb.get("type") == "feedback":
            agg.ingest_feedback(fb)
        else:
            # Wrap raw feedback dict
            wrapped = {"type": "feedback", **fb}
            agg.ingest_feedback(wrapped)

    # Ingest telemetry as executions if they contain execution data
    for event in telemetry:
        ev_type = event.get("type", "")
        if ev_type in ("execution_started", "checkpoint_pass", "checkpoint_fail", "execution_completed"):
            # Reconstruct a minimal JSONL structure for ingest_execution
            # We need to write to a temp path - instead, directly append to _executions
            if ev_type == "execution_completed":
                exec_summary = {
                    "session_id": event.get("session_id", ""),
                    "success": event.get("status") == "completed",
                    "phases": [],
                    "total_duration_s": event.get("duration_s", 0.0),
                    "error": event.get("error", ""),
                }
                agg._executions.append(exec_summary)

    metrics = agg.compute_metrics()
    suggestions = agg.suggest_improvements()

    # Calculate usage_count from telemetry and feedback
    usage_count = len(telemetry) + len(feedbacks)

    # Identify failure patterns from negative feedback
    failure_patterns: list[str] = []
    negative_fb = _identify_negative_feedback(feedbacks)
    for fb in negative_fb:
        evidence = fb.get("evidence", "")
        if evidence:
            failure_patterns.append(evidence)

    # Add common failures from metrics
    for cf in metrics.get("common_failures", []):
        if cf not in failure_patterns:
            failure_patterns.append(f"common failure in phase: {cf}")

    return {
        "pack_id": pack_id,
        "usage_count": usage_count,
        "success_rate": metrics.get("success_rate", 0.0),
        "common_failure_patterns": failure_patterns[:10],  # Limit to top 10
        "suggested_improvements": suggestions[:5],  # Limit to top 5
    }


def _rank_packs_by_usage(pack_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return packs sorted by usage_count descending."""
    return sorted(pack_reports, key=lambda r: r["usage_count"], reverse=True)


def _identify_top_failed(pack_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return packs sorted by lowest success_rate (most failures)."""
    with_failures = [r for r in pack_reports if r["success_rate"] < 1.0]
    return sorted(with_failures, key=lambda r: r["success_rate"])


def _identify_negative_packs(pack_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return packs with negative feedback."""
    return [r for r in pack_reports if r["common_failure_patterns"]]


def generate_report() -> dict[str, Any]:
    """Generate the full aggregator improvement report."""
    borg_dir = get_borg_dir()
    return generate_report_for_dir(borg_dir)


def generate_report_for_dir(borg_dir: Path) -> dict[str, Any]:
    """Generate the full aggregator improvement report for a specific BORG_DIR.

    Args:
        borg_dir: The BORG directory path

    Returns:
        The aggregator report dict
    """
    # Load data
    store = AgentStore(db_path=str(borg_dir / "guild.db"))
    feedbacks = store.list_feedback(limit=10000)
    telemetry = _load_telemetry(borg_dir)

    # Group by pack
    feedback_by_pack = _group_feedback_by_pack(feedbacks)
    telemetry_by_pack = _group_telemetry_by_pack(telemetry)

    # Get all pack IDs
    all_pack_ids = set(feedback_by_pack.keys()) | set(telemetry_by_pack.keys())

    # Compute per-pack reports
    pack_reports: list[dict[str, Any]] = []
    for pack_id in sorted(all_pack_ids):
        fbs = feedback_by_pack.get(pack_id, [])
        tel = telemetry_by_pack.get(pack_id, [])
        report = _compute_pack_report(pack_id, fbs, tel)
        pack_reports.append(report)

    # Sort and rank
    most_used = _rank_packs_by_usage(pack_reports)
    most_failed = _identify_top_failed(pack_reports)
    negative_packs = _identify_negative_packs(pack_reports)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_packs_analyzed": len(all_pack_ids),
        "total_feedback_entries": len(feedbacks),
        "total_telemetry_events": len(telemetry),
        "most_used_packs": most_used[:10],  # Top 10
        "most_failed_packs": most_failed[:10],  # Top 10 failed
        "packs_with_negative_feedback": negative_packs,
        "all_pack_reports": pack_reports,
    }

    return report


def main() -> None:
    """Run the aggregator and write the report."""
    borg_dir = get_borg_dir()

    print(f"Borg Aggregator - Analyzing feedback and telemetry...")
    print(f"BORG_DIR: {borg_dir}")

    report = generate_report()

    # Write report
    report_path = borg_dir / "aggregator_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report written to: {report_path}")
    print(f"Packs analyzed: {report['total_packs_analyzed']}")
    print(f"Most used pack: {report['most_used_packs'][0]['pack_id'] if report['most_used_packs'] else 'none'}")
    print(f"Most failed pack: {report['most_failed_packs'][0]['pack_id'] if report['most_failed_packs'] else 'none'}")


if __name__ == "__main__":
    main()
