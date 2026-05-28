"""Atom store lifecycle tests."""

from borg.core.atom_store import AtomStore
from borg.core.crypto import generate_signing_key
from borg.core.learning_atoms import sign_learning_atom, compute_atom_id
from borg.core.atom_tenant import tenant_pseudonym


def _atom():
    atom = {
        "schema_version": "1.0",
        "scope": "local",
        "task": {"type": "debug", "technology": ["python"], "error_class": "type-error", "error_pattern": "optional config none", "difficulty": "unknown"},
        "learning": {"root_cause_class": "missing_validation", "worked": "Validate optional value before split", "avoid": ["Blind reinstall"], "why": "Optional value was None"},
        "evidence": {"type": "test_passed", "strength": "medium", "support_count": 1},
        "privacy": {"risk_score": 0, "scanner_version": "privacy-v1", "finding_classes": [], "redaction_count": 0, "raw_trace_retained": False},
        "safety": {"prompt_injection_score": 0, "injection_classes": [], "imperative_text_removed": True, "retrieval_treatment": "untrusted_advisory"},
        "trust": {"submitter_key_id": "", "tenant_pseudonym": "", "agent_reputation_at_submit": 0, "independent_tenant_count": 1, "promotion_score": 0},
        "lifecycle": {"status": "local_safe", "created_at_day": "2026-05-03", "expires_at_day": "2026-08-03", "revoked_at": None, "revocation_reason": None},
    }
    atom["atom_id"] = compute_atom_id(atom)
    return atom


def test_add_safe_atom_persists(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    envelope = sign_learning_atom(_atom(), generate_signing_key())

    atom_id = store.add_atom(envelope)

    assert store.get_atom(atom_id)["atom_id"] == atom_id


def test_revoke_suppresses_get_and_search(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    envelope = sign_learning_atom(_atom(), generate_signing_key())
    atom_id = store.add_atom(envelope)

    assert store.search_atoms("optional")
    store.revoke(atom_id, "privacy request")

    assert store.get_atom(atom_id) is None
    assert store.search_atoms("optional") == []


def test_tombstone_blocks_reimport(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    envelope = sign_learning_atom(_atom(), generate_signing_key())
    atom_id = store.add_atom(envelope)
    store.revoke(atom_id, "bad atom")

    try:
        store.add_atom(envelope)
        raised = False
    except ValueError:
        raised = True

    assert raised is True


def test_store_rejects_tampered_signed_envelope(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    envelope = sign_learning_atom(_atom(), generate_signing_key())
    envelope["payload"]["learning"]["worked"] = "tampered after signing"

    try:
        store.add_atom(envelope)
        raised = False
    except ValueError as exc:
        raised = "signature" in str(exc).lower() or "atom_id" in str(exc).lower()

    assert raised is True


def test_store_rejects_unsigned_shared_atom(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    atom = _atom()
    atom["scope"] = "org"
    atom["trust"]["tenant_pseudonym"] = tenant_pseudonym("tenant-a", b"test-secret")
    atom["atom_id"] = compute_atom_id(atom)

    try:
        store.add_atom(atom)
        raised = False
    except ValueError as exc:
        raised = "valid signed atom envelope" in str(exc)

    assert raised is True


def test_store_rejects_global_candidate_without_verified_tenant_quorum(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    atom = _atom()
    atom["scope"] = "global_candidate"
    atom["trust"]["tenant_pseudonym"] = tenant_pseudonym("tenant-a", b"test-secret")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    try:
        store.add_atom(envelope)
        raised = False
    except ValueError as exc:
        raised = "policy" in str(exc).lower()

    assert raised is True


def test_store_accepts_global_candidate_with_verified_tenant_quorum(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    atom = _atom()
    atom["scope"] = "global_candidate"
    atom["trust"]["tenant_pseudonym"] = tenant_pseudonym("tenant-a", b"test-secret")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    atom_id = store.add_atom(envelope, verified_tenant_count=3)
    stored = store.get_atom(atom_id)

    assert stored is not None
    assert stored["scope"] == "global_candidate"
    assert stored["trust"]["independent_tenant_count"] == 99
    assert stored["trust"]["verified_tenant_count"] == 3


def test_store_get_does_not_label_org_payload_tenant_count_as_verified(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    atom = _atom()
    atom["scope"] = "org"
    atom["trust"]["tenant_pseudonym"] = tenant_pseudonym("tenant-a", b"test-secret")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    atom_id = store.add_atom(envelope)
    stored = store.get_atom(atom_id)

    assert stored is not None
    assert stored["trust"]["independent_tenant_count"] == 99
    assert stored["trust"]["verified_tenant_count"] == 0


def test_store_search_exposes_verified_tenant_count_not_payload_hint(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    atom = _atom()
    atom["scope"] = "global_candidate"
    atom["trust"]["tenant_pseudonym"] = tenant_pseudonym("tenant-a", b"test-secret")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    store.add_atom(envelope, verified_tenant_count=3)
    results = store.search_atoms("optional")

    assert results
    assert results[0]["trust"]["independent_tenant_count"] == 99
    assert results[0]["trust"]["verified_tenant_count"] == 3


def test_store_search_does_not_label_org_payload_tenant_count_as_verified(tmp_path):
    store = AtomStore(str(tmp_path / "atoms.db"))
    atom = _atom()
    atom["scope"] = "org"
    atom["trust"]["tenant_pseudonym"] = tenant_pseudonym("tenant-a", b"test-secret")
    atom["trust"]["independent_tenant_count"] = 99
    atom["atom_id"] = compute_atom_id(atom)
    envelope = sign_learning_atom(atom, generate_signing_key())

    store.add_atom(envelope)
    results = store.search_atoms("optional")

    assert results
    assert results[0]["trust"]["independent_tenant_count"] == 99
    assert results[0]["trust"]["verified_tenant_count"] == 0
