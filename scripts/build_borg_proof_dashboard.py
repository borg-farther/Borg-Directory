#!/usr/bin/env python3
"""Build an honest Borg proof dashboard from local repo artifacts only."""
from __future__ import annotations

import html
import json
import re
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DOCS = ROOT / "docs"
EVAL = ROOT / "eval"
PUBLIC = DOCS / "public" / "proof-dashboard"
PUBLIC_ROOT = DOCS / "public"
JSON_OUT = EVAL / "borg_proof_dashboard.json"
MD_OUT = DOCS / "BORG_PROOF_DASHBOARD.md"
HTML_OUT = DOCS / "BORG_PROOF_DASHBOARD.html"
PUBLIC_OUT = PUBLIC / "index.html"
PUBLIC_STATUS_OUT = PUBLIC_ROOT / "status.json"
PUBLIC_STATUS_ALIAS_OUT = DOCS / "status.json"
PAGES_ROOT_OUT = DOCS / "index.html"
PAGES_PROOF_ALIAS_OUT = DOCS / "proof-dashboard" / "index.html"
PUBLIC_VALUE_OUT = PUBLIC_ROOT / "value.json"
PUBLIC_IMPACT_OUT = PUBLIC_ROOT / "impact" / "impact.json"
CANONICAL_REPO_URL = "https://github.com/borg-farther/Borg-Directory"

SOURCE_PATHS = [
    "pyproject.toml",
    "borg/__init__.py",
    "eval/first_user_release_gate_snapshot.json",
    "eval/uat_scoreboard_snapshot.json",
    "eval/gate_run_snapshot.json",
    "eval/real_user_rollout_gate_snapshot.json",
    "eval/first_10_user_scoreboard.json",
    "eval/public_self_serve_launch_gate_snapshot.json",
    "eval/cold_start_trust_gate_snapshot.json",
    "eval/served_runtime_fingerprint_snapshot.json",
    "eval/release_governance_snapshot.json",
    "eval/self_service_ops_gate_snapshot.json",
    "eval/ops_readiness_watchdog_snapshot.json",
    "eval/rollback_comms_drill_snapshot.json",
    "eval/pypi_fresh_install_snapshot.json",
    "eval/github_source_install_snapshot.json",
    "eval/load_10_snapshot.json",
    "eval/load_100_snapshot.json",
    "eval/load_1000_snapshot.json",
]

HYPE_RE = re.compile(r"\b(proven external adoption|hundreds of users|production ready)\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def mtime_iso(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(rel: str) -> dict | None:
    path = ROOT / rel
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_parse_error": str(exc)}


def nested(data: dict | None, keys: list[str], default=None):
    cur = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def first_dict(*values: object) -> dict:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def status_bool(value) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "UNKNOWN"


def pyproject_version() -> str | None:
    path = ROOT / "pyproject.toml"
    if not path.exists():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return nested(data, ["project", "version"])


def init_version() -> str | None:
    path = ROOT / "borg" / "__init__.py"
    if not path.exists():
        return None
    m = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def current_commit() -> str | None:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = subprocess.run(["git", "diff", "--quiet"], cwd=ROOT).returncode != 0
        staged = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0
        untracked = bool(subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).strip())
        if dirty or staged or untracked:
            return f"{commit}+dirty"
        return commit
    except Exception:
        return None


def source_record(rel: str, claim: str, freshness: str | None = None) -> dict:
    path = ROOT / rel
    exists = path.exists()
    return {
        "path": rel,
        "exists": exists,
        "sha256": sha256(path) if exists else None,
        "freshness_timestamp": freshness or (mtime_iso(path) if exists else None),
        "claim_derived": claim if exists else f"MISSING: {claim}",
    }


def freshness_value(value) -> str | None:
    return value if isinstance(value, str) else None


def age_hours(value: str | None) -> float | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600


def freshness_passed(age: float | None, max_age_hours: float = 24.0) -> bool:
    return age is not None and 0 <= age <= max_age_hours


def pack_count() -> int | None:
    packs = ROOT / "borg" / "seeds_data" / "packs"
    if not packs.exists():
        return None
    return len(sorted(packs.glob("*.yaml")))


