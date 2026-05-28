"""Staging registry propagation tests for signed learning atoms."""

import json

import pytest

from borg.core.atom_registry import (
    ingest_atom_envelope,
    rebuild_manifest,
    revoke_registry_atom,
    sync_registry_to_store,
)
from borg.core.atom_store import AtomStore
from borg.core.atom_tenant import tenant_pseudonym
from borg.core.collective_learning import CollectiveLearningStore, normalize_problem_signature
from borg.core.crypto import generate_signing_key
from borg.core.learning_atoms import compute_atom_id, sign_learning_atom


def _strong_evidence(name: str, marker: str = "a") -> dict:
    return {
        "verification_exit_code": 0,
        "verification_output_sha256": "sha256:" + marker * 64,
        "trusted_tenant_id": f"tenant:test:{name}",
    }


def _atom(scope="org", tenant="tenant-a"):
    atom = {
        "schema_version": "1.0",
        "scope": scope,
        "task": {"type": "debug", "technology": ["python"], "error_class": "type-error", "error_pattern": "optional config none", "difficulty": "unknown"},
        "learning": {"root_cause_class": "missing_validation", "worked": "Validate optional value before split", "avoid": ["Blind reinstall"], "why": "Optional value was None"},
        "evidence": {"type": "test_passed", "strength": "medium", "support_count": 1},
        "privacy": {"risk_score": 0, "scanner_version": "privacy-v1", "finding_classes": [], "redaction_count": 0, "raw_trace_retained": False},
        "safety": {"prompt_injection_score": 0, "injection_classes": [], "imperative_text_removed": True, "retrieval_treatment": "untrusted_advisory"},
        "trust": {"submitter_key_id": "", "tenant_pseudonym": tenant_pseudonym(tenant, b"test-secret"), "agent_reputation_at_submit": 0, "independent_tenant_count": 1, "promotion_score": 0},
        "lifecycle": {"status": "org_safe" if scope == "org" else "global_candidate", "created_at_day": "2026-05-26", "expires_at_day": "2026-08-26", "revoked_at": None, "revocation_reason": None},
    }
    atom["atom_id"] = compute_atom_id(atom)
    return atom


def test_staging_registry_a_to_b_sync_then_revocation_suppresses_retrieval(tmp_path):
    registry = tmp_path / "registry"
    store_b = AtomStore(str(tmp_path / "client-b-atoms.db"))
    envelope = sign_learning_atom(_atom(scope="org"), generate_signing_key())

    receipt = ingest_atom_envelope(envelope, registry)
    first_sync = sync_registry_to_store(registry, store_b)

    assert receipt.decision == "org_safe"
    assert first_sync == {"imported": 1, "revoked": 0, "skipped": 0}
    assert store_b.search_atoms("optional")

    revoke_registry_atom(registry, envelope["payload"]["atom_id"], "bad guidance")
    second_sync = sync_registry_to_store(registry, store_b)

    assert second_sync["revoked"] == 1
    assert store_b.get_atom(envelope["payload"]["atom_id"]) is None
    assert store_b.search_atoms("optional") == []

    third_sync = sync_registry_to_store(registry, store_b)
    assert third_sync["imported"] == 0
    assert third_sync["skipped"] >= 1


