"""Tenant pseudonym and org/global atom policy tests."""

from borg.core.atom_policy import AtomDecision, classify_atom_policy
from borg.core.atom_tenant import is_valid_tenant_pseudonym, tenant_pseudonym
from borg.core.learning_atoms import compute_atom_id, distill_trace_to_atom, validate_learning_atom


def test_tenant_pseudonym_is_hmac_not_raw_identifier():
    raw = "acme-corp@example.com"
    pseudo = tenant_pseudonym(raw, b"unit-test-secret")

    assert pseudo.startswith("hmac-sha256:")
    assert raw not in pseudo
    assert is_valid_tenant_pseudonym(pseudo)


def test_learning_atom_rejects_raw_tenant_identifier():
    atom = distill_trace_to_atom(
        {
            "task_description": "TypeError optional config",
            "approach_summary": "Add explicit None validation",
            "root_cause": "optional config was None",
            "errors_encountered": ["TypeError"],
            "technology": "python",
            "outcome": "success",
        },
        scope="org",
        tenant_identifier="acme-corp@example.com",
        tenant_secret=b"unit-test-secret",
    )
    atom["trust"]["tenant_pseudonym"] = "acme-corp@example.com"
    atom["atom_id"] = compute_atom_id(atom)

    result = validate_learning_atom(atom)

    assert not result.valid
    assert any("tenant_pseudonym" in e for e in result.errors)


def test_org_policy_requires_hmac_tenant_pseudonym_even_when_signed():
    atom = distill_trace_to_atom(
        {
            "task_description": "TypeError optional config",
            "approach_summary": "Add explicit None validation",
            "root_cause": "optional config was None",
            "errors_encountered": ["TypeError"],
            "technology": "python",
            "outcome": "success",
        },
        scope="org",
    )
    atom["trust"]["submitter_key_id"] = "ed25519:test"
    atom["trust"]["tenant_pseudonym"] = "tenant-acme"
    atom["atom_id"] = compute_atom_id(atom)

    result = classify_atom_policy(atom, has_valid_signature=True)

    assert result.decision == AtomDecision.QUARANTINE
    assert "tenant HMAC pseudonym" in " ".join(result.reasons)


def test_org_distillation_sets_pseudonym_and_passes_policy_when_signed():
    atom = distill_trace_to_atom(
        {
            "task_description": "TypeError optional config",
            "approach_summary": "Add explicit None validation",
            "root_cause": "optional config was None",
            "errors_encountered": ["TypeError"],
            "technology": "python",
            "outcome": "success",
        },
        scope="org",
        tenant_identifier="acme-corp@example.com",
        tenant_secret=b"unit-test-secret",
    )
    atom["trust"]["submitter_key_id"] = "ed25519:test"
    atom["atom_id"] = compute_atom_id(atom)

    assert is_valid_tenant_pseudonym(atom["trust"]["tenant_pseudonym"])
    assert validate_learning_atom(atom).valid
    assert classify_atom_policy(atom, has_valid_signature=True).decision == AtomDecision.ORG_SAFE
