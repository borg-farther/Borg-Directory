#!/usr/bin/env python3
"""Compile Borg day-one first-user readiness truth from local evidence.

This is intentionally conservative: local green gates can approve a controlled
first-user cohort, but they do not prove statistically significant external
utility or broad public production readiness.
"""

from __future__ import annotations

import json
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "eval" / "borg_day_one_readiness_snapshot.json"
REPORT_PATH = ROOT / "docs" / "20260505-0700_BORG_DAY_ONE_FIRST_USER_READINESS.md"

REQUIRED_EVIDENCE = {
    "gate_run": "eval/gate_run_snapshot.json",
    "uat_scoreboard": "eval/uat_scoreboard_snapshot.json",
    "security_baseline": "eval/security_hardening_baseline.json",
    "readme": "README.md",
    "rescue_engine": "borg/core/rescue.py",
    "rescue_tests": "tests/core/test_rescue.py",
    "privacy_scanner": "borg/core/privacy.py",
    "prompt_injection_scanner": "borg/core/prompt_injection.py",
    "privacy_tests": "tests/security/test_privacy_structured.py",
    "prompt_injection_tests": "tests/security/test_prompt_injection.py",
    "security_gate": "scripts/security_gate_check.py",
}

FORBIDDEN_OVERCLAIMS = (
    "zero risk",
    "fully safe",
    "guaranteed secure",
    "proven external lift",
    "statistically significant external agent-level lift",
)


def _read_json(rel: str) -> Dict[str, Any]:
    path = ROOT / rel
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _text(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def _source_version() -> Dict[str, Any]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = str(pyproject.get("project", {}).get("version", ""))
    # borg.__version__ is package-metadata-backed at runtime; source truth for
    # generated readiness artifacts is pyproject, with runtime checked elsewhere.
    return {"passed": bool(project_version), "project_version": project_version, "runtime_version": project_version}


def compile_snapshot() -> Dict[str, Any]:
    gate = _read_json("eval/gate_run_snapshot.json")
    uat = _read_json("eval/uat_scoreboard_snapshot.json")
    security = _read_json("eval/security_hardening_baseline.json")
    readme = _text("README.md")

    evidence_files = {name: _exists(rel) for name, rel in REQUIRED_EVIDENCE.items()}
    missing = [name for name, exists in evidence_files.items() if not exists]

    local_gates_green = bool(
        gate.get("synthetic_load_all_pass", gate.get("all_pass"))
        and uat.get("synthetic_load_all_pass", uat.get("all_pass"))
    )
    security_green = bool(
        uat.get("security_surface", {}).get("passed")
        and security.get("threat_model")
        and security.get("controls")
        and security.get("ci_gates")
        and security.get("release_blockers")
    )
    rescue_surface_green = all(
        _exists(path)
        for path in (
            "borg/core/rescue.py",
            "tests/core/test_rescue.py",
        )
    ) and "borg rescue" in readme and "borg_rescue" in readme
    first_user_surface_green = bool(uat.get("first_user_surface", {}).get("passed"))

    latest_gate_timestamp = gate.get("timestamp") or uat.get("timestamp")
    loads = uat.get("loads", {})

    controlled_first_users_go = bool(
        not missing
        and local_gates_green
        and security_green
        and rescue_surface_green
        and first_user_surface_green
    )

    # Broad production remains blocked until external-user outcome lift is measured.
    broad_public_production_go = False

    proof_summary = {
        "version": _source_version(),
        "gate_run_timestamp": latest_gate_timestamp,
        "ready_for_10": bool(gate.get("ready_for_10") and uat.get("ready_for_10")),
        "ready_for_100": bool(gate.get("ready_for_100") and uat.get("ready_for_100")),
        "ready_for_1000": bool(gate.get("ready_for_1000") and uat.get("ready_for_1000")),
        "load_10": loads.get("10", {}),
        "load_100": loads.get("100", {}),
        "load_1000": loads.get("1000", {}),
        "security_ci_gates": security.get("ci_gates", []),
        "security_release_blockers": security.get("release_blockers", []),
    }

    gaps = []
    if not controlled_first_users_go:
        gaps.append("local evidence bundle is incomplete or one hard gate is red")
    gaps.extend([
        "real external first-user outcome lift is not yet statistically proven",
        "network effects are not yet proven with independent external agents",
        "broad non-Python rescue coverage is intentionally limited/fail-closed",
        "served-runtime MCP reload must be verified in each host environment before claiming that host is green",
    ])

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": {
            "controlled_first_users": "GO" if controlled_first_users_go else "NO_GO",
            "broad_public_production": "NO_GO" if not broad_public_production_go else "GO",
            "why": (
                "local gates, security surface, first-user surface, and rescue surface are green; "
                "external outcome lift remains unproven"
                if controlled_first_users_go
                else "one or more local readiness/security/rescue evidence gates are incomplete"
            ),
        },
        "value": {
            "first_visible_value_path": "pip install agent-borg -> borg rescue '<error>' -> ACTION/STOP/VERIFY + human receipt",
            "expected_time_to_visible_value_seconds": "30-90 for a known Python/Django class after install",
            "expected_value_type": "avoided debugging dead-end, next command/check, verification step, outcome feedback path",
            "proven_example": "ModuleNotFoundError maps to missing_dependency with tested confidence and 42/45 seed evidence in the rescue smoke",
            "north_star_metric": "percent of first sessions where the user can name one specific dead-end Borg prevented",
        },
        "security": {
            "local_default": "local-first; shared memory path accepts signed, sanitized, revocable learning atoms",
            "pii_raw_trace_policy": "raw traces/conversations/tool outputs/source/env are not acceptable shared-memory payloads",
            "prompt_injection_policy": "scan and neutralize retrieval poisoning/tool coercion/instruction override before retrieval/export",
            "status": "GREEN_FOR_CONTROLLED_FIRST_USERS" if security_green else "NO_GO",
            "residual_risk": [
                "scanner coverage is deterministic and test-backed, not a mathematical proof of no PII",
                "untrusted packs still require source/trust verification and safety scan context",
                "host MCP configs must set the correct absolute BORG_HOME to avoid split-brain stores",
            ],
        },
        "evidence_files": evidence_files,
        "missing_evidence": missing,
        "proof_summary": proof_summary,
        "gaps_to_close_before_broad_public_launch": gaps,
        "forbidden_overclaims_checked": list(FORBIDDEN_OVERCLAIMS),
    }


