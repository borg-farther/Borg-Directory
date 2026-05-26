#!/usr/bin/env python3
"""Run Borg synthetic/load gates and report separate real-user rollout status."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _run(name: str, cmd: list[str], timeout: int = 900) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace")
        stderr = proc.stderr.decode("utf-8", errors="replace")
        return {"name": name, "cmd": cmd, "started": started, "rc": proc.returncode, "stdout": stdout[-12000:], "stderr": stderr[-12000:]}
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        return {"name": name, "cmd": cmd, "started": started, "rc": 124, "stdout": stdout[-12000:], "stderr": stderr[-12000:], "timeout": timeout}


def _json_from_stdout(step: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(step.get("stdout") or "{}")
    except json.JSONDecodeError:
        return {}


def _write_decision(snapshot: dict[str, Any]) -> None:
    lines = [
        "# Borg GO / NO-GO Decision",
        "",
        f"Timestamp: `{snapshot['timestamp']}`",
        f"Soak duration seconds: `{snapshot['run_parameters']['soak_duration_seconds']}`",
        "",
        "## Step results",
        "",
    ]
    for step in snapshot["steps"]:
        if step["name"] == "real_user_rollout_gate":
            status = "GO" if snapshot.get("ready_for_100_real_users") else "NO-GO"
            lines.append(f"- {step['name']}: {status} (rc={step['rc']}; nonzero is expected until first-10 external evidence passes)")
        else:
            lines.append(f"- {step['name']}: {'PASS' if step['rc'] == 0 else 'FAIL'} (rc={step['rc']})")
    rollout = snapshot.get("real_user_rollout", {})
    blockers = rollout.get("blockers") or []
    lines.extend([
        "",
        "## Synthetic/logical load rollout",
        "",
        "These are throughput gates only. They do not authorize 100 real external users.",
        "",
        f"- Ready for 10 logical load users: {'GO' if snapshot['ready_for_10'] else 'NO-GO'}",
        f"- Ready for 100 logical load users: {'GO' if snapshot['ready_for_100'] else 'NO-GO'}",
        f"- Ready for 1000 logical load users: {'GO' if snapshot['ready_for_1000'] else 'NO-GO'}",
        "",
        "## Real external-user rollout",
        "",
        f"- Ready for 10 controlled real users: {'GO' if rollout.get('ready_for_10_controlled_beta') else 'NO-GO'}",
        f"- Ready for 100 real external users: {'GO' if rollout.get('ready_for_100_real_users') else 'NO-GO'}",
        f"- Max recommended real users now: {rollout.get('max_recommended_real_users_now', 0)}",
        "",
        "## Real-user blockers",
        "",
    ])
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("None.")
    lines.extend([
        "",
        "Snapshot: `eval/gate_run_snapshot.json`",
        "Real-user snapshot: `eval/real_user_rollout_gate_snapshot.json`",
        "",
    ])
    (ROOT / "GO_NO_GO_DECISION.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "UAT_RESULTS.md").write_text(
        "\n".join([
            "# Borg UAT Results",
            "",
            f"Timestamp: `{snapshot['timestamp']}`",
            "",
            "Final GO/NO-GO is sourced from `GO_NO_GO_DECISION.md`, `PROJECT_STATUS.md`, `eval/gate_run_snapshot.json`, and `eval/real_user_rollout_gate_snapshot.json`.",
            "",
            f"READY_FOR_10_LOGICAL_LOAD: `{snapshot['ready_for_10']}`",
            f"READY_FOR_100_LOGICAL_LOAD: `{snapshot['ready_for_100']}`",
            f"READY_FOR_1000_LOGICAL_LOAD: `{snapshot['ready_for_1000']}`",
            f"READY_FOR_10_CONTROLLED_REAL_USERS: `{rollout.get('ready_for_10_controlled_beta')}`",
            f"READY_FOR_100_REAL_EXTERNAL_USERS: `{rollout.get('ready_for_100_real_users')}`",
            f"MAX_RECOMMENDED_REAL_USERS_NOW: `{rollout.get('max_recommended_real_users_now', 0)}`",
            "",
        ]),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Borg readiness gates and write GO/NO-GO artifacts")
    parser.add_argument(
        "--synthetic-only",
        action="store_true",
        help="Exit 0 when synthetic/logical load gates pass even if real-user rollout remains blocked. Default exits nonzero unless 100-real-user readiness is also green.",
    )
    args = parser.parse_args(argv)
    soak = float(os.getenv("BORG_READINESS_SOAK_SECONDS", "30"))
    py = sys.executable
    steps = [
        ("version_distribution_tests", [py, "-m", "pytest", "-q", "tests/packaging/test_version_consistency.py", "tests/packaging/test_distribution_readiness.py", "tests/cli/test_runtime_doctor.py"], 300),
        ("atom_security_tests", [py, "-m", "pytest", "-q", "tests/security/test_atom_tenant.py", "tests/security/test_atom_policy.py", "tests/security/test_learning_atoms.py", "tests/security/test_atom_store.py", "tests/security/test_atom_retrieval_firewall.py", "tests/security/test_learning_atom_publish.py", "tests/cli/test_cli_atom.py", "tests/security/test_privacy_structured.py", "tests/security/test_prompt_injection.py", "tests/security/test_privacy.py"], 600),
        ("security_gate", [py, "scripts/security_gate_check.py"], 120),
        ("cold_start_trust_gate", [py, "eval/cold_start_trust_gate.py"], 120),
        ("atom_fixture_corpus", [py, "scripts/run_atom_fixture_corpus.py"], 120),
        ("load_10", [py, "eval/load_soak.py", "--users", "10", "--duration", str(soak)], int(soak + 180)),
        ("load_100", [py, "eval/load_soak.py", "--users", "100", "--duration", str(soak)], int(soak + 240)),
        ("load_1000", [py, "eval/load_soak.py", "--users", "1000", "--duration", str(soak)], int(soak + 360)),
        ("readiness_1000_tests", [py, "-m", "pytest", "-q", "eval/tests/test_readiness_1000.py"], 300),
    ]
    results = [_run(name, cmd, timeout) for name, cmd, timeout in steps]
    non_score_pass = all(step["rc"] == 0 for step in results)

    # Write a provisional snapshot before scoreboard so stale-prior data cannot deadlock refresh.
    provisional = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_parameters": {"soak_duration_seconds": soak},
        "steps": results,
        "ready_for_10": non_score_pass,
        "ready_for_100": non_score_pass,
        "ready_for_1000": non_score_pass,
        "all_pass": non_score_pass,
    }
    (ROOT / "eval" / "gate_run_snapshot.json").write_text(json.dumps(provisional, indent=2, sort_keys=True), encoding="utf-8")

    real_user = _run("real_user_rollout_gate", [py, "eval/real_user_rollout_gate.py"], 180)
    results.append(real_user)
    real_user_payload = _json_from_stdout(real_user)
    real_user_rollout = {
        "ready_for_10_controlled_beta": bool(real_user_payload.get("ready_for_10_controlled_beta")),
        "infrastructure_ready_for_100": bool(real_user_payload.get("infrastructure_ready_for_100")),
        "ready_for_100_real_users": bool(real_user_payload.get("ready_for_100_real_users")),
        "max_recommended_real_users_now": real_user_payload.get("max_recommended_real_users_now", 0),
        "blockers": real_user_payload.get("blockers") or ["real-user rollout gate did not return machine-readable blockers"],
        "rc": real_user["rc"],
    }

    scoreboard = _run("scoreboard_final", [py, "eval/uat_scoreboard.py", "--synthetic-only"], 180)
    results.append(scoreboard)
    scoreboard_snapshot = json.loads((ROOT / "eval" / "uat_scoreboard_snapshot.json").read_text(encoding="utf-8")) if (ROOT / "eval" / "uat_scoreboard_snapshot.json").exists() else {}
    ready_for_10 = bool(scoreboard_snapshot.get("ready_for_10"))
    ready_for_100 = bool(scoreboard_snapshot.get("ready_for_100"))
    ready_for_1000 = bool(scoreboard_snapshot.get("ready_for_1000"))
    synthetic_load_all_pass = non_score_pass and scoreboard["rc"] == 0 and ready_for_1000
    overall_100_real_user_pass = synthetic_load_all_pass and real_user_rollout["ready_for_100_real_users"]
    final = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_parameters": {"soak_duration_seconds": soak},
        "steps": results,
        "ready_for_10": ready_for_10,
        "ready_for_100": ready_for_100,
        "ready_for_1000": ready_for_1000,
        "synthetic_load_all_pass": synthetic_load_all_pass,
        "real_user_rollout": real_user_rollout,
        "ready_for_100_real_users": real_user_rollout["ready_for_100_real_users"],
        "overall_100_real_user_pass": overall_100_real_user_pass,
        "all_pass": overall_100_real_user_pass,
    }
    (ROOT / "eval" / "gate_run_snapshot.json").write_text(json.dumps(final, indent=2, sort_keys=True), encoding="utf-8")
    _write_decision(final)
    # Final scoreboard refresh after canonical decision docs exist.
    final_scoreboard = _run("scoreboard_after_decision", [py, "eval/uat_scoreboard.py", "--synthetic-only"], 180)
    final["steps"].append(final_scoreboard)
    (ROOT / "eval" / "gate_run_snapshot.json").write_text(json.dumps(final, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "ready_for_10_logical_load": ready_for_10,
        "ready_for_100_logical_load": ready_for_100,
        "ready_for_1000_logical_load": ready_for_1000,
        "synthetic_load_all_pass": synthetic_load_all_pass,
        "ready_for_10_controlled_real_users": real_user_rollout["ready_for_10_controlled_beta"],
        "ready_for_100_real_external_users": real_user_rollout["ready_for_100_real_users"],
        "max_recommended_real_users_now": real_user_rollout["max_recommended_real_users_now"],
        "overall_100_real_user_pass": overall_100_real_user_pass,
        "exit_mode": "synthetic_only" if args.synthetic_only else "full_real_user_readiness",
        "blockers": real_user_rollout["blockers"],
    }, indent=2))
    return 0 if (synthetic_load_all_pass if args.synthetic_only else overall_100_real_user_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
