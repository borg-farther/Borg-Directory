"""CLI tests for borg atom subcommands."""

import json
import sys
from unittest.mock import MagicMock, patch

import yaml

from borg.cli import main
from borg.core.learning_atoms import compute_atom_id


def capture_main(args: list[str]) -> tuple[int, str, str]:
    sys.argv = ["borg"] + args
    out = ""
    err = ""

    def stdout_write(s):
        nonlocal out
        out += str(s)

    def stderr_write(s):
        nonlocal err
        err += str(s)

    try:
        with patch.object(sys, "stdout", MagicMock(wraps=sys.stdout, write=stdout_write)), \
             patch.object(sys, "stderr", MagicMock(wraps=sys.stderr, write=stderr_write)):
            code = main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    return code, out, err


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


def test_atom_validate_valid_file(tmp_path):
    path = tmp_path / "atom.yaml"
    path.write_text(yaml.safe_dump(_atom()), encoding="utf-8")

    code, out, err = capture_main(["atom", "validate", str(path)])

    assert code == 0
    result = json.loads(out)
    assert result["success"] is True
    assert result["valid"] is True


def test_atom_help_lists_subcommands():
    code, out, err = capture_main(["atom", "--help"])

    assert code == 0
    assert "signed, sanitized, revocable learning atoms" in out
    assert "distill" in out
    assert "validate" in out
    assert "publish" in out
    assert "fail-closed policy gates" in out
    assert "no raw traces" in out
    assert "search" in out
    assert "revoke" in out


def test_atom_publish_help_frames_fail_closed_no_raw_traces():
    code, out, err = capture_main(["atom", "publish", "--help"])

    assert code == 0
    assert "signed, sanitized learning atom" in out
    assert "fail-closed policy gates" in out
    assert "Raw traces are never published" in out
