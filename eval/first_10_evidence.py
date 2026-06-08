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
    "baseline_minutes_without_borg",
    "actual_minutes_with_borg",
    "net_minutes_saved",
    "baseline_tokens_without_borg",
    "actual_tokens_with_borg",
    "net_tokens_saved",
    "savings_counterfactual_basis",
    "dead_end_avoided_confirmed",
    "user_confirmed_value",
]

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", re.I),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*[^\s<][^\s]{3,}"),
    re.compile(r"(?i)\b(?:authorization|x-api-key)\s*:\s*(?:bearer\s+)?[A-Za-z0-9._~+/=-]{8,}"),
]

PLACEHOLDER_RE = re.compile(r"(?i)\b(todo|tbd|placeholder|lorem ipsum|example\.com/placeholder|fake-user|synthetic-user)\b")
INTERNAL_RE = re.compile(r"(?i)\b(internal|maintainer|synthetic|simulated|agent-test|test-user|fake)\b")
BOT_RE = re.compile(r"(?i)(\[bot\]\b|\bbot\b|\bdependabot\b|\brenovate\b|\bgithub-actions\b|-bot\b)")

REQUIRED_EVIDENCE_TEXT_FIELDS = [
    "install_method",
    "rescue_input_redacted",
    "blocker_category",
]
REQUIRED_EVIDENCE_BOOLEAN_FIELDS = [
    "install_success",
    "rescue_returned_action_stop_verify",
    "rescue_useful",
    "mcp_setup_attempted",
    "mcp_setup_success",
    "no_confident_match_when_unknown",
    "privacy_security_incident",
    "repeat_use_within_7_days",
]

MIN_TOTAL_REAL_USERS = 10
MIN_INSTALL_SUCCESSES = 8
MIN_USEFUL_RESCUES = 6
MAX_CRITICAL_PRIVACY_SECURITY_FAILURES = 0
RESERVED_EVIDENCE_HOSTS = {"example.com", "example.org", "example.net", "localhost", "127.0.0.1", "0.0.0.0"}
RESERVED_EVIDENCE_SUFFIXES = (".test", ".invalid", ".localhost", ".example")
SAVINGS_BASIS_ALIASES = {
    "user-estimate": "user_estimate",
    "user_estimate": "user_estimate",
    "timer-before-after": "same_user_before_after",
    "timer_before_after": "same_user_before_after",
    "same-user-before-after": "same_user_before_after",
    "same_user_before_after": "same_user_before_after",
    "paired-control": "randomized_control",
    "paired_control": "randomized_control",
    "randomized-control": "randomized_control",
    "randomized_control": "randomized_control",
    "agent-trace-baseline": "agent_trace_baseline",
    "agent_trace_baseline": "agent_trace_baseline",
    "not-measured": "not_measured",
    "not_measured": "not_measured",
}
UNMEASURED_SAVINGS_BASIS = {"", "unknown", "none", "n/a", "not_measured"}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "pass", "passed", "success", "successful"}
    return False


def _boolish_present(value: Any) -> bool:
    """Return True when a row explicitly recorded a boolean/tri-state answer."""
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)) and value in (0, 1):
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return text in {
            "1",
            "0",
            "true",
            "false",
            "yes",
            "no",
            "y",
            "n",
            "pass",
            "passed",
            "success",
            "successful",
            "fail",
            "failed",
            "unknown",
            "not-tested",
            "not_tested",
            "not-attempted",
            "not_attempted",
        }
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


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _number_is_present(value: Any) -> bool:
    return value is not None and value != ""


def _round_float(value: float) -> float:
    rounded = round(float(value), 6)
    if rounded == -0.0:
        return 0.0
    return rounded


def _counterfactual_basis(row: dict[str, Any]) -> str:
    raw = str(row.get("savings_counterfactual_basis") or "unknown").strip().lower()
    normalized = raw.replace(" ", "_")
    return SAVINGS_BASIS_ALIASES.get(normalized, normalized) or "unknown"


