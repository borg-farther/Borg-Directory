#!/usr/bin/env python3
"""Lint the Borg proof dashboard for evidence discipline and anti-hype guardrails."""
from __future__ import annotations

import json
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "eval" / "borg_proof_dashboard.json"
MD_PATH = ROOT / "docs" / "BORG_PROOF_DASHBOARD.md"
HTML_PATH = ROOT / "docs" / "BORG_PROOF_DASHBOARD.html"
PUBLIC_PATH = ROOT / "docs" / "public" / "proof-dashboard" / "index.html"
PUBLIC_STATUS_PATH = ROOT / "docs" / "public" / "status.json"
PUBLIC_VALUE_PATH = ROOT / "docs" / "public" / "value.json"
PUBLIC_IMPACT_PATH = ROOT / "docs" / "public" / "impact" / "impact.json"
POST_DASHBOARD_CHECK_PATH = ROOT / "eval" / "ops_readiness_watchdog_post_dashboard_check.json"

HYPE_PHRASES = [
    "proven external adoption",
    "hundreds of users",
    "production ready",
]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def main() -> int:
    required = [JSON_PATH, MD_PATH, HTML_PATH, PUBLIC_PATH, PUBLIC_STATUS_PATH, PUBLIC_VALUE_PATH, PUBLIC_IMPACT_PATH, POST_DASHBOARD_CHECK_PATH]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        return fail("missing required files: " + ", ".join(missing))
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        public_status = json.loads(PUBLIC_STATUS_PATH.read_text(encoding="utf-8"))
        public_value = json.loads(PUBLIC_VALUE_PATH.read_text(encoding="utf-8"))
        public_impact = json.loads(PUBLIC_IMPACT_PATH.read_text(encoding="utf-8"))
        post_dashboard_check = json.loads(POST_DASHBOARD_CHECK_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid JSON: {exc}")

    generated_at = data.get("generated_at_utc")
    source_revision = data.get("source_revision")
    if public_status.get("updated_at") != generated_at:
        return fail("docs/public/status.json updated_at does not match dashboard generated_at_utc")
    if public_value.get("updated_at") != generated_at:
        return fail("docs/public/value.json updated_at does not match dashboard generated_at_utc")
    if public_impact.get("updated_at") != generated_at:
        return fail("docs/public/impact/impact.json updated_at does not match dashboard generated_at_utc")
    if public_status.get("source_revision") != source_revision:
        return fail("docs/public/status.json source_revision does not match dashboard source_revision")
    post_checks = post_dashboard_check.get("checks") or {}
    post_dashboard_consistency = post_checks.get("public_json_dashboard_consistency") or {}
    post_source_honesty = post_checks.get("source_revision_honesty") or {}
    if post_dashboard_check.get("passed") is not True:
        return fail("post-dashboard watchdog check did not pass")
    if post_dashboard_consistency.get("passed") is not True:
        return fail("post-dashboard watchdog did not validate public JSON/dashboard consistency")
    if post_dashboard_consistency.get("dashboard_generated_at_utc") != generated_at:
        return fail("post-dashboard watchdog checked a different dashboard generated_at_utc")
    if post_dashboard_consistency.get("dashboard_source_revision") != source_revision:
        return fail("post-dashboard watchdog checked a different dashboard source_revision")
    if post_source_honesty.get("passed") is not True:
        return fail("post-dashboard watchdog source_revision_honesty did not pass")
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in [MD_PATH, HTML_PATH])
    anti = data.get("anti_hype", {})
    if not anti or not anti.get("simulated_users_are_not_real_users") or not anti.get("internal_sessions_are_not_adoption"):
        return fail("anti-hype section missing required boolean guardrails")
    anti_text = str(anti.get("text", "")).lower()
    for required_phrase in ["simulated/logical users are not real users", "internal sessions", "real verified external users are 0"]:
        if required_phrase not in anti_text:
            return fail(f"anti-hype text missing phrase: {required_phrase}")

    scoreboard = data.get("first_10_user_scoreboard_template", {})
    cols = scoreboard.get("columns", [])
    required_cols = [
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
    if cols != required_cols:
        return fail("first-10 scoreboard columns are missing or reordered")
    if len(scoreboard.get("rows", [])) < 10:
        return fail("first-10 scoreboard requires at least 10 template rows")

    evidence = data.get("evidence", [])
    if not evidence:
        return fail("evidence table is empty")
    for idx, item in enumerate(evidence):
        if not item.get("path") or "exists" not in item or not item.get("claim_derived"):
            return fail(f"evidence row {idx} missing path/exists/claim")
        if item.get("exists") and not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
            return fail(f"evidence row {idx} has invalid sha256")
        if item.get("exists"):
            source_path = ROOT / str(item["path"])
            if not source_path.exists():
                return fail(f"evidence row {idx} says exists but source file is missing: {item['path']}")
            actual = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if item.get("sha256") != actual:
                return fail(f"evidence row {idx} has stale sha256 for {item['path']}")

    metrics = data.get("metrics", {})
    if public_status.get("controlled_first_10_beta") != data.get("top_verdict", {}).get("controlled_first_10_beta"):
        return fail("docs/public/status.json controlled_first_10_beta does not match dashboard verdict")
    if public_status.get("broad_public_launch") != data.get("top_verdict", {}).get("broad_public_launch"):
        return fail("docs/public/status.json broad_public_launch does not match dashboard verdict")
    if public_status.get("max_recommended_real_users_now") != metrics.get("max_recommended_real_users_now", {}).get("value", 0):
        return fail("docs/public/status.json max_recommended_real_users_now does not match dashboard metric")
    if public_status.get("verified_external_users") != metrics.get("verified_external_users", {}).get("value", 0):
        return fail("docs/public/status.json verified_external_users does not match dashboard metric")
    served_runtime_status = public_status.get("served_runtime_freshness_gate")
    release_governance_status = public_status.get("release_governance_gate")
    release_controls_status = public_status.get("release_controls_gate")
    if release_controls_status == "PASS" and (served_runtime_status != "PASS" or release_governance_status != "PASS"):
        return fail("docs/public/status.json release_controls_gate PASS while served/runtime or governance subgate is not PASS")
    if (served_runtime_status == "FAIL" or release_governance_status == "FAIL") and release_controls_status == "PASS":
        return fail("docs/public/status.json release_controls_gate overclaims PASS despite failing subgate")
    measured = (metrics.get("measured_savings", {}) or {}).get("value", {}) or {}
    if public_value.get("measured_savings") != {
        "rows_with_measured_value": int(measured.get("rows_with_measured_value") or 0),
        "dead_ends_avoided_confirmed": int(measured.get("dead_ends_avoided_confirmed") or 0),
        "net_minutes_saved": float(measured.get("net_minutes_saved") or 0.0),
        "positive_minutes_saved": float(measured.get("positive_minutes_saved") or 0.0),
        "negative_minutes_cost": float(measured.get("negative_minutes_cost") or 0.0),
        "net_tokens_saved": int(measured.get("net_tokens_saved") or 0),
        "positive_tokens_saved": int(measured.get("positive_tokens_saved") or 0),
        "negative_tokens_cost": int(measured.get("negative_tokens_cost") or 0),
        "counterfactual_basis_counts": measured.get("counterfactual_basis_counts") or {},
    }:
        return fail("docs/public/value.json measured_savings does not match dashboard metric")
    if public_impact.get("measured_savings") != public_value.get("measured_savings"):
        return fail("docs/public/impact/impact.json measured_savings does not match value.json")
    veu = metrics.get("verified_external_users", {})
    if veu.get("value") != 0:
        return fail("verified external users must be 0 unless this lint is extended with hard evidence validation")
    if data.get("top_verdict", {}).get("broad_public_launch", {}).get("verdict") != "NO-GO":
        return fail("broad public launch must remain NO-GO without real external-user evidence")
    if data.get("repo") != "https://github.com/borg-farther/Borg-Directory":
        return fail("dashboard repo field must use canonical GitHub URL, not a local filesystem path")
    if not re.fullmatch(r"[0-9a-f]{40}(?:\+dirty)?", str(data.get("source_revision", ""))):
        return fail("dashboard source_revision must be the exact git commit SHA, optionally marked +dirty for generated working-tree snapshots")

    evidence_proves_external = bool(data.get("evidence_fields_proving_external_adoption"))
    for phrase in HYPE_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text, re.I) and not evidence_proves_external:
            # The phrase may appear inside the lint policy itself only if not in dashboard outputs; here we scan outputs only.
            return fail(f"hype phrase without validated evidence field: {phrase}")

    # Explicitly require required sections in Markdown for human readers.
    md = MD_PATH.read_text(encoding="utf-8")
    for heading in ["## Big top verdict", "## Evidence table", "## Blockers", "## First-10-user scoreboard template", "## Anti-hype section", "## Next action queue before controlled first-10 beta testers"]:
        if heading not in md:
            return fail(f"missing Markdown heading: {heading}")

    print("PASS: Borg proof dashboard lint")
    return 0

if __name__ == "__main__":
    sys.exit(main())
