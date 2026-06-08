#!/usr/bin/env python3
"""Append a maintainer-reviewed first-10 GitHub issue row to the scoreboard.

This is the counting-side companion to ``first_10_issue_import.py``. The issue
workflow may create candidate artifacts, but this script is the explicit
maintainer-review step that can update ``eval/first_10_user_scoreboard.json``.
It still fails closed: no bot/internal submitters, no duplicate pseudonyms or
issue/evidence URIs, no same-actor self-review, and no writes unless the fully
updated scoreboard validates.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:  # package invocation
    from . import first_10_evidence as evidence  # type: ignore
    from . import first_10_issue_import as issue_import  # type: ignore
except ImportError:  # file invocation
    from eval import first_10_evidence as evidence  # type: ignore
    from eval import first_10_issue_import as issue_import  # type: ignore

BOT_RE = re.compile(r"(?:\[bot\]$|-bot$|bot$)", re.I)


def _blocked_actors(raw: str | set[str] | None) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, set):
        return {item.strip().lower() for item in raw if item.strip()}
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _normalize_actor(value: str, field: str) -> str:
    actor = value.strip()
    if not actor:
        raise ValueError(f"{field} is required")
    if BOT_RE.search(actor):
        raise ValueError(f"{field} must be a human reviewer/submission actor, not a bot: {actor}")
    return actor


def _existing_values(rows: list[Any], key: str) -> set[str]:
    values: set[str] = set()
    for row in rows:
        normalized = evidence.normalize_row(row)
        value = str(normalized.get(key) or "").strip()
        if value:
            values.add(value)
    return values


def reviewed_scoreboard_update(
    scoreboard: dict[str, Any],
    *,
    issue_body: str,
    issue_url: str,
    github_actor: str,
    reviewer: str,
    internal_actors: str | set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return (updated_scoreboard, appended_row, evaluation) after review.

    Raises ValueError if the row cannot be safely counted. The returned
    scoreboard has row-derived aggregate fields synchronized.
    """
    reviewer_actor = _normalize_actor(reviewer, "reviewer")
    submitter_actor = _normalize_actor(github_actor, "github_actor")
    if reviewer_actor.lower() == submitter_actor.lower():
        raise ValueError("reviewer must be different from github_actor; self-reviewed first-10 rows cannot count")

    blocked = _blocked_actors(internal_actors)
    row = issue_import.row_from_issue_body(
        issue_body,
        issue_url=issue_url,
        github_actor=submitter_actor,
        internal_actors=blocked,
    )

    existing_rows = list(scoreboard.get("rows") or [])
    user_id = str(row.get("user_id_pseudonym") or "").strip()
    evidence_uri = str(row.get("external_user_evidence_uri") or "").strip()
    if user_id and user_id in _existing_values(existing_rows, "user_id_pseudonym"):
        raise ValueError(f"duplicate user_id_pseudonym already exists in scoreboard: {user_id}")
    if evidence_uri and evidence_uri in _existing_values(existing_rows, "external_user_evidence_uri"):
        raise ValueError(f"duplicate external_user_evidence_uri already exists in scoreboard: {evidence_uri}")

    candidate = copy.deepcopy(scoreboard)
    candidate.setdefault("columns", evidence.DEFAULT_COLUMNS)
    candidate.setdefault("rows", []).append(row)
    updated = evidence.scoreboard_with_derived_fields(candidate)
    evaluation = evidence.evaluate_scoreboard(updated)
    if not evaluation["schema_valid"]:
        raise ValueError("reviewed row failed schema validation: " + json.dumps(evaluation["invalid_rows"], sort_keys=True))
    if not evaluation["stored_consistency"]["passed"]:
        raise ValueError("updated scoreboard aggregate consistency failed: " + json.dumps(evaluation["stored_consistency"], sort_keys=True))
    return updated, row, evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append a maintainer-reviewed first-10 evidence issue row to the scoreboard")
    parser.add_argument("--issue-body", required=True, help="Path to GitHub issue body markdown")
    parser.add_argument("--issue-url", required=True, help="Canonical https://github.com/borg-farther/Borg-Directory/issues/N URL")
    parser.add_argument("--github-actor", required=True, help="External GitHub actor that submitted the evidence issue")
    parser.add_argument("--reviewer", required=True, help="Human maintainer/reviewer approving the row for scoreboard inclusion")
    parser.add_argument("--internal-actors", default="", help="Comma-separated internal/maintainer submitter actors that cannot count as external evidence")
    parser.add_argument("--scoreboard", default=str(evidence.SCOREBOARD), help="Scoreboard JSON to read")
    parser.add_argument("--output", default="", help="Scoreboard JSON output path; defaults to --scoreboard")
    parser.add_argument("--write", action="store_true", help="Write the updated scoreboard only after validation passes")
    args = parser.parse_args(argv)

    scoreboard_path = Path(args.scoreboard)
    output_path = Path(args.output) if args.output else scoreboard_path
    scoreboard = json.loads(scoreboard_path.read_text(encoding="utf-8"))
    issue_body = Path(args.issue_body).read_text(encoding="utf-8", errors="replace")

    try:
        updated, row, evaluation = reviewed_scoreboard_update(
            scoreboard,
            issue_body=issue_body,
            issue_url=args.issue_url,
            github_actor=args.github_actor,
            reviewer=args.reviewer,
            internal_actors=args.internal_actors,
        )
    except ValueError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1

    if args.write:
        output_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "passed": True,
                "write_performed": bool(args.write),
                "output": str(output_path),
                "row": row,
                "evaluation": evaluation,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
