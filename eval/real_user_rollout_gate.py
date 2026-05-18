#!/usr/bin/env python3
"""Compile Borg real-user rollout readiness.

This gate exists to prevent confusing synthetic/load readiness with real-user
production readiness. Load tests can say Borg handles 100/1000 logical users,
but real-user rollout must be gated by first-10 external evidence.
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "eval" / "real_user_rollout_gate_snapshot.json"
REPORT = ROOT / "docs" / "20260517_BORG_100_REAL_USER_READINESS.md"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _version_consistent() -> dict[str, Any]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = pyproject.get("project", {}).get("version", "")
    init_text = (ROOT / "borg" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    runtime_version = match.group(1) if match else ""
    return {
        "project_version": project_version,
        "runtime_version": runtime_version,
        "passed": bool(project_version and project_version == runtime_version),
    }


def _security_ready() -> dict[str, Any]:
    required = [
        "eval/security_hardening_baseline.json",
        "docs/SECURITY_HARDENING_BASELINE.md",
        "docs/PRIVACY_MODEL.md",
        "docs/PROMPT_INJECTION_THREAT_MODEL.md",
        "scripts/security_gate_check.py",
        ".github/workflows/security-gates.yml",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    return {"passed": not missing, "missing": missing, "required": required}


def _first_user_release_ready() -> dict[str, Any]:
    snap = _read_json(ROOT / "eval" / "first_user_release_gate_snapshot.json")
    results = snap.get("results") or []
    failures = [r.get("name") for r in results if not r.get("passed")]
    return {
        "exists": bool(snap),
        "passed": bool(snap.get("success")) and not failures,
        "generated_at_utc": snap.get("generated_at_utc"),
        "passed_count": sum(1 for r in results if r.get("passed")),
        "failed_count": len(failures),
        "failures": failures,
    }


def _load_ready(users: int) -> dict[str, Any]:
    snap = _read_json(ROOT / "eval" / f"load_{users}_snapshot.json")
    return {
        "exists": bool(snap),
        "passed": bool(snap.get("passed")),
        "users": snap.get("users"),
        "success_rate": snap.get("success_rate"),
        "duration_seconds": snap.get("duration_seconds"),
        "latency_ms": snap.get("latency_ms"),
    }


def _first_10_evidence() -> dict[str, Any]:
    data = _read_json(ROOT / "eval" / "first_10_user_scoreboard.json")
    counts = data.get("current_counts") or {}
    truth = data.get("truth_policy") or {}
    thresholds = data.get("thresholds") or {}
    verdict = data.get("current_verdict") or {}
    verified = int(truth.get("verified_external_users") or 0)
    real_users = int(counts.get("real_users") or 0)
    installs = int(counts.get("install_successes") or 0)
    useful = int(counts.get("useful_rescue_moments") or 0)
    incidents = int(counts.get("critical_privacy_security_failures") or 0)
    required_users = int(thresholds.get("required_total_real_users") or 10)
    required_installs = int(thresholds.get("min_install_successes_for_public_self_serve") or 8)
    required_useful = int(thresholds.get("min_useful_rescue_moments_for_public_self_serve") or 6)
    max_incidents = int(thresholds.get("max_critical_privacy_security_failures") or 0)
    first_10_passed = (
        verified >= required_users
        and real_users >= required_users
        and installs >= required_installs
        and useful >= required_useful
        and incidents <= max_incidents
    )
    return {
        "exists": bool(data),
        "verified_external_users": verified,
        "real_users": real_users,
        "install_successes": installs,
        "useful_rescue_moments": useful,
        "critical_privacy_security_failures": incidents,
        "required_total_real_users": required_users,
        "required_install_successes": required_installs,
        "required_useful_rescue_moments": required_useful,
        "max_critical_privacy_security_failures": max_incidents,
        "scoreboard_gate": verdict.get("public_self_serve_launch_gate"),
        "scoreboard_reason": verdict.get("reason"),
        "passed": first_10_passed,
    }


def compile_rollout_gate() -> dict[str, Any]:
    version = _version_consistent()
    security = _security_ready()
    first_user = _first_user_release_ready()
    load_10 = _load_ready(10)
    load_100 = _load_ready(100)
    first_10 = _first_10_evidence()
    infra_ready_for_10 = all([
        version["passed"],
        security["passed"],
        first_user["passed"],
        load_10["passed"],
    ])
    infra_ready_for_100 = infra_ready_for_10 and load_100["passed"]
    ready_for_10_controlled_beta = infra_ready_for_10
    ready_for_100_real_users = infra_ready_for_100 and first_10["passed"]
    max_recommended_real_users_now = 0
    if ready_for_100_real_users:
        max_recommended_real_users_now = 100
    elif ready_for_10_controlled_beta:
        max_recommended_real_users_now = 10

    blockers: list[str] = []
    if not version["passed"]:
        blockers.append("source version mismatch between pyproject.toml and borg/__init__.py")
    if not security["passed"]:
        blockers.append("security baseline files missing: " + ", ".join(security["missing"]))
    if not first_user["passed"]:
        blockers.append("first-user release gate is not green")
    if not load_10["passed"]:
        blockers.append("10-user load gate is not green")
    if not load_100["passed"]:
        blockers.append("100-user load gate is not green")
    if not first_10["passed"]:
        blockers.append(
            "first-10 external-user evidence has not passed: "
            f"verified={first_10['verified_external_users']}/{first_10['required_total_real_users']}, "
            f"real_users={first_10['real_users']}/{first_10['required_total_real_users']}, "
            f"installs={first_10['install_successes']}/{first_10['required_install_successes']}, "
            f"useful={first_10['useful_rescue_moments']}/{first_10['required_useful_rescue_moments']}, "
            f"critical_incidents={first_10['critical_privacy_security_failures']}/{first_10['max_critical_privacy_security_failures']}"
        )

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "gate_type": "real_user_rollout",
        "important_distinction": "load/readiness snapshots are synthetic/logical users; this gate controls real external-user rollout",
        "version": version,
        "security": security,
        "first_user_release_gate": first_user,
        "load_gates": {"10": load_10, "100": load_100},
        "first_10_external_evidence": first_10,
        "ready_for_10_controlled_beta": ready_for_10_controlled_beta,
        "infrastructure_ready_for_100": infra_ready_for_100,
        "ready_for_100_real_users": ready_for_100_real_users,
        "max_recommended_real_users_now": max_recommended_real_users_now,
        "blockers": blockers,
        "no_fake_user_policy": "Do not mark first-10 complete or 100-real-user ready without consented external evidence rows.",
    }


def write_report(snapshot: dict[str, Any]) -> None:
    verdict = "GO" if snapshot["ready_for_100_real_users"] else "NO-GO"
    lines = [
        "# Borg 100 real-user readiness",
        "",
        f"Generated: {snapshot['generated_at_utc']}",
        "",
        f"100 real-user verdict: **{verdict}**",
        f"Max recommended real users now: **{snapshot['max_recommended_real_users_now']}**",
        "",
        "## Distinction",
        "",
        "Synthetic/logical load tests prove throughput mechanics. They do not prove real external-user readiness.",
        "Real-user rollout requires first-10 external evidence before expanding to 100.",
        "",
        "## Current gates",
        "",
        f"- ready_for_10_controlled_beta: `{snapshot['ready_for_10_controlled_beta']}`",
        f"- infrastructure_ready_for_100: `{snapshot['infrastructure_ready_for_100']}`",
        f"- ready_for_100_real_users: `{snapshot['ready_for_100_real_users']}`",
        "",
        "## First-10 evidence",
        "",
    ]
    first_10 = snapshot["first_10_external_evidence"]
    for key in [
        "verified_external_users",
        "real_users",
        "install_successes",
        "useful_rescue_moments",
        "critical_privacy_security_failures",
        "scoreboard_gate",
        "scoreboard_reason",
    ]:
        lines.append(f"- {key}: `{first_10.get(key)}`")
    lines.extend(["", "## Blockers", ""])
    if snapshot["blockers"]:
        lines.extend(f"- {b}" for b in snapshot["blockers"])
    else:
        lines.append("None.")
    lines.extend([
        "",
        "## Required action to unlock 100 real users",
        "",
        "1. Run 10 consented external users through the published PyPI path.",
        "2. Record evidence rows in `eval/first_10_user_scoreboard.json`.",
        "3. Require at least 8 install successes, 6 useful rescue moments, and 0 critical privacy/security incidents.",
        "4. Rerun `python eval/real_user_rollout_gate.py`; only a green gate authorizes 100 real users.",
        "",
        "Machine snapshot: `eval/real_user_rollout_gate_snapshot.json`",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    snapshot = compile_rollout_gate()
    SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    write_report(snapshot)
    print(json.dumps({
        "ready_for_10_controlled_beta": snapshot["ready_for_10_controlled_beta"],
        "infrastructure_ready_for_100": snapshot["infrastructure_ready_for_100"],
        "ready_for_100_real_users": snapshot["ready_for_100_real_users"],
        "max_recommended_real_users_now": snapshot["max_recommended_real_users_now"],
        "blockers": snapshot["blockers"],
        "snapshot": str(SNAPSHOT.relative_to(ROOT)),
        "report": str(REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0 if snapshot["ready_for_100_real_users"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
