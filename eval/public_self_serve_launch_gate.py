#!/usr/bin/env python3
"""Compile Borg public self-serve launch readiness.

This is the canonical hard gate for broad public self-serve. It is intentionally
stricter than local first-user or synthetic load gates: it requires row-derived
external-user evidence, PyPI latest/fresh-install proof, MCP stdio canary proof,
and docs/claim consistency. It returns nonzero until those are all true.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.first_10_evidence import evaluate_scoreboard
from eval import release_governance_gate, self_service_ops_gate, served_runtime_gate

SNAPSHOT = ROOT / "eval" / "public_self_serve_launch_gate_snapshot.json"
REPORT = ROOT / "docs" / "PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"
EXPECTED_PYPI_SUMMARY = "Failure memory CLI and MCP server for AI coding agents"
REQUIRED_PYPI_KEYWORD = "failure-memory"
BANNED_PYPI_KEYWORDS = {"collective-memory"}
BANNED_PYPI_COPY = [
    "Collective memory MCP server",
    "Semantic reasoning cache",
    "Collective Intelligence for AI Agents",
    "collective intelligence for AI agents",
]

REQUIRED_COLD_START_TRUST_CHECKS = {
    "meta_permission_mentions_are_not_permission_tasks",
    "meta_django_mentions_do_not_set_django_tech",
    "high_similarity_meta_only_trace_rejected",
    "irrelevant_real_trace_only_guidance_not_injectable",
    "concrete_permission_signal_still_allowed",
    "stdio_meta_trust_prompt_fails_closed",
    "stdio_concrete_permission_prompt_gets_specific_guidance",
}

CURRENT_CLAIM_DOCS = [
    Path("README.md"),
    Path("AGENTS.md"),
    Path("llms.txt"),
    Path("SUPPORT.md"),
    Path("SECURITY.md"),
    Path("PROJECT_STATUS.md"),
    Path("GO_NO_GO_DECISION.md"),
    Path("UAT_RESULTS.md"),
    Path("docs/README.md"),
    Path("docs/READINESS.md"),
    Path("docs/INSTALL.md"),
    Path("docs/QUICKSTART.md"),
    Path("docs/TRYING_BORG.md"),
    Path("docs/MCP_SETUP.md"),
    Path("docs/ONBOARDING.md"),
    Path("docs/FIRST_10_BETA_READINESS.md"),
    Path("docs/20260514_FIRST_10_USER_INVITE_PACKET.md"),
    Path("docs/20260514_PUBLIC_SELF_SERVE_LAUNCH_CLOSURE_PLAN.md"),
    Path("docs/20260517_BORG_100_REAL_USER_READINESS.md"),
    Path("docs/ROADMAP.md"),
    Path("docs/20260522_BORG_PRODUCTION_DAY_ONE_HARDENING_PLAN.md"),
    Path("docs/PUBLIC_SELF_SERVE_LAUNCH_GO_NO_GO.md"),
    Path("docs/VALUE_COMMUNICATION_DASHBOARD.md"),
    Path("docs/VALUE_COMMUNICATION_DASHBOARD.html"),
    Path("docs/SELF_SERVICE_OPS_READINESS.md"),
    Path("docs/SELF_SERVICE_OPS_READINESS_REPORT.md"),
    Path("docs/FIRST_10_EVIDENCE_INTAKE.md"),
    Path("docs/ROLLBACK_AND_COMMS_RUNBOOK.md"),
    Path("docs/COLD_START_TRUST_HARDENING.md"),
    Path("docs/LIVE_MCP_SELF_SERVE_CANARY.md"),
    Path("docs/20260526_7_USER_CONTROLLED_LAUNCH_AND_100_USER_STAGE_GATES.md"),
    Path("docs/BORG_PROOF_DASHBOARD.md"),
    Path("docs/BORG_PROOF_DASHBOARD.html"),
    Path("docs/public/proof-dashboard/index.html"),
    Path("docs/SECURITY_HARDENING_BASELINE.md"),
    Path("docs/PRIVACY_MODEL.md"),
    Path("docs/PROMPT_INJECTION_THREAT_MODEL.md"),
    Path("docs/TRUST_AND_PROMOTION.md"),
    Path("docs/REVOCATION_AND_DELETION.md"),
    Path("docs/LEARNING_ATOM_SCHEMA.md"),
    Path("eval/borg_proof_dashboard.json"),
]

UNSUPPORTED_WHEN_BLOCKED = [
    (re.compile(r"(?i)public\s+self[- ]serve\s+launch\s*[:\-]\s*(?:\*\*)?\s*(go|yes|ship|ready|approved)\b"), "public self-serve launch GO/ready claim"),
    (re.compile(r"(?im)^\s*Decision\s*:\s*(?:\*\*)?\s*(go|yes|ready)\b"), "unqualified GO/ready decision claim"),
    (re.compile(r"(?i)\bdecision\s*[:\-]\s*(?:\*\*)?\s*ship\b"), "unqualified SHIP decision claim"),
    (re.compile(r"(?i)\bcompletion\s+lift\s*[:\-].*\+\d+%"), "completion-lift claim without external evidence"),
    (re.compile(r"(?i)\bstatistically\s+significant\b.*\b(agent|external|lift|completion)"), "statistically significant external/agent lift claim"),
    (re.compile(r"(?i)\bfrontier[- ]better[- ]than\b.*\b(proven|yes|true|go)"), "frontier-better-than proven claim"),
    (re.compile(r"(?i)Ready\s+to\s+share\s+Git\s+now\?\W{0,80}YES"), "stale Git-sharing YES claim"),
    (re.compile(r"(?i)version_package"), "stale proof-dashboard version metric"),
    (re.compile(r"\bready_for_(?:10|1000)=True\b"), "unqualified logical-load readiness claim"),
]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def source_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def fetch_pypi_latest(package: str = "agent-borg", timeout: int = 30) -> dict[str, Any]:
    url = f"https://pypi.org/pypi/{package}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "Borg-public-self-serve-gate/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        "package": package,
        "url": url,
        "version": data.get("info", {}).get("version"),
        "summary": data.get("info", {}).get("summary") or "",
        "keywords": data.get("info", {}).get("keywords") or "",
        "project_urls": data.get("info", {}).get("project_urls") or {},
        "requires_dist": data.get("info", {}).get("requires_dist") or [],
    }


def pypi_latest_check(expected_version: str, *, fetch_network: bool = True, pypi_data: dict[str, Any] | None = None) -> dict[str, Any]:
    if pypi_data is None and fetch_network:
        try:
            pypi_data = fetch_pypi_latest()
        except Exception as exc:  # pragma: no cover - network failure shape is environment-specific
            return {"passed": False, "error": str(exc), "expected_version": expected_version}
    elif pypi_data is None:
        return {"passed": False, "error": "network disabled and no PyPI data provided", "expected_version": expected_version}

    project_urls = pypi_data.get("project_urls") or {}
    required_urls = {
        "Homepage": "https://github.com/borg-farther/Borg-Directory",
        "Repository": "https://github.com/borg-farther/Borg-Directory",
        "Documentation": "https://github.com/borg-farther/Borg-Directory#readme",
        "Issues": "https://github.com/borg-farther/Borg-Directory/issues",
    }
    url_missing = sorted(set(required_urls) - set(project_urls))
    url_mismatches = {
        key: {"expected": expected, "actual": project_urls.get(key)}
        for key, expected in required_urls.items()
        if project_urls.get(key) != expected
    }
    latest = pypi_data.get("version")
    summary = str(pypi_data.get("summary") or "")
    keywords = {
        token.strip()
        for token in re.split(r"[,\s]+", str(pypi_data.get("keywords") or ""))
        if token.strip()
    }
    stale_copy = [snippet for snippet in BANNED_PYPI_COPY if snippet in summary]
    keyword_missing = REQUIRED_PYPI_KEYWORD not in keywords
    banned_keywords_present = sorted(keywords & BANNED_PYPI_KEYWORDS)
    passed = (
        latest == expected_version
        and not url_missing
        and not url_mismatches
        and summary == EXPECTED_PYPI_SUMMARY
        and not keyword_missing
        and not banned_keywords_present
        and not stale_copy
    )
    return {
        "passed": passed,
        "package": pypi_data.get("package", "agent-borg"),
        "latest_version": latest,
        "expected_version": expected_version,
        "summary": summary,
        "expected_summary": EXPECTED_PYPI_SUMMARY,
        "keywords": sorted(keywords),
        "keyword_missing": keyword_missing,
        "banned_keywords_present": banned_keywords_present,
        "stale_copy": stale_copy,
        "url_missing": url_missing,
        "url_mismatches": url_mismatches,
        "requires_dist": pypi_data.get("requires_dist") or [],
        "project_urls": project_urls,
    }


def first_user_release_check(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    results = data.get("results") or []
    failures = [item.get("name") for item in results if not item.get("passed")]
    return {
        "passed": bool(data.get("success")) and not failures,
        "exists": bool(data),
        "generated_at_utc": data.get("generated_at_utc"),
        "passed_count": sum(1 for item in results if item.get("passed")),
        "failed_count": len(failures),
        "failures": failures,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
    }


def pypi_fresh_install_check(path: Path, expected_version: str) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {"passed": False, "exists": False, "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path), "error": "missing PyPI fresh-install snapshot"}
    results = data.get("results") or []
    failures = [item.get("name") for item in results if not item.get("passed")]
    mcp = data.get("mcp_stdio_canary") or {}
    passed = bool(data.get("success")) and data.get("version") == expected_version and not failures and bool(mcp.get("passed"))
    return {
        "passed": passed,
        "exists": True,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "generated_at_utc": data.get("generated_at_utc"),
        "version": data.get("version"),
        "expected_version": expected_version,
        "failed_count": len(failures),
        "failures": failures,
        "mcp_stdio_canary_passed": bool(mcp.get("passed")),
        "mcp_server_info": mcp.get("server_info"),
    }


def _line_names_post_package_blocker(line_text: str) -> bool:
    """True when docs block beta on non-package release controls.

    After PyPI/fresh-install canaries are green, stale docs that still say beta
    is blocked by package proof should fail. Honest docs that say package proof
    is green but beta is blocked by served-runtime freshness, release
    governance, or branch protection should pass.
    """
    lower = line_text.lower()
    release_control_terms = [
        "served-runtime",
        "served runtime",
        "runtime fingerprint",
        "release-governance",
        "release governance",
        "release control",
        "branch protection",
        "main is unprotected",
        "main` is unprotected",
        "main branch is not protected",
        "github `main` is unprotected",
    ]
    return any(term in lower for term in release_control_terms)


def docs_claim_guard(
    paths: list[Path],
    expected_version: str,
    *,
    public_evidence_ready: bool,
    package_evidence_ready: bool = True,
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    checked: list[str] = []
    for rel in paths:
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(str(rel))

        for match in re.finditer(r"agent-borg==(?P<version>\d+\.\d+\.\d+)", text):
            if match.group("version") != expected_version:
                violations.append({
                    "path": str(rel),
                    "kind": "stale agent-borg pin",
                    "detail": f"found agent-borg=={match.group('version')} expected agent-borg=={expected_version}",
                })

        stale_release_tokens = [
            (r"BORG_338_RELEASE_PREFLIGHT", "stale 3.3.8 release-proof reference"),
            (r"release_preflight_3_3_8", "stale 3.3.8 release-preflight snapshot reference"),
            (r"serverInfo\.version\s*==\s*3\.3\.8", "stale MCP version claim"),
            (r"BORG_339_RELEASE_PREFLIGHT", "stale 3.3.9 release-proof reference"),
            (r"serverInfo\.version\s*==\s*3\.3\.9", "stale MCP version claim"),
        ]
        for pattern, label in stale_release_tokens:
            match = re.search(pattern, text)
            if match:
                violations.append({"path": str(rel), "kind": label, "detail": match.group(0)[:180]})

        if re.search(r"(?im)^\s*(?:python\s+-m\s+)?pipx\s+install\s+git\+https://github\.com/borg-farther/Borg-Directory\.git\b", text):
            violations.append({"path": str(rel), "kind": "public git+ install path", "detail": "current public first-user docs must use PyPI agent-borg, not git+ source install"})

        if not public_evidence_ready:
            for pattern, label in UNSUPPORTED_WHEN_BLOCKED:
                match = pattern.search(text)
                if match:
                    line = text[: match.start()].count("\n") + 1
                    line_text = text.splitlines()[line - 1] if line - 1 < len(text.splitlines()) else match.group(0)
                    negated = re.search(r"(?i)\b(not claimed|not proven|unproven|no claim|does not claim|without claiming)\b", line_text)
                    if "statistically significant" in label and negated:
                        continue
                    violations.append({"path": str(rel), "line": line, "kind": label, "detail": match.group(0)[:180]})

        if not package_evidence_ready:
            blocked_package_claims = [
                (r"(?i)Package infrastructure is green for \*\*controlled first-10 public-package beta\*\*", "controlled beta package infrastructure green before PyPI canary"),
                (r"(?i)Published controlled-beta package line:\s*`?agent-borg==", "published controlled-beta package line before PyPI canary"),
                (r"(?i)production PyPI upload and fresh-install \+ stdio MCP canary are green", "production PyPI canary green before PyPI canary"),
                (r"(?i)Ready to invite .*controlled .*beta testers", "ready-to-invite claim before PyPI canary"),
                (r"(?i)controlled first-10 beta invites may start", "controlled beta invites-may-start before PyPI canary"),
                (r"(?i)CONDITIONAL GO for controlled first-10", "controlled first-10 conditional GO before PyPI canary"),
                (r"(?i)PyPI latest metadata, fresh PyPI install, stdio MCP canary, GitHub CI/security gates, and source/local first-user gates passed", "package canaries-passed claim before PyPI canary"),
            ]
            for pattern, label in blocked_package_claims:
                match = re.search(pattern, text)
                if match:
                    line = text[: match.start()].count("\n") + 1
                    violations.append({
                        "path": str(rel),
                        "line": line,
                        "kind": label,
                        "detail": text.splitlines()[line - 1][:180] if line - 1 < len(text.splitlines()) else match.group(0)[:180],
                    })

            for line_number, line_text in enumerate(text.splitlines(), start=1):
                lower = line_text.lower()
                claims_controlled_go = (
                    "controlled first-10" in lower
                    and "go" in lower
                    and "no-go" not in lower
                    and not re.search(r"(?i)\b(after|until|pending|not yet|only after)\b", line_text)
                )
                claims_controlled_ready = (
                    "controlled first-10" in lower
                    and re.search(r"(?i)\b(ready|share|sharing)\b", line_text)
                    and "no-go" not in lower
                    and not re.search(r"(?i)\b(after|until|pending|not yet|not ready|blocked|only after)\b", line_text)
                )
                claims_package_green = (
                    "pypi latest" in lower
                    and "fresh-install" in lower
                    and "stdio mcp" in lower
                    and "green" in lower
                    and "not green" not in lower
                    and "not yet" not in lower
                    and not re.search(r"(?i)\b(after|until|pending|not yet|only after|before)\b", line_text)
                )
                claims_controlled_green = (
                    "controlled first-10" in lower
                    and "green" in lower
                    and "no-go" not in lower
                    and "not green" not in lower
                    and not re.search(r"(?i)\b(after|until|pending|not yet|only after|before|blocked)\b", line_text)
                )
                claims_invites_start = (
                    ("invite" in lower or "invites" in lower or "testers" in lower)
                    and ("may start" in lower or "ready to invite" in lower or "invite up to" in lower)
                    and "no-go" not in lower
                    and not re.search(r"(?i)\b(after|until|pending|not yet|only after|before|blocked|do not|no invites)\b", line_text)
                )
                if claims_controlled_go or claims_controlled_ready or claims_package_green or claims_controlled_green or claims_invites_start:
                    violations.append({
                        "path": str(rel),
                        "line": line_number,
                        "kind": "controlled first-10 package GO before PyPI canary",
                        "detail": line_text[:180],
                    })

        if package_evidence_ready:
            stale_package_blockers_after_release = [
                (r"(?i)NO-GO for this source revision\W{0,40}until .*PyPI", "stale package NO-GO after PyPI canary"),
                (r"(?i)blocked for `?agent-borg==" + re.escape(expected_version) + r"`? until PyPI", "stale package-blocked wording after PyPI canary"),
                (r"(?i)(controlled first-10|controlled beta|public-package beta|package path|PyPI CLI|PyPI in active Python env).{0,180}(NO-GO|BLOCKED|blocked|not yet|until).{0,220}(PyPI|published|fresh[- ]install|canary|latest)", "stale controlled-beta package blocker after PyPI canary"),
                (r"(?i)(controlled first-10|controlled beta|public-package beta|PyPI beta|7 users).{0,180}(NO-GO|BLOCKED|blocked|not yet|until).{0,220}(package/proof chain|package proof|proof chain)", "stale package-proof-chain blocker after PyPI canary"),
                (r"(?i)(PyPI latest|production PyPI|fresh install|fresh-install|MCP stdio).{0,160}(not yet|not green|not current|does not match|prior release|stale|blocked)", "stale PyPI/fresh-install blocker after PyPI canary"),
                (r"(?i)Current package path status:.*not yet published/canaried", "stale unpublished package-path status after PyPI canary"),
                (r"(?i)controlled first-10 beta invites may not start.*until", "stale invite-start blocker after PyPI canary"),
                (r"(?i)source/local release[- ]candidate|source/local only|release[- ]candidate contract", "stale source/local-only wording after PyPI canary"),
                (r"(?i)until `?agent-borg==" + re.escape(expected_version) + r"`? is published", "stale unpublished-version wording after PyPI canary"),
                (r"(?i)PENDING until publish", "stale pending-publish wording after PyPI canary"),
                (r"(?i)before controlled beta resumes", "stale beta-resume blocker after PyPI canary"),
                (r"(?i)latest metadata does not match source version", "stale PyPI-latest mismatch blocker after PyPI canary"),
                (r"(?i)fresh install \+ MCP stdio canary is not green", "stale fresh-install blocker after PyPI canary"),
            ]
            for pattern, label in stale_package_blockers_after_release:
                match = re.search(pattern, text)
                if match:
                    line = text[: match.start()].count("\n") + 1
                    line_text = text.splitlines()[line - 1] if line - 1 < len(text.splitlines()) else match.group(0)
                    if _line_names_post_package_blocker(line_text):
                        continue
                    violations.append({
                        "path": str(rel),
                        "line": line,
                        "kind": label,
                        "detail": line_text[:180],
                    })

    return {"passed": not violations, "checked": checked, "violations": violations}


def first_10_evidence_check(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    if not data:
        return {"passed": False, "exists": False, "error": "missing first-10 scoreboard"}
    evidence = evaluate_scoreboard(data)
    passed = bool(evidence["schema_valid"] and evidence["thresholds_passed"] and evidence["stored_consistency"]["passed"])
    derived = evidence["derived_counts"]
    thresholds = evidence["thresholds"]
    return {
        "passed": passed,
        "exists": True,
        "row_count": evidence["row_count"],
        "counted_external_rows": evidence["counted_external_rows"],
        "derived_counts": derived,
        "thresholds": thresholds,
        "stored_consistency": evidence["stored_consistency"],
        "invalid_rows": evidence["invalid_rows"],
        "blockers": evidence["blockers"],
        "scoreboard_gate": (data.get("current_verdict") or {}).get("public_self_serve_launch_gate"),
    }


def cold_start_trust_check(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    rel_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    if not data:
        return {"passed": False, "exists": False, "path": rel_path, "error": "missing cold-start trust gate snapshot"}
    checks = data.get("checks") or []
    names = {str(item.get("name")) for item in checks if isinstance(item, dict)}
    missing = sorted(REQUIRED_COLD_START_TRUST_CHECKS - names)
    failed = [item.get("name") for item in checks if isinstance(item, dict) and not item.get("passed")]
    trust_policy = str(data.get("trust_policy") or "")
    has_feedback_path = isinstance(data.get("bad_answer_feedback_path"), dict) and bool(data.get("bad_answer_feedback_path"))
    passed = bool(
        data.get("passed")
        and checks
        and not missing
        and not failed
        and "fail closed" in trust_policy.lower()
        and has_feedback_path
    )
    return {
        "passed": passed,
        "exists": True,
        "path": rel_path,
        "generated_at_utc": data.get("generated_at_utc"),
        "failed_count": len(failed),
        "failures": failed,
        "missing_required_checks": missing,
        "required_check_count": len(REQUIRED_COLD_START_TRUST_CHECKS),
        "observed_check_count": len(names),
        "has_bad_answer_feedback_path": has_feedback_path,
        "trust_policy": data.get("trust_policy"),
    }


def self_service_ops_check() -> dict[str, Any]:
    data = self_service_ops_gate.compile_gate()
    return {
        "passed": bool(data.get("passed")),
        "generated_at_utc": data.get("generated_at_utc"),
        "blockers": data.get("blockers") or [],
        "rollout_policy": data.get("rollout_policy"),
        "snapshot": "eval/self_service_ops_gate_snapshot.json",
        "report": "docs/SELF_SERVICE_OPS_READINESS_REPORT.md",
    }


def ops_readiness_watchdog_check(path: Path) -> dict[str, Any]:
    data = _read_json(path)
    blockers = data.get("blockers") or []
    passed = bool(data.get("passed") is True and not blockers)
    return {
        "passed": passed,
        "generated_at_utc": data.get("generated_at_utc"),
        "blockers": blockers,
        "snapshot": "eval/ops_readiness_watchdog_snapshot.json",
        "truth_policy": data.get("truth_policy"),
    }


def served_runtime_freshness_check(path: Path, expected_version: str) -> dict[str, Any]:
    payload, read_error = served_runtime_gate._read_payload(path)
    result = served_runtime_gate.evaluate_snapshot(payload, expected_version=expected_version)
    if read_error:
        result["blockers"].insert(0, read_error)
        result["passed"] = False
    result["snapshot"] = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return result


def release_governance_check(*, fetch_network: bool = True) -> dict[str, Any]:
    snapshot_path = ROOT / "eval" / "release_governance_snapshot.json"
    blockers: list[str] = []
    payload: dict[str, Any] | None = None
    source = "snapshot"
    if snapshot_path.exists():
        try:
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            blockers.append(f"release governance snapshot unreadable: {exc}")
    elif fetch_network:
        source = "github_api"
        try:
            payload = release_governance_gate.fetch_branch_payload("borg-farther/Borg-Directory", "main")
        except Exception as exc:  # pragma: no cover - live GitHub/API failures vary by environment
            blockers.append(f"release governance live check failed: {exc}")
    else:
        blockers.append("release governance snapshot missing and network disabled")

    if payload is None:
        return {
            "schema_version": 1,
            "passed": False,
            "blockers": blockers or ["release governance evidence missing"],
            "snapshot": "eval/release_governance_snapshot.json",
            "source": source,
        }

    result = release_governance_gate.evaluate_branch_payload(payload)
    if blockers:
        result["blockers"] = blockers + list(result.get("blockers") or [])
        result["passed"] = False
    result["snapshot"] = "eval/release_governance_snapshot.json"
    result["source"] = source
    return result


def compile_gate(
    *,
    fetch_network: bool = True,
    pypi_data: dict[str, Any] | None = None,
    require_ops_watchdog: bool = True,
) -> dict[str, Any]:
    version = source_version()
    first_10 = first_10_evidence_check(ROOT / "eval" / "first_10_user_scoreboard.json")
    first_user = first_user_release_check(ROOT / "eval" / "first_user_release_gate_snapshot.json")
    pypi_latest = pypi_latest_check(version, fetch_network=fetch_network, pypi_data=pypi_data)
    pypi_fresh = pypi_fresh_install_check(ROOT / "eval" / "pypi_fresh_install_snapshot.json", version)
    cold_start_trust = cold_start_trust_check(ROOT / "eval" / "cold_start_trust_gate_snapshot.json")
    served_runtime = served_runtime_freshness_check(ROOT / "eval" / "served_runtime_fingerprint_snapshot.json", version)
    release_governance = release_governance_check(fetch_network=fetch_network)
    self_service_ops = self_service_ops_check()
    ops_watchdog = (
        ops_readiness_watchdog_check(ROOT / "eval" / "ops_readiness_watchdog_snapshot.json")
        if require_ops_watchdog
        else {
            "passed": True,
            "skipped": True,
            "snapshot": "eval/ops_readiness_watchdog_snapshot.json",
            "reason": "ops watchdog is evaluating this gate and applies its own freshness/consistency checks",
        }
    )
    package_evidence_ready = bool(pypi_latest["passed"] and pypi_fresh["passed"])
    reported_privacy_security_incidents = int((first_10.get("derived_counts") or {}).get("critical_privacy_security_failures") or 0)
    privacy_security_pause_clear = reported_privacy_security_incidents == 0
    docs = docs_claim_guard(
        CURRENT_CLAIM_DOCS,
        version,
        public_evidence_ready=first_10["passed"],
        package_evidence_ready=package_evidence_ready,
    )

    infrastructure_ready = bool(
        first_user["passed"]
        and package_evidence_ready
        and cold_start_trust["passed"]
        and served_runtime["passed"]
        and release_governance["passed"]
        and self_service_ops["passed"]
        and ops_watchdog["passed"]
        and docs["passed"]
        and privacy_security_pause_clear
    )
    public_self_serve_ready = bool(infrastructure_ready and first_10["passed"])
    blockers: list[str] = []
    if not first_user["passed"]:
        blockers.append("first-user local release gate snapshot is missing or failing")
    if not pypi_latest["passed"]:
        blockers.append("PyPI latest metadata does not match source version or required project URLs")
    if not pypi_fresh["passed"]:
        blockers.append("PyPI fresh-install + MCP stdio canary snapshot is missing or failing")
    if not cold_start_trust["passed"]:
        blockers.append("cold-start trust hardening gate snapshot is missing or failing")
    if not served_runtime["passed"]:
        blockers.extend(served_runtime.get("blockers") or ["served runtime freshness gate is missing or failing"])
    if not release_governance["passed"]:
        blockers.extend(release_governance.get("blockers") or ["release governance gate is missing or failing"])
    if not self_service_ops["passed"]:
        blockers.extend(self_service_ops.get("blockers") or ["self-service ops readiness gate is missing or failing"])
    if not ops_watchdog["passed"]:
        blockers.extend(ops_watchdog.get("blockers") or ["ops readiness watchdog snapshot is missing or failing"])
    if not docs["passed"]:
        blockers.append("public docs/claim guard found stale install pins or unsupported launch/value claims")
    if not privacy_security_pause_clear:
        blockers.append(
            "controlled first-10 beta is paused because first-10 evidence reports "
            f"{reported_privacy_security_incidents} privacy/security incident(s)"
        )
    if not first_10["passed"]:
        blockers.extend(first_10.get("blockers") or ["first-10 external-user evidence has not passed"])

    return {
        "schema_version": 1,
        "gate_type": "public_self_serve_launch",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": version,
        "ready_for_controlled_first_10_beta": infrastructure_ready,
        "ready_for_public_self_serve_launch": public_self_serve_ready,
        "max_recommended_real_users_now": 100 if public_self_serve_ready else 10 if infrastructure_ready else 0,
        "gates": {
            "first_user_release": first_user,
            "pypi_latest": pypi_latest,
            "pypi_fresh_install_and_mcp_stdio": pypi_fresh,
            "cold_start_trust_hardening": cold_start_trust,
            "served_runtime_freshness": served_runtime,
            "release_governance": release_governance,
            "self_service_ops_readiness": self_service_ops,
            "ops_readiness_watchdog": ops_watchdog,
            "docs_claim_guard": docs,
            "privacy_security_incident_pause": {
                "passed": privacy_security_pause_clear,
                "critical_privacy_security_failures": reported_privacy_security_incidents,
                "policy": "Any first-10 privacy/security incident pauses controlled beta until triaged, even before first-10 thresholds pass.",
            },
            "first_10_external_evidence": first_10,
        },
        "blockers": blockers,
        "truth_policy": "Public self-serve is GO only after PyPI/fresh-install/MCP/docs/cold-start-trust/served-runtime/release-governance/self-service-ops/watchdog gates pass AND row-derived first-10 external-user evidence passes. Synthetic users and aggregate-only edits never count.",
    }


def write_report(snapshot: dict[str, Any]) -> None:
    verdict = "GO" if snapshot["ready_for_public_self_serve_launch"] else "NO-GO"
    lines = [
        "# Borg public self-serve launch go/no-go",
        "",
        f"Generated: {snapshot['generated_at_utc']}",
        f"Source version: `{snapshot['source_version']}`",
        "",
        f"Public self-serve launch: **{verdict}**",
        f"Controlled first-10 beta infrastructure: **{'CONDITIONAL GO while gates remain green' if snapshot['ready_for_controlled_first_10_beta'] else 'NO-GO'}**",
        f"Max recommended real users now: **{snapshot['max_recommended_real_users_now']}**",
        "",
        "## Hard rule",
        "",
        snapshot["truth_policy"],
        "",
        "## Gate results",
        "",
    ]
    for name, gate in snapshot["gates"].items():
        lines.append(f"- `{name}`: `{'PASS' if gate.get('passed') else 'FAIL'}`")
    lines.extend(["", "## Blockers", ""])
    if snapshot["blockers"]:
        lines.extend(f"- {blocker}" for blocker in snapshot["blockers"])
    else:
        lines.append("None.")
    lines.extend([
        "",
        "## Evidence artifacts",
        "",
        "- `eval/public_self_serve_launch_gate_snapshot.json`",
        "- `eval/first_10_user_scoreboard.json`",
        "- `eval/pypi_fresh_install_snapshot.json`",
        "- `eval/first_user_release_gate_snapshot.json`",
        "- `eval/cold_start_trust_gate_snapshot.json`",
        "- `eval/served_runtime_fingerprint_snapshot.json`",
        "- `eval/release_governance_snapshot.json`",
        "- `eval/self_service_ops_gate_snapshot.json`",
        "- `eval/ops_readiness_watchdog_snapshot.json`",
        "",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Borg public self-serve launch readiness")
    parser.add_argument("--no-network", action="store_true", help="Do not query PyPI; gate fails unless test code injects PyPI data")
    parser.add_argument("--no-write", action="store_true", help="Do not write snapshot/report artifacts")
    args = parser.parse_args(argv)

    snapshot = compile_gate(fetch_network=not args.no_network)
    if not args.no_write:
        SNAPSHOT.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_report(snapshot)
    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["ready_for_public_self_serve_launch"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
