#!/usr/bin/env python3
"""Validate and optionally update Borg first-10 external-user evidence.

This module is deliberately stricter than a dashboard compiler: public
self-serve readiness is derived from row-level consented external evidence,
not from mutable aggregate counters. Aggregate fields are checked for
consistency and can be regenerated with ``--write`` after real rows are added.

No synthetic/internal/maintainer row may count toward public launch.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCOREBOARD = ROOT / "eval" / "first_10_user_scoreboard.json"

DEFAULT_COLUMNS = [
    "user_id_pseudonym",
    "external_user_evidence_uri",
    "consent_confirmed",
    "install_method",
    "install_success",
    "time_to_first_rescue_minutes",
    "rescue_input_redacted",
    "rescue_returned_action_stop_verify",
    "rescue_useful",
    "mcp_setup_attempted",
    "mcp_setup_success",
    "no_confident_match_when_unknown",
    "blocker_category",
    "blocker_notes_redacted",
    "privacy_security_incident",
    "repeat_use_within_7_days",
    "outcome_recorded",
]

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|token)\s*=\s*[^\s<][^\s]{5,}"),
]

PLACEHOLDER_RE = re.compile(r"(?i)\b(todo|tbd|placeholder|lorem ipsum|example\.com/placeholder|fake-user|synthetic-user)\b")
INTERNAL_RE = re.compile(r"(?i)\b(internal|maintainer|synthetic|simulated|agent-test|test-user|fake)\b")

MIN_TOTAL_REAL_USERS = 10
MIN_INSTALL_SUCCESSES = 8
MIN_USEFUL_RESCUES = 6
MAX_CRITICAL_PRIVACY_SECURITY_FAILURES = 0
RESERVED_EVIDENCE_HOSTS = {"example.com", "example.org", "example.net", "localhost", "127.0.0.1", "0.0.0.0"}
RESERVED_EVIDENCE_SUFFIXES = (".test", ".invalid", ".localhost", ".example")


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "pass", "passed", "success", "successful"}
    return False


def _is_nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER_RE.search(value)


def _has_secret(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in SECRET_PATTERNS)


def _iter_string_fields(value: Any, prefix: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from _iter_string_fields(child, child_prefix)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            yield from _iter_string_fields(child, child_prefix)
    elif isinstance(value, str):
        yield prefix or "<value>", value


def _is_valid_external_evidence_uri(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    text = value.strip()
    if PLACEHOLDER_RE.search(text) or _has_secret(text):
        return False
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return False
    if host in RESERVED_EVIDENCE_HOSTS or host.endswith(RESERVED_EVIDENCE_SUFFIXES):
        return False
    return True


def _int_or_default(raw: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(raw.get(key, default))
    except (TypeError, ValueError):
        return default


def normalize_row(row: Any, columns: list[str] | None = None) -> dict[str, Any]:
    """Normalize dict or list-style scoreboard rows to a dict."""
    if isinstance(row, dict):
        return dict(row)
    if isinstance(row, list):
        names = columns or DEFAULT_COLUMNS
        return {name: row[idx] if idx < len(row) else None for idx, name in enumerate(names)}
    return {"__malformed_row__": row}


def _thresholds(data: dict[str, Any]) -> dict[str, int]:
    raw = data.get("thresholds") or {}
    return {
        "required_total_real_users": max(
            MIN_TOTAL_REAL_USERS,
            _int_or_default(raw, "required_total_real_users", MIN_TOTAL_REAL_USERS),
        ),
        "required_install_successes": max(
            MIN_INSTALL_SUCCESSES,
            _int_or_default(raw, "min_install_successes_for_public_self_serve", MIN_INSTALL_SUCCESSES),
        ),
        "required_useful_rescue_moments": max(
            MIN_USEFUL_RESCUES,
            _int_or_default(raw, "min_useful_rescue_moments_for_public_self_serve", MIN_USEFUL_RESCUES),
        ),
        "max_critical_privacy_security_failures": MAX_CRITICAL_PRIVACY_SECURITY_FAILURES,
    }


def _row_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if "__malformed_row__" in row:
        return ["row is not an object or columns-aligned list"]

    user_id = str(row.get("user_id_pseudonym") or "").strip()
    evidence_uri = str(row.get("external_user_evidence_uri") or "").strip()
    text_for_internal_check = " ".join(
        str(row.get(key) or "")
        for key in ["user_id_pseudonym", "external_user_evidence_uri", "install_method", "blocker_notes_redacted"]
    )

    if not _is_nonempty(user_id):
        reasons.append("missing non-placeholder user_id_pseudonym")
    if not _is_valid_external_evidence_uri(evidence_uri):
        reasons.append("missing valid https external_user_evidence_uri")
    if not _truthy(row.get("consent_confirmed")):
        reasons.append("consent_confirmed is not true")
    if not _truthy(row.get("outcome_recorded")):
        reasons.append("outcome_recorded is not true")
    if INTERNAL_RE.search(text_for_internal_check):
        reasons.append("row appears internal, maintainer, synthetic, simulated, or fake")

    for field, value in _iter_string_fields(row):
        if _has_secret(value):
            reasons.append(f"{field} appears to contain an unredacted secret")

    return reasons


def _stored_consistency(data: dict[str, Any], derived: dict[str, int], thresholds_passed: bool) -> dict[str, Any]:
    counts = data.get("current_counts") or {}
    truth = data.get("truth_policy") or {}
    verdict = data.get("current_verdict") or {}

    expected = {
        "current_counts.real_users": derived["real_users"],
        "current_counts.install_successes": derived["install_successes"],
        "current_counts.useful_rescue_moments": derived["useful_rescue_moments"],
        "current_counts.critical_privacy_security_failures": derived["critical_privacy_security_failures"],
        "current_counts.repeat_use_within_7_days": derived["repeat_use_within_7_days"],
        "truth_policy.verified_external_users": derived["verified_external_users"],
        "current_verdict.first_10_complete": thresholds_passed,
    }
    actual = {
        "current_counts.real_users": int(counts.get("real_users") or 0),
        "current_counts.install_successes": int(counts.get("install_successes") or 0),
        "current_counts.useful_rescue_moments": int(counts.get("useful_rescue_moments") or 0),
        "current_counts.critical_privacy_security_failures": int(counts.get("critical_privacy_security_failures") or 0),
        "current_counts.repeat_use_within_7_days": int(counts.get("repeat_use_within_7_days") or 0),
        "truth_policy.verified_external_users": int(truth.get("verified_external_users") or 0),
        "current_verdict.first_10_complete": bool(verdict.get("first_10_complete")),
    }

    mismatches = []
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            mismatches.append({"field": key, "expected": expected_value, "actual": actual.get(key)})

    gate = str(verdict.get("public_self_serve_launch_gate") or "").upper()
    expected_gate = "READY" if thresholds_passed else "BLOCKED"
    allowed_gate_values = {"READY", "GO", "PASS", "ALLOWED"} if thresholds_passed else {"BLOCKED", "NO-GO", "NO_GO", "NO"}
    if gate not in allowed_gate_values:
        mismatches.append({"field": "current_verdict.public_self_serve_launch_gate", "expected": expected_gate, "actual": gate or None})

    return {"passed": not mismatches, "mismatches": mismatches, "expected_gate": expected_gate}


def evaluate_scoreboard(data: dict[str, Any]) -> dict[str, Any]:
    """Return a fail-closed row-derived first-10 evidence evaluation."""
    columns = data.get("columns") or DEFAULT_COLUMNS
    raw_rows = data.get("rows") or []
    normalized_rows = [normalize_row(row, columns) for row in raw_rows]

    invalid_rows: list[dict[str, Any]] = []
    duplicate_user_ids: list[str] = []
    seen_user_ids: set[str] = set()
    counted_rows: list[dict[str, Any]] = []

    for idx, row in enumerate(normalized_rows):
        reasons = _row_reasons(row)
        user_id = str(row.get("user_id_pseudonym") or "").strip()
        if user_id:
            if user_id in seen_user_ids:
                duplicate_user_ids.append(user_id)
                reasons.append("duplicate user_id_pseudonym")
            seen_user_ids.add(user_id)
        if reasons:
            invalid_rows.append({"index": idx, "user_id_pseudonym": user_id or None, "reasons": reasons})
        else:
            counted_rows.append(row)

    derived = {
        "verified_external_users": len(counted_rows),
        "real_users": len(counted_rows),
        "install_successes": sum(1 for row in counted_rows if _truthy(row.get("install_success"))),
        "useful_rescue_moments": sum(
            1
            for row in counted_rows
            if _truthy(row.get("rescue_useful")) and _truthy(row.get("rescue_returned_action_stop_verify"))
        ),
        "critical_privacy_security_failures": sum(1 for row in counted_rows if _truthy(row.get("privacy_security_incident"))),
        "repeat_use_within_7_days": sum(1 for row in counted_rows if _truthy(row.get("repeat_use_within_7_days"))),
    }
    thresholds = _thresholds(data)
    thresholds_passed = (
        derived["verified_external_users"] >= thresholds["required_total_real_users"]
        and derived["real_users"] >= thresholds["required_total_real_users"]
        and derived["install_successes"] >= thresholds["required_install_successes"]
        and derived["useful_rescue_moments"] >= thresholds["required_useful_rescue_moments"]
        and derived["critical_privacy_security_failures"] <= thresholds["max_critical_privacy_security_failures"]
    )

    consistency = _stored_consistency(data, derived, thresholds_passed)
    schema_valid = not invalid_rows and not duplicate_user_ids

    blockers: list[str] = []
    if duplicate_user_ids:
        blockers.append("duplicate user_id_pseudonym values: " + ", ".join(sorted(set(duplicate_user_ids))))
    if invalid_rows:
        blockers.append(f"{len(invalid_rows)} row(s) failed external-evidence validation")
    secret_rows = [item for item in invalid_rows if any("unredacted secret" in r for r in item["reasons"])]
    if secret_rows:
        blockers.append("one or more evidence row fields appear to contain unredacted secrets")
    if not consistency["passed"]:
        blockers.append("stored aggregate fields do not match row-derived evidence")
    if not thresholds_passed:
        blockers.append(
            "first-10 external-user evidence has not passed: "
            f"verified={derived['verified_external_users']}/{thresholds['required_total_real_users']}, "
            f"real_users={derived['real_users']}/{thresholds['required_total_real_users']}, "
            f"installs={derived['install_successes']}/{thresholds['required_install_successes']}, "
            f"useful={derived['useful_rescue_moments']}/{thresholds['required_useful_rescue_moments']}, "
            f"critical_incidents={derived['critical_privacy_security_failures']}/{thresholds['max_critical_privacy_security_failures']}"
        )

    return {
        "schema_version": 1,
        "schema_valid": schema_valid,
        "thresholds_passed": thresholds_passed,
        "public_self_serve_launch_gate": "READY" if thresholds_passed and schema_valid and consistency["passed"] else "BLOCKED",
        "row_count": len(normalized_rows),
        "counted_external_rows": len(counted_rows),
        "invalid_rows": invalid_rows,
        "duplicate_user_ids": sorted(set(duplicate_user_ids)),
        "thresholds": thresholds,
        "derived_counts": derived,
        "stored_consistency": consistency,
        "blockers": blockers,
        "counted_user_ids": [str(row.get("user_id_pseudonym")) for row in counted_rows],
    }


def scoreboard_with_derived_fields(data: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a copy of scoreboard JSON with aggregate fields synced to rows."""
    updated = copy.deepcopy(data)
    evaluation = evaluation or evaluate_scoreboard(updated)
    derived = evaluation["derived_counts"]
    thresholds_passed = bool(evaluation["thresholds_passed"])
    schema_valid = bool(evaluation["schema_valid"])

    updated.setdefault("truth_policy", {})["verified_external_users"] = derived["verified_external_users"]
    updated.setdefault("truth_policy", {})["public_self_serve_launch_allowed_before_thresholds"] = False
    updated["current_counts"] = {
        "real_users": derived["real_users"],
        "install_successes": derived["install_successes"],
        "useful_rescue_moments": derived["useful_rescue_moments"],
        "critical_privacy_security_failures": derived["critical_privacy_security_failures"],
        "repeat_use_within_7_days": derived["repeat_use_within_7_days"],
    }
    ready = thresholds_passed and schema_valid
    updated["current_verdict"] = {
        "first_10_complete": ready,
        "public_self_serve_launch_gate": "READY" if ready else "BLOCKED",
        "reason": "First-10 external-user evidence thresholds passed." if ready else "First-10 external-user evidence thresholds have not passed.",
    }
    updated["generated_at_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return updated


def load_scoreboard(path: Path = SCOREBOARD) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Borg first-10 external-user evidence")
    parser.add_argument("--input", default=str(SCOREBOARD), help="Scoreboard JSON path")
    parser.add_argument("--output", default="", help="Output JSON path when --write is used; defaults to --input")
    parser.add_argument("--add-row-json", default="", help="Append one JSON object/list row before validation")
    parser.add_argument("--write", action="store_true", help="Write row-derived aggregate fields back to --output/--input")
    parser.add_argument("--require-thresholds", action="store_true", help="Exit nonzero until public self-serve evidence thresholds pass")
    args = parser.parse_args(argv)

    path = Path(args.input)
    data = load_scoreboard(path)
    if args.add_row_json:
        row = json.loads(args.add_row_json)
        data.setdefault("rows", []).append(row)

    evaluation = evaluate_scoreboard(data)
    if args.write:
        output = Path(args.output) if args.output else path
        updated = scoreboard_with_derived_fields(data, evaluation)
        # Re-evaluate after write so stored consistency reflects the file that will exist.
        evaluation = evaluate_scoreboard(updated)
        output.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(evaluation, indent=2, sort_keys=True))
    ok = evaluation["schema_valid"] and evaluation["stored_consistency"]["passed"]
    if args.require_thresholds:
        ok = ok and evaluation["thresholds_passed"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
