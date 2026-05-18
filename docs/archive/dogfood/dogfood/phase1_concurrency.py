#!/usr/bin/env python3
"""
Phase 1 Concurrency Stress Test — Borg v3.1.0
================================================
Orchestrator script (run from KVM8) that coordinates 4 VPS nodes,
firing concurrent Borg CLI operations via SSH and validating results.

Tests:
  C-01  Simultaneous search across all nodes
  C-02  Concurrent observe (borg try) across all nodes
  C-03  Concurrent feedback write (borg feedback) across all nodes
  C-04  Concurrent apply (borg init) across all nodes
  C-05  Mixed read/write operations across all nodes
  C-06  Rapid-fire 100 operations per node

Usage:
  python3 phase1_concurrency.py [--nodes IP1,IP2,...] [--report FILE]
"""

import argparse
import json
import os
import subprocess
import sys
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_NODES = [
    "147.93.72.73",
    "72.61.53.248",
    "76.13.198.23",
    "76.13.209.192",
]

SSH_OPTS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=10",
    "-o", "LogLevel=ERROR",
]

SSH_USER = "root"
BORG_DB_DIR = "~/.hermes/guild"

# How many workers per node for rapid-fire
RAPID_FIRE_OPS = 100
MAX_WORKERS = 32  # thread pool ceiling


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class OpResult:
    node: str
    test_id: str
    command: str
    stdout: str
    stderr: str
    returncode: int
    start_ts: float
    end_ts: float
    latency_ms: float = 0.0

    def __post_init__(self):
        self.latency_ms = round((self.end_ts - self.start_ts) * 1000, 2)

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class TestVerdict:
    test_id: str
    name: str
    passed: bool
    total_ops: int = 0
    errors: int = 0
    latency_p50: float = 0.0
    latency_p95: float = 0.0
    latency_max: float = 0.0
    detail: str = ""


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------
def ssh_cmd(node: str, remote_cmd: str, timeout: int = 30) -> OpResult:
    """Run a command on a remote node via SSH and return an OpResult."""
    full = ["ssh"] + SSH_OPTS + [f"{SSH_USER}@{node}", remote_cmd]
    start = time.time()
    try:
        proc = subprocess.run(
            full, capture_output=True, text=True, timeout=timeout
        )
        end = time.time()
        return OpResult(
            node=node,
            test_id="",
            command=remote_cmd,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            returncode=proc.returncode,
            start_ts=start,
            end_ts=end,
        )
    except subprocess.TimeoutExpired:
        end = time.time()
        return OpResult(
            node=node,
            test_id="",
            command=remote_cmd,
            stdout="",
            stderr="TIMEOUT after {}s".format(timeout),
            returncode=-1,
            start_ts=start,
            end_ts=end,
        )
    except Exception as exc:
        end = time.time()
        return OpResult(
            node=node,
            test_id="",
            command=remote_cmd,
            stdout="",
            stderr=str(exc),
            returncode=-2,
            start_ts=start,
            end_ts=end,
        )


def parallel_ssh(nodes: List[str], cmds_per_node: Dict[str, List[str]],
                 test_id: str, timeout: int = 30,
                 max_workers: int = MAX_WORKERS) -> List[OpResult]:
    """Fire commands in parallel across nodes. Returns list of OpResults."""
    results: List[OpResult] = []
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for node in nodes:
            for cmd in cmds_per_node.get(node, []):
                fut = pool.submit(ssh_cmd, node, cmd, timeout)
                futures.append((node, cmd, fut))
        for node, cmd, fut in futures:
            r = fut.result()
            r.test_id = test_id
            results.append(r)
    return results


def broadcast_ssh(nodes: List[str], cmd: str, test_id: str,
                  timeout: int = 30) -> List[OpResult]:
    """Run the same command on all nodes in parallel."""
    cmds = {n: [cmd] for n in nodes}
    return parallel_ssh(nodes, cmds, test_id, timeout)