def _value_reasons_and_measurement(row: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    """Validate optional savings fields and return a derived measurement.

    Measurement is optional for first-10 adoption. Once any savings/value field is
    present, it must be internally consistent, consented, and externally sourced.
    """
    measurement_fields = [
        "baseline_minutes_without_borg",
        "actual_minutes_with_borg",
        "net_minutes_saved",
        "baseline_tokens_without_borg",
        "actual_tokens_with_borg",
        "net_tokens_saved",
    ]
    has_any_value_field = (
        any(_number_is_present(row.get(field)) for field in measurement_fields)
        or _counterfactual_basis(row) not in UNMEASURED_SAVINGS_BASIS
        or _truthy(row.get("dead_end_avoided_confirmed"))
    )
    if not has_any_value_field:
        return [], None

    reasons: list[str] = []
    baseline_minutes = _number_or_none(row.get("baseline_minutes_without_borg"))
    actual_minutes = _number_or_none(row.get("actual_minutes_with_borg"))
    stated_minutes = _number_or_none(row.get("net_minutes_saved"))
    baseline_tokens = _number_or_none(row.get("baseline_tokens_without_borg"))
    actual_tokens = _number_or_none(row.get("actual_tokens_with_borg"))
    stated_tokens = _number_or_none(row.get("net_tokens_saved"))
    basis = _counterfactual_basis(row)

    if not _truthy(row.get("user_confirmed_value")):
        reasons.append("user_confirmed_value is required before savings can count")
    if basis not in {"randomized_control", "same_user_before_after", "agent_trace_baseline", "user_estimate"}:
        reasons.append("savings_counterfactual_basis must be randomized_control/paired-control, same_user_before_after/timer-before-after, agent_trace_baseline, or user_estimate/user-estimate")

    if baseline_minutes is None and actual_minutes is None and stated_minutes is not None:
        reasons.append("net_minutes_saved cannot be supplied without baseline_minutes_without_borg and actual_minutes_with_borg")
    if baseline_tokens is None and actual_tokens is None and stated_tokens is not None:
        reasons.append("net_tokens_saved cannot be supplied without baseline_tokens_without_borg and actual_tokens_with_borg")

    net_minutes: float | None = None
    if baseline_minutes is not None or actual_minutes is not None:
        if baseline_minutes is None or actual_minutes is None:
            reasons.append("baseline_minutes_without_borg and actual_minutes_with_borg must be supplied together")
        elif baseline_minutes < 0 or actual_minutes < 0:
            reasons.append("baseline/actual minutes must be non-negative")
        else:
            net_minutes = _round_float(baseline_minutes - actual_minutes)
            if stated_minutes is not None and abs(stated_minutes - net_minutes) > 1e-6:
                reasons.append("net_minutes_saved does not match baseline_minutes_without_borg - actual_minutes_with_borg")
    elif stated_minutes is not None:
        reasons.append("net_minutes_saved cannot be derived without baseline and actual minutes")

    net_tokens: int | None = None
    if baseline_tokens is not None or actual_tokens is not None:
        if baseline_tokens is None or actual_tokens is None:
            reasons.append("baseline_tokens_without_borg and actual_tokens_with_borg must be supplied together")
        elif baseline_tokens < 0 or actual_tokens < 0:
            reasons.append("baseline/actual tokens must be non-negative")
        else:
            net_tokens = int(round(baseline_tokens - actual_tokens))
            if stated_tokens is not None and int(round(stated_tokens)) != net_tokens:
                reasons.append("net_tokens_saved does not match baseline_tokens_without_borg - actual_tokens_with_borg")
    elif stated_tokens is not None:
        reasons.append("net_tokens_saved cannot be derived without baseline and actual tokens")

    if net_minutes is None and net_tokens is None:
        reasons.append("at least one before/after minutes or token pair is required for measured savings")

    if reasons:
        return reasons, None

    return [], {
        "net_minutes_saved": net_minutes or 0.0,
        "positive_minutes_saved": max(net_minutes or 0.0, 0.0),
        "negative_minutes_cost": abs(min(net_minutes or 0.0, 0.0)),
        "net_tokens_saved": net_tokens or 0,
        "positive_tokens_saved": max(net_tokens or 0, 0),
        "negative_tokens_cost": abs(min(net_tokens or 0, 0)),
        "dead_end_avoided_confirmed": _truthy(row.get("dead_end_avoided_confirmed")),
        "savings_counterfactual_basis": basis,
    }


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

    if not _is_nonempty(user_id):
        reasons.append("missing non-placeholder user_id_pseudonym")
    if BOT_RE.search(user_id):
        reasons.append("user_id_pseudonym appears to identify a bot or automation account")
    if not _is_valid_external_evidence_uri(evidence_uri):
        reasons.append("missing valid https external_user_evidence_uri")
    if not _truthy(row.get("consent_confirmed")):
        reasons.append("consent_confirmed is not true")
    if not _truthy(row.get("outcome_recorded")):
        reasons.append("outcome_recorded is not true")

    for field in REQUIRED_EVIDENCE_TEXT_FIELDS:
        if not _is_nonempty(row.get(field)):
            reasons.append(f"missing non-placeholder {field}")

    time_to_first_rescue = _number_or_none(row.get("time_to_first_rescue_minutes"))
    if time_to_first_rescue is None or time_to_first_rescue < 0:
        reasons.append("time_to_first_rescue_minutes must be numeric and non-negative")

    for field in REQUIRED_EVIDENCE_BOOLEAN_FIELDS:
        if not _boolish_present(row.get(field)):
            reasons.append(f"missing explicit boolean/tri-state {field}")

    for field, value in _iter_string_fields(row):
        if _has_secret(value):
            reasons.append(f"{field} appears to contain an unredacted secret")
        if INTERNAL_RE.search(value):
            reasons.append(f"{field} appears internal, maintainer, synthetic, simulated, or fake")
        if BOT_RE.search(value):
            reasons.append(f"{field} appears to identify a bot or automation account")

    return reasons


def _stored_consistency(
    data: dict[str, Any],
    derived: dict[str, int],
    thresholds_passed: bool,
    derived_value: dict[str, Any] | None = None,
) -> dict[str, Any]:
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

    if derived_value is not None and ("current_value_counts" in data or any(derived_value.get(key, 0) for key in derived_value)):
        value_counts = data.get("current_value_counts") or {}
        value_expected = {
            "current_value_counts.rows_with_measured_value": int(derived_value["rows_with_measured_value"]),
            "current_value_counts.dead_ends_avoided_confirmed": int(derived_value["dead_ends_avoided_confirmed"]),
            "current_value_counts.net_minutes_saved": _round_float(float(derived_value["net_minutes_saved"])),
            "current_value_counts.positive_minutes_saved": _round_float(float(derived_value["positive_minutes_saved"])),
            "current_value_counts.negative_minutes_cost": _round_float(float(derived_value["negative_minutes_cost"])),
            "current_value_counts.net_tokens_saved": int(derived_value["net_tokens_saved"]),
            "current_value_counts.positive_tokens_saved": int(derived_value["positive_tokens_saved"]),
            "current_value_counts.negative_tokens_cost": int(derived_value["negative_tokens_cost"]),
        }
        value_actual = {
            "current_value_counts.rows_with_measured_value": int(value_counts.get("rows_with_measured_value") or 0),
            "current_value_counts.dead_ends_avoided_confirmed": int(value_counts.get("dead_ends_avoided_confirmed") or 0),
            "current_value_counts.net_minutes_saved": _round_float(float(value_counts.get("net_minutes_saved") or 0.0)),
            "current_value_counts.positive_minutes_saved": _round_float(float(value_counts.get("positive_minutes_saved") or 0.0)),
            "current_value_counts.negative_minutes_cost": _round_float(float(value_counts.get("negative_minutes_cost") or 0.0)),
            "current_value_counts.net_tokens_saved": int(value_counts.get("net_tokens_saved") or 0),
            "current_value_counts.positive_tokens_saved": int(value_counts.get("positive_tokens_saved") or 0),
            "current_value_counts.negative_tokens_cost": int(value_counts.get("negative_tokens_cost") or 0),
        }
        for key, expected_value in value_expected.items():
            if value_actual.get(key) != expected_value:
                mismatches.append({"field": key, "expected": expected_value, "actual": value_actual.get(key)})

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
    value_measurements: list[dict[str, Any]] = []

    for idx, row in enumerate(normalized_rows):
        reasons = _row_reasons(row)
        value_reasons, value_measurement = _value_reasons_and_measurement(row)
        reasons.extend(value_reasons)
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
            if value_measurement is not None:
                value_measurements.append(value_measurement)

    raw_privacy_security_incidents = sum(1 for row in normalized_rows if _truthy(row.get("privacy_security_incident")))
    derived = {
        "verified_external_users": len(counted_rows),
        "real_users": len(counted_rows),
        "install_successes": sum(1 for row in counted_rows if _truthy(row.get("install_success"))),
        "useful_rescue_moments": sum(
            1
            for row in counted_rows
            if _truthy(row.get("rescue_useful")) and _truthy(row.get("rescue_returned_action_stop_verify"))
        ),
        "critical_privacy_security_failures": raw_privacy_security_incidents,
        "repeat_use_within_7_days": sum(1 for row in counted_rows if _truthy(row.get("repeat_use_within_7_days"))),
    }
    basis_counts: dict[str, int] = {}
    for measurement in value_measurements:
        basis = str(measurement.get("savings_counterfactual_basis") or "unknown")
        basis_counts[basis] = basis_counts.get(basis, 0) + 1
    derived_value = {
        "rows_with_measured_value": len(value_measurements),
        "dead_ends_avoided_confirmed": sum(1 for item in value_measurements if item.get("dead_end_avoided_confirmed")),
        "net_minutes_saved": _round_float(sum(float(item.get("net_minutes_saved") or 0.0) for item in value_measurements)),
        "positive_minutes_saved": _round_float(sum(float(item.get("positive_minutes_saved") or 0.0) for item in value_measurements)),
        "negative_minutes_cost": _round_float(sum(float(item.get("negative_minutes_cost") or 0.0) for item in value_measurements)),
        "net_tokens_saved": int(sum(int(item.get("net_tokens_saved") or 0) for item in value_measurements)),
        "positive_tokens_saved": int(sum(int(item.get("positive_tokens_saved") or 0) for item in value_measurements)),
        "negative_tokens_cost": int(sum(int(item.get("negative_tokens_cost") or 0) for item in value_measurements)),
        "counterfactual_basis_counts": basis_counts,
    }
    thresholds = _thresholds(data)
    thresholds_passed = (
        derived["verified_external_users"] >= thresholds["required_total_real_users"]
        and derived["real_users"] >= thresholds["required_total_real_users"]
        and derived["install_successes"] >= thresholds["required_install_successes"]
        and derived["useful_rescue_moments"] >= thresholds["required_useful_rescue_moments"]
        and derived["critical_privacy_security_failures"] <= thresholds["max_critical_privacy_security_failures"]
    )

    consistency = _stored_consistency(data, derived, thresholds_passed, derived_value)
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
        "derived_value": derived_value,
        "stored_consistency": consistency,
        "blockers": blockers,
        "counted_user_ids": [str(row.get("user_id_pseudonym")) for row in counted_rows],
    }


def scoreboard_with_derived_fields(data: dict[str, Any], evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a copy of scoreboard JSON with aggregate fields synced to rows."""
    updated = copy.deepcopy(data)
    evaluation = evaluation or evaluate_scoreboard(updated)
    derived = evaluation["derived_counts"]
    derived_value = evaluation["derived_value"]
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
    updated["current_value_counts"] = {
        "rows_with_measured_value": derived_value["rows_with_measured_value"],
        "dead_ends_avoided_confirmed": derived_value["dead_ends_avoided_confirmed"],
        "net_minutes_saved": derived_value["net_minutes_saved"],
        "positive_minutes_saved": derived_value["positive_minutes_saved"],
        "negative_minutes_cost": derived_value["negative_minutes_cost"],
        "net_tokens_saved": derived_value["net_tokens_saved"],
        "positive_tokens_saved": derived_value["positive_tokens_saved"],
        "negative_tokens_cost": derived_value["negative_tokens_cost"],
        "counterfactual_basis_counts": derived_value["counterfactual_basis_counts"],
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
