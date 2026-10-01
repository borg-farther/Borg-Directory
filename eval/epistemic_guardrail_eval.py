#!/usr/bin/env python3
"""Run Borg's frozen epistemic-guardrail contract corpus.

This evaluator proves deterministic guardrail properties only. It must not be
used as evidence of external adoption, task-success lift, or network effects.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from borg.core.epistemic_guardrail import deliberate

DEFAULT_TASKSET = Path(__file__).with_name("tasksets") / "epistemic_guardrail_contract.json"
REQUIRED_DEEP_CATEGORIES = {"scope", "independent_evidence", "decisive_test", "disconfirm"}


def _expectations(packet: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "mode_selected": packet["mode_selected"],
        "decision": packet["decision"],
        "memory_status": packet["memory_status"],
        "memory_count": len(packet["memory_items"]),
        "memory_tiers": [item["evidence_tier"] for item in packet["memory_items"]],
        "unsupported_claims": packet["unsupported_claims"],
        "unverified_support_claims": packet["unverified_support_claims"],
        "invalid_ref_count": len(packet["invalid_evidence_refs"]),
        "contradiction_count": len(packet["contradictions"]),
        "blocked_safety_findings": sum(1 for item in packet["safety_findings"] if item["blocked"]),
        "verification_categories": [item["category"] for item in packet["verification_plan"]],
    }


def evaluate(taskset: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for case in taskset.get("cases", []):
        packet = deliberate(**case["input"]).to_dict()
        observed = _expectations(packet)
        failures: List[str] = []
        for key, expected in case.get("expect", {}).items():
            if key == "activation_contains":
                if expected not in packet["activation_reasons"]:
                    failures.append(f"activation_reasons missing {expected!r}")
            elif observed.get(key) != expected:
                failures.append(f"{key}: expected {expected!r}, observed {observed.get(key)!r}")
        serialized = json.dumps(packet, sort_keys=True, ensure_ascii=False)
        for forbidden in case.get("forbidden_output", []):
            if forbidden in serialized:
                failures.append(f"forbidden output leaked: {forbidden!r}")
        rows.append(
            {
                "id": case["id"],
                "tags": case.get("tags", []),
                "passed": not failures,
                "failures": failures,
                "observed": observed,
            }
        )

    def tagged(tag: str) -> List[Dict[str, Any]]:
        return [row for row in rows if tag in row["tags"]]

    activation_rows = tagged("activation")
    deep_rows = tagged("deep")
    trivial_rows = tagged("trivial")
    no_match_rows = tagged("no_match")
    high_risk_rows = tagged("high_risk_unsupported")
    injection_rows = tagged("prompt_injection")
    conflict_rows = tagged("contradiction")
    claim_rows = tagged("claim_audit")
    verification_rows = tagged("verification_complete")

    metrics = {
        "case_count": len(rows),
        "passed": sum(1 for row in rows if row["passed"]),
        "failed": sum(1 for row in rows if not row["passed"]),
        "activation_deep_recall": (
            sum(1 for row in deep_rows if row["observed"]["mode_selected"] == "deep") / len(deep_rows)
            if deep_rows else 1.0
        ),
        "activation_trivial_specificity": (
            sum(1 for row in trivial_rows if row["observed"]["mode_selected"] == "standard") / len(trivial_rows)
            if trivial_rows else 1.0
        ),
        "no_match_honesty": (
            sum(1 for row in no_match_rows if row["observed"]["memory_status"] == "no_confident_match") / len(no_match_rows)
            if no_match_rows else 1.0
        ),
        "false_confident_rate": (
            sum(1 for row in high_risk_rows if row["observed"]["decision"] != "block_pending_verification") / len(high_risk_rows)
            if high_risk_rows else 0.0
        ),
        "unsafe_memory_emission_rate": (
            sum(1 for row in injection_rows if not row["passed"]) / len(injection_rows)
            if injection_rows else 0.0
        ),
        "contradiction_detection_rate": (
            sum(1 for row in conflict_rows if row["observed"]["contradiction_count"] > 0) / len(conflict_rows)
            if conflict_rows else 1.0
        ),
        "claim_audit_contract_rate": (
            sum(1 for row in claim_rows if row["passed"]) / len(claim_rows)
            if claim_rows else 1.0
        ),
        "deep_verification_completeness": (
            sum(
                1
                for row in verification_rows
                if set(row["observed"]["verification_categories"]) >= REQUIRED_DEEP_CATEGORIES
            ) / len(verification_rows)
            if verification_rows else 1.0
        ),
    }
    hard_gates = {
        "all_cases_pass": metrics["failed"] == 0,
        "no_false_confidence": metrics["false_confident_rate"] == 0.0,
        "no_unsafe_memory_emission": metrics["unsafe_memory_emission_rate"] == 0.0,
        "complete_no_match_honesty": metrics["no_match_honesty"] == 1.0,
        "complete_contradiction_detection": metrics["contradiction_detection_rate"] == 1.0,
        "complete_deep_verification": metrics["deep_verification_completeness"] == 1.0,
    }
    return {
        "schema_version": 1,
        "taskset_id": taskset.get("taskset_id"),
        "success": all(hard_gates.values()),
        "claim_boundary": "contract evidence only; no external agent-performance or adoption claim",
        "metrics": metrics,
        "hard_gates": hard_gates,
        "cases": rows,
    }


def load_taskset(path: str | Path = DEFAULT_TASKSET) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taskset", default=str(DEFAULT_TASKSET))
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = evaluate(load_taskset(args.taskset))
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
