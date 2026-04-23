#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PLACEHOLDER_MARKERS = ("todo", "tbd", "placeholder", "lorem ipsum", "coming soon")


@dataclass
class CheckResult:
    id: str
    severity: str
    passed: bool
    detail: str
    evidence: list[str]


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def add_check(
    checks: list[CheckResult],
    check_id: str,
    severity: str,
    passed: bool,
    detail: str,
    evidence: list[str],
) -> None:
    checks.append(
        CheckResult(
            id=check_id,
            severity=severity,
            passed=bool(passed),
            detail=detail,
            evidence=evidence,
        )
    )


def bool_str(value: bool) -> str:
    return "PASS" if value else "FAIL"


def main() -> int:
    repo = Path(os.getenv("BORG_REPO_ROOT", "/root/hermes-workspace/borg")).resolve()
    eval_dir = repo / "eval"

    timestamp = now_utc_iso()
    checks: list[CheckResult] = []
    warnings: list[str] = []

    # 1) Git home cutover
    git_config_path = repo / ".git" / "config"
    cfg = read_text(git_config_path)
    origin_ok = "url = https://github.com/borg-farther/Borg-Directory.git" in cfg
    legacy_remote_present = '[remote "legacy"]' in cfg
    legacy_push_disabled = "pushurl = DISABLED_LEGACY_BACKUP_REMOTE" in cfg
    add_check(
        checks,
        "git-home-cutover",
        "critical",
        origin_ok and not legacy_remote_present,
        (
            f"origin_ok={origin_ok}, legacy_remote_present={legacy_remote_present}, "
            f"legacy_push_disabled={legacy_push_disabled}"
        ),
        [str(git_config_path.relative_to(repo))],
    )

    # 2) Governance enforcement
    governance_path = eval_dir / "new_home_governance_enforcement.json"
    governance = read_json(governance_path)
    gov_ok = bool(governance.get("success") is True)
    add_check(
        checks,
        "governance-enforcement",
        "critical",
        gov_ok,
        f"success={governance.get('success')}",
        [str(governance_path.relative_to(repo))],
    )

    # 3) Readiness contract
    readiness_path = eval_dir / "new_home_readiness_report.json"
    readiness = read_json(readiness_path)
    readiness_ok = (
        readiness.get("overall_status") == "pass"
        and readiness.get("operational_ready") is True
    )
    sync_status = str(readiness.get("sync_status", "unknown"))
    if sync_status != "pass":
        warnings.append(f"sync_status={sync_status}")
    add_check(
        checks,
        "readiness-contract",
        "critical",
        readiness_ok,
        (
            f"overall_status={readiness.get('overall_status')}, "
            f"operational_ready={readiness.get('operational_ready')}, "
            f"sync_status={sync_status}"
        ),
        [str(readiness_path.relative_to(repo))],
    )

    # 4) Test gate
    test_gate_path = eval_dir / "new_home_test_gate_report.json"
    test_gate = read_json(test_gate_path)
    pytest_rc = int(test_gate.get("pytest_rc", 1))
    test_gate_ok = test_gate.get("status") == "pass" and pytest_rc == 0
    add_check(
        checks,
        "test-gate",
        "critical",
        test_gate_ok,
        (
            f"status={test_gate.get('status')}, pytest_rc={pytest_rc}, "
            f"summary={test_gate.get('pytest_summary', '')}"
        ),
        [str(test_gate_path.relative_to(repo))],
    )

    # 5) Scale gates
    scoreboard_path = eval_dir / "uat_scoreboard_snapshot.json"
    scoreboard = read_json(scoreboard_path)
    gates = dict(scoreboard.get("gates", {}))
    scale_ok = all(
        gates.get(key) is True
        for key in ("ready_for_10", "ready_for_100", "ready_for_1000", "all_pass")
    )
    add_check(
        checks,
        "scale-gates",
        "critical",
        scale_ok,
        (
            f"ready_for_10={gates.get('ready_for_10')}, "
            f"ready_for_100={gates.get('ready_for_100')}, "
            f"ready_for_1000={gates.get('ready_for_1000')}, all_pass={gates.get('all_pass')}"
        ),
        [str(scoreboard_path.relative_to(repo))],
    )

    # 6) Utility and savings
    packet_path = eval_dir / "experiment_packet.json"
    packet = read_json(packet_path)
    metrics = dict(packet.get("metrics", {}))
    control_completion = float(metrics.get("control_completion_rate", 0.0))
    treatment_completion = float(metrics.get("treatment_completion_rate", 0.0))
    success_lift = float(metrics.get("success_lift", treatment_completion - control_completion))
    control_tokens = float(metrics.get("control_tokens_mean", 0.0))
    treatment_tokens = float(metrics.get("treatment_tokens_mean", 0.0))

    utility_ok = (
        success_lift >= 0.05
        and treatment_completion > control_completion
        and treatment_tokens < control_tokens
    )
    add_check(
        checks,
        "utility-and-savings",
        "critical",
        utility_ok,
        (
            f"success_lift={success_lift:.4f}, control_completion={control_completion:.4f}, "
            f"treatment_completion={treatment_completion:.4f}, "
            f"control_tokens_mean={control_tokens:.2f}, treatment_tokens_mean={treatment_tokens:.2f}"
        ),
        [str(packet_path.relative_to(repo))],
    )

    # 7) Anti-theater artifact quality
    required_artifacts = [
        repo / "docs" / "20260422-0909_NEW_HOME_PRODUCTION_CLOSURE.md",
        eval_dir / "gate_run_snapshot.json",
        eval_dir / "experiment_packet.json",
        eval_dir / "uat_scoreboard_snapshot.json",
        eval_dir / "new_home_readiness_report.json",
        eval_dir / "new_home_test_gate_report.json",
    ]

    artifact_report: list[dict[str, Any]] = []
    anti_theater_ok = True
    for path in required_artifacts:
        entry: dict[str, Any] = {
            "path": str(path.relative_to(repo)),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "placeholder_markers": [],
            "sha256": None,
        }
        if not path.exists() or entry["size_bytes"] == 0:
            anti_theater_ok = False
        else:
            text = read_text(path)
            lowered = text.lower()
            markers = [m for m in PLACEHOLDER_MARKERS if m in lowered]
            entry["placeholder_markers"] = markers
            entry["sha256"] = sha256_text(text)
            if markers:
                anti_theater_ok = False
        artifact_report.append(entry)

    add_check(
        checks,
        "anti-theater-artifacts",
        "high",
        anti_theater_ok,
        "all required artifacts exist, are non-empty, and contain no placeholder markers",
        [a["path"] for a in artifact_report],
    )

    # 8) Legacy access warning accounting
    readiness_warnings = readiness.get("warnings", [])
    legacy_warning_present = any(
        "legacy_repo_not_accessible_from_current_token" in str(w) for w in readiness_warnings
    )
    add_check(
        checks,
        "legacy-access-warning",
        "warning",
        True,
        (
            "legacy warning present and recorded" if legacy_warning_present
            else "no legacy access warning reported"
        ),
        [str(readiness_path.relative_to(repo))],
    )

    critical_failed = [c for c in checks if c.severity == "critical" and not c.passed]
    high_failed = [c for c in checks if c.severity == "high" and not c.passed]
    overall_status = "pass" if not critical_failed and not high_failed else "fail"
    decision = "GO" if overall_status == "pass" else "NO-GO"

    snapshot = {
        "timestamp_utc": timestamp,
        "plan_id": "borg-google-tier-uat-20260422",
        "overall_status": overall_status,
        "decision": decision,
        "summary": {
            "total_checks": len(checks),
            "critical_failed": len(critical_failed),
            "high_failed": len(high_failed),
            "warnings_count": len(warnings),
        },
        "checks": [asdict(c) for c in checks],
        "warnings": warnings,
        "artifact_quality": artifact_report,
        "metrics": {
            "success_lift": success_lift,
            "control_completion_rate": control_completion,
            "treatment_completion_rate": treatment_completion,
            "control_tokens_mean": control_tokens,
            "treatment_tokens_mean": treatment_tokens,
        },
        "sources": {
            "git_config": str(git_config_path.relative_to(repo)),
            "governance": str(governance_path.relative_to(repo)),
            "readiness": str(readiness_path.relative_to(repo)),
            "test_gate": str(test_gate_path.relative_to(repo)),
            "scoreboard": str(scoreboard_path.relative_to(repo)),
            "experiment_packet": str(packet_path.relative_to(repo)),
        },
    }

    snapshot_path = eval_dir / "google_tier_uat_snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    scoreboard_out = {
        "timestamp_utc": timestamp,
        "overall_status": overall_status,
        "decision": decision,
        "critical_failures": [c.id for c in critical_failed],
        "high_failures": [c.id for c in high_failed],
        "checks": {c.id: c.passed for c in checks},
    }
    (eval_dir / "google_tier_uat_scoreboard.json").write_text(
        json.dumps(scoreboard_out, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# UAT Results",
        "",
        f"- timestamp (utc): `{timestamp}`",
        f"- overall status: **{overall_status.upper()}**",
        f"- decision: **{decision}**",
        "",
        "## Checks",
        "",
        "| check | severity | status | detail |",
        "|---|---|---|---|",
    ]
    for c in checks:
        lines.append(
            f"| `{c.id}` | `{c.severity}` | **{bool_str(c.passed)}** | {c.detail} |"
        )
    if warnings:
        lines.extend(["", "## Warnings", ""]) 
        for w in warnings:
            lines.append(f"- {w}")

    (repo / "UAT_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    project_status = [
        "# PROJECT STATUS",
        "",
        f"- updated: `{timestamp}`",
        f"- production readiness (new home): **{overall_status.upper()}**",
        f"- decision: **{decision}**",
        "- canonical evidence: `eval/google_tier_uat_snapshot.json`",
        "",
        "## Gate summary",
        "",
    ]
    for c in checks:
        project_status.append(f"- `{c.id}`: {bool_str(c.passed)} ({c.severity})")
    (repo / "PROJECT_STATUS.md").write_text("\n".join(project_status) + "\n", encoding="utf-8")

    blockers = [c for c in checks if not c.passed and c.severity in {"critical", "high"}]
    decision_doc = [
        "# GO / NO-GO DECISION",
        "",
        f"- timestamp (utc): `{timestamp}`",
        f"- verdict: **{decision}**",
        f"- readiness status: **{overall_status.upper()}**",
        "- authoritative snapshot: `eval/google_tier_uat_snapshot.json`",
        "",
    ]
    if blockers:
        decision_doc.extend(["## Blockers", ""])
        for b in blockers:
            decision_doc.append(f"- `{b.id}` ({b.severity}): {b.detail}")
    else:
        decision_doc.extend(["## Blockers", "", "- none"])

    decision_doc.extend(["", "## Warnings", ""])
    if warnings:
        for w in warnings:
            decision_doc.append(f"- {w}")
    else:
        decision_doc.append("- none")

    (repo / "GO_NO_GO_DECISION.md").write_text("\n".join(decision_doc) + "\n", encoding="utf-8")

    print(json.dumps({"overall_status": overall_status, "decision": decision, "snapshot": str(snapshot_path.relative_to(repo))}))
    return 0 if overall_status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
