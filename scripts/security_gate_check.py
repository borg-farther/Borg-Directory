#!/usr/bin/env python3
"""Policy gate for Borg privacy-safe failure memory baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/PRIVACY_MODEL.md",
    "docs/LEARNING_ATOM_SCHEMA.md",
    "docs/PROMPT_INJECTION_THREAT_MODEL.md",
    "docs/TRUST_AND_PROMOTION.md",
    "docs/REVOCATION_AND_DELETION.md",
    "docs/EVAL_PLAN_FAILURE_MEMORY.md",
    "docs/SECURITY_HARDENING_BASELINE.md",
    "eval/security_hardening_baseline.json",
    ".github/workflows/security-gates.yml",
    "LICENSE",
    "borg/core/learning_atoms.py",
    "borg/core/prompt_injection.py",
    "borg/core/atom_policy.py",
    "borg/core/atom_store.py",
    "borg/core/atom_retrieval.py",
]

REQUIRED_PRIVACY_SENTENCE = (
    "Borg is failure memory for AI coding agents. It does not upload raw agent conversations, "
    "raw traces, tool outputs, source files, screenshots, or environment variables by default. "
    "Any shared failure-memory path is opt-in and accepts only signed, sanitized, revocable learning atoms."
)

FORBIDDEN_CLAIMS = [
    "proven 30% improvement",
    "validated at scale",
    "zero risk",
    "fully anonymous",
    "10m-agent ready",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> int:
    missing = [p for p in REQUIRED_FILES if not (ROOT / p).exists()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    privacy_doc = (ROOT / "docs/PRIVACY_MODEL.md").read_text(encoding="utf-8")
    if REQUIRED_PRIVACY_SENTENCE not in privacy_doc:
        fail("PRIVACY_MODEL.md missing required exact privacy sentence")

    docs_text = "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in (ROOT / "docs").glob("*.md")
    ).lower()
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8", errors="ignore")
    if "SECURITY_HARDENING_BASELINE.md" not in docs_index or "security_hardening_baseline.json" not in docs_index:
        fail("docs/README.md missing security baseline references")
    for claim in FORBIDDEN_CLAIMS:
        if claim in docs_text:
            fail(f"forbidden claim found: {claim}")

    baseline = json.loads((ROOT / "eval/security_hardening_baseline.json").read_text(encoding="utf-8"))
    workflow_text = (ROOT / ".github" / "workflows" / "security-gates.yml").read_text(encoding="utf-8", errors="ignore")
    if "pip-audit || true" in workflow_text or "bandit" in workflow_text and "bandit" in workflow_text.split("bandit", 1)[1].split("\n", 1)[0] and "|| true" in workflow_text.split("bandit", 1)[1].split("\n", 1)[0]:
        fail("security workflow contains fail-open scanner command")
    if "pip-audit" not in workflow_text:
        fail("security workflow missing dependency audit command")
    if "python -m pip install -e" not in workflow_text or ".[http,crypto]" not in workflow_text:
        fail("dependency audit must install Borg package runtime/security extras before running pip-audit")

    for key in ["threat_model", "controls", "ci_gates", "release_blockers"]:
        if key not in baseline or not baseline[key]:
            fail(f"baseline missing populated key: {key}")

    required_gates = {"secret_scan", "dependency_vuln_scan", "static_security_scan", "policy_enforcement"}
    if not required_gates.issubset(set(baseline.get("ci_gates", []))):
        fail("baseline missing required CI gates")

    print("PASS: Borg security hardening policy gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
