#!/usr/bin/env python3
"""Read-only release governance gate for Borg.

The gate intentionally separates two facts:
1. repository source/tests may be green, and
2. GitHub branch/release controls are actually enforced server-side.

It fails closed when `main` is unprotected, exact required status checks are
absent, CODEOWNERS review is not enforced, CODEOWNERS owners are invalid, or
high-risk bypasses such as force-push/deletion allowances are enabled. It does
not mutate GitHub settings.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# These are the exact GitHub Actions check-run contexts observed on protected
# commits. Workflow display names such as "CI" are not sufficient branch
# protection contexts; requiring non-existent broad labels can deadlock merges
# while still looking plausible in docs.
DEFAULT_REQUIRED_CHECKS = [
    "test (3.10)",
    "test (3.11)",
    "test (3.12)",
    "dependency-audit",
    "policy-check",
    "secret-scan",
    "static-security",
    "ops-readiness-watchdog",
    "old-account-reference",
]


def _enabled(value: Any) -> bool | None:
    if isinstance(value, dict):
        enabled = value.get("enabled")
        return enabled if isinstance(enabled, bool) else None
    if isinstance(value, bool):
        return value
    return None


def _protection_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    protection = payload.get("protection")
    if isinstance(protection, dict) and protection:
        return protection
    # Accept the full `/branches/{branch}/protection` payload as well as the
    # abbreviated `/branches/{branch}` payload used by older tests/snapshots.
    if "required_status_checks" in payload or "required_pull_request_reviews" in payload:
        return payload
    return {}


def _observed_status_contexts(required_status: dict[str, Any]) -> set[str]:
    observed = {str(item) for item in (required_status.get("contexts") or []) if item}
    for check in required_status.get("checks") or []:
        if isinstance(check, dict) and check.get("context"):
            observed.add(str(check["context"]))
    return observed


def _codeowners_error_summary(errors: list[Any]) -> list[str]:
    summary: list[str] = []
    for error in errors:
        if isinstance(error, dict):
            path = error.get("path") or "CODEOWNERS"
            line = error.get("line") or "?"
            kind = error.get("kind") or "error"
            message = error.get("message") or "CODEOWNERS validation error"
            summary.append(f"{path}:{line}: {kind}: {message}")
        else:
            summary.append(str(error))
    return summary


def _bypass_allowance_count(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    total = 0
    for key in ["users", "teams", "apps"]:
        items = value.get(key) or []
        if isinstance(items, list):
            total += len(items)
        elif items:
            total += 1
    return total


def _non_empty_bypass_allowances(*values: Any) -> list[str]:
    names = [
        "pull_request_review_bypass_allowances",
        "branch_bypass_allowances",
        "force_push_bypass_allowances",
        "deletion_bypass_allowances",
    ]
    return [name for name, value in zip(names, values) if _bypass_allowance_count(value) > 0]


def evaluate_branch_payload(
    payload: dict[str, Any],
    *,
    required_checks: list[str] | None = None,
    codeowners_errors: list[Any] | None = None,
    require_codeowners_validation: bool = False,
) -> dict[str, Any]:
    required_checks = required_checks or DEFAULT_REQUIRED_CHECKS
    blockers: list[str] = []

    protection = _protection_from_payload(payload)
    protected = payload.get("protected")
    if protected is None and protection:
        # Full branch-protection endpoint payloads do not include a `protected`
        # boolean. If protection settings are present, treat the branch as
        # protected for evaluation purposes.
        protected = True

    if protected is not True:
        blockers.append("main branch is not protected")

    if protected is True and not protection:
        blockers.append("branch protection details are missing")

    required_status = protection.get("required_status_checks") or {}
    observed = _observed_status_contexts(required_status)
    missing_checks = [check for check in required_checks if check not in observed]
    unexpected_checks = sorted(observed - set(required_checks))
    if protected is True and missing_checks:
        blockers.append(f"branch protection missing required checks: {', '.join(missing_checks)}")
    if protected is True and unexpected_checks:
        blockers.append(f"branch protection has unexpected required checks: {', '.join(unexpected_checks)}")
    if protected is True and required_status.get("strict") is not True:
        blockers.append("branch protection required status checks are not strict")

    required_reviews = protection.get("required_pull_request_reviews") or {}
    if protected is True and required_reviews.get("require_code_owner_reviews") is not True:
        blockers.append("branch protection does not require CODEOWNERS review")
    approving_reviews = required_reviews.get("required_approving_review_count")
    if protected is True and not (isinstance(approving_reviews, int) and approving_reviews >= 1):
        blockers.append("branch protection requires fewer than 1 approving review")
    if protected is True and required_reviews.get("dismiss_stale_reviews") is not True:
        blockers.append("branch protection does not dismiss stale reviews")
    if protected is True and required_reviews.get("require_last_push_approval") is not True:
        blockers.append("branch protection does not require last-push approval")

    if protected is True and _enabled(protection.get("enforce_admins")) is not True:
        blockers.append("branch protection does not enforce rules for admins")
    if protected is True and _enabled(protection.get("required_conversation_resolution")) is not True:
        blockers.append("branch protection does not require conversation resolution")
    if protected is True and _enabled(protection.get("allow_force_pushes")) is True:
        blockers.append("branch protection allows force pushes")
    if protected is True and _enabled(protection.get("allow_deletions")) is True:
        blockers.append("branch protection allows branch deletion")

    bypass_allowances = _non_empty_bypass_allowances(
        required_reviews.get("bypass_pull_request_allowances"),
        protection.get("bypass_pull_request_allowances"),
        protection.get("bypass_force_push_allowances"),
        protection.get("bypass_deletion_allowances"),
    )
    if protected is True and bypass_allowances:
        blockers.append(f"branch protection has bypass allowances: {', '.join(bypass_allowances)}")

    codeowners_checked = codeowners_errors is not None
    codeowners_error_summaries = _codeowners_error_summary(codeowners_errors or [])
    if require_codeowners_validation and not codeowners_checked:
        blockers.append("CODEOWNERS validation errors were not checked")
    if codeowners_error_summaries:
        blockers.append(f"CODEOWNERS validation has errors: {len(codeowners_error_summaries)}")

    return {
        "schema_version": 1,
        "passed": not blockers,
        "blockers": blockers,
        "protected": protected,
        "required_checks_observed": sorted(observed),
        "required_checks_expected": required_checks,
        "strict_required_status_checks": required_status.get("strict"),
        "codeowners_review_required": required_reviews.get("require_code_owner_reviews"),
        "required_approving_review_count": approving_reviews,
        "dismiss_stale_reviews": required_reviews.get("dismiss_stale_reviews"),
        "require_last_push_approval": required_reviews.get("require_last_push_approval"),
        "enforce_admins": _enabled(protection.get("enforce_admins")),
        "required_conversation_resolution": _enabled(protection.get("required_conversation_resolution")),
        "allow_force_pushes": _enabled(protection.get("allow_force_pushes")),
        "allow_deletions": _enabled(protection.get("allow_deletions")),
        "bypass_allowances": bypass_allowances,
        "codeowners_errors_checked": codeowners_checked,
        "codeowners_error_count": len(codeowners_error_summaries),
        "codeowners_errors": codeowners_error_summaries,
    }


def _github_env_token_candidates() -> list[str]:
    """Return environment token candidates without logging or persisting secrets."""
    candidates: list[str] = []
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        token = os.environ.get(name)
        if token and token not in candidates:
            candidates.append(token)
    return candidates


def _github_cli_token_candidate() -> str | None:
    """Return the gh CLI stored token without letting stale env tokens override it.

    CI normally provides `GITHUB_TOKEN`. Local operator shells often only have
    `gh` authenticated, while a stale exported `GITHUB_TOKEN` can produce 401s.
    GitHub CLI itself honors those env vars, so sanitize them before asking for
    the stored operator token. The token is never printed or persisted.
    """
    if shutil.which("gh"):
        try:
            clean_env = {key: value for key, value in os.environ.items() if key not in {"GITHUB_TOKEN", "GH_TOKEN"}}
            proc = subprocess.run(
                ["gh", "auth", "token"],
                check=False,
                capture_output=True,
                env=clean_env,
                text=True,
                timeout=10,
            )
            token = proc.stdout.strip() if proc.returncode == 0 else ""
            return token or None
        except (OSError, subprocess.SubprocessError):
            return None
    return None


# D-017: the watchdog's live branch-protection check intermittently hits GitHub
# rate limits (HTTP 403, occasionally 429/5xx) and turned the whole required
# check red. These are transient: retry with backoff, honoring Retry-After /
# x-ratelimit-reset when GitHub provides them. 401 is NOT retried — it means
# "wrong token" and the caller's token-candidate fallthrough must run instead.
_RETRYABLE_HTTP_CODES = {403, 429, 500, 502, 503, 504}
_MAX_FETCH_ATTEMPTS = 4
_MAX_RETRY_DELAY_SECONDS = 60.0


def _retry_delay_seconds(exc: urllib.error.HTTPError, attempt: int) -> float:
    headers = getattr(exc, "headers", None)
    if headers is not None:
        retry_after = str(headers.get("Retry-After") or "").strip()
        if retry_after.isdigit():
            return min(float(retry_after), _MAX_RETRY_DELAY_SECONDS)
        if str(headers.get("x-ratelimit-remaining") or "").strip() == "0":
            reset = str(headers.get("x-ratelimit-reset") or "").strip()
            if reset.isdigit():
                delay = float(reset) - time.time()
                if delay > 0:
                    return min(delay, _MAX_RETRY_DELAY_SECONDS)
    return min(float(2**attempt), _MAX_RETRY_DELAY_SECONDS)


def _urlopen_json_with_retry(request: urllib.request.Request) -> dict[str, Any]:
    """GET JSON with bounded retry/backoff on transient GitHub failures."""
    for attempt in range(1, _MAX_FETCH_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310 - fixed GitHub API host
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in _RETRYABLE_HTTP_CODES and attempt < _MAX_FETCH_ATTEMPTS:
                time.sleep(_retry_delay_seconds(exc, attempt))
                continue
            raise
        except urllib.error.URLError:
            if attempt < _MAX_FETCH_ATTEMPTS:
                time.sleep(min(float(2**attempt), _MAX_RETRY_DELAY_SECONDS))
                continue
            raise
    raise RuntimeError("unreachable: retry loop must return or raise")


def _github_get_json(path: str) -> dict[str, Any]:
    url = f"https://api.github.com/{path.lstrip('/')}"
    base_headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "borg-release-governance-gate",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    last_unauthorized: urllib.error.HTTPError | None = None
    attempted_tokens = set()
    for token in _github_env_token_candidates():
        headers = dict(base_headers)
        headers["Authorization"] = f"Bearer {token}"
        attempted_tokens.add(token)
        request = urllib.request.Request(url, headers=headers)
        try:
            return _urlopen_json_with_retry(request)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                last_unauthorized = exc
                continue
            raise
    gh_token = _github_cli_token_candidate()
    if gh_token and gh_token not in attempted_tokens:
        headers = dict(base_headers)
        headers["Authorization"] = f"Bearer {gh_token}"
        request = urllib.request.Request(url, headers=headers)
        try:
            return _urlopen_json_with_retry(request)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                last_unauthorized = exc
            else:
                raise
    request = urllib.request.Request(url, headers=dict(base_headers))
    try:
        return _urlopen_json_with_retry(request)
    except urllib.error.HTTPError as exc:
        if exc.code == 401 and last_unauthorized is not None:
            raise last_unauthorized
        raise


def fetch_branch_payload(repo: str, branch: str) -> dict[str, Any]:
    return _github_get_json(f"repos/{repo}/branches/{branch}")


def fetch_branch_protection_payload(repo: str, branch: str) -> dict[str, Any]:
    return _github_get_json(f"repos/{repo}/branches/{branch}/protection")


def fetch_live_branch_payload(repo: str, branch: str) -> dict[str, Any]:
    payload = fetch_branch_payload(repo, branch)
    if payload.get("protected") is True:
        payload = dict(payload)
        payload["protection"] = fetch_branch_protection_payload(repo, branch)
    return payload


def fetch_codeowners_errors(repo: str, ref: str | None = None) -> list[Any]:
    try:
        path = f"repos/{repo}/codeowners/errors"
        if ref:
            path += "?ref=" + urllib.parse.quote(ref, safe="")
        data = _github_get_json(path)
    except urllib.error.HTTPError as exc:  # pragma: no cover - permission/rate-limit dependent
        return [{"path": ".github/CODEOWNERS", "line": "?", "kind": f"HTTP {exc.code}", "message": "CODEOWNERS validation endpoint could not be fetched"}]
    errors = data.get("errors") or []
    return errors if isinstance(errors, list) else [errors]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Borg GitHub branch/release governance")
    parser.add_argument("--repo", default="borg-farther/Borg-Directory")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--snapshot", help="Use a saved GitHub branch/protection API payload instead of fetching live")
    parser.add_argument("--output", help="Write the evaluated governance snapshot JSON to this path")
    parser.add_argument("--required-check", action="append", dest="required_checks")
    args = parser.parse_args(argv)

    codeowners_errors: list[Any] | None = None
    require_codeowners_validation = False
    try:
        if args.snapshot:
            payload = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
            require_codeowners_validation = True
            if "codeowners_errors" in payload:
                raw_errors = payload.get("codeowners_errors") or []
                codeowners_errors = raw_errors if isinstance(raw_errors, list) else [raw_errors]
        else:
            payload = fetch_live_branch_payload(args.repo, args.branch)
            codeowners_errors = fetch_codeowners_errors(args.repo, ref=args.branch)
            require_codeowners_validation = True
        result = evaluate_branch_payload(
            payload,
            required_checks=args.required_checks or DEFAULT_REQUIRED_CHECKS,
            codeowners_errors=codeowners_errors,
            require_codeowners_validation=require_codeowners_validation,
        )
    except Exception as exc:
        # Still write a fresh, explicit failure snapshot when the live GitHub
        # fetch or snapshot parse fails. Otherwise downstream gates can keep
        # consuming a stale prior release_governance_snapshot.json and mask the
        # fact that governance evidence was unavailable.
        result = {
            "schema_version": 1,
            "passed": False,
            "blockers": [f"release governance evidence unavailable: {exc}"],
            "protected": None,
            "required_checks_observed": [],
            "required_checks_expected": args.required_checks or DEFAULT_REQUIRED_CHECKS,
            "strict_required_status_checks": None,
            "codeowners_review_required": None,
            "required_approving_review_count": None,
            "dismiss_stale_reviews": None,
            "require_last_push_approval": None,
            "enforce_admins": None,
            "required_conversation_resolution": None,
            "allow_force_pushes": None,
            "allow_deletions": None,
            "bypass_allowances": [],
            "codeowners_errors_checked": codeowners_errors is not None,
            "codeowners_error_count": 0,
            "codeowners_errors": [],
        }
    result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["repo"] = args.repo
    result["branch"] = args.branch
    result["source"] = "snapshot" if args.snapshot else "github_api"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
