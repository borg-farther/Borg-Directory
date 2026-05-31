#!/usr/bin/env python3
"""Read-only release governance gate for Borg.

The gate intentionally separates two facts:
1. repository source/tests may be green, and
2. GitHub branch/release controls are actually enforced server-side.

It fails closed when `main` is unprotected, required status checks are absent, or
release governance evidence is missing. It does not mutate GitHub settings.
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_REQUIRED_CHECKS = [
    "CI",
    "Borg Security Gates",
    "Self-service readiness watchdog",
    "Account Reference Firewall",
]


def evaluate_branch_payload(
    payload: dict[str, Any],
    *,
    required_checks: list[str] | None = None,
) -> dict[str, Any]:
    required_checks = required_checks or DEFAULT_REQUIRED_CHECKS
    blockers: list[str] = []
    if payload.get("protected") is not True:
        blockers.append("main branch is not protected")

    protection = payload.get("protection") or {}
    if payload.get("protected") is True and not protection:
        blockers.append("branch protection details are missing")
    required_status = protection.get("required_status_checks") or {}
    contexts = set(required_status.get("contexts") or [])
    checks = set()
    for check in required_status.get("checks") or []:
        if isinstance(check, dict) and check.get("context"):
            checks.add(str(check["context"]))
    observed = contexts | checks
    missing_checks = [check for check in required_checks if not any(check in item for item in observed)]
    if payload.get("protected") is True and missing_checks:
        blockers.append(f"branch protection missing required checks: {', '.join(missing_checks)}")

    required_reviews = protection.get("required_pull_request_reviews") or {}
    if payload.get("protected") is True and required_reviews.get("require_code_owner_reviews") is not True:
        blockers.append("branch protection does not require CODEOWNERS review")

    return {
        "schema_version": 1,
        "passed": not blockers,
        "blockers": blockers,
        "protected": payload.get("protected"),
        "required_checks_observed": sorted(observed),
        "required_checks_expected": required_checks,
        "codeowners_review_required": required_reviews.get("require_code_owner_reviews"),
    }


def fetch_branch_payload(repo: str, branch: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/branches/{branch}"
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "borg-release-governance-gate"})
    with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310 - fixed GitHub API URL built from CLI repo/branch
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Borg GitHub branch/release governance")
    parser.add_argument("--repo", default="borg-farther/Borg-Directory")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--snapshot", help="Use a saved GitHub branch API payload instead of fetching live")
    parser.add_argument("--required-check", action="append", dest="required_checks")
    args = parser.parse_args(argv)

    if args.snapshot:
        payload = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    else:
        payload = fetch_branch_payload(args.repo, args.branch)
    result = evaluate_branch_payload(payload, required_checks=args.required_checks or DEFAULT_REQUIRED_CHECKS)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
