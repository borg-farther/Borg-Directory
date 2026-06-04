#!/usr/bin/env python3
"""Compile Borg self-service operations readiness.

This gate is deliberately operational, not product-marketing. It answers:
if a first-10 tester hits a bad answer, install failure, privacy concern, or bad
release, does the public repo contain a tested path to report, triage, pause,
rollback, and keep proof snapshots fresh?
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone

import yaml
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SNAPSHOT = ROOT / "eval" / "self_service_ops_gate_snapshot.json"
REPORT = ROOT / "docs" / "SELF_SERVICE_OPS_READINESS_REPORT.md"
MAX_OPS_PROOF_AGE_HOURS = 24.0

REQUIRED_DOCS = {
    "support_policy": Path("SUPPORT.md"),
    "security_policy": Path("SECURITY.md"),
    "ops_readiness": Path("docs/SELF_SERVICE_OPS_READINESS.md"),
    "first_10_intake": Path("docs/FIRST_10_EVIDENCE_INTAKE.md"),
    "rollback_comms": Path("docs/ROLLBACK_AND_COMMS_RUNBOOK.md"),
    "cold_start_trust": Path("docs/COLD_START_TRUST_HARDENING.md"),
}

REQUIRED_ISSUE_TEMPLATES = {
    "bad_answer": Path(".github/ISSUE_TEMPLATE/bad-answer.yml"),
    "first_10_evidence": Path(".github/ISSUE_TEMPLATE/first-10-evidence.yml"),
    "install_mcp_support": Path(".github/ISSUE_TEMPLATE/install-mcp-support.yml"),
    "issue_config": Path(".github/ISSUE_TEMPLATE/config.yml"),
}

REQUIRED_STATIC_FILES = {
    "codeowners": Path(".github/CODEOWNERS"),
    "watchdog_workflow": Path(".github/workflows/self-service-watchdog.yml"),
    "rollback_drill_snapshot": Path("eval/rollback_comms_drill_snapshot.json"),
}

SUPPORT_REQUIRED_PHRASES = [
    "first-10 beta support window",
    "P0",
    "P1",
    "P2",
    "pause first-10 invites",
    "maintainer handholding",
    "privacy/security escalation",
]

SECURITY_REQUIRED_PHRASES = [
    "report a vulnerability",
    "do not include secrets",
    "privacy/security incident",
    "revocation",
]

BAD_ANSWER_REQUIRED_FIELDS = [
    "borg-version",
    "surface",
    "sanitized-input",
    "returned-action-stop-verify",
    "confidence-block",
    "expected-guidance",
    "actual-wrong-guidance",
    "reproduction-command",
    "severity",
    "privacy-confirmation",
]

FIRST10_REQUIRED_FIELDS = [
    "user-id-pseudonym",
    "external-user-evidence-uri",
    "consent-confirmed",
    "install-method",
    "install-success",
    "time-to-first-rescue-minutes",
    "rescue-input-redacted",
    "rescue-returned-action-stop-verify",
    "rescue-useful",
    "mcp-setup-attempted",
    "mcp-setup-success",
    "no-confident-match-when-unknown",
    "privacy-security-incident",
    "outcome-recorded",
    "baseline-minutes-without-borg",
    "actual-minutes-with-borg",
    "net-minutes-saved",
    "baseline-tokens-without-borg",
    "actual-tokens-with-borg",
    "net-tokens-saved",
    "savings-counterfactual-basis",
    "dead-end-avoided-confirmed",
    "user-confirmed-value",
]

INSTALL_SUPPORT_REQUIRED_FIELDS = [
    "borg-version",
    "install-method",
    "operating-system",
    "python-version",
    "command-output-redacted",
    "mcp-client",
    "severity",
    "privacy-confirmation",
]

# These IDs must exist in the first-10 issue form so the row contract stays
# visible to testers, but they are intentionally optional until a tester has
# measured savings/value evidence. Requiring blank-able numeric inputs would
# make GitHub issue submission impossible for unmeasured rows.
PRESENT_ONLY_ISSUE_FIELDS = {
    "baseline-minutes-without-borg",
    "actual-minutes-with-borg",
    "net-minutes-saved",
    "baseline-tokens-without-borg",
    "actual-tokens-with-borg",
    "net-tokens-saved",
}

WORKFLOW_REQUIRED_SNIPPETS = [
    "schedule:",
    "workflow_dispatch:",
    "python eval/run_pypi_fresh_install_canary.py",
    "python eval/run_github_source_install_canary.py",
    "python eval/cold_start_trust_gate.py",
    "python eval/release_governance_gate.py --output eval/release_governance_snapshot.json",
    "python eval/rollback_comms_drill.py",
    "python eval/self_service_ops_gate.py",
    "python eval/public_self_serve_launch_gate.py",
    "python eval/real_user_rollout_gate.py",
    "python eval/ops_readiness_watchdog.py",
    "--max-snapshot-age-hours 24",
    "python scripts/build_borg_proof_dashboard.py",
    "python eval/ops_readiness_watchdog.py --mode pr --json --no-write --output eval/ops_readiness_watchdog_post_dashboard_check.json --max-snapshot-age-hours 24 --allow-public-blocker release_controls_or_first_10_evidence --require-ci-schedule",
    "python scripts/borg_proof_dashboard_lint.py",
]

BAD_FEEDBACK_BANNED = ["borg_rate(helpful=False)", "borg_rate"]
BAD_FEEDBACK_REQUIRED = ["borg_record_failure", "bad-answer.yml", "first-10-evidence.yml"]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _age_hours(value: str | None) -> float | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600


def _contains_all(path: Path, phrases: list[str]) -> dict[str, Any]:
    text = _read(path)
    lowered = text.lower()
    missing = [phrase for phrase in phrases if phrase.lower() not in lowered]
    return {
        "path": _rel(path),
        "exists": path.exists(),
        "passed": path.exists() and not missing,
        "missing_phrases": missing,
    }


def _issue_template_check(path: Path, required_fields: list[str]) -> dict[str, Any]:
    text = _read(path)
    missing: list[str] = []
    non_required: list[str] = []
    parse_error = ""
    required_by_id: dict[str, bool] = {}
    if path.exists():
        try:
            data = yaml.safe_load(text) or {}
            body = data.get("body") if isinstance(data, dict) else []
            for item in body or []:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                field_id = str(item["id"])
                raw_validations = item.get("validations")
                validations = raw_validations if isinstance(raw_validations, dict) else {}
                is_required = bool(validations.get("required"))
                if item.get("type") == "checkboxes" and not is_required:
                    raw_attributes = item.get("attributes")
                    attributes = raw_attributes if isinstance(raw_attributes, dict) else {}
                    raw_options = attributes.get("options")
                    options = raw_options if isinstance(raw_options, list) else []
                    is_required = any(isinstance(option, dict) and bool(option.get("required")) for option in options)
                required_by_id[field_id] = is_required
        except Exception as exc:
            parse_error = f"invalid issue form yaml: {exc}"
    for field in required_fields:
        if field not in required_by_id:
            missing.append(field)
        elif not required_by_id[field] and field not in PRESENT_ONLY_ISSUE_FIELDS:
            non_required.append(field)
    secret_warning = all(token in text.lower() for token in ["redact", "secret"])
    return {
        "path": _rel(path),
        "exists": path.exists(),
        "passed": path.exists() and not parse_error and not missing and not non_required and secret_warning,
        "missing_fields": missing,
        "non_required_fields": non_required,
        "has_secret_redaction_warning": secret_warning,
        "parse_error": parse_error,
    }


def _watchdog_workflow_check(path: Path) -> dict[str, Any]:
    text = _read(path)
    missing = [snippet for snippet in WORKFLOW_REQUIRED_SNIPPETS if snippet not in text]
    return {
        "path": _rel(path),
        "exists": path.exists(),
        "passed": path.exists() and not missing,
        "missing_snippets": missing,
    }


def _rollback_drill_check(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": _rel(path), "exists": False, "passed": False, "error": "missing rollback drill snapshot"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"path": _rel(path), "exists": True, "passed": False, "error": f"invalid json: {exc}"}
    required_steps = {"pause_first_10_invites", "pypi_bad_release_response", "served_mcp_operator_rollback", "bad_guidance_disable_path", "public_status_update", "user_notification_template"}
    observed = {str(item.get("name")) for item in data.get("steps", []) if isinstance(item, dict)}
    missing = sorted(required_steps - observed)
    failed = [item.get("name") for item in data.get("steps", []) if isinstance(item, dict) and not item.get("passed")]
    age_hours = _age_hours(data.get("generated_at_utc"))
    fresh = age_hours is not None and age_hours <= MAX_OPS_PROOF_AGE_HOURS
    dry_run_only = bool(data.get("dry_run_only"))
    return {
        "path": _rel(path),
        "exists": True,
        "generated_at_utc": data.get("generated_at_utc"),
        "age_hours": age_hours,
        "max_age_hours": MAX_OPS_PROOF_AGE_HOURS,
        "passed": bool(data.get("passed") and dry_run_only and fresh and not missing and not failed),
        "missing_steps": missing,
        "failed_steps": failed,
        "dry_run_only": dry_run_only,
        "fresh": fresh,
    }


def _bad_answer_feedback_path_check() -> dict[str, Any]:
    paths = [
        ROOT / "docs" / "COLD_START_TRUST_HARDENING.md",
        ROOT / "eval" / "cold_start_trust_gate_snapshot.json",
        ROOT / ".github" / "ISSUE_TEMPLATE" / "bad-answer.yml",
        ROOT / "docs" / "SELF_SERVICE_OPS_READINESS.md",
    ]
    combined = "\n".join(_read(path) for path in paths)
    banned_hits = sorted({token for token in BAD_FEEDBACK_BANNED if token in combined})
    missing_required = [token for token in BAD_FEEDBACK_REQUIRED if token not in combined]
    return {
        "paths": [_rel(path) for path in paths],
        "passed": not banned_hits and not missing_required,
        "banned_hits": banned_hits,
        "missing_required_tokens": missing_required,
        "policy": "Bad first-answer reporting must use shipped CLI/MCP paths and GitHub issue intake; nonexistent borg_rate paths are blocked.",
    }


def _codeowners_owner_tokens(text: str) -> list[str]:
    owners: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        owners.extend(parts[1:])
    return owners


def _codeowners_file_check(path: Path) -> dict[str, Any]:
    text = _read(path)
    banned_owner = "@borg-farther/maintainers"
    required_owner = "@borg-farther"
    owners = _codeowners_owner_tokens(text)
    contains_required_owner = required_owner in owners
    contains_banned_owner = banned_owner in owners
    invalid_owner_tokens = sorted({owner for owner in owners if owner.startswith("@borg-farther") and owner != required_owner})
    return {
        "path": _rel(path),
        "exists": path.exists(),
        "passed": path.exists() and contains_required_owner and not contains_banned_owner and not invalid_owner_tokens,
        "required_owner": required_owner,
        "banned_owner": banned_owner,
        "owners": owners,
        "invalid_owner_tokens": invalid_owner_tokens,
        "contains_required_owner": contains_required_owner,
        "contains_banned_owner": contains_banned_owner,
        "policy": "Static self-service ops parses non-comment CODEOWNERS owner tokens exactly; live owner validity and enforcement are proven by the release governance gate.",
    }


def compile_gate() -> dict[str, Any]:
    doc_checks = {name: _contains_all(ROOT / rel, SUPPORT_REQUIRED_PHRASES if name == "support_policy" else SECURITY_REQUIRED_PHRASES if name == "security_policy" else []) for name, rel in REQUIRED_DOCS.items()}
    # For docs without phrase-specific checks, require non-placeholder content with current rollout language.
    for name in ["ops_readiness", "first_10_intake", "rollback_comms", "cold_start_trust"]:
        rel = REQUIRED_DOCS[name]
        path = ROOT / rel
        text = _read(path)
        doc_checks[name].update({
            "passed": path.exists() and len(text.strip()) > 800 and "TODO" not in text[:1200],
            "minimum_bytes": len(text.encode("utf-8")),
        })

    template_checks = {
        "bad_answer": _issue_template_check(ROOT / REQUIRED_ISSUE_TEMPLATES["bad_answer"], BAD_ANSWER_REQUIRED_FIELDS),
        "first_10_evidence": _issue_template_check(ROOT / REQUIRED_ISSUE_TEMPLATES["first_10_evidence"], FIRST10_REQUIRED_FIELDS),
        "install_mcp_support": _issue_template_check(ROOT / REQUIRED_ISSUE_TEMPLATES["install_mcp_support"], INSTALL_SUPPORT_REQUIRED_FIELDS),
        "issue_config": {"path": _rel(ROOT / REQUIRED_ISSUE_TEMPLATES["issue_config"]), "exists": (ROOT / REQUIRED_ISSUE_TEMPLATES["issue_config"]).exists(), "passed": (ROOT / REQUIRED_ISSUE_TEMPLATES["issue_config"]).exists()},
    }

    static_checks = {
        "codeowners": _codeowners_file_check(ROOT / REQUIRED_STATIC_FILES["codeowners"]),
        "watchdog_workflow": _watchdog_workflow_check(ROOT / REQUIRED_STATIC_FILES["watchdog_workflow"]),
        "rollback_drill_snapshot": _rollback_drill_check(ROOT / REQUIRED_STATIC_FILES["rollback_drill_snapshot"]),
    }

    feedback = _bad_answer_feedback_path_check()
    categories = {
        "docs": doc_checks,
        "issue_templates": template_checks,
        "static_files": static_checks,
        "bad_answer_feedback_path": {"feedback_path": feedback},
    }
    blockers: list[str] = []
    for category, checks in categories.items():
        for name, check in checks.items():
            if not check.get("passed"):
                blockers.append(f"{category}.{name} is not ready: {check}")
    passed = not blockers
    return {
        "schema_version": 1,
        "gate_type": "self_service_ops_readiness",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "checks": categories,
        "blockers": blockers,
        "rollout_policy": "Ops readiness is necessary but not sufficient for controlled first-10; package provenance, served-runtime freshness, release governance, ops/watchdog freshness, and first-10 guardrails must also pass. broad public self-serve still requires row-derived first-10 external evidence.",
    }


def write_report(snapshot: dict[str, Any]) -> None:
    lines = [
        "# Borg self-service operations readiness",
        "",
        f"Generated: `{snapshot['generated_at_utc']}`",
        f"Verdict: **{'PASS' if snapshot['passed'] else 'FAIL'}**",
        "",
        "## Scope",
        "",
        "This gate verifies the support, bad-answer intake, first-10 evidence intake, rollback/comms drill, and watchdog automation required before Borg invites controlled first-10 testers. It does not authorize broad public self-serve; that remains row-derived external-user gated.",
        "",
        "## Policy",
        "",
        snapshot["rollout_policy"],
        "",
        "## Blockers",
        "",
    ]
    if snapshot["blockers"]:
        lines.extend(f"- {b}" for b in snapshot["blockers"])
    else:
        lines.append("None.")
    lines.extend(["", "## Required artifacts", ""])
    for category, checks in snapshot["checks"].items():
        lines.append(f"### {category}")
        lines.append("")
        for name, check in checks.items():
            lines.append(f"- `{name}`: `{'PASS' if check.get('passed') else 'FAIL'}` — `{check.get('path', 'multiple')}`")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Borg self-service operations readiness")
    parser.add_argument("--no-write", action="store_true", help="Do not write snapshot/report artifacts")
    parser.add_argument("--json", action="store_true", help="Print full JSON snapshot")
    args = parser.parse_args(argv)
    snapshot = compile_gate()
    if not args.no_write:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_report(snapshot)
    print(json.dumps(snapshot if args.json else {"passed": snapshot["passed"], "blockers": snapshot["blockers"], "snapshot": _rel(SNAPSHOT)}, indent=2, sort_keys=True))
    return 0 if snapshot["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
