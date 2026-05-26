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
from borg.core.crypto import generate_signing_key
from borg.core.learning_atoms import compute_atom_id, sign_learning_atom


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


def test_staging_registry_accepts_global_candidate_with_verified_quorum(tmp_path):
    atom = _atom(scope="global_candidate")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())
    registry = tmp_path / "registry"
    store_b = AtomStore(str(tmp_path / "client-b-atoms.db"))

    receipt = ingest_atom_envelope(envelope, registry, verified_tenant_count=3)
    sync = sync_registry_to_store(registry, store_b)

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
