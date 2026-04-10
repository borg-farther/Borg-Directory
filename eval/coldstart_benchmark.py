#!/usr/bin/env python3
"""
Cold-start benchmark for borg v3.3.0

Runs 50 queries from swebench_coldstart_50.json against `borg search`
and outputs a JSON report with latency and match metrics.

Usage:
    python3 coldstart_benchmark.py [--json]
    python3 -m borg.cli search "query"  # for manual testing

Output format:
{
    "total": 50,
    "non_empty": X,
    "latency_ms_avg": Y,
    "per_query": [...]
}
"""

import json
import time
import subprocess
import sys
import os
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent.parent / "borg" / "tests" / "fixtures" / "swebench_coldstart_50.json"
REPORT_PATH = Path(__file__).parent / "coldstart_report.json"


def run_borg_search(query: str) -> dict:
    """Run `borg search <query>` and return parsed result with latency."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "borg.cli", "search", "--json", query],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        if result.returncode != 0:
            return {
                "query": query,
                "returned_pack": None,
                "latency_ms": round(latency_ms, 2),
                "non_empty": False,
                "error": result.stderr or "non-zero exit",
            }

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "query": query,
                "returned_pack": None,
                "latency_ms": round(latency_ms, 2),
                "non_empty": False,
                "error": "invalid JSON output",
            }

        matches = data.get("matches", [])
        first_pack = matches[0].get("name") if matches else None

        return {
            "query": query,
            "returned_pack": first_pack,
            "latency_ms": round(latency_ms, 2),
            "non_empty": len(matches) > 0,
            "match_count": len(matches),
        }

    except subprocess.TimeoutExpired:
        return {
            "query": query,
            "returned_pack": None,
            "latency_ms": 30000,
            "non_empty": False,
            "error": "timeout after 30s",
        }
    except Exception as e:
        return {
            "query": query,
            "returned_pack": None,
            "latency_ms": 0,
            "non_empty": False,
            "error": str(e),
        }


def main():
    # Load fixture
    if not FIXTURE_PATH.exists():
        print(f"ERROR: Fixture not found at {FIXTURE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(FIXTURE_PATH, "r") as f:
        fixture = json.load(f)

    if not isinstance(fixture, list):
        print("ERROR: Fixture must be a JSON array of query objects", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(fixture)} queries from fixture")
    print(f"Running borg search for each query...\n")

    results = []
    for i, entry in enumerate(fixture, 1):
        query = entry.get("query", "")
        expected = entry.get("expected_pack", "")
        problem_class = entry.get("problem_class", "")
        instance_id = entry.get("instance_id", "")

        result = run_borg_search(query)
        result["expected_pack"] = expected
        result["problem_class"] = problem_class
        result["instance_id"] = instance_id
        result["match"] = (result.get("returned_pack") == expected) if result.get("returned_pack") else False

        results.append(result)

        status = "✓" if result["non_empty"] else "✗"
        returned = result.get("returned_pack") or "NONE"
        expected = entry.get("expected_pack", "")
        match_status = "✓" if result.get("returned_pack") == entry.get("expected_pack") else "✗"
        print(f"  [{i:2d}/50] {status} non_empty={result['non_empty']} "
              f"latency={result['latency_ms']:.1f}ms "
              f"returned={returned:<30} "
              f"expected={expected:<30} "
              f"match={match_status}")

    # Aggregate
    non_empty_count = sum(1 for r in results if r["non_empty"])
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    report = {
        "total": len(results),
        "non_empty": non_empty_count,
        "non_empty_pct": round(non_empty_count / len(results) * 100, 1),
        "latency_ms_avg": round(avg_latency, 2),
        "latency_ms_p50": round(sorted(latencies)[len(latencies)//2], 2) if latencies else 0,
        "latency_ms_p95": round(sorted(latencies)[int(len(latencies)*0.95)], 2) if latencies else 0,
        "per_query": results,
    }

    # Write report
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== BENCHMARK RESULTS ===")
    print(f"Total queries:   {report['total']}")
    print(f"Non-empty:       {report['non_empty']} ({report['non_empty_pct']}%)")
    print(f"Avg latency:    {report['latency_ms_avg']:.2f}ms")
    print(f"P50 latency:    {report['latency_ms_p50']:.2f}ms")
    print(f"P95 latency:    {report['latency_ms_p95']:.2f}ms")
    print(f"\nFull report written to: {REPORT_PATH}")

    # Print JSON to stdout as well
    if "--json" in sys.argv:
        print("\n" + json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())