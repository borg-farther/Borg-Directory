"""Debug: standalone test to understand why pytest mocks don't work."""
import json, yaml, tempfile, sys, traceback
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from borg.core import publish as publish_module


def minimal_pack(overrides=None):
    base = {
        "type": "workflow_pack", "version": "1.0", "id": "test/pack",
        "problem_class": "classification", "mental_model": "fast-thinker",
        "phases": [{"description": "Read the input", "checkpoint": "read_done",
                    "prompts": ["Read {input}"], "anti_patterns": []}],
        "provenance": {"author": "agent://test", "created": "2026-01-01T00:00:00+00:00",
                       "confidence": "inferred", "evidence": "tested in CI",
                       "failure_cases": ["wrong label"]},
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.fixture
def tmp_guild_fixture(monkeypatch, tmp_path):
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
    return {"agent_dir": agent_dir, "outbox_dir": outbox_dir, "feedback_dir": feedback_dir}


def test_with_standalone_patch_objects(tmp_guild_fixture, tmp_path):
    """This uses patch() as context manager, not decorator."""
    agent_dir = tmp_guild_fixture["agent_dir"]
    outbox_dir = tmp_guild_fixture["outbox_dir"]

    pack_dir = agent_dir / "test-pack"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text(yaml.dump(minimal_pack({"id": "test-pack"})))

    with patch.object(publish_module, "check_rate_limit", return_value=(True, 0)), \
         patch.object(publish_module, "validate_proof_gates", return_value=[]), \
         patch.object(publish_module, "scan_pack_safety", return_value=[]), \
         patch.object(publish_module, "privacy_scan_artifact",
                      return_value=(minimal_pack({"id": "test-pack"}), [])), \
         patch.object(publish_module, "create_github_pr",
                      return_value={"success": True, "pr_url": "https://github.com/test/pull/1"}):

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))
        print("Result:", json.dumps(result, indent=2))
        assert result["success"] is True
        assert result["published"] is True
