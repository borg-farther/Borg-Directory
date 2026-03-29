#!/usr/bin/env python3
"""
Benchmark script for borg_observe latency.
Calls borg_observe 100 times with typical inputs and measures p50/p95/p99 latency.
"""

import json
import sys
import time
import statistics
from pathlib import Path

# Add borg to path
sys.path.insert(0, str(Path(__file__).parent.parent / "borg"))

# Typical task inputs for benchmarking
TYPICAL_TASKS = [
    "Fix TypeError: 'NoneType' object has no attribute 'split' in auth.py",
    "pytest tests are failing after recent refactor",
    "Debug memory leak in the worker process",
    "Review pull request for the new payment module",
    "Handle race condition in concurrent requests",
    "Add unit tests for the user authentication flow",
    "Refactor database queries for better performance",
    "Fix segmentation fault in C extension",
    "Debug why the background job keeps crashing",
    "Write documentation for the API endpoints",
] * 10  # 100 total calls

def run_benchmark():
    # Import borg_observe
    try:
        from borg.integrations.mcp_server import borg_observe
    except ImportError as e:
        print(f"ERROR: Could not import borg_observe: {e}")
        print("Make sure borg is in the Python path")
        return

    latencies = []
    errors = 0
    empty_responses = 0

    print(f"Running {len(TYPICAL_TASKS)} borg_observe calls...")
    print("-" * 60)

    for i, task in enumerate(TYPICAL_TASKS):
        start = time.perf_counter()
        try:
            result = borg_observe(
                task=task,
                context="Python 3.11, FastAPI application",
                context_dict={
                    "error_message": "TypeError" if "TypeError" in task else None,
                    "attempts": 1,
                },
            )
            elapsed = (time.perf_counter() - start) * 1000  # ms

            latencies.append(elapsed)

            # Check if response was empty (no pack found)
            try:
                parsed = json.loads(result)
                if not parsed.get("observed", False):
                    empty_responses += 1
            except:
                pass

        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            print(f"  Call {i+1} ERROR after {elapsed:.2f}ms: {e}")
            errors += 1

        if (i + 1) % 20 == 0:
            print(f"  Completed {i+1}/{len(TYPICAL_TASKS)}...")

    print("-" * 60)

    if not latencies:
        print("ERROR: No successful calls completed")
        return

    latencies.sort()
    n = len(latencies)

    p50 = latencies[int(n * 0.50)] if n > 0 else 0
    p95 = latencies[int(n * 0.95)] if n > 0 else 0
    p99 = latencies[int(n * 0.99)] if n > 0 else 0
    mean = statistics.mean(latencies)
    stddev = statistics.stdev(latencies) if len(latencies) > 1 else 0
    min_lat = min(latencies) if latencies else 0
    max_lat = max(latencies) if latencies else 0

    print(f"\n=== BENCHMARK RESULTS ===")
    print(f"Total calls:      {len(TYPICAL_TASKS)}")
    print(f"Successful:       {len(latencies)}")
    print(f"Errors:           {errors}")
    print(f"Empty responses:  {empty_responses}")
    print(f"")
    print(f"Latency (ms):")
    print(f"  Min:     {min_lat:.2f}")
    print(f"  Mean:    {mean:.2f}")
    print(f"  StdDev:  {stddev:.2f}")
    print(f"  p50:     {p50:.2f}")
    print(f"  p95:     {p95:.2f}")
    print(f"  p99:     {p99:.2f}")
    print(f"  Max:     {max_lat:.2f}")

    # Token estimation
    # Typical response is ~300-800 chars of guidance text
    avg_chars = 500
    tokens_per_call = int(avg_chars * 0.25)  # ~4 chars per token
    total_tokens = tokens_per_call * len(TYPICAL_TASKS)

    print(f"\nToken overhead estimation:")
    print(f"  Avg chars per response: ~{avg_chars}")
    print(f"  Estimated tokens/call: ~{tokens_per_call}")
    print(f"  Total tokens for {len(TYPICAL_TASKS)} calls: ~{total_tokens:,}")

if __name__ == "__main__":
    run_benchmark()
