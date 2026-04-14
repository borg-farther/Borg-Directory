"""
Integration test for the full publish pipeline (T1.8).

This test verifies the complete action_publish flow:
  a. Creates a valid pack YAML in the guild directory
  b. Calls action_publish(path=...) with gh CLI mocked
  c. Verifies: rate limit checked, proof gates validated, safety scanned,
     privacy scanned, PR would be created
  d. Verifies outbox fallback works when gh CLI fails

Run: cd /root/hermes-workspace/guild-v2 && python -m pytest guild/tests/test_publish_flow_integration.py -v
"""

import json
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core import publish as publish_module


def minimal_pack(overrides=None):
    """Minimal valid workflow_pack artifact."""
    base = {
        "type": "workflow_pack",
        "version": "1.0",
        "id": "test/pack",
        "problem_class": "classification",
        "mental_model": "fast-thinker",
        "phases": [
            {
                "description": "Read the input",
                "checkpoint": "read_done",
                "prompts": ["Read {input}"],
                "anti_patterns": [],
            },
        ],
        "provenance": {
            "author": "agent://test",
            "created": "2026-01-01T00:00:00+00:00",
            "confidence": "inferred",
            "evidence": "tested in CI",
            "failure_cases": ["wrong label"],
        },
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.fixture
def tmp_guild(monkeypatch, tmp_path):
    """Mount a temporary BORG_DIR for the duration of a test."""
    agent_dir = tmp_path / ".hermes" / "guild"
    outbox_dir = agent_dir / "outbox"
    feedback_dir = agent_dir / "feedback"
    agent_dir.mkdir(parents=True, exist_ok=True)
    outbox_dir.mkdir(parents=True, exist_ok=True)
    feedback_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(publish_module, "BORG_DIR", agent_dir)
    monkeypatch.setattr(publish_module, "OUTBOX_DIR", outbox_dir)
    monkeypatch.setattr(publish_module, "FEEDBACK_DIR", feedback_dir)
    monkeypatch.setattr(publish_module, "PUBLISH_LOG", agent_dir / "publish_log.jsonl")

    return {
        "agent_dir": agent_dir,
        "outbox_dir": outbox_dir,
        "feedback_dir": feedback_dir,
    }


class TestFullPublishPipeline:
    """Full publish pipeline with all gates verified.

    Uses patch.object() as context manager instead of @patch decorators
    to avoid parameter-order bugs that come from decorator stacking.
    """

    def test_full_pipeline_with_all_gates_checked(
        self, tmp_guild, tmp_path, monkeypatch
    ):
        """
        Verify the full publish pipeline:
        a. Creates a valid pack YAML in the guild directory
        b. Calls action_publish(path=...) with gh CLI mocked
        c. Verifies: rate limit checked, proof gates validated, safety scanned,
           privacy scanned, PR would be created
        """
        # --- Setup mocks using context managers ---
        with patch.object(publish_module, "check_rate_limit", return_value=(True, 0)) as mock_rate_limit, \
             patch.object(publish_module, "validate_proof_gates", return_value=[]) as mock_proof_gates, \
             patch.object(publish_module, "scan_pack_safety", return_value=[]) as mock_safety, \
             patch.object(publish_module, "privacy_scan_artifact",
                          return_value=(minimal_pack({"id": "full-pipeline-test"}), [])) as mock_privacy, \
             patch.object(publish_module, "create_github_pr",
                          return_value={"success": True, "pr_url": "https://github.com/test/pull/42"}) as mock_pr:

            # --- Step a: Create a valid pack YAML in the guild directory ---
            pack_dir = tmp_guild["agent_dir"] / "full-pipeline-test"
            pack_dir.mkdir()
            pack_path = pack_dir / "pack.yaml"
            pack_path.write_text(yaml.dump(minimal_pack({"id": "full-pipeline-test"})))

            # --- Step b & c: Call action_publish and verify all gates ---
            result = json.loads(publish_module.action_publish(path=str(pack_path)))

            # Verify action_publish succeeded
            assert result["success"] is True, f"action_publish failed: {result.get('error')}"
            assert result["published"] is True
            assert result["pr_url"] == "https://github.com/test/pull/42"

            # Verify rate limit was checked (called before proceeding)
            mock_rate_limit.assert_called_once()

            # Verify proof gates were validated
            mock_proof_gates.assert_called_once()
            call_args = mock_proof_gates.call_args[0][0]
            assert call_args["id"] == "full-pipeline-test"

            # Verify safety scan was run
            mock_safety.assert_called_once()

            # Verify privacy scan was run
            mock_privacy.assert_called_once()

            # Verify PR was created via gh CLI (mocked)
            mock_pr.assert_called_once()
            pr_call_kwargs = mock_pr.call_args.kwargs
            assert pr_call_kwargs["artifact_type"] == "workflow_pack"
            assert "full-pipeline-test.workflow.yaml" in pr_call_kwargs["filename"]

            # Verify outbox file was saved
            assert "outbox_path" in result
            assert Path(result["outbox_path"]).exists()

            # Verify publish was logged
            log_lines = publish_module.PUBLISH_LOG.read_text().strip().split("\n")
            assert len(log_lines) == 1
            log_entry = json.loads(log_lines[0])
            assert log_entry["status"] == "published"
            assert log_entry["artifact_id"] == "full-pipeline-test"
            assert log_entry["pr_url"] == "https://github.com/test/pull/42"

    def test_outbox_fallback_when_gh_cli_fails(
        self, tmp_guild, tmp_path, monkeypatch
    ):
        """
        Verify outbox fallback works when gh CLI fails.

        When create_github_pr returns an error (simulating gh CLI failure),
        action_publish should:
        - Return success=True (not a hard failure)
        - Set published=False
        - Save the artifact to the outbox directory
        - Log with status='outbox'
        """
        # --- Setup: gh CLI fails using context managers ---
        with patch.object(publish_module, "check_rate_limit", return_value=(True, 0)) as mock_rate_limit, \
             patch.object(publish_module, "validate_proof_gates", return_value=[]) as mock_proof_gates, \
             patch.object(publish_module, "scan_pack_safety", return_value=[]) as mock_safety, \
             patch.object(publish_module, "privacy_scan_artifact",
                          return_value=(minimal_pack({"id": "offline-pack"}), [])) as mock_privacy, \
             patch.object(publish_module, "create_github_pr",
                          return_value={"success": False, "error": "gh CLI not found or network error"}) as mock_pr:

            # --- Create pack ---
            pack_dir = tmp_guild["agent_dir"] / "offline-pack"
            pack_dir.mkdir()
            pack_path = pack_dir / "pack.yaml"
            pack_path.write_text(yaml.dump(minimal_pack({"id": "offline-pack"})))

            # --- Call action_publish ---
            result = json.loads(publish_module.action_publish(path=str(pack_path)))

            # --- Verify: returns success with published=False ---
            assert result["success"] is True, "Should return success even when PR fails"
            assert result["published"] is False, "published should be False when PR fails"
            assert "outbox_path" in result, "Must include outbox_path for manual retry"

            # --- Verify: outbox file was saved and exists ---
            outbox_path = Path(result["outbox_path"])
            assert outbox_path.exists(), f"Outbox file should exist at {outbox_path}"
            assert outbox_path.parent == tmp_guild["outbox_dir"]

            # --- Verify: gh PR was still attempted ---
            mock_pr.assert_called_once()

            # --- Verify: publish was logged with outbox status ---
            log_lines = publish_module.PUBLISH_LOG.read_text().strip().split("\n")
            assert len(log_lines) == 1
            log_entry = json.loads(log_lines[0])
            assert log_entry["status"] == "outbox", "Status should be 'outbox' when PR fails"
            assert log_entry["artifact_id"] == "offline-pack"
            assert log_entry["outbox_path"] == str(outbox_path)

            # --- Verify: error hint is included for manual retry ---
            assert "hint" in result
            assert "retry" in result["hint"].lower() or "outbox" in result["hint"].lower()


class TestPublishPipelineGateRejections:
    """Verify each gate properly rejects invalid packs."""

    def test_rate_limit_gate_rejects(self, tmp_guild, tmp_path, monkeypatch):
        """Rate limit gate should reject when daily limit reached."""
        monkeypatch.setattr(publish_module, "MAX_PUBLISHES_PER_DAY", 0)

        pack_dir = tmp_guild["agent_dir"] / "rate-limited"
        pack_dir.mkdir()
        (pack_dir / "pack.yaml").write_text(yaml.dump(minimal_pack({"id": "rate-limited"})))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is False
        assert "Daily publish limit" in result["error"]

    @patch("borg.core.publish.validate_proof_gates")
    def test_proof_gates_gate_rejects(self, mock_validate, tmp_guild, tmp_path):
        """Proof gates should reject packs with missing provenance."""
        mock_validate.return_value = ["Missing provenance.evidence"]

        pack_dir = tmp_guild["agent_dir"] / "bad-gates"
        pack_dir.mkdir()
        (pack_dir / "pack.yaml").write_text(yaml.dump(minimal_pack({"id": "bad-gates"})))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is False
        assert "Proof gate validation failed" in result["error"]
        assert "Missing provenance.evidence" in result["gate_errors"]

    @patch("borg.core.publish.scan_pack_safety")
    def test_safety_gate_rejects(self, mock_safety, tmp_guild, tmp_path):
        """Safety scan should reject packs with threats."""
        mock_safety.return_value = ["Prompt injection detected"]

        pack_dir = tmp_guild["agent_dir"] / "unsafe"
        pack_dir.mkdir()
        (pack_dir / "pack.yaml").write_text(yaml.dump(minimal_pack({"id": "unsafe"})))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is False
        assert "Safety scan failed" in result["error"]
        assert "Prompt injection detected" in result["threats"]

    @patch("borg.core.publish.create_github_pr")
    @patch("borg.core.publish.validate_proof_gates", return_value=[])
    @patch("borg.core.publish.scan_pack_safety", return_value=[])
    def test_privacy_scan_redacts_before_publish(
        self, mock_safety, mock_proof, mock_pr, tmp_guild, tmp_path
    ):
        """Privacy scan should redact sensitive data before PR is created."""
        mock_pr.return_value = {"success": True, "pr_url": "https://github.com/test/pull/99"}

        # Pack with an email that should be redacted
        pack_with_email = minimal_pack({
            "id": "privacy-test",
            "description": "Contact: test@example.com for support",
        })
        pack_dir = tmp_guild["agent_dir"] / "privacy-test"
        pack_dir.mkdir()
        (pack_dir / "pack.yaml").write_text(yaml.dump(pack_with_email))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is True

        # The outbox file should have email redacted
        outbox_content = Path(result["outbox_path"]).read_text()
        assert "test@example.com" not in outbox_content, "Email should be redacted in outbox"
        assert "[REDACTED" in outbox_content, "Outbox should contain redaction marker"