def test_staging_registry_rejects_tampered_signature(tmp_path):
    envelope = sign_learning_atom(_atom(scope="org"), generate_signing_key())
    envelope["payload"]["learning"]["worked"] = "tampered"

    with pytest.raises(ValueError, match="signature"):
        ingest_atom_envelope(envelope, tmp_path / "registry")

    manifest = json.loads((tmp_path / "registry" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["atoms"] == []
    assert manifest["receipts"]


def test_staging_registry_rejects_local_scope_atoms(tmp_path):
    envelope = sign_learning_atom(_atom(scope="local"), generate_signing_key())

    with pytest.raises(ValueError, match="local-scope"):
        ingest_atom_envelope(envelope, tmp_path / "registry")


def test_staging_registry_quarantines_self_declared_global_quorum(tmp_path):
    atom = _atom(scope="global_candidate")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    with pytest.raises(ValueError, match="registry-computed"):
        ingest_atom_envelope(envelope, tmp_path / "registry")


def test_staging_registry_rejects_untrusted_explicit_verified_quorum(tmp_path):
    atom = _atom(scope="global_candidate")
    atom["trust"]["independent_tenant_count"] = 1
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    with pytest.raises(ValueError, match="registry-computed"):
        ingest_atom_envelope(envelope, tmp_path / "registry", verified_tenant_count=99)


def test_direct_global_ingest_cannot_piggyback_other_atom_receipts_without_cluster_promotion(tmp_path):
    registry = tmp_path / "registry"
    source_atom = _atom(scope="global_candidate")
    source_atom_id = source_atom["atom_id"]
    cluster_id = normalize_problem_signature(
        source_atom["task"]["type"],
        source_atom["task"]["technology"],
        source_atom["task"]["error_class"],
        source_atom["task"]["error_pattern"],
    )
    outcomes = CollectiveLearningStore(str(tmp_path / "outcomes.db"))
    receipt_ids = []

    for tenant in ["tenant-a", "tenant-b", "tenant-c"]:
        tenant_id = tenant_pseudonym(tenant, b"test-secret")
        intervention = outcomes.record_intervention(
            source_tool="borg_rescue",
            task_text="type-error optional config none",
            context="python",
            guidance="Validate optional value before split",
            agent_id=f"agent-{tenant}",
            tenant_pseudonym=tenant_id,
            source_refs=[source_atom_id],
            task_type=source_atom["task"]["type"],
            technology=source_atom["task"]["technology"],
            error_class=source_atom["task"]["error_class"],
            error_pattern=source_atom["task"]["error_pattern"],
        )
        receipt = outcomes.record_outcome(
            intervention_id=intervention["intervention_id"],
            outcome="success",
            helpful=True,
            verified=True,
            verification_command="pytest tests/test_config.py",
            **_strong_evidence(tenant, "a"),
            tenant_pseudonym=tenant_id,
            agent_id=f"agent-{tenant}",
            atom_id=source_atom_id,
            cluster_id=cluster_id,
        )
        receipt_ids.append(receipt["receipt_id"])

    assert outcomes.export_verified_outcomes(registry)["exported"] == 3

    piggyback = _atom(scope="global_candidate", tenant="tenant-x")
    piggyback["learning"]["worked"] = "Delete the optional config file instead of validating it"
    piggyback["evidence"] = {
        "type": "outcome_receipt",
        "strength": "verified_quorum",
        "support_count": 3,
        "cluster_id": cluster_id,
        "supporting_receipt_ids": receipt_ids,
    }
    piggyback["trust"]["independent_tenant_count"] = 99
    piggyback["atom_id"] = compute_atom_id(piggyback)
    envelope = sign_learning_atom(piggyback, generate_signing_key())

    with pytest.raises(ValueError, match="registry-computed"):
        ingest_atom_envelope(envelope, registry)


def test_direct_global_ingest_cannot_piggyback_cluster_only_receipts_without_cluster_promotion(tmp_path):
    registry = tmp_path / "registry"
    source_atom = _atom(scope="global_candidate")
    source_atom_id = source_atom["atom_id"]
    cluster_id = normalize_problem_signature(
        source_atom["task"]["type"],
        source_atom["task"]["technology"],
        source_atom["task"]["error_class"],
        source_atom["task"]["error_pattern"],
    )
    outcomes = CollectiveLearningStore(str(tmp_path / "outcomes.db"))

    for tenant in ["tenant-a", "tenant-b", "tenant-c"]:
        tenant_id = tenant_pseudonym(tenant, b"test-secret")
        intervention = outcomes.record_intervention(
            source_tool="borg_rescue",
            task_text="type-error optional config none",
            context="python",
            guidance="Validate optional value before split",
            agent_id=f"agent-{tenant}",
            tenant_pseudonym=tenant_id,
            source_refs=[source_atom_id],
            task_type=source_atom["task"]["type"],
            technology=source_atom["task"]["technology"],
            error_class=source_atom["task"]["error_class"],
            error_pattern=source_atom["task"]["error_pattern"],
        )
        outcomes.record_outcome(
            intervention_id=intervention["intervention_id"],
            outcome="success",
            helpful=True,
            verified=True,
            verification_command="pytest tests/test_config.py",
            **_strong_evidence(tenant, "a"),
            tenant_pseudonym=tenant_id,
            agent_id=f"agent-{tenant}",
            # Cluster-level receipts are useful to the local promotion path but
            # must not authorize arbitrary direct public atoms in that cluster.
            atom_id=None,
            cluster_id=cluster_id,
        )

    exported = outcomes.export_verified_outcomes(registry)
    assert exported["exported"] == 3

    piggyback = _atom(scope="global_candidate", tenant="tenant-x")
    piggyback["learning"]["worked"] = "Delete the optional config file instead of validating it"
    piggyback["evidence"] = {"type": "outcome_receipt", "strength": "verified_quorum", "cluster_id": cluster_id}
    piggyback["trust"]["independent_tenant_count"] = 99
    piggyback["atom_id"] = compute_atom_id(piggyback)
    envelope = sign_learning_atom(piggyback, generate_signing_key())

    with pytest.raises(ValueError, match="registry-computed"):
        ingest_atom_envelope(
            envelope,
            registry,
            trusted_receipt_signer_key_ids=exported["trusted_receipt_signer_key_ids"],
        )


def test_staging_registry_default_sync_does_not_import_global_candidate_from_unsigned_local_receipts(tmp_path):
    atom = _atom(scope="global_candidate")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())
    registry = tmp_path / "registry"
    store_b = AtomStore(str(tmp_path / "client-b-atoms.db"))

    receipt = ingest_atom_envelope(envelope, registry, verified_tenant_count=3, allow_trusted_verified_tenant_count=True)
    sync = sync_registry_to_store(registry, store_b)

    assert receipt.decision == "global_candidate"
    assert sync["imported"] == 0
    assert sync["skipped"] >= 1
    assert store_b.get_atom(envelope["payload"]["atom_id"]) is None


def test_staging_registry_explicit_operator_sync_can_import_global_candidate(tmp_path):
    atom = _atom(scope="global_candidate")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())
    registry = tmp_path / "registry"
    store_b = AtomStore(str(tmp_path / "client-b-atoms.db"))

    receipt = ingest_atom_envelope(envelope, registry, verified_tenant_count=3, allow_trusted_verified_tenant_count=True)
    sync = sync_registry_to_store(registry, store_b, allow_unsigned_global_candidates=True)

    assert receipt.decision == "global_candidate"
    assert sync["imported"] == 1
    stored = store_b.get_atom(envelope["payload"]["atom_id"])
    assert stored is not None
    assert stored["scope"] == "global_candidate"


def test_staging_registry_manifest_lists_atoms_receipts_and_tombstones(tmp_path):
    registry = tmp_path / "registry"
    envelope = sign_learning_atom(_atom(scope="org"), generate_signing_key())
    ingest_atom_envelope(envelope, registry)
    revoke_registry_atom(registry, envelope["payload"]["atom_id"], "bad guidance")

    manifest = rebuild_manifest(registry)

    assert manifest["schema_version"] == "1.0"
    assert len(manifest["atoms"]) == 1
    assert len(manifest["tombstones"]) == 1
    assert len(manifest["receipts"]) >= 2
