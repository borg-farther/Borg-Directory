"""Learning atom publish hardening tests."""

import json
import yaml

from borg.core.crypto import generate_signing_key
from borg.core.learning_atoms import compute_atom_id, sign_learning_atom
from borg.core import publish as publish_module


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


def _mount_tmp_guild(monkeypatch, tmp_path):
    borg_dir = tmp_path / "guild"
    outbox = borg_dir / "outbox"
    feedback = borg_dir / "feedback"
    borg_dir.mkdir(parents=True)
    outbox.mkdir()
    feedback.mkdir()
    monkeypatch.setattr(publish_module, "BORG_DIR", borg_dir)
    monkeypatch.setattr(publish_module, "OUTBOX_DIR", outbox)
    monkeypatch.setattr(publish_module, "FEEDBACK_DIR", feedback)
    monkeypatch.setattr(publish_module, "PUBLISH_LOG", borg_dir / "publish_log.jsonl")
    return borg_dir


def test_learning_atom_publish_rejects_unsigned_envelope(monkeypatch, tmp_path):
    borg_dir = _mount_tmp_guild(monkeypatch, tmp_path)
    artifact_path = borg_dir / "unsigned.yaml"
    artifact_path.write_text(yaml.safe_dump({"type": "learning_atom", "payload": _atom()}), encoding="utf-8")

    result = json.loads(publish_module.action_publish(path=str(artifact_path)))

    assert result["success"] is False
    assert "signed atom envelope" in result["error"]


def test_learning_atom_publish_rejects_tampered_signature(monkeypatch, tmp_path):
    borg_dir = _mount_tmp_guild(monkeypatch, tmp_path)
    envelope = sign_learning_atom(_atom(), generate_signing_key())
    envelope["payload"]["learning"]["worked"] = "tampered"
    artifact_path = borg_dir / "tampered.yaml"
    artifact_path.write_text(yaml.safe_dump(envelope), encoding="utf-8")

    result = json.loads(publish_module.action_publish(path=str(artifact_path)))

    assert result["success"] is False
    assert "signature" in result["error"].lower()


def test_learning_atom_publish_signed_safe_atom_saves_outbox(monkeypatch, tmp_path):
    borg_dir = _mount_tmp_guild(monkeypatch, tmp_path)
    envelope = sign_learning_atom(_atom(), generate_signing_key())
    artifact_path = borg_dir / "safe.yaml"
    artifact_path.write_text(yaml.safe_dump(envelope), encoding="utf-8")
    monkeypatch.setattr(publish_module, "create_github_pr", lambda **kwargs: {"success": False, "error": "gh unavailable"})

    result = json.loads(publish_module.action_publish(path=str(artifact_path)))

    assert result["success"] is True
    assert result["published"] is False
    assert result["outbox_path"].endswith(".learning-atom.yaml")
