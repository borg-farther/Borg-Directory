#!/usr/bin/env python3
"""Lint the Borg proof dashboard for evidence discipline and anti-hype guardrails."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "eval" / "borg_proof_dashboard.json"
MD_PATH = ROOT / "docs" / "BORG_PROOF_DASHBOARD.md"
HTML_PATH = ROOT / "docs" / "BORG_PROOF_DASHBOARD.html"
PUBLIC_PATH = ROOT / "docs" / "public" / "proof-dashboard" / "index.html"

HYPE_PHRASES = [
    "proven external adoption",
    "hundreds of users",
    "production ready",
]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def main() -> int:
    required = [JSON_PATH, MD_PATH, HTML_PATH, PUBLIC_PATH]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        return fail("missing required files: " + ", ".join(missing))
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid JSON: {exc}")

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
    required_cols = ["user id/pseudonym", "install success", "time to first rescue", "rescue useful yes/no", "MCP setup success", "blocker", "outcome recorded"]
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

    metrics = data.get("metrics", {})
    veu = metrics.get("verified_external_users", {})
    if veu.get("value") != 0:
        return fail("verified external users must be 0 unless this lint is extended with hard evidence validation")
    if data.get("top_verdict", {}).get("broad_public_launch", {}).get("verdict") != "NO-GO":
        return fail("broad public launch must remain NO-GO without real external-user evidence")

    evidence_proves_external = bool(data.get("evidence_fields_proving_external_adoption"))
    for phrase in HYPE_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", text, re.I) and not evidence_proves_external:
            # The phrase may appear inside the lint policy itself only if not in dashboard outputs; here we scan outputs only.
            return fail(f"hype phrase without validated evidence field: {phrase}")

    # Explicitly require required sections in Markdown for human readers.
    md = MD_PATH.read_text(encoding="utf-8")
    for heading in ["## Big top verdict", "## Evidence table", "## Blockers", "## First-10-user scoreboard template", "## Anti-hype section", "## Next action queue before sharing Git with first user"]:
        if heading not in md:
            return fail(f"missing Markdown heading: {heading}")

    print("PASS: Borg proof dashboard lint")
    return 0

if __name__ == "__main__":
    sys.exit(main())
