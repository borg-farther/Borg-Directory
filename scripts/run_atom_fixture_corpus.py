#!/usr/bin/env python3
"""Run Borg M0 atom safety fixture corpus."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from borg.core.atom_policy import AtomDecision, classify_atom_policy
from borg.core.learning_atoms import compute_atom_id

FIXTURES = ROOT / "borg" / "tests" / "fixtures"


def atom_with_text(text: str) -> dict:
    atom = {
        "schema_version": "1.0",
        "scope": "local",
        "task": {"type": "debug", "technology": ["python"], "error_class": "generic-error", "error_pattern": "fixture", "difficulty": "unknown"},
        "learning": {"root_cause_class": "fixture", "worked": text, "avoid": ["repeat unsafe approach"], "why": "fixture"},
        "evidence": {"type": "agent_reported", "strength": "weak", "support_count": 1},
        "privacy": {"risk_score": 0, "scanner_version": "privacy-v1", "finding_classes": [], "redaction_count": 0, "raw_trace_retained": False},
        "safety": {"prompt_injection_score": 0, "injection_classes": [], "imperative_text_removed": True, "retrieval_treatment": "untrusted_advisory"},
        "trust": {"submitter_key_id": "", "tenant_pseudonym": "", "agent_reputation_at_submit": 0, "independent_tenant_count": 1, "promotion_score": 0},
        "lifecycle": {"status": "local_safe", "created_at_day": "2026-05-03", "expires_at_day": "2026-08-03", "revoked_at": None, "revocation_reason": None},
    }
    atom["atom_id"] = compute_atom_id(atom)
    return atom


def iter_cases(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def expected_to_decisions(expected: str):
    if expected == "reject_pii":
        return {AtomDecision.REJECT_PII}
    if expected == "reject_secret":
        return {AtomDecision.REJECT_SECRET}
    if expected == "reject_prompt_injection":
        return {AtomDecision.REJECT_PROMPT_INJECTION}
    if expected == "quarantine":
        return {AtomDecision.QUARANTINE, AtomDecision.LOCAL_SAFE}
    if expected == "safe":
        return {AtomDecision.LOCAL_SAFE}
    raise ValueError(expected)


def main() -> int:
    total = 0
    failed = []
    for fixture in ["privacy_cases.jsonl", "prompt_injection_cases.jsonl", "safe_learning_atom_cases.jsonl"]:
        for case in iter_cases(FIXTURES / fixture):
            total += 1
            decision = classify_atom_policy(atom_with_text(case["input"])).decision
            allowed = expected_to_decisions(case["expected"])
            if decision not in allowed:
                failed.append({"id": case["id"], "expected": sorted(d.value for d in allowed), "actual": decision.value})
    if failed:
        print(json.dumps({"success": False, "total": total, "failed": failed}, indent=2))
        return 1
    print(json.dumps({"success": True, "total": total, "failed": []}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
