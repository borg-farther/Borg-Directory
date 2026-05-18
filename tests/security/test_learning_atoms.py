"""Learning atom schema, distillation, canonicalization, and signing tests."""

from borg.core.learning_atoms import (
    compute_atom_id,
    distill_trace_to_atom,
    validate_learning_atom,
    canonical_atom_json,
    sign_learning_atom,
    verify_signed_atom,
)
from borg.core.crypto import generate_signing_key


def _valid_atom():
    return {
        "schema_version": "1.0",
        "scope": "local",
        "task": {
            "type": "debug",
            "technology": ["python", "django"],
            "error_class": "db-migration-error",
            "error_pattern": "migration table exists but state missing",
            "difficulty": "unknown",
        },
        "learning": {
            "root_cause_class": "schema_state_mismatch",
            "worked": "Use migration framework with fake-initial when tables already match models.",
            "avoid": ["Manual schema edits without migration state reconciliation."],
            "why": "Runtime schema and migration history diverged.",
        },
        "evidence": {"type": "test_passed", "strength": "strong", "support_count": 1},
        "privacy": {"risk_score": 0, "scanner_version": "privacy-v1", "finding_classes": [], "redaction_count": 0, "raw_trace_retained": False},
        "safety": {"prompt_injection_score": 0, "injection_classes": [], "imperative_text_removed": True, "retrieval_treatment": "untrusted_advisory"},
        "trust": {"submitter_key_id": "", "tenant_pseudonym": "", "agent_reputation_at_submit": 0, "independent_tenant_count": 1, "promotion_score": 0},
        "lifecycle": {"status": "local_safe", "created_at_day": "2026-05-03", "expires_at_day": "2026-08-03", "revoked_at": None, "revocation_reason": None},
    }


def test_minimal_valid_atom_passes_and_gets_canonical_id():
    atom = _valid_atom()
    atom["atom_id"] = compute_atom_id(atom)

    result = validate_learning_atom(atom)

    assert result.valid is True
    assert atom["atom_id"].startswith("sha256:")


def test_freeform_raw_trace_field_fails():
    atom = _valid_atom()
    atom["tool_calls"] = [{"tool": "read_file", "result": "secret"}]

    result = validate_learning_atom(atom)

    assert result.valid is False
    assert any("unknown field" in e.lower() for e in result.errors)


def test_global_scope_disallows_raw_paths_in_text():
    atom = _valid_atom()
    atom["scope"] = "global"
    atom["learning"]["worked"] = "Edit /home/alice/private/project/settings.py"

    result = validate_learning_atom(atom)

    assert result.valid is False
    assert any("privacy" in e.lower() or "path" in e.lower() for e in result.errors)


def test_canonical_json_key_order_stable():
    atom_a = _valid_atom()
    atom_b = {k: atom_a[k] for k in reversed(list(atom_a.keys()))}

    assert canonical_atom_json(atom_a) == canonical_atom_json(atom_b)


def test_distill_trace_excludes_raw_tool_result_and_file_lists():
    trace = {
        "task_description": "Fix Django migration error for user alice@example.com",
        "outcome": "success",
        "root_cause": "Runtime schema and migration history diverged",
        "approach_summary": "Use migration framework with fake-initial",
        "files_read": '["/home/alice/private/models.py"]',
        "files_modified": '["/home/alice/private/models.py"]',
        "errors_encountered": '["django.db.utils.OperationalError: table already exists"]',
        "dead_ends": '["Manual ALTER TABLE"]',
        "technology": "django",
        "error_patterns": "OperationalError",
        "tool_calls": [{"result": "secret raw output"}],
    }

    atom = distill_trace_to_atom(trace, scope="local")
    as_text = str(atom)

    assert "tool_calls" not in atom
    assert "files_read" not in atom
    assert "files_modified" not in atom
    assert "secret raw output" not in as_text
    assert "alice@example.com" not in as_text
    assert atom["privacy"]["raw_trace_retained"] is False


def test_signed_atom_verifies_and_tampering_fails():
    atom = _valid_atom()
    signing_key = generate_signing_key()

    envelope = sign_learning_atom(atom, signing_key)
    assert verify_signed_atom(envelope).valid is True

    envelope["payload"]["learning"]["worked"] = "tampered"
    assert verify_signed_atom(envelope).valid is False