def build_model() -> dict:
    first = load_json("eval/first_user_release_gate_snapshot.json")
    uat = load_json("eval/uat_scoreboard_snapshot.json")
    gate = load_json("eval/gate_run_snapshot.json")
    real_user = load_json("eval/real_user_rollout_gate_snapshot.json")
    first10_scoreboard = load_json("eval/first_10_user_scoreboard.json")
    public_gate = load_json("eval/public_self_serve_launch_gate_snapshot.json")
    cold_start_trust = load_json("eval/cold_start_trust_gate_snapshot.json")
    served_runtime_snapshot = load_json("eval/served_runtime_fingerprint_snapshot.json")
    release_governance_snapshot = load_json("eval/release_governance_snapshot.json")
    self_service_ops = load_json("eval/self_service_ops_gate_snapshot.json")
    ops_watchdog = load_json("eval/ops_readiness_watchdog_snapshot.json")
    rollback_drill = load_json("eval/rollback_comms_drill_snapshot.json")
    pypi_fresh = load_json("eval/pypi_fresh_install_snapshot.json")
    github_source = load_json("eval/github_source_install_snapshot.json")
    loads = {str(n): load_json(f"eval/load_{n}_snapshot.json") for n in (10, 100, 1000)}
    pv, rv = pyproject_version(), init_version()
    commit = current_commit()
    pcount = pack_count()

    first10_evaluation = None
    verified_external_users = 0
    measured_savings = {
        "rows_with_measured_value": 0,
        "dead_ends_avoided_confirmed": 0,
        "net_minutes_saved": 0.0,
        "positive_minutes_saved": 0.0,
        "negative_minutes_cost": 0.0,
        "net_tokens_saved": 0,
        "positive_tokens_saved": 0,
        "negative_tokens_cost": 0,
        "counterfactual_basis_counts": {},
    }
    external_user_evidence = "No artifact found that identifies real verified external users; simulated/logical load users are excluded."
    if isinstance(first10_scoreboard, dict) and "_parse_error" not in first10_scoreboard:
        try:
            from eval.first_10_evidence import evaluate_scoreboard

            first10_evaluation = evaluate_scoreboard(first10_scoreboard)
            verified_external_users = int(first10_evaluation["derived_counts"].get("verified_external_users", 0))
            measured_savings = dict(first10_evaluation.get("derived_value") or measured_savings)
            external_user_evidence = "eval/first_10_user_scoreboard.json row-derived external-user evidence"
        except Exception as exc:
            external_user_evidence = f"eval/first_10_user_scoreboard.json could not be evaluated: {exc}"

    version_consistent = bool(pv and rv and pv == rv)
    first_gate_pass = nested(first, ["all_pass"])
    if first_gate_pass is None and isinstance(first, dict) and isinstance(first.get("results"), list):
        first_gate_pass = all(item.get("passed") is True for item in first["results"] if isinstance(item, dict))
    uat_pass = nested(uat, ["synthetic_load_all_pass"], nested(uat, ["all_pass"]))
    gate_pass = nested(gate, ["synthetic_load_all_pass"], nested(gate, ["all_pass"]))
    real_user_100_pass = nested(real_user, ["ready_for_100_real_users"], nested(uat, ["real_user_rollout", "ready_for_100_real_users"]))
    public_self_serve_pass = nested(public_gate, ["ready_for_public_self_serve_launch"])
    cold_start_trust_pass = nested(cold_start_trust, ["passed"])
    self_service_ops_pass = nested(self_service_ops, ["passed"])
    self_service_ops_blockers = nested(self_service_ops, ["blockers"], []) or []
    # Keep dashboard claims artifact-bound: the evidence row hashes
    # eval/self_service_ops_gate_snapshot.json, so its status/timestamp must come
    # from that file. Refresh the snapshot before running this dashboard builder
    # instead of compiling a transient in-memory gate with a different timestamp.
    ops_watchdog_pass = nested(ops_watchdog, ["passed"])
    rollback_drill_pass = nested(rollback_drill, ["passed"])
    if any("rollback_drill_snapshot" in str(blocker) for blocker in self_service_ops_blockers):
        rollback_drill_pass = False
    pypi_fresh_pass = nested(pypi_fresh, ["success"])
    pypi_fresh_version = nested(pypi_fresh, ["version"])
    pypi_fresh_mcp_pass = nested(pypi_fresh, ["mcp_stdio_canary", "passed"])
    pypi_fresh_generated_at = nested(pypi_fresh, ["generated_at_utc"])
    pypi_fresh_age = age_hours(pypi_fresh_generated_at if isinstance(pypi_fresh_generated_at, str) else None)
    pypi_fresh_age_ok = freshness_passed(pypi_fresh_age, 24.0)
    pypi_fresh_current = bool(
        pypi_fresh_pass is True
        and pypi_fresh_version == pv
        and pypi_fresh_mcp_pass is True
        and pypi_fresh_age_ok
    )
    pypi_latest_gate = nested(public_gate, ["gates", "pypi_latest"], {}) if isinstance(public_gate, dict) else {}
    pypi_latest_current = nested(pypi_latest_gate, ["passed"])
    pypi_description_stale = bool(nested(pypi_latest_gate, ["description_stale_copy"], []))
    pypi_alignment_failure = nested(pypi_latest_gate, ["source_upload_alignment", "failure_kind"])
    pypi_package_current = bool(pypi_latest_current is True and pypi_fresh_current)
    github_source_pass = nested(github_source, ["success"])
    github_source_version = nested(github_source, ["version"])
    github_source_mcp_pass = nested(github_source, ["mcp_stdio_canary", "passed"])
    github_source_leakage_pass = nested(github_source, ["checkout_import_leakage", "passed"])
    github_source_generated_at = nested(github_source, ["generated_at_utc"])
    github_source_age = age_hours(github_source_generated_at if isinstance(github_source_generated_at, str) else None)
    github_source_age_ok = freshness_passed(github_source_age, 24.0)
    github_source_gate: dict = {
        "passed": False,
        "exists": github_source is not None,
        "path": "eval/github_source_install_snapshot.json",
        "error": "GitHub source-install gate not evaluated",
    }
    try:
        from eval import public_self_serve_launch_gate as _public_self_serve_launch_gate

        github_source_gate = _public_self_serve_launch_gate.github_source_install_check(
            ROOT / "eval" / "github_source_install_snapshot.json",
            str(pv or "UNKNOWN"),
            max_snapshot_age_hours=24.0,
        )
    except Exception as exc:
        github_source_gate = {
            "passed": False,
            "exists": github_source is not None,
            "path": "eval/github_source_install_snapshot.json",
            "error": f"GitHub source-install gate could not be evaluated: {exc}",
        }
    github_source_green = bool(github_source_gate.get("passed") is True)
    github_source_current = github_source_green

    served_runtime_gate = first_dict(
        nested(public_gate, ["gates", "served_runtime_freshness"]),
        nested(real_user, ["release_controls_gate", "served_runtime_freshness"]),
    )
    if not served_runtime_gate and isinstance(served_runtime_snapshot, dict) and "_parse_error" not in served_runtime_snapshot:
        try:
            from eval import served_runtime_gate as _served_runtime_gate

            served_runtime_payload = served_runtime_snapshot
            if isinstance(served_runtime_payload.get("result"), str):
                try:
                    parsed_payload = json.loads(served_runtime_payload["result"])
                    if isinstance(parsed_payload, dict):
                        served_runtime_payload = parsed_payload
                except json.JSONDecodeError:
                    pass
            served_runtime_gate = _served_runtime_gate.evaluate_snapshot(
                served_runtime_payload,
                expected_version=str(pv or "UNKNOWN"),
            )
        except Exception as exc:
            served_runtime_gate = {"passed": False, "blockers": [f"served runtime snapshot could not be evaluated: {exc}"]}
    served_runtime_pass = nested(served_runtime_gate, ["passed"])

    release_governance_gate = first_dict(
        nested(public_gate, ["gates", "release_governance"]),
        nested(real_user, ["release_controls_gate", "release_governance"]),
    )
    if not release_governance_gate and isinstance(release_governance_snapshot, dict) and "_parse_error" not in release_governance_snapshot:
        try:
            from eval import release_governance_gate as _release_governance_gate

            if "passed" in release_governance_snapshot and "required_checks_observed" in release_governance_snapshot:
                release_governance_gate = release_governance_snapshot
            else:
                release_governance_gate = _release_governance_gate.evaluate_branch_payload(release_governance_snapshot)
        except Exception as exc:
            release_governance_gate = {"passed": False, "blockers": [f"release governance snapshot could not be evaluated: {exc}"]}
    release_governance_pass = nested(release_governance_gate, ["passed"])
    release_controls_pass = nested(real_user, ["release_controls_gate", "passed"])
    if release_controls_pass is None:
        release_controls_pass = bool(served_runtime_pass is True and release_governance_pass is True)

    first10_counts = first10_evaluation.get("derived_counts") if isinstance(first10_evaluation, dict) else {}
    first10_privacy_security_incidents = int(first10_counts.get("critical_privacy_security_failures") or 0) if isinstance(first10_counts, dict) else 0
    real_user_blockers = nested(real_user, ["blockers"], nested(uat, ["real_user_rollout", "blockers"], []))
    load_summary = {}
    for n, data in loads.items():
        load_summary[n] = {
            "exists": data is not None,
            "passed": nested(data, ["passed"], nested(uat, ["loads", n, "passed"])),
            "users_label": nested(data, ["users"], int(n)),
            "concurrency_model": nested(data, ["concurrency_model"], "UNKNOWN" if data is None else None),
            "total_requests": nested(data, ["total_requests"], nested(uat, ["loads", n, "total_requests"])),
            "success_rate": nested(data, ["success_rate"], nested(uat, ["loads", n, "success_rate"])),
            "p95_ms": nested(data, ["latency_ms", "p95"], nested(uat, ["loads", n, "p95_ms"])),
            "p99_ms": nested(data, ["latency_ms", "p99"], nested(uat, ["loads", n, "p99_ms"])),
            "timestamp": nested(data, ["timestamp"], nested(uat, ["loads", n, "timestamp"])),
        }

    local_release_candidate_ready = bool(version_consistent and (first_gate_pass is True) and (uat_pass is True) and (gate_pass is True))
    controlled_beta_ready = bool(
        pypi_package_current
        and github_source_current
        and cold_start_trust_pass is True
        and served_runtime_pass is True
        and release_governance_pass is True
        and self_service_ops_pass is True
        and ops_watchdog_pass is True
        and local_release_candidate_ready
        and first10_privacy_security_incidents == 0
    )
    controlled_beta_missing = []
    if not pypi_package_current:
        if pypi_description_stale:
            controlled_beta_missing.append("PyPI latest project description/long-description copy")
        elif pypi_fresh_current and pypi_alignment_failure:
            controlled_beta_missing.append(f"PyPI latest package source/metadata alignment ({pypi_alignment_failure})")
        else:
            controlled_beta_missing.append("PyPI latest/fresh-install/stdio MCP package path")
    if not github_source_current:
        controlled_beta_missing.append("GitHub source-install/stdio MCP channel")
    if cold_start_trust_pass is not True:
        controlled_beta_missing.append("cold-start trust gate")
    if served_runtime_pass is not True:
        controlled_beta_missing.append("served-runtime freshness")
    if release_governance_pass is not True:
        controlled_beta_missing.append("release governance / main branch protection")
    if self_service_ops_pass is not True:
        controlled_beta_missing.append("self-service ops gate")
    if rollback_drill_pass is not True:
        controlled_beta_missing.append("rollback/comms drill freshness")
    if ops_watchdog_pass is not True:
        controlled_beta_missing.append("ops watchdog")
    if not local_release_candidate_ready:
        controlled_beta_missing.append("local release-candidate gate")
    if first10_privacy_security_incidents != 0:
        controlled_beta_missing.append("first-10 privacy/security incident triage")

    max_recommended_real_users = 100 if public_self_serve_pass is True else 10 if controlled_beta_ready else 0
    controlled_beta_why = (
        "The 10-tester infrastructure, served-runtime freshness, release governance, and ops guardrails are green; broad launch remains NO-GO pending row-derived external-user evidence."
        if controlled_beta_ready
        else "Controlled first-10 beta is blocked until these failed gates are green: " + "; ".join(controlled_beta_missing or ["unknown readiness gate"])
    )
    verdicts = {
        "controlled_first_10_beta": {
            "verdict": "CONDITIONAL" if controlled_beta_ready else "NO-GO",
            "why": controlled_beta_why,
        },
        "local_release_candidate": {
            "verdict": "CONDITIONAL" if local_release_candidate_ready else "NO-GO",
            "why": "Local source/wheel gates pass; package/public rollout still depends on current PyPI proof, served runtime, release governance, and row-derived external-user evidence." if local_release_candidate_ready else "Required local first-user/readiness gates are not all passing or are missing.",
        },
        "unattended_git_onboarding": {
            "verdict": "NO-GO",
            "why": "No verified external install/onboarding evidence yet; Git-only flow should not be treated as self-serve until at least the first-10 scoreboard has real outcomes.",
        },
        "broad_public_launch": {
            "verdict": "NO-GO" if public_self_serve_pass is not True else "GO",
            "why": (
                "Public self-serve gate is blocked only by row-derived first-10 external-user evidence; PyPI/latest/fresh-install/MCP, GitHub source-install, docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates are green."
                if pypi_package_current
                and github_source_current
                and cold_start_trust_pass is True
                and served_runtime_pass is True
                and release_governance_pass is True
                and self_service_ops_pass is True
                and ops_watchdog_pass is True
                and public_self_serve_pass is not True
                else "Public self-serve gate is blocked until PyPI latest/fresh-install/MCP, GitHub source-install, docs/cold-start-trust/served-runtime/release-governance/self-service-ops/ops-watchdog gates pass and first-10 external evidence exists."
            ) if public_self_serve_pass is not True else "Public self-serve gate has passed with row-derived external evidence.",
        },
    }

    metrics = {
        "verified_external_users": {"value": verified_external_users, "honesty_label": "ROW_DERIVED_EXTERNAL_USERS", "provenance": external_user_evidence},
        "measured_savings": {"value": measured_savings, "honesty_label": "ROW_DERIVED_EXTERNAL_USER_SAVINGS", "provenance": external_user_evidence},
        "active_contributors_consumers": {"value": "UNKNOWN", "honesty_label": "MISSING_BORG_ANALYTICS_ARTIFACT", "provenance": "No Borg analytics export artifact was found under eval/ or docs/."},
        "packs": {"value": pcount if pcount is not None else "MISSING", "honesty_label": "REPO_FILE_COUNT" if pcount is not None else "MISSING", "provenance": "borg/seeds_data/packs/*.yaml"},
        "first_user_release_gate": {"value": status_bool(first_gate_pass), "honesty_label": "LOCAL_ARTIFACT", "provenance": "eval/first_user_release_gate_snapshot.json" if first else "MISSING"},
        "uat_scoreboard_synthetic_load": {"value": status_bool(uat_pass), "honesty_label": "LOCAL_ARTIFACT_LOGICAL_USERS", "provenance": "eval/uat_scoreboard_snapshot.json" if uat else "MISSING"},
        "gate_run_synthetic_load": {"value": status_bool(gate_pass), "honesty_label": "LOCAL_ARTIFACT_LOGICAL_USERS", "provenance": "eval/gate_run_snapshot.json" if gate else "MISSING"},
        "real_user_100_rollout_gate": {"value": status_bool(real_user_100_pass), "honesty_label": "REAL_EXTERNAL_USERS", "provenance": "eval/real_user_rollout_gate_snapshot.json" if real_user else "MISSING"},
        "max_recommended_real_users_now": {"value": max_recommended_real_users, "honesty_label": "REAL_EXTERNAL_USERS", "provenance": "eval/real_user_rollout_gate_snapshot.json" if real_user else "MISSING"},
        "public_self_serve_launch_gate": {"value": status_bool(public_self_serve_pass), "honesty_label": "PUBLIC_LAUNCH_GATE", "provenance": "eval/public_self_serve_launch_gate_snapshot.json" if public_gate else "MISSING"},
        "cold_start_trust_hardening_gate": {"value": status_bool(cold_start_trust_pass), "honesty_label": "FIRST_ANSWER_TRUST_GATE", "provenance": "eval/cold_start_trust_gate_snapshot.json" if cold_start_trust else "MISSING"},
        "served_runtime_freshness_gate": {"value": status_bool(served_runtime_pass), "honesty_label": "SERVED_RUNTIME_FINGERPRINT_GATE", "provenance": "eval/served_runtime_fingerprint_snapshot.json" if served_runtime_snapshot else "MISSING"},
        "release_governance_gate": {"value": status_bool(release_governance_pass), "honesty_label": "RELEASE_GOVERNANCE_BRANCH_PROTECTION_GATE", "provenance": "eval/release_governance_snapshot.json" if release_governance_snapshot else "MISSING"},
        "release_controls_gate": {"value": status_bool(release_controls_pass), "honesty_label": "SERVED_RUNTIME_PLUS_RELEASE_GOVERNANCE", "provenance": "eval/real_user_rollout_gate_snapshot.json" if real_user else "eval/served_runtime_fingerprint_snapshot.json; eval/release_governance_snapshot.json"},
        "self_service_ops_gate": {"value": status_bool(self_service_ops_pass), "honesty_label": "SELF_SERVICE_OPS_GATE", "provenance": "eval/self_service_ops_gate_snapshot.json" if self_service_ops else "MISSING"},
        "first_10_privacy_security_incidents": {"value": first10_privacy_security_incidents, "honesty_label": "ROW_DERIVED_EXTERNAL_USER_RISK", "provenance": external_user_evidence},
        "ops_readiness_watchdog": {"value": status_bool(ops_watchdog_pass), "honesty_label": "OPS_PROOF_FRESHNESS_GATE", "provenance": "eval/ops_readiness_watchdog_snapshot.json" if ops_watchdog else "MISSING"},
        "rollback_comms_drill": {"value": status_bool(rollback_drill_pass), "honesty_label": "DRY_RUN_ROLLBACK_COMMS_DRILL", "provenance": "eval/rollback_comms_drill_snapshot.json" if rollback_drill else "MISSING"},
        "pypi_fresh_install_canary": {"value": status_bool(pypi_fresh_current), "honesty_label": "PYPI_FRESH_INSTALL_CURRENT_VERSION", "provenance": "eval/pypi_fresh_install_snapshot.json" if pypi_fresh else "MISSING"},
        "github_source_install_canary": {"value": status_bool(github_source_current), "honesty_label": "GITHUB_SOURCE_FRESH_INSTALL_CURRENT_VERSION", "provenance": "eval/github_source_install_snapshot.json" if github_source else "MISSING"},
        "github_source_green": {"value": status_bool(github_source_green), "honesty_label": "STRICT_GITHUB_SOURCE_INSTALL_GATE", "provenance": f"eval/github_source_install_snapshot.json; canonical_target={github_source_gate.get('canonical_install_target')}; missing_results={github_source_gate.get('missing_required_results', [])}; missing_mcp_tools={github_source_gate.get('missing_mcp_tools', [])}"},
        "github_source_gate_detail": {"value": github_source_gate, "honesty_label": "STRICT_GITHUB_SOURCE_INSTALL_GATE_DETAIL", "provenance": "eval/public_self_serve_launch_gate.py github_source_install_check"},
        "pypi_package_current_gate": {"value": status_bool(pypi_package_current), "honesty_label": "PYPI_METADATA_PLUS_FRESH_INSTALL_CURRENT_SOURCE", "provenance": "eval/public_self_serve_launch_gate_snapshot.json gates.pypi_latest + eval/pypi_fresh_install_snapshot.json"},
        "source_version_consistency": {"value": f"pyproject={pv or 'MISSING'} runtime={rv or 'MISSING'}", "honesty_label": "REPO_SOURCE", "provenance": "pyproject.toml; borg/__init__.py"},
        "host_runtime_split_brain": {"value": status_bool(served_runtime_pass), "honesty_label": "SERVED_RUNTIME_EVIDENCE", "provenance": "Dashboard reads eval/served_runtime_fingerprint_snapshot.json; it does not restart or mutate long-lived Hermes/MCP runtimes. Served runtime GO requires borg_runtime_fingerprint with version_matches_source=true, reload_status=loaded_code_matches_source_behavior, and observe_behavior_canary.passed=true." if served_runtime_snapshot else "MISSING eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof."},
        "load_gates": {"value": load_summary, "honesty_label": "LOGICAL_USERS_NOT_REAL_USERS", "provenance": "eval/load_*_snapshot.json and eval/uat_scoreboard_snapshot.json"},
    }

    blockers = {
        "user_affecting": [
            "No real external first-user install/rescue outcome has been recorded yet.",
            "PyPI package gate is not green for the current source revision yet." if not pypi_package_current else "PyPI latest metadata and fresh-install canary are green for the current source revision.",
            "GitHub source-install canary is not green for the current source revision yet." if not github_source_current else "GitHub source-install canary is green: git-based install, CLI/API, and local stdio MCP work from an isolated non-repo environment.",
            "Cold-start trust gate is not green yet." if cold_start_trust_pass is not True else "Cold-start trust gate is green: meta/readiness prompts fail closed before random framework guidance reaches first users.",
            "Served runtime freshness gate is not green yet." if served_runtime_pass is not True else "Served runtime freshness gate is green: live MCP fingerprint matches source and behavior canaries.",
            "Release governance gate is not green yet." if release_governance_pass is not True else "Release governance gate is green: main branch protection, required checks, and CODEOWNERS review are proven.",
            "Self-service ops gate is not green yet." if self_service_ops_pass is not True else "Self-service ops gate is green: bad-answer intake, first-10 evidence intake, support/SLA, rollback/comms, and watchdog workflow exist.",
            "Ops watchdog has not produced a fresh green snapshot yet." if ops_watchdog_pass is not True else "Ops watchdog is green: proof snapshots and public status are internally consistent.",
            "Unattended Git-only onboarding remains unproven until external user can install, configure MCP, and receive a useful rescue without maintainer intervention.",
        ],
        "investor_affecting": [
            "Verified external users: 0 based on available hard evidence.",
            "Local/logical load gates prove engineering readiness, not market adoption or retention.",
        ],
        "security_privacy": [
            "Security surface artifacts/gates exist in local snapshots, but no third-party audit or live adversarial user evidence is present.",
            "Do not collect/share user traces until consent, redaction, revocation, and privacy policy are explicitly confirmed in the onboarding script.",
        ],
        "release_hygiene": [
            "Do not change repo visibility from this proof build.",
            "Need one supervised dry run from a clean PyPI install by a non-author before claiming self-serve readiness.",
        ],
        "evidence_gaps": [
            "No Borg analytics export proving active contributors or consumers was found.",
            "No first-10-user scoreboard with real outcomes exists yet.",
            "Ops readiness/watchdog plus served-runtime and release-governance gates must stay green; any P0/P1 bad-answer, privacy, support, stale-proof, stale-runtime, or branch-protection failure pauses controlled beta invites.",
            f"100-real-user gate remains blocked: {real_user_blockers or ['no blocker detail found']}",
            "Served/runtime freshness must be proven from eval/served_runtime_fingerprint_snapshot.json; source/fresh-process green is not live cutover proof.",
            "Release governance must be proven from eval/release_governance_snapshot.json; missing/unprotected branch details block release readiness.",
        ],
    }

    if controlled_beta_ready and pypi_package_current:
        first_tester_action = f"Use `pipx install agent-borg=={pypi_fresh_version or pv or 'CURRENT_VERSION'}` with controlled first-10 beta testers and label it as beta evidence capture, not public launch."
    elif pypi_package_current:
        first_tester_action = f"Do not invite controlled first-10 testers yet: `agent-borg=={pypi_fresh_version or pv or 'CURRENT_VERSION'}` package metadata and runtime canaries pass, but {', '.join(controlled_beta_missing or ['release/ops gates'])} must pass first."
    else:
        target_version = pv or "CURRENT_VERSION"
        if pypi_description_stale:
            first_tester_action = f"Do not invite controlled first-10 testers yet: `agent-borg=={pypi_fresh_version or target_version}` fresh-install/runtime canary passes, but the PyPI project description/long-description is stale; publish a new immutable version after `{target_version}` before using public package metadata as current proof. Served-runtime, release-governance, ops, and watchdog gates must also pass."
        elif pypi_latest_current is True and pypi_fresh_version == pv:
            first_tester_action = f"Do not invite controlled first-10 testers yet: rerun or fix the fresh-install + stdio MCP canary for immutable `agent-borg=={target_version}`; if the published artifact itself is wrong, bump and publish a new immutable version after `{target_version}`. Served-runtime, release-governance, ops, and watchdog gates must also pass before tester use."
        elif pypi_fresh_current and pypi_alignment_failure:
            first_tester_action = f"Do not invite controlled first-10 testers yet: `agent-borg=={pypi_fresh_version or target_version}` installs and runs, but package source/metadata alignment is blocked by `{pypi_alignment_failure}`; fix the source/proof state or publish a new immutable version after `{target_version}` before tester use."
        else:
            first_tester_action = f"Do not invite controlled first-10 testers yet: publish immutable `agent-borg=={target_version}`, then require PyPI latest metadata, fresh-install, stdio MCP, served-runtime, release-governance, ops, and watchdog gates to pass before using that exact version with testers."
    next_actions = [
        first_tester_action,
        "Create a fresh-PyPI runbook: install package, run borg --version, configure MCP, run one rescue, capture exact timestamps and blockers.",
        "Keep the self-service ops gate and watchdog green before each tester invite; pause if bad-answer/support/privacy intake fails.",
        "Record first user in the first-10 scoreboard template using a pseudonym and consented outcome fields.",
        "If any onboarding step fails, add artifact path/stdout/stderr and keep broad launch at NO-GO.",
        "Export Borg analytics or explicitly keep contributor/consumer metrics UNKNOWN.",
        "Before any public claim, replace logical-user load evidence with real external-user evidence or clearly label the distinction.",
    ]

    evidence = []
    if first:
        evidence.append(source_record("eval/first_user_release_gate_snapshot.json", f"first-user release gate all_pass={first_gate_pass}", nested(first, ["generated_at_utc"], nested(first, ["timestamp"]))))
    else:
        evidence.append(source_record("eval/first_user_release_gate_snapshot.json", "first-user release gate status unknown"))
    if uat:
        evidence.append(source_record("eval/uat_scoreboard_snapshot.json", f"UAT synthetic_load_all_pass={uat_pass}; real_user_100_all_pass={real_user_100_pass}; ready_for_10_logical_load={nested(uat, ['ready_for_10'])}; ready_for_1000_logical_load={nested(uat, ['ready_for_1000'])}; not_real_user_or_public_beta_evidence=True", nested(uat, ["timestamp"])))
    else:
        evidence.append(source_record("eval/uat_scoreboard_snapshot.json", "UAT scoreboard missing"))
    if gate:
        evidence.append(source_record("eval/gate_run_snapshot.json", f"gate run synthetic_load_all_pass={gate_pass}; overall_100_real_user_pass={real_user_100_pass}; ready_for_10_logical_load={nested(gate, ['ready_for_10'])}; ready_for_1000_logical_load={nested(gate, ['ready_for_1000'])}; not_real_user_or_public_beta_evidence=True", nested(gate, ["timestamp"])))
    else:
        evidence.append(source_record("eval/gate_run_snapshot.json", "gate run missing"))
    if real_user:
        evidence.append(source_record("eval/real_user_rollout_gate_snapshot.json", f"100-real-user gate={real_user_100_pass}; max_recommended_real_users={max_recommended_real_users}; blockers={real_user_blockers}", nested(real_user, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/real_user_rollout_gate_snapshot.json", "real-user rollout gate missing"))
    if first10_scoreboard:
        evidence.append(source_record("eval/first_10_user_scoreboard.json", f"first-10 row evidence users={verified_external_users}; measured_savings={measured_savings}; gate={nested(first10_evaluation, ['public_self_serve_launch_gate']) if isinstance(first10_evaluation, dict) else 'UNKNOWN'}", nested(first10_scoreboard, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/first_10_user_scoreboard.json", "first-10 row evidence scoreboard missing"))
    if public_gate:
        evidence.append(source_record("eval/public_self_serve_launch_gate_snapshot.json", f"public self-serve gate={public_self_serve_pass}; max_recommended_real_users={nested(public_gate, ['max_recommended_real_users_now'])}; blockers={nested(public_gate, ['blockers'], [])}", nested(public_gate, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/public_self_serve_launch_gate_snapshot.json", "public self-serve launch gate missing"))
    if cold_start_trust:
        cold_start_generated_at = nested(cold_start_trust, ["generated_at_utc"])
        evidence.append(source_record("eval/cold_start_trust_gate_snapshot.json", f"cold-start trust gate={cold_start_trust_pass}; blockers={nested(cold_start_trust, ['blockers'], [])}", cold_start_generated_at if isinstance(cold_start_generated_at, str) else None))
    else:
        evidence.append(source_record("eval/cold_start_trust_gate_snapshot.json", "cold-start trust hardening gate missing"))
    if self_service_ops:
        evidence.append(source_record("eval/self_service_ops_gate_snapshot.json", f"self-service ops gate={self_service_ops_pass}; blockers={nested(self_service_ops, ['blockers'], [])}", freshness_value(nested(self_service_ops, ["generated_at_utc"]))))
    else:
        evidence.append(source_record("eval/self_service_ops_gate_snapshot.json", "self-service ops readiness gate missing"))
    if ops_watchdog:
        evidence.append(source_record("eval/ops_readiness_watchdog_snapshot.json", f"ops readiness watchdog={ops_watchdog_pass}; blocker details live in eval/ops_readiness_watchdog_snapshot.json", freshness_value(nested(ops_watchdog, ["generated_at_utc"]))))
    else:
        evidence.append(source_record("eval/ops_readiness_watchdog_snapshot.json", "ops readiness watchdog snapshot missing"))
    if rollback_drill:
        evidence.append(source_record("eval/rollback_comms_drill_snapshot.json", f"rollback/comms drill={rollback_drill_pass}; dry_run_only={nested(rollback_drill, ['dry_run_only'])}", freshness_value(nested(rollback_drill, ["generated_at_utc"]))))
    else:
        evidence.append(source_record("eval/rollback_comms_drill_snapshot.json", "rollback/comms dry-run drill missing"))
    if pypi_fresh:
        evidence.append(source_record("eval/pypi_fresh_install_snapshot.json", f"PyPI fresh-install canary success={pypi_fresh_pass}; version={nested(pypi_fresh, ['version'])}", nested(pypi_fresh, ["generated_at_utc"])))
    else:
        evidence.append(source_record("eval/pypi_fresh_install_snapshot.json", "PyPI fresh-install canary missing"))
    if github_source:
        evidence.append(source_record("eval/github_source_install_snapshot.json", f"GitHub source-install canary strict_gate={github_source_green}; success={github_source_pass}; version={nested(github_source, ['version'])}; canonical_target={github_source_gate.get('canonical_install_target')}; missing_required_results={github_source_gate.get('missing_required_results', [])}; missing_mcp_tools={github_source_gate.get('missing_mcp_tools', [])}", freshness_value(nested(github_source, ["generated_at_utc"]))))
    else:
        evidence.append(source_record("eval/github_source_install_snapshot.json", "GitHub source-install canary missing"))
    for n, data in loads.items():
        evidence.append(source_record(f"eval/load_{n}_snapshot.json", f"logical load {n}: passed={load_summary[str(n)]['passed']}; total_requests={load_summary[str(n)]['total_requests']}; success_rate={load_summary[str(n)]['success_rate']}; p95_ms={load_summary[str(n)]['p95_ms']}; model={load_summary[str(n)]['concurrency_model']}", load_summary[str(n)]["timestamp"]))
    evidence.append(source_record("pyproject.toml", f"package version={pv}; scripts declared in project metadata"))
    evidence.append(source_record("borg/__init__.py", f"runtime __version__={rv}; top-level check() delegates to search"))

    first10_cols = [
        "user id/pseudonym",
        "install success",
        "time to first rescue",
        "rescue useful yes/no",
        "MCP setup success",
        "blocker",
        "outcome recorded",
        "baseline minutes without Borg",
        "actual minutes with Borg",
        "net minutes saved",
        "baseline tokens without Borg",
        "actual tokens with Borg",
        "net tokens saved",
        "savings counterfactual basis",
        "dead end avoided confirmed",
        "user confirmed value",
    ]
    first10_rows = [{c: "" for c in first10_cols} for _ in range(10)]

    return {
        "generated_at_utc": now_iso(),
        "repo": CANONICAL_REPO_URL,
        "source_revision": commit,
        "top_verdict": verdicts,
        "controlled_first_10_beta": {
            "answer": "CONDITIONAL GO" if controlled_beta_ready else "NO-GO",
            "conditions": [
                "Controlled testers only while package, served-runtime, release-governance, ops, watchdog, rollback, and docs gates remain green." if controlled_beta_ready else "Do not invite controlled beta users until these failed gates are green: " + "; ".join(controlled_beta_missing or ["unknown readiness gate"]),
                "Do not present as unattended public launch ready.",
                "Capture real first-user outcome evidence immediately." if controlled_beta_ready else "Keep first-10 evidence capture prepared, but blocked until package/release-control/ops evidence is green.",
            ],
        },
        "metrics": metrics,
        "evidence": evidence,
        "blockers": blockers,
        "first_10_user_scoreboard_template": {"columns": first10_cols, "rows": first10_rows},
        "anti_hype": {
            "simulated_users_are_not_real_users": True,
            "internal_sessions_are_not_adoption": True,
            "verified_external_users_default_zero": True,
            "text": "Simulated/logical users are not real users. Internal sessions, tool calls, local tests, and maintainer runs are not adoption. Real verified external users are 0 unless a hard evidence artifact proves otherwise; no such artifact was found by this build.",
        },
        "next_action_queue_before_sharing_git_with_first_user": next_actions,
    }


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", "<br>") for x in row) + " |")
    return "\n".join(out)


def render_md(model: dict) -> str:
    verdict_rows = [[k.replace("_", " "), v["verdict"], v["why"]] for k, v in model["top_verdict"].items()]
    metric_rows = []
    for k, v in model["metrics"].items():
        val = v["value"]
        if isinstance(val, (dict, list)):
            val = "`" + json.dumps(val, sort_keys=True) + "`"
        metric_rows.append([k, val, v["honesty_label"], v["provenance"]])
    evidence_rows = [[e["path"], e["exists"], e["sha256"] or "MISSING", e["freshness_timestamp"] or "UNKNOWN", e["claim_derived"]] for e in model["evidence"]]
    blocker_rows = [[cat.replace("_", " "), "<br>".join(items)] for cat, items in model["blockers"].items()]
    score_cols = model["first_10_user_scoreboard_template"]["columns"]
    score_rows = [[i + 1] + [r[c] for c in score_cols] for i, r in enumerate(model["first_10_user_scoreboard_template"]["rows"])]
    next_rows = [[i + 1, item] for i, item in enumerate(model["next_action_queue_before_sharing_git_with_first_user"])]
    return f"""# Borg Proof Dashboard

Generated: `{model['generated_at_utc']}`
Repo: `{model['repo']}`
Source snapshot: `{model.get('source_revision') or 'UNKNOWN'}`

## Big top verdict

{md_table(['Scope', 'Verdict', 'Why'], verdict_rows)}

**Controlled first-10 beta only?** {model['controlled_first_10_beta']['answer']} — {'; '.join(model['controlled_first_10_beta']['conditions'])}

## Metrics with provenance and honesty labels

{md_table(['Metric', 'Value', 'Honesty label', 'Provenance'], metric_rows)}

## Evidence table

{md_table(['Source file path', 'Exists', 'SHA256', 'Freshness timestamp', 'Exact claim derived'], evidence_rows)}

## Blockers

{md_table(['Category', 'Blockers'], blocker_rows)}

## First-10-user scoreboard template

{md_table(['#'] + score_cols, score_rows)}

## Anti-hype section

{model['anti_hype']['text']}

## Next action queue before controlled first-10 beta testers

{md_table(['#', 'Action'], next_rows)}
"""


def render_html(model: dict, md: str) -> str:
    # Simple standalone HTML; the markdown is embedded as escaped preformatted source plus readable sections.
    css = """
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1180px;margin:2rem auto;padding:0 1rem;line-height:1.45;color:#16202a}table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #d7dee8;padding:.5rem;vertical-align:top}th{background:#edf2f7}.verdict{font-size:1.25rem;font-weight:700}.conditional{color:#9a5b00}.nogo{color:#9b1c1c}.go{color:#126b33}.note{background:#fff7db;border:1px solid #f0ce73;padding:1rem;border-radius:8px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em;word-break:break-all}pre{white-space:pre-wrap;background:#f7fafc;border:1px solid #d7dee8;padding:1rem;border-radius:8px}
"""
    def esc(x): return html.escape(str(x))
    verdict_html = "".join(f"<tr><td>{esc(k.replace('_',' '))}</td><td class='verdict {esc(v['verdict'].lower().replace('-',''))}'>{esc(v['verdict'])}</td><td>{esc(v['why'])}</td></tr>" for k,v in model["top_verdict"].items())
    metric_html = "".join(f"<tr><td>{esc(k)}</td><td class='mono'>{esc(json.dumps(v['value'], sort_keys=True) if isinstance(v['value'], (dict,list)) else v['value'])}</td><td>{esc(v['honesty_label'])}</td><td>{esc(v['provenance'])}</td></tr>" for k,v in model["metrics"].items())
    evidence_html = "".join(f"<tr><td class='mono'>{esc(e['path'])}</td><td>{esc(e['exists'])}</td><td class='mono'>{esc(e['sha256'] or 'MISSING')}</td><td>{esc(e['freshness_timestamp'] or 'UNKNOWN')}</td><td>{esc(e['claim_derived'])}</td></tr>" for e in model["evidence"])
    blockers_html = "".join(f"<tr><td>{esc(k.replace('_',' '))}</td><td><ul>{''.join('<li>'+esc(i)+'</li>' for i in v)}</ul></td></tr>" for k,v in model["blockers"].items())
    cols = model["first_10_user_scoreboard_template"]["columns"]
    score_head = "".join(f"<th>{esc(c)}</th>" for c in ["#"]+cols)
    score_body = "".join("<tr><td>%d</td>%s</tr>" % (i+1, "".join(f"<td>{esc(row[c])}</td>" for c in cols)) for i,row in enumerate(model["first_10_user_scoreboard_template"]["rows"]))
    next_html = "".join(f"<li>{esc(x)}</li>" for x in model["next_action_queue_before_sharing_git_with_first_user"])
    return f"""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Borg Proof Dashboard</title><style>{css}</style></head><body>
<h1>Borg Proof Dashboard</h1><p>Generated: <span class=\"mono\">{esc(model['generated_at_utc'])}</span><br>Repo: <span class=\"mono\">{esc(model['repo'])}</span><br>Source snapshot: <span class=\"mono\">{esc(model.get('source_revision') or 'UNKNOWN')}</span></p>
<h2>Big top verdict</h2><table><tr><th>Scope</th><th>Verdict</th><th>Why</th></tr>{verdict_html}</table>
<p class=\"note\"><strong>Controlled first-10 beta only?</strong> {esc(model['controlled_first_10_beta']['answer'])}. {' '.join(esc(c) for c in model['controlled_first_10_beta']['conditions'])}</p>
<h2>Metrics with provenance and honesty labels</h2><table><tr><th>Metric</th><th>Value</th><th>Honesty label</th><th>Provenance</th></tr>{metric_html}</table>
<h2>Evidence table</h2><table><tr><th>Source file path</th><th>Exists</th><th>SHA256</th><th>Freshness timestamp</th><th>Exact claim derived</th></tr>{evidence_html}</table>
<h2>Blockers</h2><table><tr><th>Category</th><th>Blockers</th></tr>{blockers_html}</table>
<h2>First-10-user scoreboard template</h2><table><tr>{score_head}</tr>{score_body}</table>
<h2>Anti-hype section</h2><p class=\"note\">{esc(model['anti_hype']['text'])}</p>
<h2>Next action queue before controlled first-10 beta testers</h2><ol>{next_html}</ol>
<h2>Markdown source</h2><pre>{esc(md)}</pre>
</body></html>"""


def build_public_payloads(model: dict) -> tuple[dict, dict, dict]:
    """Return compact JSON payloads consumed by docs/public/borg-live-dashboard.html."""
    controlled = model["top_verdict"]["controlled_first_10_beta"]
    broad = model["top_verdict"]["broad_public_launch"]
    local = model["top_verdict"]["local_release_candidate"]
    blockers = model.get("blockers", {})
    metrics = model.get("metrics", {})
    source_version = str(metrics.get("source_version_consistency", {}).get("value", "UNKNOWN"))
    measured_savings = metrics.get("measured_savings", {}).get("value", {}) or {}
    generated = model["generated_at_utc"]
    controlled_is_green = controlled.get("verdict") == "CONDITIONAL"
    broad_is_green = broad.get("verdict") == "GO"
    package_path_green = metrics.get("pypi_package_current_gate", {}).get("value") == "PASS"
    github_source_path_green = metrics.get("github_source_green", {}).get("value") == "PASS"
    pypi_fresh_green = metrics.get("pypi_fresh_install_canary", {}).get("value") == "PASS"
    flat_blockers = [str(item) for items in blockers.values() for item in (items if isinstance(items, list) else [items])]
    pypi_metadata_stale = any("description" in item.lower() or "long-description" in item.lower() or "metadata" in item.lower() for item in flat_blockers)
    if broad_is_green:
        public_state = "GO public self-serve"
        value_detail = "Public self-serve launch gate is green with row-derived external-user evidence."
    elif controlled_is_green:
        public_state = "NO-GO public self-serve; controlled first-10 beta CONDITIONAL GO while gates remain green"
        value_detail = "Controlled first-10 public-package beta package, served-runtime, release-governance, and ops guardrails are green; public self-serve remains blocked until row-derived first-10 external-user evidence passes."
    elif package_path_green and github_source_path_green:
        public_state = "NO-GO public self-serve; package and GitHub source proof green, release controls blocked"
        value_detail = "Public-package and GitHub source-install controlled beta channels are green, but controlled beta remains blocked until the failing release-control and ops gates pass; served-runtime freshness, release governance, rollback/self-service ops, watchdog, docs guard, and privacy/security gates must all stay green before invites."
    elif package_path_green:
        public_state = "NO-GO public self-serve; public package proof green, GitHub source proof blocked"
        value_detail = "Public-package controlled beta remains blocked: PyPI/package proof is green, but GitHub source-install proof or release-control/ops gates are not green for this source revision."
    elif pypi_fresh_green and not package_path_green:
        public_state = "NO-GO public self-serve; PyPI runtime canary green, package metadata stale"
        if pypi_metadata_stale:
            value_detail = "Public-package controlled beta remains blocked: fresh PyPI install/runtime canary passes, but PyPI package metadata/description is not current proof."
        else:
            value_detail = "Public-package controlled beta remains blocked: fresh PyPI install/runtime canary passes, but PyPI metadata/source alignment is not current proof."
    else:
        public_state = "NO-GO public self-serve; source/local release-candidate only"
        value_detail = "Public-package controlled beta remains blocked until package, release-control, and ops gates pass; PyPI/fresh-install proof is not yet current for the source version."

    status_payload = {
        "schema_version": 1,
        "source": "docs/public/status.json",
        "updated_at": generated,
        "repo": model["repo"],
        "source_revision": model.get("source_revision"),
        "source_version_consistency": source_version,
        "readiness": broad["verdict"],
        "state": public_state,
        "status": broad["verdict"],
        "decision": broad["verdict"],
        "go_no_go": broad["why"],
        "distribution_gate": controlled["verdict"],
        "local_release_candidate": local,
        "controlled_first_10_beta": controlled,
        "broad_public_launch": broad,
        "max_recommended_real_users_now": metrics.get("max_recommended_real_users_now", {}).get("value", 0),
        "verified_external_users": metrics.get("verified_external_users", {}).get("value", 0),
        "cold_start_trust_hardening_gate": metrics.get("cold_start_trust_hardening_gate", {}).get("value", "UNKNOWN"),
        "served_runtime_freshness_gate": metrics.get("served_runtime_freshness_gate", {}).get("value", "UNKNOWN"),
        "release_governance_gate": metrics.get("release_governance_gate", {}).get("value", "UNKNOWN"),
        "release_controls_gate": metrics.get("release_controls_gate", {}).get("value", "UNKNOWN"),
        "self_service_ops_gate": metrics.get("self_service_ops_gate", {}).get("value", "UNKNOWN"),
        "ops_readiness_watchdog": metrics.get("ops_readiness_watchdog", {}).get("value", "UNKNOWN"),
        "rollback_comms_drill": metrics.get("rollback_comms_drill", {}).get("value", "UNKNOWN"),
        "github_source_green": metrics.get("github_source_green", {}).get("value", "UNKNOWN"),
        "github_source_install_canary": metrics.get("github_source_install_canary", {}).get("value", "UNKNOWN"),
        "blockers": blockers,
        "evidence": [
            "eval/first_user_release_gate_snapshot.json",
            "eval/public_self_serve_launch_gate_snapshot.json",
            "eval/cold_start_trust_gate_snapshot.json",
            "eval/served_runtime_fingerprint_snapshot.json",
            "eval/release_governance_snapshot.json",
            "eval/self_service_ops_gate_snapshot.json",
            "eval/ops_readiness_watchdog_snapshot.json",
            "eval/rollback_comms_drill_snapshot.json",
            "eval/pypi_fresh_install_snapshot.json",
            "eval/github_source_install_snapshot.json",
            "eval/real_user_rollout_gate_snapshot.json",
        ],
    }
    value_payload = {
        "schema_version": 1,
        "updated_at": generated,
        "headline": "ACTION / STOP / VERIFY rescue packets are green in local/source first-user gates",
        "summary": "Borg gives coding agents a concrete next action, a dead end to avoid, and a verification step for known failure classes.",
        "detail": value_detail,
        "primary_metric": "LOCAL_SOURCE_FIRST_USER_GATE_" + str(metrics.get("first_user_release_gate", {}).get("value", "UNKNOWN")),
        "primary_metric_scope": "local/source first-user release gate; not external adoption or public-package beta proof",
        "honesty_label": "LOCAL_SOURCE_GATE_NOT_EXTERNAL_ADOPTION",
        "value_honesty_label": "ROW_DERIVED_EXTERNAL_USER_SAVINGS_REQUIRED",
        "verified_external_users": metrics.get("verified_external_users", {}).get("value", 0),
        "measured_savings": {
            "rows_with_measured_value": int(measured_savings.get("rows_with_measured_value") or 0),
            "dead_ends_avoided_confirmed": int(measured_savings.get("dead_ends_avoided_confirmed") or 0),
            "net_minutes_saved": float(measured_savings.get("net_minutes_saved") or 0.0),
            "positive_minutes_saved": float(measured_savings.get("positive_minutes_saved") or 0.0),
            "negative_minutes_cost": float(measured_savings.get("negative_minutes_cost") or 0.0),
            "net_tokens_saved": int(measured_savings.get("net_tokens_saved") or 0),
            "positive_tokens_saved": int(measured_savings.get("positive_tokens_saved") or 0),
            "negative_tokens_cost": int(measured_savings.get("negative_tokens_cost") or 0),
            "counterfactual_basis_counts": measured_savings.get("counterfactual_basis_counts") or {},
        },
        "measurement_contract": "Only consented external first-10 rows with before/after time or token data can create measured savings. Estimates and maintainer runs do not count.",
    }
    impact_payload = {
        "schema_version": 1,
        "updated_at": generated,
        "headline": "external-user impact not proven yet",
        "summary": "0 verified external users in row-derived first-10 evidence; synthetic/logical load does not count as adoption.",
        "detail": "Public self-serve launch requires 10 consented external users, at least 8 installs, at least 6 useful rescues, and 0 critical privacy/security incidents.",
        "primary_impact": "NO-GO public self-serve",
        "measured_savings": value_payload["measured_savings"],
        "honesty_label": "REAL_EXTERNAL_USERS_REQUIRED",
    }
    return status_payload, value_payload, impact_payload


def display_path(path: Path) -> str:
    """Return a stable path for CLI output even when tests redirect outputs."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def render_pages_redirect(*, title: str, target_href: str, status_href: str) -> str:
    """Return a stable GitHub Pages redirect shell for human and bot users.

    GitHub Pages can serve `/`, `/proof-dashboard/`, and `/status.json` from
    the `/docs` source.  The canonical generated dashboard intentionally lives
    under `docs/public/proof-dashboard/`; these small aliases keep natural
    self-service URLs live without duplicating the dashboard payload.
    """
    safe_title = html.escape(title)
    safe_target = html.escape(target_href, quote=True)
    safe_status = html.escape(status_href, quote=True)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <meta http-equiv=\"refresh\" content=\"0; url={safe_target}\">
  <title>{safe_title}</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif; background: #05070d; color: #e5eefc; }}
    main {{ max-width: 720px; padding: 32px; }}
    a {{ color: #8bd3ff; }}
  </style>
</head>
<body>
  <main>
    <h1>Redirecting to Borg proof dashboard…</h1>
    <p>If redirect does not happen, open <a href=\"{safe_target}\">the canonical proof dashboard</a>.</p>
    <p>Machine status: <a href=\"{safe_status}\">status.json</a></p>
  </main>
</body>
</html>
"""


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    EVAL.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    PUBLIC_STATUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_STATUS_ALIAS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAGES_ROOT_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAGES_PROOF_ALIAS_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_VALUE_OUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_IMPACT_OUT.parent.mkdir(parents=True, exist_ok=True)
    model = build_model()
    md = render_md(model)
    html_text = render_html(model, md)
    status_payload, value_payload, impact_payload = build_public_payloads(model)
    JSON_OUT.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MD_OUT.write_text(md, encoding="utf-8")
    HTML_OUT.write_text(html_text, encoding="utf-8")
    PUBLIC_OUT.write_text(html_text, encoding="utf-8")
    status_text = json.dumps(status_payload, indent=2, sort_keys=True) + "\n"
    PUBLIC_STATUS_OUT.write_text(status_text, encoding="utf-8")
    PUBLIC_STATUS_ALIAS_OUT.write_text(status_text, encoding="utf-8")
    PAGES_ROOT_OUT.write_text(
        render_pages_redirect(
            title="Borg proof dashboard",
            target_href="./public/proof-dashboard/",
            status_href="./status.json",
        ),
        encoding="utf-8",
    )
    PAGES_PROOF_ALIAS_OUT.write_text(
        render_pages_redirect(
            title="Borg proof dashboard redirect",
            target_href="../public/proof-dashboard/",
            status_href="../status.json",
        ),
        encoding="utf-8",
    )
    PUBLIC_VALUE_OUT.write_text(json.dumps(value_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    PUBLIC_IMPACT_OUT.write_text(json.dumps(impact_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(display_path(MD_OUT))
    print(display_path(HTML_OUT))
    print(display_path(JSON_OUT))
    print(display_path(PUBLIC_OUT))
    print(display_path(PUBLIC_STATUS_OUT))
    print(display_path(PUBLIC_STATUS_ALIAS_OUT))
    print(display_path(PAGES_ROOT_OUT))
    print(display_path(PAGES_PROOF_ALIAS_OUT))
    print(display_path(PUBLIC_VALUE_OUT))
    print(display_path(PUBLIC_IMPACT_OUT))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