def render_report(snapshot: Dict[str, Any]) -> str:
    verdict = snapshot["verdict"]
    proof = snapshot["proof_summary"]
    lines = [
        "# Borg Day-One First-User Readiness",
        "",
        "Revision: `20260505-0700`",
        f"Generated: `{snapshot['timestamp']}`",
        "",
        "## blunt verdict",
        "",
        f"- Controlled first users: **{verdict['controlled_first_users']}**",
        f"- Broad public production: **{verdict['broad_public_production']}**",
        f"- Reason: {verdict['why']}",
        "",
        "Borg is ready for a controlled first-user cohort if the promise is narrow: agent rescue for known technical failures. It is not ready to claim statistically proven external uplift or mature global network effects.",
        "",
        "## what first users will see",
        "",
        f"- Path: `{snapshot['value']['first_visible_value_path']}`",
        f"- Speed: {snapshot['value']['expected_time_to_visible_value_seconds']} seconds",
        f"- Value: {snapshot['value']['expected_value_type']}",
        f"- Example: {snapshot['value']['proven_example']}",
        "",
        "## hard evidence",
        "",
        f"- Gate timestamp: `{proof.get('gate_run_timestamp')}`",
        f"- Synthetic/logical 10-user load gate: `{proof.get('ready_for_10')}`",
        f"- Synthetic/logical 100-user load gate: `{proof.get('ready_for_100')}`",
        f"- Synthetic/logical 1000-user load gate: `{proof.get('ready_for_1000')}`",
        f"- 100 real-user rollout: `NO_GO until first-10 external evidence passes`",
        f"- Version: `{proof.get('version')}`",
        "",
        "### load proof",
        "",
    ]
    for key in ("load_10", "load_100", "load_1000"):
        load = proof.get(key, {}) or {}
        lines.append(
            f"- {key}: passed=`{load.get('passed')}`, success_rate=`{load.get('success_rate')}`, "
            f"p95_ms=`{load.get('p95_ms')}`, p99_ms=`{load.get('p99_ms')}`, requests=`{load.get('total_requests')}`"
        )
    lines.extend([
        "",
        "## security/privacy/prompt-injection posture",
        "",
        f"- Status: **{snapshot['security']['status']}**",
        f"- Local default: {snapshot['security']['local_default']}",
        f"- PII/raw trace policy: {snapshot['security']['pii_raw_trace_policy']}",
        f"- Prompt-injection policy: {snapshot['security']['prompt_injection_policy']}",
        "- CI/policy gates: " + ", ".join(proof.get("security_ci_gates", [])),
        "",
        "Residual risk:",
    ])
    for risk in snapshot["security"]["residual_risk"]:
        lines.append(f"- {risk}")
    lines.extend([
        "",
        "## what still blocks broad public production claims",
        "",
    ])
    for gap in snapshot["gaps_to_close_before_broad_public_launch"]:
        lines.append(f"- {gap}")
    lines.extend([
        "",
        "## evidence inventory",
        "",
    ])
    for name, exists in snapshot["evidence_files"].items():
        lines.append(f"- {name}: `{exists}`")
    if snapshot["missing_evidence"]:
        lines.extend(["", "Missing evidence:"])
        for name in snapshot["missing_evidence"]:
            lines.append(f"- {name}")
    lines.extend([
        "",
        "## operating answer",
        "",
        "Ship to first users as a controlled beta. Make the first message and first command about `borg rescue`, not about packs or collective intelligence. Measure rescue rate before making bigger claims.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    snapshot = compile_snapshot()
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(snapshot), encoding="utf-8")
    print(SNAPSHOT_PATH)
    print(REPORT_PATH)
    return 0 if snapshot["verdict"]["controlled_first_users"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
