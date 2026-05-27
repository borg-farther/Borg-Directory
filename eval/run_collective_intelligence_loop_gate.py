#!/usr/bin/env python3
"""Executable gate for Borg's max-value collective intelligence loop.

This proves the internal mechanism, not external-user lift:

intervention -> verified outcome receipts -> dedupe/generalize -> registry-computed
quorum -> signed atom promotion -> unified scored retrieval -> first-10 truth boundary
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from borg.core.atom_registry import ingest_atom_envelope, rebuild_manifest  # noqa: E402
from borg.core.atom_store import AtomStore  # noqa: E402
from borg.core.atom_tenant import tenant_pseudonym  # noqa: E402
from borg.core.collective_learning import (  # noqa: E402
    CollectiveLearningStore,
    compute_verified_tenant_count_from_outcomes,
    normalize_problem_signature,
    unified_collective_retrieve,
)
from borg.core.crypto import generate_signing_key  # noqa: E402
from borg.core.learning_atoms import compute_atom_id, sign_learning_atom  # noqa: E402


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _git_context() -> Dict[str, Any]:
    def run(*args: str) -> str:
        proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=10, check=False)
        return proc.stdout.strip() if proc.returncode == 0 else ""

    status = run("status", "--short")
    return {"commit": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current"), "dirty": bool(status), "dirty_files": status.splitlines()}


def _payload() -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": "1.0",
        "scope": "global_candidate",
        "task": {
            "type": "debug",
            "technology": ["python"],
            "error_class": "ModuleNotFoundError",
            "error_pattern": "No module named flask",
            "difficulty": "medium",
        },
        "learning": {
            "root_cause_class": "missing_dependency",
            "worked": "Install Flask in the active virtual environment, then verify import.",
            "avoid": ["Do not reinstall Python before checking the active environment."],
            "why": "The error means the active interpreter cannot import the Flask package.",
        },
        "evidence": {"type": "outcome_receipt", "strength": "verified", "support_count": 3},
        "privacy": {"risk_score": 0, "scanner_version": "gate", "finding_classes": [], "redaction_count": 0, "raw_trace_retained": False},
        "safety": {"prompt_injection_score": 0, "injection_classes": [], "imperative_text_removed": True, "retrieval_treatment": "untrusted_advisory"},
        # Deliberately inflated. The registry must ignore this and compute quorum
        # from signed/exported outcome receipts instead.
        "trust": {"submitter_key_id": "", "tenant_pseudonym": tenant_pseudonym("tenant-a", b"gate-secret"), "agent_reputation_at_submit": 0, "independent_tenant_count": 99, "promotion_score": 0},
        "lifecycle": {"status": "global_candidate", "created_at_day": "2026-05-26", "expires_at_day": "2026-12-31", "revoked_at": None, "revocation_reason": None},
    }
    payload["atom_id"] = compute_atom_id(payload)
    return payload


def run_gate() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="borg-collective-loop-") as td:
        root = Path(td)
        registry = root / "registry"
        outcomes = CollectiveLearningStore(root / "outcomes.db")
        payload = _payload()
        envelope = sign_learning_atom(payload, generate_signing_key())
        atom_id = envelope["payload"]["atom_id"]
        cluster_id = normalize_problem_signature("debug", ["python"], "ModuleNotFoundError", "No module named flask")

        intervention_ids = []
        for tenant in ["tenant-a", "tenant-b", "tenant-c"]:
            intervention = outcomes.record_intervention(
                source_tool="borg_rescue",
                task_text="ModuleNotFoundError: No module named flask",
                context="python",
                guidance={"action": ["Install Flask in the active virtual environment"], "verify": ["python -c 'import flask'"]},
                agent_id=f"agent-{tenant}",
                tenant_pseudonym=tenant,
                source_refs=[atom_id],
            )
            intervention_ids.append(intervention["intervention_id"])
            outcomes.record_outcome(
                intervention_id=intervention["intervention_id"],
                outcome="success",
                helpful=True,
                verified=True,
                verification_command="python -c 'import flask'",
                tenant_pseudonym=tenant,
                agent_id=f"agent-{tenant}",
                atom_id=atom_id,
                cluster_id=cluster_id,
                time_saved_minutes=3.0,
                tokens_saved=600,
                dead_ends_avoided=1,
            )

        # Negative evidence is retained and affects scoring, but does not add to
        # the helpful quorum.
        negative = outcomes.record_intervention(
            source_tool="borg_rescue",
            task_text="ModuleNotFoundError: No module named flask",
            context="python",
            guidance="Reinstall Python",
            agent_id="agent-negative",
            tenant_pseudonym="tenant-z",
            source_refs=[atom_id],
        )
        outcomes.record_outcome(
            intervention_id=negative["intervention_id"],
            outcome="failure",
            helpful=False,
            verified=True,
            verification_command="python -c 'import flask'",
            tenant_pseudonym="tenant-z",
            agent_id="agent-negative",
            atom_id=atom_id,
            cluster_id=cluster_id,
        )

        exported = outcomes.export_verified_outcomes(registry)
        trusted_signers = exported["trusted_receipt_signer_key_ids"]
        computed_quorum = compute_verified_tenant_count_from_outcomes(
            registry,
            atom_id=atom_id,
            cluster_id=cluster_id,
            trusted_receipt_signer_key_ids=trusted_signers,
        )
        receipt = ingest_atom_envelope(envelope, registry, trusted_receipt_signer_key_ids=trusted_signers)
        rebuild_manifest(registry)
        cluster_stats = outcomes.cluster_stats(cluster_id)
        value_summary = outcomes.recent_value_summary()
        atom_candidate = outcomes.build_learning_atom_candidate(cluster_id)
        promoted = outcomes.promote_cluster_to_registry(cluster_id, registry, generate_signing_key())
        promoted_atoms = AtomStore(str(root / "promoted-atoms.db"))
        promoted_atoms.add_atom(promoted["envelope"], verified_tenant_count=promoted["registry_receipt"]["verified_tenant_count"])
        ranked = unified_collective_retrieve("ModuleNotFoundError: No module named flask", atom_store=promoted_atoms, outcome_store=outcomes, limit=3)
        contribution_summary = outcomes.contribution_summary()
        first10 = json.loads((ROOT / "eval" / "first_10_user_scoreboard.json").read_text(encoding="utf-8"))
        first10_counts = first10.get("current_counts", {})
        first10_value = first10.get("current_value_counts", {})

        checks = {
            "interventions_recorded": len(intervention_ids) == 3,
            "outcome_receipts_exported": exported["exported"] == 4,
            "dedupe_cluster_stable": cluster_stats["interventions"] == 4 and cluster_stats["distinct_tenants"] == 4,
            "registry_computed_quorum": computed_quorum == 3 and receipt.verified_tenant_count == 3,
            "payload_quorum_ignored": receipt.verified_tenant_count != payload["trust"]["independent_tenant_count"],
            "unified_retrieval_ranked": bool(ranked) and ranked[0]["atom_id"] == promoted["registry_receipt"]["atom_id"] and ranked[0]["score"] > 0,
            "retrieval_explains_value": bool(ranked) and {"verified_quorum", "helpful_outcomes"}.issubset(set(ranked[0]["score_reasons"])),
            "negative_evidence_retained": bool(ranked) and "negative_evidence_present" in ranked[0]["score_reasons"],
            "contribution_ledger_complete": contribution_summary["by_type"].get("intervention") == 4 and contribution_summary["by_type"].get("outcome_receipt") == 4,
            "atom_candidate_distilled_from_receipts": atom_candidate["promotable"] is True and atom_candidate["helpful_verified_tenants"] == 3,
            "cluster_promotion_signed_and_staged": promoted["registry_receipt"]["decision"] == "global_candidate" and promoted["registry_receipt"]["reason"] == "accepted" and promoted["registry_receipt"]["verified_tenant_count"] == 3,
            "first10_not_faked": int(first10_counts.get("real_users", 0)) == 0 and int(first10_value.get("rows_with_measured_value", 0)) == 0,
        }
        success = all(checks.values())
        return {
            "schema_version": 1,
            "generated_at_utc": _utc_now(),
            "success": success,
            "verdict": "GO" if success else "NO-GO",
            "scope": "max_value_collective_intelligence_loop_primitives",
            "public_external_lift": "NO-GO_REAL_FIRST_10_ROWS_REQUIRED",
            "git": _git_context(),
            "checks": checks,
            "cluster_stats": cluster_stats,
            "value_summary": value_summary,
            "contribution_summary": contribution_summary,
            "atom_candidate": {
                "atom_id": atom_candidate["atom_id"],
                "promotable": atom_candidate["promotable"],
                "blockers": atom_candidate["blockers"],
                "helpful_verified_tenants": atom_candidate["helpful_verified_tenants"],
            },
            "registry_promotion": promoted["registry_receipt"],
            "registry_quorum": {"computed_from_outcome_receipts": computed_quorum, "payload_hint": payload["trust"]["independent_tenant_count"], "receipt_verified_tenant_count": receipt.verified_tenant_count},
            "retrieval_top": ranked[0] if ranked else None,
            "first10_counts": first10_counts,
            "first10_value_counts": first10_value,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Borg collective intelligence loop gate")
    parser.add_argument("--output", default=str(ROOT / "eval" / "collective_intelligence_loop_gate.json"))
    args = parser.parse_args()
    result = run_gate()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"success": result["success"], "verdict": result["verdict"], "scope": result["scope"], "public_external_lift": result["public_external_lift"]}, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
