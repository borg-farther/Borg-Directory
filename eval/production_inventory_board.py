#!/usr/bin/env python3
"""Compile Borg's production inventory board.

This board is intentionally stricter than a status page. It separates:

- source/package proof from served-runtime proof;
- protocol/mechanism proof from operated production proof;
- internal/synthetic learning-loop proof from measured external-user lift;
- local/manual recursive improvement from autonomous global promotion.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback uses regex below.
    tomllib = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.first_10_evidence import evaluate_scoreboard  # noqa: E402
from eval import release_governance_gate, served_runtime_gate, self_service_ops_gate  # noqa: E402

SNAPSHOT = ROOT / "eval" / "production_inventory_board_snapshot.json"
REPORT = ROOT / "docs" / "20260531_BORG_PRODUCTION_INVENTORY_BOARD.md"


STATUS_GO = "GO"
STATUS_CONDITIONAL = "CONDITIONAL_GO"
STATUS_INTERNAL = "GO_INTERNAL_ONLY"
STATUS_PROTOCOL = "GO_PROTOCOL_ONLY"
STATUS_BLOCKED = "NO_GO"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_UNKNOWN = "UNKNOWN"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.exists():
        return {"_missing": True, "path": rel}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # fail closed for malformed proof artifacts
        return {"_parse_error": str(exc), "path": rel}


def _nested(data: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _git_context() -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=10, check=False)
            return proc.stdout.strip() if proc.returncode == 0 else ""
        except Exception:
            return ""

    status = run("status", "--short")
    return {
        "branch": run("branch", "--show-current"),
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(status),
        "dirty_files": [line for line in status.splitlines() if line],
        "remote": run("remote", "-v").splitlines(),
    }


def _versions() -> dict[str, Any]:
    pyproject_text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if tomllib is not None:
        pyproject = tomllib.loads(pyproject_text)
        project_version = pyproject.get("project", {}).get("version")
    else:  # pragma: no cover - only used on Python 3.10 without tomli.
        match_project = re.search(r"(?m)^version\s*=\s*['\"]([^'\"]+)['\"]", pyproject_text)
        project_version = match_project.group(1) if match_project else None
    init_text = (ROOT / "borg" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    runtime_version = match.group(1) if match else None
    return {
        "project_version": project_version,
        "runtime_version": runtime_version,
        "source_versions_match": bool(project_version and project_version == runtime_version),
    }


def _truth_status(passed: bool | None) -> str:
    if passed is True:
        return STATUS_GO
    if passed is False:
        return STATUS_BLOCKED
    return STATUS_UNKNOWN


def _component(
    component_id: str,
    name: str,
    status: str,
    *,
    evidence: list[str],
    blockers: list[str] | None = None,
    outstanding: list[str] | None = None,
    done: list[str] | None = None,
    challenge: str = "",
) -> dict[str, Any]:
    return {
        "id": component_id,
        "name": name,
        "status": status,
        "evidence": evidence,
        "done": done or [],
        "blockers": blockers or [],
        "outstanding": outstanding or [],
        "assumption_challenge": challenge,
    }


def _first_user_release_status(snapshot: dict[str, Any]) -> dict[str, Any]:
    results = snapshot.get("results") or []
    failures = [str(item.get("name")) for item in results if isinstance(item, dict) and item.get("passed") is not True]
    passed = bool(snapshot.get("success") is True and not failures)
    return {"passed": passed, "failures": failures, "generated_at_utc": snapshot.get("generated_at_utc")}


def _first10_status(scoreboard: dict[str, Any]) -> dict[str, Any]:
    if scoreboard.get("_missing") or scoreboard.get("_parse_error"):
        return {
            "passed": False,
            "row_count": 0,
            "derived_counts": {"verified_external_users": 0, "real_users": 0, "install_successes": 0, "useful_rescue_moments": 0, "critical_privacy_security_failures": 0},
            "blockers": ["first-10 scoreboard missing or unreadable"],
        }
    evidence = evaluate_scoreboard(scoreboard)
    passed = bool(evidence["schema_valid"] and evidence["thresholds_passed"] and evidence["stored_consistency"]["passed"])
    return {
        "passed": passed,
        "row_count": evidence["row_count"],
        "derived_counts": evidence["derived_counts"],
        "thresholds": evidence["thresholds"],
        "invalid_rows": evidence["invalid_rows"],
        "blockers": evidence["blockers"],
    }


def _served_runtime_status(snapshot: dict[str, Any], expected_version: str) -> dict[str, Any]:
    if snapshot.get("_missing") or snapshot.get("_parse_error"):
        return {"passed": False, "blockers": ["served runtime fingerprint snapshot missing or unreadable"], "summary": {}}
    payload = snapshot
    # Some runtime-fingerprint MCP outputs are wrapped as {"result": "<json>"}; accept either shape.
    if isinstance(snapshot.get("result"), str):
        try:
            parsed = json.loads(snapshot["result"])
            if isinstance(parsed, dict):
                payload = parsed
        except json.JSONDecodeError:
            pass
    return served_runtime_gate.evaluate_snapshot(payload, expected_version=expected_version)


def _release_governance_status(snapshot: dict[str, Any]) -> dict[str, Any]:
    if snapshot.get("_missing") or snapshot.get("_parse_error"):
        return {"passed": False, "blockers": ["release governance snapshot missing or unreadable"]}
    if "passed" in snapshot and ("required_checks_observed" in snapshot or "protected" in snapshot):
        evaluated = dict(snapshot)
        evaluated["passed"] = bool(snapshot.get("passed"))
        evaluated["blockers"] = list(snapshot.get("blockers") or [])
        return evaluated
    return release_governance_gate.evaluate_branch_payload(snapshot, require_codeowners_validation=True)


def _self_service_ops_status() -> dict[str, Any]:
    try:
        data = self_service_ops_gate.compile_gate()
        return {"passed": bool(data.get("passed")), "blockers": data.get("blockers") or [], "generated_at_utc": data.get("generated_at_utc")}
    except Exception as exc:  # fail closed for inventory use
        return {"passed": False, "blockers": [f"self-service ops gate failed to compile: {exc}"]}


def compile_inventory() -> dict[str, Any]:
    git = _git_context()
    versions = _versions()
    expected_version = str(versions.get("project_version") or "")

    first_user = _first_user_release_status(_read_json("eval/first_user_release_gate_snapshot.json"))
    github_source = _read_json("eval/github_source_install_snapshot.json")
    github_source_resolution = github_source.get("source_resolution") or {}
    github_source_mcp = github_source.get("mcp_stdio_canary") or {}
    github_source_dist = github_source.get("python_distribution_probe") or {}
    github_source_pass = bool(
        github_source.get("success") is True
        and github_source.get("version") == expected_version
        and github_source_resolution.get("commit_matches_expected") is True
        and github_source_resolution.get("url_matches_expected") is True
        and github_source_mcp.get("passed") is True
        and github_source_dist.get("passed") is True
    )
    pypi_fresh = _read_json("eval/pypi_fresh_install_snapshot.json")
    pypi_fresh_pass = bool(pypi_fresh.get("success") is True and pypi_fresh.get("version") == expected_version)
    cold_start = _read_json("eval/cold_start_trust_gate_snapshot.json")
    cold_start_pass = bool(cold_start.get("passed") is True)
    first10 = _first10_status(_read_json("eval/first_10_user_scoreboard.json"))
    served_runtime = _served_runtime_status(_read_json("eval/served_runtime_fingerprint_snapshot.json"), expected_version)
    release_governance = _release_governance_status(_read_json("eval/release_governance_snapshot.json"))
    self_service_ops = _self_service_ops_status()
    raw_ops_blockers = list(self_service_ops.get("blockers") or [])
    ops_blockers = [
        "rollback/comms drill snapshot is stale or not ready"
        if "rollback_drill_snapshot" in blocker
        else str(blocker)
        for blocker in raw_ops_blockers
    ]
    watchdog = _read_json("eval/ops_readiness_watchdog_snapshot.json")
    watchdog_blockers = list(watchdog.get("blockers") or [])
    watchdog_pass = bool(watchdog.get("passed") is True and not watchdog_blockers)
    rollback = _read_json("eval/rollback_comms_drill_snapshot.json")
    rollback_snapshot_pass = bool(rollback.get("passed") is True)
    rollback_effective_pass = bool(rollback_snapshot_pass and not any("rollback_drill_snapshot" in blocker for blocker in raw_ops_blockers))
    public_gate = _read_json("eval/public_self_serve_launch_gate_snapshot.json")
    pypi_latest_gate = (public_gate.get("gates") or {}).get("pypi_latest") or {}
    pypi_latest_pass = bool(pypi_latest_gate.get("passed") is True)
    pypi_package_current = bool(pypi_latest_pass and pypi_fresh_pass)
    package_path_green = bool(versions["source_versions_match"] and pypi_package_current and github_source_pass and first_user["passed"])
    rollout = _read_json("eval/real_user_rollout_gate_snapshot.json")
    federated = _read_json("eval/federated_learning_gate_snapshot.json")
    collective = _read_json("eval/collective_intelligence_loop_gate.json")
    optimality = _read_json("eval/federated_learning_optimality_audit.json")
    optimizer = _read_json("eval/pack_optimizer_gate_snapshot.json")

    governance_green = bool(release_governance.get("passed") is True)
    served_runtime_green = bool(served_runtime.get("passed") is True)
    release_controls_green = bool(served_runtime.get("passed") is True and release_governance.get("passed") is True)
    ops_green = bool(self_service_ops.get("passed") is True and watchdog_pass and rollback_effective_pass)
    public_ready = bool(package_path_green and release_controls_green and cold_start_pass and ops_green and first10["passed"])
    controlled_ready = bool(package_path_green and release_controls_green and cold_start_pass and ops_green)
    federated_protocol_go = bool(federated.get("success") is True and federated.get("verdict") == "GO" and federated.get("scope") == "remote_global_federated_protocol")
    collective_primitives_go = bool(collective.get("success") is True and collective.get("verdict") == "GO" and collective.get("scope") == "max_value_collective_intelligence_loop_primitives")
    google_optimal_go = bool(_nested(optimality, "verdict", "google_god_tier_optimal") == "GO")
    optimizer_green = bool(optimizer.get("success") is True and optimizer.get("global_promotion_allowed") is False and optimizer.get("first_10_claim") is False)

    first10_counts = first10.get("derived_counts") or {}
    first10_blocker = (
        f"first-10 evidence not passed: verified={first10_counts.get('verified_external_users', 0)}/10, "
        f"real_users={first10_counts.get('real_users', 0)}/10, "
        f"installs={first10_counts.get('install_successes', 0)}/8, "
        f"useful={first10_counts.get('useful_rescue_moments', 0)}/6, "
        f"critical_incidents={first10_counts.get('critical_privacy_security_failures', 0)}/0"
    )
    effective_ops_blockers = (
        ops_blockers
        + ([] if watchdog_pass else ["ops readiness watchdog snapshot is failing or stale"] + [str(blocker) for blocker in watchdog_blockers])
        + ([] if rollback_effective_pass else ["rollback/comms drill snapshot is stale or not passing"])
    )
    pypi_package_blockers: list[str] = []
    if not pypi_latest_pass:
        alignment = pypi_latest_gate.get("source_upload_alignment") or {}
        if alignment.get("failure_kind") == "same_version_pypi_upload_predates_source_revision":
            pypi_package_blockers.append("PyPI same-version release upload predates current source revision")
        else:
            pypi_package_blockers.append("PyPI latest metadata gate is not green for the current source revision")
    if not pypi_fresh_pass:
        pypi_package_blockers.append("PyPI fresh-install/stdout MCP canary is not green for the current source version")
    if not github_source_pass:
        pypi_package_blockers.append("GitHub source exact-commit install + local stdio MCP canary is not green for the current source version")
    source_package_status = (
        STATUS_CONDITIONAL if package_path_green and not git["dirty"]
        else STATUS_IN_PROGRESS if git["dirty"]
        else STATUS_BLOCKED
    )

    components = [
        _component(
            "source_package_cli_stdio",
            "source, GitHub source install, PyPI package, CLI, generated rules, and local stdio MCP",
            source_package_status,
            evidence=[
                "pyproject.toml and borg/__init__.py",
                "eval/first_user_release_gate_snapshot.json",
                "eval/github_source_install_snapshot.json",
                "eval/pypi_fresh_install_snapshot.json",
            ],
            done=[
                f"source versions match: {versions['source_versions_match']} ({versions.get('project_version')})",
                f"GitHub source exact-commit install/local MCP canary green: {github_source_pass} ({github_source_resolution.get('resolved_commit')})",
                f"PyPI latest metadata/current-source gate green: {pypi_latest_pass}",
                f"PyPI fresh-install/stdout MCP canary green: {pypi_fresh_pass}",
                f"first-user release gate green: {first_user['passed']}",
            ],
            blockers=pypi_package_blockers + (["working tree is dirty/unshipped; current hardening branch is not committed/pushed/CI-proven"] if git["dirty"] else []),
            outstanding=["rerun GitHub source + PyPI proof on the final branch head", "commit/push and watch CI before claiming shipped", "publish a new immutable version only if package code/version changes"],
            challenge="A clean GitHub source/PyPI canary proves fresh-process install behavior, not source revisions that land after the proof or a long-lived served process.",
        ),
        _component(
            "security_hardening_current_branch",
            "current hardening branch: pack safety, pickle removal, HTTP/MCP hardening, docs truth gates",
            STATUS_IN_PROGRESS if git["dirty"] else STATUS_CONDITIONAL,
            evidence=["git status --short", "tests/security", "tests/mcp", "tests/readiness", "eval/tests"],
            done=[
                "pack ingestion/export hardening is implemented in working tree",
                "embedding cache pickle load has been replaced with safe JSON schema in working tree",
                "HTTP MCP auth/body/schema/read-only hardening is implemented in working tree",
                "served-runtime and release-governance gates are implemented in working tree",
            ],
            blockers=["not yet full-suite/static/security proven after latest dashboard/inventory changes", "not committed or pushed"],
            outstanding=["run focused and full pytest", "run security_gate_check.py", "regenerate dashboard/status artifacts", "commit/push only after proof is green or report blockers"],
            challenge="Regression tests for narrow fixes are not equivalent to a release proof over every changed surface.",
        ),
        _component(
            "served_runtime",
            "served/Hermes MCP runtime freshness",
            _truth_status(bool(served_runtime.get("passed"))),
            evidence=["eval/served_runtime_fingerprint_snapshot.json", "borg_runtime_fingerprint MCP canary"],
            done=[f"snapshot captured: borg_version={_nested(served_runtime, 'summary', 'borg_version')}, source_version={_nested(served_runtime, 'summary', 'source_version')}"] if served_runtime.get("summary") else [],
            blockers=list(served_runtime.get("blockers") or []),
            outstanding=["operator-approved reload/cutover", "recapture fingerprint through the exact served channel", "rerun behavior canaries after cutover"],
            challenge="Local source, PyPI, and fresh stdio MCP can all be green while a long-lived served process is stale.",
        ),
        _component(
            "release_governance",
            "GitHub release governance and main-branch protection",
            _truth_status(bool(release_governance.get("passed"))),
            evidence=["eval/release_governance_snapshot.json", "GitHub branch API payload for main"],
            done=[f"protected={release_governance.get('protected')}", f"observed checks={release_governance.get('required_checks_observed')}"] if release_governance else [],
            blockers=list(release_governance.get("blockers") or []),
            outstanding=["maintain release-governance snapshot freshness", "keep required CI/security/watchdog/account-firewall checks exact", "keep CODEOWNERS validation green"] if release_governance.get("passed") else ["enable branch protection", "require CI/security/watchdog/account-firewall checks", "require CODEOWNERS review"],
            challenge="Green local checks do not matter if main can bypass the release ritual.",
        ),
        _component(
            "self_service_ops_watchdog",
            "self-service ops, rollback/comms, support intake, watchdog freshness",
            STATUS_GO if ops_green else STATUS_BLOCKED,
            evidence=["eval/self_service_ops_gate_snapshot.json", "eval/ops_readiness_watchdog_snapshot.json", "eval/rollback_comms_drill_snapshot.json"],
            done=[f"watchdog passed: {watchdog_pass}"],
            blockers=effective_ops_blockers,
            outstanding=["refresh rollback/comms drill", "rerun self-service ops gate", "keep watchdog under freshness SLA"],
            challenge="Ops docs are not readiness unless the live snapshots are fresh and fail closed.",
        ),
        _component(
            "first_10_external_evidence",
            "first-10 consented external-user evidence",
            STATUS_GO if first10["passed"] else STATUS_BLOCKED,
            evidence=["eval/first_10_user_scoreboard.json", "eval/first_10_evidence.py"],
            done=[f"row_count={first10.get('row_count', 0)}", f"counts={first10_counts}"],
            blockers=[] if first10["passed"] else [first10_blocker],
            outstanding=["recruit 10 consented external users", "record installs, useful rescues, repeated use, and negative outcomes", "keep critical privacy/security incidents at 0"],
            challenge="Synthetic load users, internal dogfood, and anecdotes never count as first-10 external evidence.",
        ),
        _component(
            "controlled_first_10_beta",
            "controlled first-10 beta readiness",
            STATUS_CONDITIONAL if controlled_ready else STATUS_BLOCKED,
            evidence=["eval/public_self_serve_launch_gate.py --no-write", "eval/real_user_rollout_gate.py --no-write"],
            blockers=[] if controlled_ready else list(served_runtime.get("blockers") or []) + list(release_governance.get("blockers") or []) + effective_ops_blockers,
            outstanding=["served runtime fresh", "branch protection/release governance green", "ops snapshots fresh", "cap at 10 until first-10 rows pass"],
            challenge="Earlier conditional GO is revoked when release controls or ops freshness fail.",
        ),
        _component(
            "public_self_serve",
            "broad public self-serve launch",
            STATUS_GO if public_ready else STATUS_BLOCKED,
            evidence=["eval/public_self_serve_launch_gate.py", "docs/public/status.json", "eval/first_10_user_scoreboard.json"],
            blockers=[] if public_ready else [first10_blocker] + list(served_runtime.get("blockers") or []) + list(release_governance.get("blockers") or []) + effective_ops_blockers,
            outstanding=["pass first-10 row-derived evidence", "keep package/served-runtime/governance/ops/docs gates green", "regenerate public status/dashboard from current snapshots"],
            challenge="A polished dashboard is dangerous if it hides the first-10 or served-runtime blockers.",
        ),
        _component(
            "hundred_user_rollout",
            "25 -> 50 -> 100 real-user staged rollout",
            STATUS_BLOCKED,
            evidence=["eval/real_user_rollout_gate.py", "docs/20260517_BORG_100_REAL_USER_READINESS.md"],
            blockers=["100-user rollout is downstream of first-10 evidence and public self-serve gate"],
            outstanding=["25-user stage", "50-user repeat-use/retention stage", "100-user support/incident proof"],
            challenge="100 synthetic/load users are not 100 real users.",
        ),
        _component(
            "remote_global_federated_protocol",
            "remote/global/federated learning protocol",
            STATUS_PROTOCOL if federated_protocol_go else STATUS_BLOCKED,
            evidence=["eval/run_federated_learning_gate.py", "eval/federated_learning_gate_snapshot.json", "tests/security/test_federated_learning_gate.py"],
            done=[
                "signed hosted-registry manifest sync",
                "hash/size verification before import",
                "replay/tamper/key/channel/expiry rejection",
                "tombstone-first revocation convergence",
            ] if federated_protocol_go else [],
            blockers=[] if federated_protocol_go else ["federated protocol gate is not green"],
            outstanding=["production hosted registry ops", "monitoring and revocation SLO telemetry", "backup/restore and key-rotation drills", "transparency-log anchoring"],
            challenge="Protocol GO is not hosted-registry production ops, public self-serve, or measured value proof.",
        ),
        _component(
            "collective_recursive_learning_loop",
            "outcome-grounded collective/recursive learning mechanism",
            STATUS_INTERNAL if collective_primitives_go else STATUS_BLOCKED,
            evidence=["eval/run_collective_intelligence_loop_gate.py", "eval/collective_intelligence_loop_gate.json", "eval/federated_learning_optimality_audit.json"],
            done=[
                "intervention IDs and signed outcome receipts",
                "verified helpful/unhelpful outcome storage",
                "dedupe/generalization clusters",
                "registry-computed quorum from signed receipts",
                "sanitized atom candidate/promotion path",
                "unified scored retrieval with negative evidence",
            ] if collective_primitives_go else [],
            blockers=[] if collective_primitives_go else ["collective intelligence loop gate is not green"],
            outstanding=["prove real external lift", "run 3-condition no-Borg/empty-Borg/seeded-Borg evaluation", "operate production registry", "abuse/quarantine workflow and transparency anchoring"],
            challenge="Internal synthetic loop primitives are real, but they do not prove agents improve in the wild.",
        ),
        _component(
            "recursive_pack_optimizer",
            "recursive/local pack optimizer and learning-to-improve packs",
            STATUS_INTERNAL if optimizer_green else STATUS_IN_PROGRESS,
            evidence=["eval/pack_optimizer_gate_snapshot.json", "borg/core/pack_optimizer.py", "borg/core/pack_optimizer_rejections.py"],
            done=["local-only candidate generation", "privacy/prompt-injection scans", "manual-review eligibility", "rejected-edit memory"] if optimizer_green else [],
            blockers=[] if optimizer_green else ["pack optimizer gate is missing or failing"],
            outstanding=["wire into a supervised recurring improvement lane", "run cross-agent A/B before accepting edits", "keep global promotion disabled until first-10 and registry ops gates pass"],
            challenge="Recursive optimization must stay evidence-bound; autonomous global edits before external proof would amplify mistakes.",
        ),
        _component(
            "google_tier_measured_lift",
            "Google/God-tier measured utility and learning optimality",
            STATUS_GO if google_optimal_go else STATUS_BLOCKED,
            evidence=["eval/federated_learning_optimality_audit.json", "eval/first_10_user_scoreboard.json", "docs/20260526-2230_MAX_VALUE_COLLECTIVE_INTELLIGENCE_LOOP.md"],
            done=[f"optimality scores={_nested(optimality, 'scores_0_to_10', default={})}"],
            blockers=list(_nested(optimality, "p0_gaps_to_google_tier", default=[])) or ["external lift not measured"],
            outstanding=["measured external outcomes", "statistically honest counterfactual evaluation", "repeat-use and negative-guidance analysis"],
            challenge="Strong protocol/security scores can coexist with a low optimality ceiling when external truth grounding is 0-1/10.",
        ),
        _component(
            "marketplace_remote_distribution",
            "marketplaces, remote MCP listings, and public distribution channels",
            STATUS_BLOCKED,
            evidence=["deploy/smithery/smithery.yaml", "docs/ROADMAP.md", "docs/20260528_BORG_PRODUCTION_READY_FINAL_TODO.md"],
            blockers=([] if served_runtime_green else ["served remote MCP/runtime freshness is not green"])
            + ([] if governance_green else ["release governance is not green"])
            + ["no production hosted registry ops proof"],
            outstanding=["keep Smithery/local stdio draft honest", "remote HTTP auth/rate-limit/audit-redaction proof", "served-runtime fingerprint for the listed channel"],
            challenge="Distribution breadth is not value; premature listings multiply support and trust failures.",
        ),
    ]

    status_counts: dict[str, int] = {}
    for component in components:
        status_counts[component["status"]] = status_counts.get(component["status"], 0) + 1

    outstanding = [
        {
            "priority": "P0",
            "item": "Finish and prove the current hardening branch",
            "why": "Security/runtime/governance changes exist in the working tree but are not shipped or full-suite proven.",
            "acceptance": ["focused tests green", "full pytest/static/security gates green", "dashboard/status regenerated", "commit/push/CI watched"],
        },
        {
            "priority": "P0",
            "item": "Refresh served runtime through operator-approved cutover",
            "why": f"Current served fingerprint says {_nested(served_runtime, 'summary', 'borg_version') or 'unknown'} while source targets {versions.get('project_version')}.",
            "acceptance": ["served borg_version == source_version == PyPI latest", "runtime hash/path/schema canary captured", "behavior canaries pass"],
        },
        (
            {
                "priority": "P0",
                "item": "Turn on release governance",
                "why": "Release governance snapshot is not green for the captured GitHub branch payload.",
                "acceptance": ["branch protection enabled", "required checks enforced", "CODEOWNERS review required", "release_governance_gate passes"],
            }
            if not governance_green
            else {
                "priority": "P1",
                "item": "Maintain release-governance freshness",
                "why": "Current GitHub main release-governance proof is green; keep the snapshot fresh and exact-check policy enforced through PR/merge/tag.",
                "acceptance": ["release_governance_gate passes", "required checks remain exact", "CODEOWNERS review remains required", "no bypass allowances appear"],
            }
        ),
        {
            "priority": "P0" if not ops_green else "P1",
            "item": "Maintain ops/watchdog/rollback readiness freshness",
            "why": "Self-service ops, watchdog, and rollback/comms proof are controlled-beta prerequisites; current gate state is " + ("green" if ops_green else "blocked or stale") + ".",
            "acceptance": ["rollback drill fresh", "self-service ops gate passes", "watchdog passes with freshness SLA"],
        },
        {
            "priority": "P0",
            "item": "Run first-10 external beta evidence collection",
            "why": "Public self-serve, 100 users, and measured lift are all blocked at 0/10 external rows.",
            "acceptance": ["10 verified external users", "8 installs", "6 useful rescues", "0 critical privacy/security incidents", "negative rows retained"],
        },
        {
            "priority": "P0",
            "item": "Regenerate proof dashboard/public status from current gates",
            "why": "Generated snapshots/status must reflect served-runtime, release-governance, and ops blockers, not older conditional-GO language.",
            "acceptance": ["public gate snapshot current", "rollout snapshot current", "borg proof dashboard rebuilt", "dashboard lint passes"],
        },
        {
            "priority": "P1",
            "item": "Operate production federated registry",
            "why": "Federated protocol is green, but hosted ops are still not production-proven.",
            "acceptance": ["monitoring", "backups", "restore drill", "key rotation", "revocation telemetry", "abuse/quarantine workflow", "transparency-log plan"],
        },
        {
            "priority": "P1",
            "item": "Graduate recursive optimizer from local/manual to evidence-backed supervised loop",
            "why": "Pack optimizer is local/manual only; autonomous/global promotion must wait for external proof and ops controls.",
            "acceptance": ["scheduled supervised lane", "A/B comparison", "manual approval", "negative-evidence rejection memory", "no global promotion without first-10 + registry gates"],
        },
        {
            "priority": "P1",
            "item": "Cross-platform first-user matrix",
            "why": "Linux PyPI canary is strong but not enough for broad self-serve.",
            "acceptance": ["Linux/macOS/Windows", "Python 3.10/3.11/3.12", "pipx and pip", "multiple MCP hosts"],
        },
        {
            "priority": "P1",
            "item": "Measured value experiment",
            "why": "Google-tier claims require counterfactual evidence, not mechanism proof.",
            "acceptance": ["no Borg vs empty Borg vs seeded Borg", "minutes/tokens/dead-ends measured", "repeat use", "false-positive/NO_CONFIDENT_MATCH analysis"],
        },
    ]

    final_challenge = [
        "Could package proof alone justify controlled beta? No: current release controls add served-runtime freshness, release-governance freshness, and ops freshness; any red/stale required gate blocks beta.",
        "Could protocol GO mean federated learning is production-ready? No: it proves signed sync/revocation mechanics, not hosted operations or public utility.",
        "Could internal outcome receipts prove recursive learning is ready? Only as internal primitives; external lift and autonomous promotion remain blocked.",
        "Could synthetic load tests stand in for users? No: first-10 row-derived evidence is 0/10 and explicitly blocks public/100-user claims.",
        "Could a dashboard hide these blockers? It must not; stale generated artifacts are themselves blockers until rebuilt from current gates.",
    ]

    return {
        "schema_version": 1,
        "generated_at_utc": _now(),
        "board_name": "borg_production_inventory_board",
        "source": {
            "repo": "https://github.com/borg-farther/Borg-Directory",
            "root": str(ROOT),
            "git": git,
            "versions": versions,
        },
        "task_outline": [
            "reconstruct promised production features from docs/session evidence",
            "separate proof lanes: source/package, served runtime, governance, ops, external users, federated protocol, recursive learning, measured value",
            "challenge readiness claims against fail-closed gates and row-derived evidence",
            "produce durable docs and machine-readable outstanding inventory",
            "add regression tests so future edits cannot collapse the boundaries",
        ],
        "top_verdict": {
            "controlled_first_10_beta": "CONDITIONAL_GO" if controlled_ready else "NO_GO",
            "public_self_serve": "GO" if public_ready else "NO_GO",
            "hundred_real_users": "NO_GO",
            "served_runtime_freshness": "GO" if served_runtime.get("passed") else "NO_GO",
            "remote_mcp_distribution": "NO_GO",
            "served_remote_mcp": "NO_GO",
            "published_package_local_stdio": "CONDITIONAL_GO" if package_path_green else "NO_GO",
            "current_source_hardening_branch": "IN_PROGRESS" if git["dirty"] else "CONDITIONAL_GO",
            "source_package_local_stdio": ("IN_PROGRESS" if git["dirty"] else "CONDITIONAL_GO") if package_path_green else "NO_GO",
            "global_federated_learning_protocol": "GO_PROTOCOL_ONLY" if federated_protocol_go else "NO_GO",
            "recursive_collective_learning_mechanism": "GO_INTERNAL_ONLY" if collective_primitives_go else "NO_GO",
            "recursive_pack_optimizer": "GO_INTERNAL_MANUAL_ONLY" if optimizer_green else "NO_GO",
            "google_tier_external_lift": "GO" if google_optimal_go else "NO_GO",
        },
        "status_counts": status_counts,
        "evidence_summary": {
            "first_10_counts": first10_counts,
            "pypi_latest_metadata_current_source_passed": pypi_latest_pass,
            "github_source_install_passed": github_source_pass,
            "github_source_resolved_commit": github_source_resolution.get("resolved_commit"),
            "pypi_fresh_install_passed": pypi_fresh_pass,
            "first_user_release_passed": first_user["passed"],
            "cold_start_trust_passed": cold_start_pass,
            "served_runtime_passed": bool(served_runtime.get("passed")),
            "release_governance_passed": bool(release_governance.get("passed")),
            "self_service_ops_passed": bool(self_service_ops.get("passed")),
            "watchdog_passed": watchdog_pass,
            "rollback_drill_passed": rollback_effective_pass,
            "federated_protocol_go": federated_protocol_go,
            "collective_loop_primitives_go": collective_primitives_go,
            "pack_optimizer_manual_go": optimizer_green,
            "overall_optimality_ceiling": _nested(optimality, "scores_0_to_10", "overall_optimality_ceiling"),
        },
        "components": components,
        "outstanding": outstanding,
        "final_reflective_challenge_pass": final_challenge,
        "current_blockers_ordered": (
            ([] if github_source_pass else ["GitHub source install gate not green"])
            + ([] if served_runtime.get("passed") else ["served runtime stale or not proven current"])
            + ([] if governance_green else ["main branch protection/release governance not green"])
            + ([] if ops_green else ["rollback/self-service ops freshness not green"])
            + (["current hardening branch unshipped/full-proof pending"] if git["dirty"] else [])
            + [
                "first-10 external evidence 0/10",
                "public self-serve, 100-user, marketplace, measured-lift claims blocked until above gates pass",
            ]
        ),
    }


def render_markdown(data: dict[str, Any]) -> str:
    verdict = data["top_verdict"]
    evidence = data["evidence_summary"]
    components = data["components"]
    outstanding = data["outstanding"]
    source = data["source"]
    git = source["git"]
    versions = source["versions"]

    lines: list[str] = [
        "# Borg production inventory board",
        "",
        f"Generated: `{data['generated_at_utc']}`",
        f"Repo: `{source['repo']}`",
        f"Branch/head: `{git.get('branch')}` / `{git.get('commit')}`",
        f"Working tree dirty: `{git.get('dirty')}`",
        f"Version: pyproject `{versions.get('project_version')}` / borg `__version__` `{versions.get('runtime_version')}`",
        "",
        "## Task outline / decomposition",
        "",
    ]
    lines.extend(f"- {item}" for item in data["task_outline"])
    lines.extend([
        "",
        "## Bottom-line verdicts",
        "",
        f"- controlled first-10 beta: `{verdict['controlled_first_10_beta']}`",
        f"- broad public self-serve: `{verdict['public_self_serve']}`",
        f"- 100 real users: `{verdict['hundred_real_users']}`",
        f"- current source/hardening branch: `{verdict['current_source_hardening_branch']}`",
        f"- published package/local stdio: `{verdict['published_package_local_stdio']}`",
        f"- served runtime freshness: `{verdict['served_runtime_freshness']}`",
        f"- remote MCP/marketplace distribution: `{verdict['remote_mcp_distribution']}`",
        f"- global/federated learning protocol: `{verdict['global_federated_learning_protocol']}`",
        f"- recursive collective learning mechanism: `{verdict['recursive_collective_learning_mechanism']}`",
        f"- recursive pack optimizer: `{verdict['recursive_pack_optimizer']}`",
        f"- Google/God-tier measured external lift: `{verdict['google_tier_external_lift']}`",
        "",
        "## Evidence summary",
        "",
        f"- first-10 external rows: `{evidence['first_10_counts']}`",
        f"- GitHub source exact-commit install + local stdio MCP: `{evidence['github_source_install_passed']}` ({evidence.get('github_source_resolved_commit')})",
        f"- PyPI fresh install + stdio MCP: `{evidence['pypi_fresh_install_passed']}`",
        f"- first-user release gate: `{evidence['first_user_release_passed']}`",
        f"- cold-start trust: `{evidence['cold_start_trust_passed']}`",
        f"- served runtime freshness: `{evidence['served_runtime_passed']}`",
        f"- release governance: `{evidence['release_governance_passed']}`",
        f"- self-service ops: `{evidence['self_service_ops_passed']}`",
        f"- ops watchdog: `{evidence['watchdog_passed']}`",
        f"- rollback drill: `{evidence['rollback_drill_passed']}`",
        f"- federated protocol gate: `{evidence['federated_protocol_go']}`",
        f"- collective loop primitives: `{evidence['collective_loop_primitives_go']}`",
        f"- pack optimizer local/manual gate: `{evidence['pack_optimizer_manual_go']}`",
        f"- optimality ceiling: `{evidence['overall_optimality_ceiling']}`",
        "",
        "## Component inventory",
        "",
    ])

    for component in components:
        lines.extend([
            f"### {component['id']} — {component['name']}",
            "",
            f"Status: `{component['status']}`",
            "",
            "Evidence:",
        ])
        lines.extend(f"- `{item}`" for item in component["evidence"])
        if component["done"]:
            lines.append("Done/proven:")
            lines.extend(f"- {item}" for item in component["done"])
        if component["blockers"]:
            lines.append("Blockers:")
            lines.extend(f"- {item}" for item in component["blockers"])
        if component["outstanding"]:
            lines.append("Outstanding:")
            lines.extend(f"- {item}" for item in component["outstanding"])
        if component["assumption_challenge"]:
            lines.extend(["Challenge:", f"- {component['assumption_challenge']}"])
        lines.append("")

    lines.extend([
        "## Outstanding production work, ordered",
        "",
    ])
    for item in outstanding:
        lines.extend([
            f"### {item['priority']} — {item['item']}",
            "",
            f"Why: {item['why']}",
            "",
            "Acceptance:",
        ])
        lines.extend(f"- {acceptance}" for acceptance in item["acceptance"])
        lines.append("")

    lines.extend([
        "## Final reflective challenge pass",
        "",
    ])
    lines.extend(f"- {item}" for item in data["final_reflective_challenge_pass"])
    lines.extend([
        "",
        "## Current blocker hierarchy",
        "",
    ])
    lines.extend(f"{idx}. {item}" for idx, item in enumerate(data["current_blockers_ordered"], start=1))
    lines.extend([
        "",
        "## Hard boundary",
        "",
        "The global/federated and recursive learning mechanisms have real internal/protocol proof, but they are not production-global value proof. Public production still requires served-runtime freshness, release governance, fresh ops readiness, first-10 external rows, and measured outcomes.",
        "",
    ])
    return "\n".join(lines)


def write_artifacts(data: dict[str, Any]) -> None:
    SNAPSHOT.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT.write_text(render_markdown(data), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile Borg production inventory board")
    parser.add_argument("--no-write", action="store_true", help="print JSON without writing snapshot/report artifacts")
    parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    args = parser.parse_args(argv)

    data = compile_inventory()
    if not args.no_write:
        write_artifacts(data)
    if args.json or args.no_write:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"production_inventory_board: wrote {SNAPSHOT.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}")
        print(f"public_self_serve={data['top_verdict']['public_self_serve']} served_runtime={data['top_verdict']['served_runtime_freshness']} google_tier={data['top_verdict']['google_tier_external_lift']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
