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
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.first_10_evidence import evaluate_scoreboard
from eval import public_self_serve_launch_gate as public_gate

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


def _public_package_ready() -> dict[str, Any]:
    version = _version_consistent().get("project_version") or public_gate.source_version()
    pypi_latest = public_gate.pypi_latest_check(str(version), fetch_network=True)
    pypi_fresh = public_gate.pypi_fresh_install_check(ROOT / "eval" / "pypi_fresh_install_snapshot.json", str(version))
    blockers: list[str] = []
    if not pypi_latest.get("passed"):
        blockers.append("PyPI latest/fresh-install package evidence is not green: latest metadata does not match source version")
    if not pypi_fresh.get("passed"):
        blockers.append("PyPI latest/fresh-install package evidence is not green: fresh install + MCP stdio canary is not green")
    return {
        "passed": bool(pypi_latest.get("passed") and pypi_fresh.get("passed")),
        "pypi_latest": pypi_latest,
        "pypi_fresh_install_and_mcp_stdio": pypi_fresh,
        "blockers": blockers,
    }


def _first_10_evidence() -> dict[str, Any]:
    data = _read_json(ROOT / "eval" / "first_10_user_scoreboard.json")
    if not data:
        return {
            "exists": False,
            "verified_external_users": 0,
            "real_users": 0,
            "install_successes": 0,
            "useful_rescue_moments": 0,
            "critical_privacy_security_failures": 0,
            "required_total_real_users": 10,
            "required_install_successes": 8,
            "required_useful_rescue_moments": 6,
            "max_critical_privacy_security_failures": 0,
            "scoreboard_gate": None,
            "scoreboard_reason": "scoreboard missing",
            "row_count": 0,
            "invalid_rows": [],
            "stored_consistency": {"passed": False, "mismatches": [{"field": "file", "expected": "present", "actual": "missing"}]},
            "passed": False,
        }

    evidence = evaluate_scoreboard(data)
    derived = evidence["derived_counts"]
    thresholds = evidence["thresholds"]
    verdict = data.get("current_verdict") or {}
    passed = bool(
        evidence["schema_valid"]
        and evidence["thresholds_passed"]
        and evidence["stored_consistency"]["passed"]
    )
    return {
        "exists": True,
        "verified_external_users": derived["verified_external_users"],
        "real_users": derived["real_users"],
        "install_successes": derived["install_successes"],
        "useful_rescue_moments": derived["useful_rescue_moments"],
        "critical_privacy_security_failures": derived["critical_privacy_security_failures"],
        "required_total_real_users": thresholds["required_total_real_users"],
        "required_install_successes": thresholds["required_install_successes"],
        "required_useful_rescue_moments": thresholds["required_useful_rescue_moments"],
        "max_critical_privacy_security_failures": thresholds["max_critical_privacy_security_failures"],
        "scoreboard_gate": verdict.get("public_self_serve_launch_gate"),
        "scoreboard_reason": verdict.get("reason"),
        "row_count": evidence["row_count"],
        "counted_external_rows": evidence["counted_external_rows"],
        "invalid_rows": evidence["invalid_rows"],
        "stored_consistency": evidence["stored_consistency"],
        "row_level_blockers": evidence["blockers"],
        "passed": passed,
    }


def compile_rollout_gate() -> dict[str, Any]:
    version = _version_consistent()
    security = _security_ready()
    first_user = _first_user_release_ready()
    package = _public_package_ready()
    load_10 = _load_ready(10)
    load_100 = _load_ready(100)
    first_10 = _first_10_evidence()
    local_infra_ready_for_10 = all([
        version["passed"],
        security["passed"],
        first_user["passed"],
        load_10["passed"],
    ])
    ready_for_10_controlled_beta = bool(local_infra_ready_for_10 and package["passed"])
    infrastructure_ready_for_100 = bool(ready_for_10_controlled_beta and load_100["passed"])
    ready_for_100_real_users = infrastructure_ready_for_100 and first_10["passed"]
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
    if not package["passed"]:
        blockers.extend(package.get("blockers") or ["public PyPI package/fresh-install evidence is not green"])
    if not first_10["passed"]:
        row_blockers = first_10.get("row_level_blockers") or []
        if row_blockers:
            blockers.extend(str(blocker) for blocker in row_blockers)
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
        "public_package_gate": package,
        "load_gates": {"10": load_10, "100": load_100},
        "first_10_external_evidence": first_10,
        "local_infrastructure_ready_for_10": local_infra_ready_for_10,
        "ready_for_10_controlled_beta": ready_for_10_controlled_beta,
        "infrastructure_ready_for_100": infrastructure_ready_for_100,
        "ready_for_100_real_users": ready_for_100_real_users,
        "max_recommended_real_users_now": max_recommended_real_users_now,
        "blockers": list(dict.fromkeys(blockers)),
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
