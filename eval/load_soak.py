#!/usr/bin/env python3
"""Borg local concurrency soak runner.

This exercises the privacy-safe read path used by agent memory retrieval under
many concurrent logical users. It intentionally avoids network calls and writes
only deterministic machine artifacts so readiness gates can be rerun locally.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _thresholds(users: int) -> dict[str, float]:
    if users >= 1000:
        return {"success_rate_min": 0.99, "p95_ms_max": 500.0, "p99_ms_max": 1500.0, "min_requests_per_user": 1.0}
    if users >= 100:
        return {"success_rate_min": 0.95, "p95_ms_max": 1000.0, "p99_ms_max": 3000.0, "min_requests_per_user": 1.0}
    return {"success_rate_min": 0.95, "p95_ms_max": 2000.0, "p99_ms_max": 4000.0, "min_requests_per_user": 1.0}


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ordered[int(k)]
    return ordered[f] * (c - k) + ordered[c] * (k - f)


def _sample_atom() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "atom_id": "sha256:soak-sample",
        "scope": "local",
        "task": {
            "type": "debug",
            "technology": ["python", "django"],
            "error_class": "db-migration-error",
            "error_pattern": "migration state mismatch",
            "difficulty": "hard",
        },
        "learning": {
            "root_cause_class": "schema_state_mismatch",
            "worked": "Use migration framework with fake-initial when runtime schema already matches models.",
            "avoid": ["Manual schema edits without reconciling migration history."],
            "why": "Runtime schema and migration history diverged.",
        },
        "evidence": {"type": "test_passed", "strength": "strong", "support_count": 7},
        "privacy": {"risk_score": 0, "scanner_version": "privacy-v1", "finding_classes": [], "redaction_count": 0, "raw_trace_retained": False},
        "safety": {"prompt_injection_score": 0, "injection_classes": [], "imperative_text_removed": True, "retrieval_treatment": "untrusted_advisory"},
        "trust": {"submitter_key_id": "", "tenant_pseudonym": "", "agent_reputation_at_submit": 0, "independent_tenant_count": 7, "promotion_score": 0},
        "lifecycle": {"status": "local_safe", "created_at_day": "2026-05-04", "expires_at_day": None, "revoked_at": None, "revocation_reason": None},
    }


async def _run_user(user_id: int, deadline: float, think_time_ms: float, latencies: list[float], failures: list[str]) -> int:
    from borg.core.atom_retrieval import format_atom_for_agent
    from borg.core.privacy import privacy_scan_structured
    from borg.core.prompt_injection import scan_prompt_injection

    atom = _sample_atom()
    completed = 0
    sleep_s = max(think_time_ms, 0.0) / 1000.0
    while time.perf_counter() < deadline:
        start = time.perf_counter()
        try:
            rendered = format_atom_for_agent(atom)
            privacy = privacy_scan_structured(rendered)
            injection = scan_prompt_injection(rendered)
            if privacy.blocked or injection.blocked or "UNTRUSTED HISTORICAL ADVICE" not in rendered:
                raise RuntimeError("retrieval firewall produced unsafe output")
            latencies.append((time.perf_counter() - start) * 1000.0)
            completed += 1
        except Exception as exc:  # pragma: no cover - captured in artifact
            failures.append(f"user={user_id}: {type(exc).__name__}: {exc}")
        if sleep_s:
            await asyncio.sleep(sleep_s)
        else:
            await asyncio.sleep(0)
    return completed


async def _run(users: int, duration: float, think_time_ms: float) -> dict[str, Any]:
    latencies: list[float] = []
    failures: list[str] = []
    deadline = time.perf_counter() + duration
    tasks = [asyncio.create_task(_run_user(i, deadline, think_time_ms, latencies, failures)) for i in range(users)]
    per_user_counts = await asyncio.gather(*tasks)
    successes = len(latencies)
    failure_count = len(failures)
    total = successes + failure_count
    success_rate = successes / total if total else 0.0
    thresholds = _thresholds(users)
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    min_requests_observed = min(per_user_counts) if per_user_counts else 0
    passed = (
        success_rate >= thresholds["success_rate_min"]
        and p95 <= thresholds["p95_ms_max"]
        and p99 <= thresholds["p99_ms_max"]
        and min_requests_observed >= thresholds["min_requests_per_user"]
    )
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "users": users,
        "duration_seconds": duration,
        "concurrency_model": "asyncio_logical_users",
        "operation": "learning_atom_retrieval_firewall_privacy_prompt_scan",
        "total_requests": total,
        "successes": successes,
        "failures": failure_count,
        "success_rate": success_rate,
        "requests_per_second": successes / duration if duration else 0.0,
        "per_user_min_requests": min_requests_observed,
        "latency_ms": {
            "avg": statistics.fmean(latencies) if latencies else 0.0,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "max": max(latencies) if latencies else 0.0,
        },
        "thresholds": thresholds,
        "sample_failures": failures[:10],
        "passed": passed,
    }


def _write_report(snapshot: dict[str, Any]) -> None:
    users = int(snapshot["users"])
    report = ROOT / f"LOAD_TEST_REPORT_{users}.md"
    report.write_text(
        "\n".join([
            f"# Borg {users} logical-user load report",
            "",
            "Scope: synthetic asyncio logical users only. This proves local throughput mechanics; it does not authorize 100 real external users.",
            f"concurrency_model: `{snapshot['concurrency_model']}`",
            f"timestamp: `{snapshot['timestamp']}`",
            f"duration_seconds: `{snapshot['duration_seconds']}`",
            f"total_requests: `{snapshot['total_requests']}`",
            f"success_rate: `{snapshot['success_rate']:.6f}`",
            f"requests_per_second: `{snapshot['requests_per_second']:.2f}`",
            f"p95_ms: `{snapshot['latency_ms']['p95']:.3f}`",
            f"p99_ms: `{snapshot['latency_ms']['p99']:.3f}`",
            f"passed: `{snapshot['passed']}`",
            "",
            "Source snapshot: `eval/load_%s_snapshot.json`" % users,
            "",
        ]),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Borg local concurrency soak")
    parser.add_argument("--users", type=int, choices=[10, 100, 1000], required=True)
    parser.add_argument("--duration", type=float, default=float(os.getenv("BORG_READINESS_SOAK_SECONDS", "30")))
    parser.add_argument("--think-time-ms", type=float, default=None)
    args = parser.parse_args()

    if args.think_time_ms is None:
        args.think_time_ms = 0.0 if args.users <= 10 else (10.0 if args.users <= 100 else 50.0)

    snapshot = asyncio.run(_run(args.users, args.duration, args.think_time_ms))
    out = ROOT / "eval" / f"load_{args.users}_snapshot.json"
    out.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    _write_report(snapshot)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