# ---------------------------------------------------------------------------
# Latency stats helper
# ---------------------------------------------------------------------------
def latency_stats(results: List[OpResult]) -> Tuple[float, float, float]:
    """Return (p50, p95, max) latency in ms from a list of OpResults."""
    lats = sorted(r.latency_ms for r in results)
    if not lats:
        return (0.0, 0.0, 0.0)
    p50 = lats[len(lats) // 2]
    p95_idx = min(int(len(lats) * 0.95), len(lats) - 1)
    p95 = lats[p95_idx]
    mx = lats[-1]
    return (round(p50, 2), round(p95, 2), round(mx, 2))


def make_verdict(test_id: str, name: str, results: List[OpResult],
                 extra_check: Optional[bool] = None) -> TestVerdict:
    errors = sum(1 for r in results if not r.ok)
    p50, p95, mx = latency_stats(results)
    passed = (errors == 0) if extra_check is None else (errors == 0 and extra_check)
    return TestVerdict(
        test_id=test_id,
        name=name,
        passed=passed,
        total_ops=len(results),
        errors=errors,
        latency_p50=p50,
        latency_p95=p95,
        latency_max=mx,
    )


# ---------------------------------------------------------------------------
# Pre-flight: verify connectivity & borg availability
# ---------------------------------------------------------------------------
def preflight(nodes: List[str]) -> bool:
    print("[preflight] Checking SSH connectivity and borg availability...")
    ok = True
    results = broadcast_ssh(nodes, "borg --version 2>/dev/null || borg version 2>/dev/null || echo BORG_NOT_FOUND", "preflight")
    for r in results:
        status = "OK" if r.ok else "FAIL"
        print(f"  {r.node}: {status}  ({r.stdout or r.stderr})")
        if not r.ok or "NOT_FOUND" in r.stdout:
            ok = False
    return ok


# ---------------------------------------------------------------------------
# Test implementations
# ---------------------------------------------------------------------------
def test_c01_simultaneous_search(nodes: List[str]) -> Tuple[TestVerdict, List[OpResult]]:
    """C-01: Fire 'borg search' simultaneously on all 4 nodes."""
    tid = "C-01"
    print(f"\n[{tid}] Simultaneous search across {len(nodes)} nodes...")
    queries = ["python", "git", "docker", "linux"]
    cmds = {n: [f"borg search {q}"] for n, q in zip(nodes, queries)}
    results = parallel_ssh(nodes, cmds, tid)
    v = make_verdict(tid, "Simultaneous search", results)
    return v, results


def test_c02_concurrent_observe(nodes: List[str]) -> Tuple[TestVerdict, List[OpResult]]:
    """C-02: Fire 'borg try <pack>' concurrently (read-only observe)."""
    tid = "C-02"
    print(f"\n[{tid}] Concurrent observe (borg try) across {len(nodes)} nodes...")
    packs = ["hello-world", "demo-pack", "test-pack", "sample"]
    cmds = {n: [f"borg try {p}"] for n, p in zip(nodes, packs)}
    results = parallel_ssh(nodes, cmds, tid, timeout=60)
    # Allow non-zero exit if pack simply doesn't exist — only count crashes
    v = make_verdict(tid, "Concurrent observe", results)
    return v, results


def test_c03_concurrent_feedback(nodes: List[str]) -> Tuple[TestVerdict, List[OpResult]]:
    """C-03: Concurrent feedback writes — multiple writes per node."""
    tid = "C-03"
    print(f"\n[{tid}] Concurrent feedback write across {len(nodes)} nodes...")
    cmds: Dict[str, List[str]] = {}
    for i, node in enumerate(nodes):
        cmds[node] = [
            f'borg feedback "concurrency test feedback {i}-{j} at $(date +%s)"'
            for j in range(4)
        ]
    results = parallel_ssh(nodes, cmds, tid)
    v = make_verdict(tid, "Concurrent feedback write", results)
    return v, results


def test_c04_concurrent_apply(nodes: List[str]) -> Tuple[TestVerdict, List[OpResult]]:
    """C-04: Concurrent apply (borg init) — each node inits a unique project."""
    tid = "C-04"
    print(f"\n[{tid}] Concurrent apply (borg init) across {len(nodes)} nodes...")
    ts = int(time.time())
    cmds = {
        n: [f"cd /tmp && mkdir -p stress_{ts}_{i} && cd stress_{ts}_{i} && borg init stress-project-{i}"]
        for i, n in enumerate(nodes)
    }
    results = parallel_ssh(nodes, cmds, tid, timeout=60)
    # Cleanup
    for i, n in enumerate(nodes):
        ssh_cmd(n, f"rm -rf /tmp/stress_{ts}_{i}", timeout=10)
    v = make_verdict(tid, "Concurrent apply", results)
    return v, results


def test_c05_mixed_read_write(nodes: List[str]) -> Tuple[TestVerdict, List[OpResult]]:
    """C-05: Mixed read/write — each node gets a mix of search + feedback."""
    tid = "C-05"
    print(f"\n[{tid}] Mixed read/write across {len(nodes)} nodes...")
    cmds: Dict[str, List[str]] = {}
    for i, node in enumerate(nodes):
        cmds[node] = [
            "borg search python",
            f'borg feedback "mixed-test write {i}-a"',
            "borg list",
            f'borg feedback "mixed-test write {i}-b"',
            "borg search linux",
        ]
    results = parallel_ssh(nodes, cmds, tid)
    v = make_verdict(tid, "Mixed read/write", results)
    return v, results


def test_c06_rapid_fire(nodes: List[str]) -> Tuple[TestVerdict, List[OpResult]]:
    """C-06: Rapid-fire 100 operations per node (400 total)."""
    tid = "C-06"
    total = RAPID_FIRE_OPS * len(nodes)
    print(f"\n[{tid}] Rapid-fire {RAPID_FIRE_OPS} ops/node ({total} total)...")
    read_cmds = ["borg search python", "borg list", "borg search git", "borg search docker"]
    cmds: Dict[str, List[str]] = {}
    for node in nodes:
        node_cmds = []
        for j in range(RAPID_FIRE_OPS):
            node_cmds.append(read_cmds[j % len(read_cmds)])
        cmds[node] = node_cmds
    results = parallel_ssh(nodes, cmds, tid, timeout=120, max_workers=MAX_WORKERS)
    v = make_verdict(tid, f"Rapid-fire {total} ops", results)
    return v, results


# ---------------------------------------------------------------------------
# Post-hoc: DB integrity check
# ---------------------------------------------------------------------------
def check_db_integrity(nodes: List[str]) -> Tuple[bool, List[OpResult]]:
    """Run SQLite integrity_check on each node's Borg DB."""
    print("\n[post-hoc] Verifying DB integrity on all nodes...")
    cmd = (
        'for db in ~/.hermes/guild/*.db ~/.hermes/guild/*.sqlite '
        '~/.hermes/guild/db/*.db 2>/dev/null; do '
        '  [ -f "$db" ] && echo "CHECK: $db" && sqlite3 "$db" "PRAGMA integrity_check;" ; '
        'done; echo DONE'
    )
    results = broadcast_ssh(nodes, cmd, "integrity")
    all_ok = True
    for r in results:
        ok_flag = r.ok and ("corrupt" not in r.stdout.lower())
        status = "OK" if ok_flag else "FAIL"
        print(f"  {r.node}: {status}")
        if not ok_flag:
            all_ok = False
            print(f"    stdout: {r.stdout[:300]}")
            print(f"    stderr: {r.stderr[:300]}")
    return all_ok, results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_report(verdicts: List[TestVerdict], db_ok: bool,
                 all_results: List[OpResult], elapsed: float,
                 report_path: Optional[str] = None):
    """Print and optionally save a summary report."""
    sep = "=" * 70
    lines = []

    def out(s=""):
        lines.append(s)
        print(s)

    out(sep)
    out("  BORG v3.1.0 — Phase 1 Concurrency Stress Test Report")
    out(f"  Generated: {datetime.now(timezone.utc).isoformat()}")
    out(f"  Total wall time: {elapsed:.1f}s")
    out(sep)
    out()
    out(f"  {'Test':<8} {'Name':<30} {'Ops':>5} {'Err':>5} {'P50ms':>8} {'P95ms':>8} {'Max ms':>8}  {'Result'}")
    out(f"  {'-'*6:<8} {'-'*28:<30} {'---':>5} {'---':>5} {'-----':>8} {'-----':>8} {'------':>8}  {'------'}")
    for v in verdicts:
        tag = "PASS" if v.passed else "FAIL"
        out(f"  {v.test_id:<8} {v.name:<30} {v.total_ops:>5} {v.errors:>5} "
            f"{v.latency_p50:>8.1f} {v.latency_p95:>8.1f} {v.latency_max:>8.1f}  {tag}")

    out()
    db_tag = "PASS" if db_ok else "FAIL"
    out(f"  DB Integrity Check: {db_tag}")

    total_ops = sum(v.total_ops for v in verdicts)
    total_errs = sum(v.errors for v in verdicts)
    all_passed = all(v.passed for v in verdicts) and db_ok
    out()
    out(f"  Total operations: {total_ops}")
    out(f"  Total errors:     {total_errs}")
    out(f"  Overall:          {'ALL PASS' if all_passed else 'SOME FAILURES'}")
    out(sep)

    if report_path:
        # Save detailed JSON report
        report = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(elapsed, 2),
            "db_integrity": db_ok,
            "overall_pass": all_passed,
            "total_ops": total_ops,
            "total_errors": total_errs,
            "tests": [],
            "raw_results": [],
        }
        for v in verdicts:
            report["tests"].append({
                "test_id": v.test_id,
                "name": v.name,
                "passed": v.passed,
                "total_ops": v.total_ops,
                "errors": v.errors,
                "latency_p50_ms": v.latency_p50,
                "latency_p95_ms": v.latency_p95,
                "latency_max_ms": v.latency_max,
            })
        for r in all_results:
            report["raw_results"].append({
                "test_id": r.test_id,
                "node": r.node,
                "command": r.command,
                "returncode": r.returncode,
                "latency_ms": r.latency_ms,
                "stdout_preview": r.stdout[:200],
                "stderr_preview": r.stderr[:200],
                "start_ts": r.start_ts,
                "end_ts": r.end_ts,
            })
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Detailed JSON report saved to: {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Borg v3.1.0 Phase 1 Concurrency Stress Test")
    parser.add_argument("--nodes", type=str, default=",".join(DEFAULT_NODES),
                        help="Comma-separated VPS IPs")
    parser.add_argument("--report", type=str,
                        default="/root/hermes-workspace/borg/dogfood/phase1_report.json",
                        help="Path to save JSON report")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip preflight connectivity check")
    args = parser.parse_args()

    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    print(f"Borg v3.1.0 Phase 1 Concurrency Stress Test")
    print(f"Nodes: {nodes}")
    print(f"Time:  {datetime.now(timezone.utc).isoformat()}")

    # Preflight
    if not args.skip_preflight:
        if not preflight(nodes):
            print("\n[ABORT] Preflight failed — fix connectivity/borg install first.")
            sys.exit(1)

    wall_start = time.time()
    all_results: List[OpResult] = []
    verdicts: List[TestVerdict] = []

    # Run all 6 tests
    tests = [
        test_c01_simultaneous_search,
        test_c02_concurrent_observe,
        test_c03_concurrent_feedback,
        test_c04_concurrent_apply,
        test_c05_mixed_read_write,
        test_c06_rapid_fire,
    ]

    for test_fn in tests:
        try:
            v, results = test_fn(nodes)
            verdicts.append(v)
            all_results.extend(results)
            tag = "PASS" if v.passed else "FAIL"
            print(f"  => {v.test_id} {tag}  (ops={v.total_ops}, errors={v.errors}, "
                  f"p50={v.latency_p50:.0f}ms, p95={v.latency_p95:.0f}ms)")
        except Exception as exc:
            print(f"  => TEST EXCEPTION: {exc}")
            verdicts.append(TestVerdict(
                test_id=test_fn.__name__,
                name=test_fn.__doc__ or "",
                passed=False,
                detail=str(exc),
            ))

    # Post-hoc DB integrity
    db_ok, db_results = check_db_integrity(nodes)

    wall_elapsed = time.time() - wall_start

    # Report
    print_report(verdicts, db_ok, all_results, wall_elapsed, args.report)

    # Exit code reflects overall pass/fail
    all_pass = all(v.passed for v in verdicts) and db_ok
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
