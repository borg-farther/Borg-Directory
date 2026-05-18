#!/usr/bin/env python3
"""Final Borg readiness proof sweep for 2026-05-17.

Captures full stdout/stderr for the current repo after the 100-real-user gate
patch. Synthetic/load gates may pass while the real-user rollout gate remains
NO-GO until first-10 external evidence exists.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "20260517_borg_final_proof_run.json"
REPORT = ROOT / "docs" / "20260517_BORG_FINAL_PROOF_RUN.md"


def run(name: str, cmd: list[str], *, timeout: int = 900, expected_returncodes: set[int] | None = None) -> dict[str, Any]:
    expected = expected_returncodes or {0}
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        rc = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        rc = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode("utf-8", errors="replace")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode("utf-8", errors="replace")
        timed_out = True
    return {
        "name": name,
        "cmd": cmd,
        "started_at_utc": started,
        "duration_seconds": round(time.monotonic() - t0, 3),
        "returncode": rc,
        "expected_returncodes": sorted(expected),
        "passed": rc in expected,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
    }


def read_json(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    py = sys.executable
    commands = [
        ("targeted_readiness_and_store_tests", [py, "-m", "pytest", "-q", "eval/tests/test_readiness_1000.py", "eval/tests/test_real_user_rollout_gate.py", "borg/tests/test_store_concurrency.py"], 600, {0}),
        ("full_pytest_suite", [py, "-m", "pytest", "-q"], 600, {0}),
        ("security_gate_check", [py, "scripts/security_gate_check.py"], 180, {0}),
        ("first_user_release_gate_fresh_venv", [py, "eval/run_first_user_release_gate.py"], 900, {0}),
        ("synthetic_load_readiness_gates", [py, "eval/run_readiness_gates.py"], 1200, {0}),
        ("real_user_rollout_gate_expected_block", [py, "eval/real_user_rollout_gate.py"], 180, {1}),
        ("doc_and_whitespace_diff_check", ["git", "diff", "--check"], 180, {0}),
    ]
    results = [run(name, cmd, timeout=timeout, expected_returncodes=expected) for name, cmd, timeout, expected in commands]
    first_user = read_json("eval/first_user_release_gate_snapshot.json")
    gate_run = read_json("eval/gate_run_snapshot.json")
    uat = read_json("eval/uat_scoreboard_snapshot.json")
    real_user = read_json("eval/real_user_rollout_gate_snapshot.json")
    summary = {
        "all_expected_commands_passed": all(r["passed"] for r in results),
        "first_user_release_gate_passed": bool(first_user.get("success")),
        "synthetic_load_all_pass": bool(gate_run.get("synthetic_load_all_pass", gate_run.get("all_pass"))),
        "ready_for_10_logical_load": bool(gate_run.get("ready_for_10")),
        "ready_for_100_logical_load": bool(gate_run.get("ready_for_100")),
        "ready_for_1000_logical_load": bool(gate_run.get("ready_for_1000")),
        "ready_for_10_controlled_real_users": bool(real_user.get("ready_for_10_controlled_beta")),
        "infrastructure_ready_for_100": bool(real_user.get("infrastructure_ready_for_100")),
        "ready_for_100_real_external_users": bool(real_user.get("ready_for_100_real_users")),
        "max_recommended_real_users_now": int(real_user.get("max_recommended_real_users_now") or 0),
        "real_user_blockers": real_user.get("blockers") or [],
        "uat_real_user_rollout": uat.get("real_user_rollout") or {},
    }
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo": str(ROOT),
        "summary": summary,
        "results": results,
        "snapshots": {
            "first_user_release_gate": first_user,
            "gate_run": gate_run,
            "uat_scoreboard": uat,
            "real_user_rollout_gate": real_user,
        },
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Borg final proof run — 2026-05-17",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        "",
        "## Binary result",
        "",
        f"- Expected commands passed: `{summary['all_expected_commands_passed']}`",
        f"- First-user release gate: `{summary['first_user_release_gate_passed']}`",
        f"- Synthetic/load gates through 1000 logical users: `{summary['synthetic_load_all_pass']}`",
        f"- Ready for 100 real external users: `{summary['ready_for_100_real_external_users']}`",
        f"- Max recommended real users now: `{summary['max_recommended_real_users_now']}`",
        "",
        "## Real-user blockers",
        "",
    ]
    blockers = summary["real_user_blockers"]
    if blockers:
        lines.extend(f"- {b}" for b in blockers)
    else:
        lines.append("None.")
    lines.extend([
        "",
        "## Command evidence",
        "",
    ])
    for r in results:
        lines.append(f"- `{r['name']}`: passed=`{r['passed']}` rc=`{r['returncode']}` expected=`{r['expected_returncodes']}` duration_s=`{r['duration_seconds']}`")
    lines.extend([
        "",
        "Full raw stdout/stderr is captured in `eval/20260517_borg_final_proof_run.json`.",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"summary": summary, "artifact": str(OUT.relative_to(ROOT)), "report": str(REPORT.relative_to(ROOT))}, indent=2, sort_keys=True))
    return 0 if summary["all_expected_commands_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
