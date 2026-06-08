#!/usr/bin/env python3
"""Parse a GitHub issue-form submission into a Borg first-10 evidence row.

This is intentionally a candidate-row importer, not a launch bypass. It parses one
GitHub issue body, normalizes fields into eval.first_10_evidence.DEFAULT_COLUMNS,
validates the row with the same row-derived evidence gate, and writes a JSON row
that maintainers/a bot can use in a scoreboard PR.

It never counts synthetic/internal/maintainer/bot rows as public-launch evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # package invocation
    from . import first_10_evidence as evidence  # type: ignore
except ImportError:  # file invocation
    from eval import first_10_evidence as evidence  # type: ignore

NO_RESPONSE_VALUES = {"", "_no response_", "no response", "n/a", "na"}
BOT_RE = re.compile(r"(?:\[bot\]$|-bot$|bot$)", re.I)
CHECKED_RE = re.compile(r"^\s*-\s*\[[xX]\]", re.M)
HEADING_RE = re.compile(r"^###\s+(.+?)\s*$")
GITHUB_ISSUE_PATH_RE = re.compile(r"^/borg-farther/Borg-Directory/issues/\d+/?$", re.I)
REQUIRED_CHECKBOX_COUNTS = {
    "consent-confirmed": 1,
    "privacy-confirmation": 2,
}

ISSUE_FIELD_TO_ROW_FIELD = {
    "user-id-pseudonym": "user_id_pseudonym",
    "external-user-evidence-uri": "external_user_evidence_uri",
    "install-method": "install_method",
    "install-success": "install_success",
    "time-to-first-rescue-minutes": "time_to_first_rescue_minutes",
    "rescue-input-redacted": "rescue_input_redacted",
    "rescue-returned-action-stop-verify": "rescue_returned_action_stop_verify",
    "rescue-useful": "rescue_useful",
    "mcp-setup-attempted": "mcp_setup_attempted",
    "mcp-setup-success": "mcp_setup_success",
    "no-confident-match-when-unknown": "no_confident_match_when_unknown",
    "blocker-category": "blocker_category",
    "blocker-notes-redacted": "blocker_notes_redacted",
    "privacy-security-incident": "privacy_security_incident",
    "repeat-use-within-7-days": "repeat_use_within_7_days",
    "outcome-recorded": "outcome_recorded",
    "baseline-minutes-without-borg": "baseline_minutes_without_borg",
    "actual-minutes-with-borg": "actual_minutes_with_borg",
    "net-minutes-saved": "net_minutes_saved",
    "baseline-tokens-without-borg": "baseline_tokens_without_borg",
    "actual-tokens-with-borg": "actual_tokens_with_borg",
    "net-tokens-saved": "net_tokens_saved",
    "savings-counterfactual-basis": "savings_counterfactual_basis",
    "dead-end-avoided-confirmed": "dead_end_avoided_confirmed",
    "user-confirmed-value": "user_confirmed_value",
}

CHECKBOX_FIELDS = {
    "consent-confirmed": "consent_confirmed",
    "privacy-confirmation": "__privacy_confirmation__",
}

BOOL_FIELDS = {
    "consent_confirmed",
    "install_success",
    "rescue_returned_action_stop_verify",
    "rescue_useful",
    "mcp_setup_attempted",
    "mcp_setup_success",
    "no_confident_match_when_unknown",
    "privacy_security_incident",
    "repeat_use_within_7_days",
    "outcome_recorded",
    "dead_end_avoided_confirmed",
    "user_confirmed_value",
}

NUMERIC_FIELDS = {
    "time_to_first_rescue_minutes",
    "baseline_minutes_without_borg",
    "actual_minutes_with_borg",
    "net_minutes_saved",
    "baseline_tokens_without_borg",
    "actual_tokens_with_borg",
    "net_tokens_saved",
}


def parse_issue_form_body(text: str) -> dict[str, str]:
    """Return raw GitHub issue-form answers keyed by normalized field label."""
    fields: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            current = _slug(match.group(1))
            fields.setdefault(current, [])
            continue
        if current is not None:
            fields[current].append(line)
    return {key: _clean_answer("\n".join(lines)) for key, lines in fields.items()}


def _slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.strip().lower()).strip("-")


def _clean_answer(value: str) -> str:
    stripped = value.strip()
    if stripped.lower() in NO_RESPONSE_VALUES:
        return ""
    return stripped


def _checked_count(value: Any) -> int:
    return len(CHECKED_RE.findall(str(value or "")))


def _require_checked(parsed: dict[str, str], key: str, minimum: int) -> None:
    if _checked_count(parsed.get(key, "")) < minimum:
        raise ValueError(f"{key} must have at least {minimum} checked required option(s)")


def _valid_borg_github_issue_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme == "https" and parsed.netloc.lower() == "github.com" and bool(GITHUB_ISSUE_PATH_RE.fullmatch(parsed.path))


def _parse_bool(value: Any) -> bool | str:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"true", "yes", "y", "1", "pass", "passed", "success", "successful"}:
        return True
    if text in {"false", "no", "n", "0", "fail", "failed", "not-attempted", "not-tested", "unknown"}:
        return False
    if CHECKED_RE.search(str(value or "")):
        return True
    return value


def _parse_number(value: Any) -> int | float | str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    if number.is_integer():
        return int(number)
    return number


def row_from_issue_body(
    body: str,
    *,
    issue_url: str,
    github_actor: str = "",
    internal_actors: set[str] | None = None,
) -> dict[str, Any]:
    """Parse and normalize a row candidate.

    Raises ValueError for bot/internal actor submissions. The row is still later
    validated by eval.first_10_evidence for secrets, placeholders, duplicates,
    and thresholds.
    """
    actor = github_actor.strip()
    if not actor:
        raise ValueError("github_actor is required for GitHub issue-form evidence import")
    blocked = {item.strip().lower() for item in (internal_actors or set()) if item.strip()}
    if BOT_RE.search(actor) or actor.lower() in blocked:
        raise ValueError(f"github_actor is not eligible external evidence: {actor}")
    if not _valid_borg_github_issue_url(issue_url):
        raise ValueError(f"issue_url must be an HTTPS GitHub issue URL for borg-farther/Borg-Directory: {issue_url}")

    parsed = parse_issue_form_body(body)
    for issue_key, minimum in REQUIRED_CHECKBOX_COUNTS.items():
        _require_checked(parsed, issue_key, minimum)
    row: dict[str, Any] = {column: "" for column in evidence.DEFAULT_COLUMNS}
    for issue_key, row_key in ISSUE_FIELD_TO_ROW_FIELD.items():
        if issue_key in parsed:
            row[row_key] = parsed[issue_key]
    for issue_key, row_key in CHECKBOX_FIELDS.items():
        if issue_key in parsed:
            row[row_key] = CHECKED_RE.search(parsed[issue_key]) is not None

    if not str(row.get("external_user_evidence_uri") or "").strip():
        row["external_user_evidence_uri"] = issue_url.strip()
    if actor and not str(row.get("blocker_notes_redacted") or "").strip():
        row["blocker_notes_redacted"] = f"GitHub issue-form submission by external actor {actor}; no additional blocker notes."

    # The privacy checkbox is a separate template control; require it but do not
    # persist it as a scoreboard column.
    if "__privacy_confirmation__" in row and not row.pop("__privacy_confirmation__"):
        row["blocker_notes_redacted"] = (str(row.get("blocker_notes_redacted") or "") + " privacy-confirmation missing").strip()

    for key in list(row):
        if key in BOOL_FIELDS:
            row[key] = _parse_bool(row[key])
        elif key in NUMERIC_FIELDS:
            parsed_number = _parse_number(row[key])
            row[key] = "" if parsed_number is None else parsed_number

    return row


def validate_single_row(row: dict[str, Any]) -> dict[str, Any]:
    scoreboard = {
        "schema_version": 1,
        "truth_policy": {
            "simulated_users_count_as_real": False,
            "internal_sessions_count_as_real": False,
            "maintainer_runs_count_as_real": False,
            "verified_external_users": 0,
            "public_self_serve_launch_allowed_before_thresholds": False,
        },
        "thresholds": {
            "required_total_real_users": evidence.MIN_TOTAL_REAL_USERS,
            "min_install_successes_for_public_self_serve": evidence.MIN_INSTALL_SUCCESSES,
            "min_useful_rescue_moments_for_public_self_serve": evidence.MIN_USEFUL_RESCUES,
            "max_critical_privacy_security_failures": evidence.MAX_CRITICAL_PRIVACY_SECURITY_FAILURES,
        },
        "columns": evidence.DEFAULT_COLUMNS,
        "rows": [row],
        "current_counts": {},
        "current_value_counts": {},
        "current_verdict": {},
    }
    updated = evidence.scoreboard_with_derived_fields(scoreboard)
    return evidence.evaluate_scoreboard(updated)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert a GitHub issue form into a first-10 evidence row candidate")
    parser.add_argument("--issue-body", required=True, help="Path to GitHub issue body markdown")
    parser.add_argument("--issue-url", required=True, help="HTTPS GitHub issue URL; used as evidence URI when form field is blank")
    parser.add_argument("--github-actor", required=True, help="GitHub actor that opened/submitted the issue")
    parser.add_argument("--internal-actors", default="", help="Comma-separated maintainer/internal actors that must not count")
    parser.add_argument("--output", default="", help="Write normalized row JSON to this path")
    args = parser.parse_args(argv)

    internal = {item.strip() for item in args.internal_actors.split(",") if item.strip()}
    body = Path(args.issue_body).read_text(encoding="utf-8", errors="replace")
    try:
        row = row_from_issue_body(
            body,
            issue_url=args.issue_url,
            github_actor=args.github_actor,
            internal_actors=internal,
        )
    except ValueError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    evaluation = validate_single_row(row)
    payload = {"passed": bool(evaluation["schema_valid"]), "row": row, "evaluation": evaluation}
    if args.output and payload["passed"]:
        Path(args.output).write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
