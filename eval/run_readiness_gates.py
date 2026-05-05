#!/usr/bin/env python3
"""Run Borg production readiness gates through 1000 concurrent users."""
from __future__ import annotations

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
        lines.append(f"- {step['name']}: {'PASS' if step['rc'] == 0 else 'FAIL'} (rc={step['rc']})")
    lines.extend([
        "",
        "## Rollout",
        "",
        f"- Ready for 10 users: {'GO' if snapshot['ready_for_10'] else 'NO-GO'}",
        f"- Ready for 100 users: {'GO' if snapshot['ready_for_100'] else 'NO-GO'}",
        f"- Ready for 1000 users: {'GO' if snapshot['ready_for_1000'] else 'NO-GO'}",
        "",
        "Snapshot: `eval/gate_run_snapshot.json`",
        "",
    ])
    (ROOT / "GO_NO_GO_DECISION.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "UAT_RESULTS.md").write_text(
        "\n".join([
            "# Borg UAT Results",
            "",
            f"Timestamp: `{snapshot['timestamp']}`",
            "",
            "Final GO/NO-GO is always sourced from `GO_NO_GO_DECISION.md`, `PROJECT_STATUS.md`, and `eval/gate_run_snapshot.json`.",
            "",
            f"READY_FOR_10: `{snapshot['ready_for_10']}`",
            f"READY_FOR_100: `{snapshot['ready_for_100']}`",
            f"READY_FOR_1000: `{snapshot['ready_for_1000']}`",
            "",
        ]),
        encoding="utf-8",
    )


def main() -> int:
    soak = float(os.getenv("BORG_READINESS_SOAK_SECONDS", "30"))
    py = sys.executable
    steps = [
        ("version_distribution_tests", [py, "-m", "pytest", "-q", "borg/tests/test_version_consistency.py", "borg/tests/test_distribution_readiness.py", "borg/tests/test_runtime_doctor.py"], 300),
        ("atom_security_tests", [py, "-m", "pytest", "-q", "borg/tests/test_atom_tenant.py", "borg/tests/test_atom_policy.py", "borg/tests/test_learning_atoms.py", "borg/tests/test_atom_store.py", "borg/tests/test_atom_retrieval_firewall.py", "borg/tests/test_learning_atom_publish.py", "borg/tests/test_cli_atom.py", "borg/tests/test_privacy_structured.py", "borg/tests/test_prompt_injection.py", "borg/tests/test_privacy.py"], 600),
        ("security_gate", [py, "scripts/security_gate_check.py"], 120),
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

    scoreboard = _run("scoreboard_final", [py, "eval/uat_scoreboard.py"], 180)
    results.append(scoreboard)
    scoreboard_snapshot = json.loads((ROOT / "eval" / "uat_scoreboard_snapshot.json").read_text(encoding="utf-8")) if (ROOT / "eval" / "uat_scoreboard_snapshot.json").exists() else {}
    ready_for_10 = bool(scoreboard_snapshot.get("ready_for_10"))
    ready_for_100 = bool(scoreboard_snapshot.get("ready_for_100"))
    ready_for_1000 = bool(scoreboard_snapshot.get("ready_for_1000"))
    all_pass = non_score_pass and scoreboard["rc"] == 0 and ready_for_1000
    final = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_parameters": {"soak_duration_seconds": soak},
        "steps": results,
        "ready_for_10": ready_for_10,
        "ready_for_100": ready_for_100,
        "ready_for_1000": ready_for_1000,
        "all_pass": all_pass,
    }
    (ROOT / "eval" / "gate_run_snapshot.json").write_text(json.dumps(final, indent=2, sort_keys=True), encoding="utf-8")
    _write_decision(final)
    # Final scoreboard refresh after canonical decision docs exist.
    final_scoreboard = _run("scoreboard_after_decision", [py, "eval/uat_scoreboard.py"], 180)
    final["steps"].append(final_scoreboard)
    (ROOT / "eval" / "gate_run_snapshot.json").write_text(json.dumps(final, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ready_for_10": ready_for_10, "ready_for_100": ready_for_100, "ready_for_1000": ready_for_1000, "all_pass": all_pass}, indent=2))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
