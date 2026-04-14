"""
Tests for sybil resistance in borg/core/publish.py.

Tests:
  - _check_publish_access() rejects COMMUNITY tier agents
  - _check_publish_access() rejects THROTTLED free-rider agents
  - _check_publish_access() rejects RESTRICTED free-rider agents
  - _check_publish_access() allows VALIDATED tier with OK free-rider status
  - action_publish integration with sybil checks
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.core import publish as publish_module
from borg.db.reputation import (
    ReputationEngine,
    AccessTier,
    FreeRiderStatus,
    ReputationProfile,
)


# ============================================================================
# Helpers
# ============================================================================

def minimal_pack(overrides: Dict[str, Any] = None) -> dict:
    """Minimal valid workflow_pack artifact."""
    base = {
        "type": "workflow_pack",
        "version": "1.0",
        "id": "test-sybil-pack",
        "problem_class": "debugging",
        "mental_model": "fast-thinker",
        "phases": [
            {
                "description": "Reproduce the bug",
                "checkpoint": "Bug reproduced",
                "prompts": ["Reproduce {input}"],
                "anti_patterns": [],
            },
        ],
        "provenance": {
            "author": "agent://test",
            "author_agent": "agent://test",
            "created": "2026-01-01T00:00:00+00:00",
            "confidence": "inferred",
            "evidence": "tested in CI",
        },
    }
    if overrides:
        base.update(overrides)
    return base


def pack_yaml(artifact: dict) -> str:
    return yaml.dump(artifact, default_flow_style=False, sort_keys=False)


# ============================================================================
# Mock helpers
# ============================================================================

class MockReputationEngine:
    """Mock ReputationEngine that returns controlled profiles."""

    def __init__(self, store=None):
        self.store = store

    def build_profile(self, agent_id: str) -> ReputationProfile:
        return self._profile_map.get(agent_id, self._default_profile)

    def set_profile(self, agent_id: str, profile: ReputationProfile):
        self._profile_map[agent_id] = profile

    def __enter__(self):
        self._profile_map = {}
        self._default_profile = ReputationProfile(
            agent_id="default",
            contribution_score=0.0,
            access_tier=AccessTier.COMMUNITY,
            free_rider_status=FreeRiderStatus.OK,
        )
        return self

    def __exit__(self, *args):
        pass


def make_profile(
    agent_id: str,
    contribution_score: float,
    access_tier: AccessTier,
    free_rider_score: float = 0.0,
    free_rider_status: FreeRiderStatus = FreeRiderStatus.OK,
) -> ReputationProfile:
    return ReputationProfile(
        agent_id=agent_id,
        contribution_score=contribution_score,
        access_tier=access_tier,
        free_rider_score=free_rider_score,
        free_rider_status=free_rider_status,
    )


# ============================================================================
# _check_publish_access tests
# ============================================================================

class TestCheckPublishAccessSybil:
    """Tests for _check_publish_access() sybil resistance."""

    @patch.object(publish_module, 'AgentStore', None)
    def test_allows_when_no_store(self):
        """No store = degraded mode = allow."""
        allowed, msg = publish_module._check_publish_access("any-agent")
        assert allowed is True
        assert msg == ""

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_rejects_community_tier(self, mock_engine_cls, mock_store_cls):
        """COMMUNITY tier agents cannot publish."""
        community_profile = make_profile(
            agent_id="new-agent",
            contribution_score=5.0,
            access_tier=AccessTier.COMMUNITY,
        )

        mock_store = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = community_profile
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("new-agent")

        assert allowed is False
        assert "COMMUNITY tier" in msg
        assert "score=5.0" in msg
        assert "VALIDATED tier" in msg

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_rejects_throttled_free_rider(self, mock_engine_cls, mock_store_cls):
        """THROTTLED free-rider agents cannot publish."""
        throttled_profile = make_profile(
            agent_id="throttled-agent",
            contribution_score=30.0,
            access_tier=AccessTier.VALIDATED,
            free_rider_score=75.0,
            free_rider_status=FreeRiderStatus.THROTTLED,
        )

        mock_store = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = throttled_profile
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("throttled-agent")

        assert allowed is False
        assert "free-rider status" in msg
        assert "throttled" in msg
        assert "score=75.0" in msg

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_rejects_restricted_free_rider(self, mock_engine_cls, mock_store_cls):
        """RESTRICTED free-rider agents cannot publish."""
        restricted_profile = make_profile(
            agent_id="restricted-agent",
            contribution_score=15.0,
            access_tier=AccessTier.VALIDATED,
            free_rider_score=120.0,
            free_rider_status=FreeRiderStatus.RESTRICTED,
        )

        mock_store = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = restricted_profile
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("restricted-agent")

        assert allowed is False
        assert "restricted" in msg
        assert "score=120.0" in msg

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_allows_validated_tier_ok_free_rider(self, mock_engine_cls, mock_store_cls):
        """VALIDATED tier agents with OK free-rider status can publish."""
        good_profile = make_profile(
            agent_id="good-agent",
            contribution_score=25.0,
            access_tier=AccessTier.VALIDATED,
            free_rider_score=2.0,
            free_rider_status=FreeRiderStatus.OK,
        )

        mock_store = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = good_profile
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("good-agent")

        assert allowed is True
        assert msg == ""

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_allows_flagged_free_rider(self, mock_engine_cls, mock_store_cls):
        """FLAGGED free-rider agents can still publish (warning only)."""
        flagged_profile = make_profile(
            agent_id="flagged-agent",
            contribution_score=15.0,
            access_tier=AccessTier.VALIDATED,
            free_rider_score=30.0,
            free_rider_status=FreeRiderStatus.FLAGGED,
        )

        mock_store = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = flagged_profile
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("flagged-agent")

        # FLAGGED is not blocked — only THROTTLED and RESTRICTED
        assert allowed is True

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_allows_core_tier(self, mock_engine_cls, mock_store_cls):
        """CORE and GOVERNANCE tier agents can publish."""
        core_profile = make_profile(
            agent_id="core-agent",
            contribution_score=100.0,
            access_tier=AccessTier.CORE,
            free_rider_score=0.5,
            free_rider_status=FreeRiderStatus.OK,
        )

        mock_store = MagicMock()
        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = core_profile
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("core-agent")

        assert allowed is True

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_fails_open_on_exception(self, mock_engine_cls, mock_store_cls):
        """Exception in reputation check = fail open (allow)."""
        mock_engine = MagicMock()
        mock_engine.build_profile.side_effect = RuntimeError("DB error")
        mock_engine_cls.return_value = mock_engine

        allowed, msg = publish_module._check_publish_access("any-agent")

        assert allowed is True
        assert msg == ""


# ============================================================================
# action_publish sybil integration tests
# ============================================================================

class TestActionPublishSybilIntegration:
    """Integration tests for action_publish with sybil resistance."""

    @pytest.fixture
    def tmp_guild(self, monkeypatch, tmp_path):
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

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_publish_rejects_community_tier(self, mock_engine_cls, mock_store_cls, tmp_guild, monkeypatch):
        """action_publish returns error for COMMUNITY tier author."""
        community_profile = make_profile(
            agent_id="new-agent",
            contribution_score=3.0,
            access_tier=AccessTier.COMMUNITY,
        )

        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = community_profile
        mock_engine_cls.return_value = mock_engine

        # Create pack authored by community-tier agent
        pack_dir = tmp_guild["agent_dir"] / "community-pack"
        pack_dir.mkdir()
        pack = minimal_pack({"id": "community-pack", "provenance": {"author_agent": "new-agent"}})
        (pack_dir / "pack.yaml").write_text(yaml.dump(pack))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is False
        assert "Publish access denied" in result["error"]
        assert "COMMUNITY tier" in result["reason"]

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    def test_publish_rejects_throttled_free_rider(self, mock_engine_cls, mock_store_cls, tmp_guild, monkeypatch):
        """action_publish returns error for THROTTLED free-rider author."""
        throttled_profile = make_profile(
            agent_id="free-rider-agent",
            contribution_score=40.0,
            access_tier=AccessTier.VALIDATED,
            free_rider_score=80.0,
            free_rider_status=FreeRiderStatus.THROTTLED,
        )

        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = throttled_profile
        mock_engine_cls.return_value = mock_engine

        pack_dir = tmp_guild["agent_dir"] / "fr-pack"
        pack_dir.mkdir()
        pack = minimal_pack({"id": "fr-pack", "provenance": {"author_agent": "free-rider-agent"}})
        (pack_dir / "pack.yaml").write_text(yaml.dump(pack))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is False
        assert "Publish access denied" in result["error"]
        assert "throttled" in result["reason"]

    @patch("borg.core.publish.validate_proof_gates")
    @patch("borg.core.publish.create_github_pr")
    def test_publish_unknown_author_allowed(
        self, mock_pr, mock_validate, tmp_guild, monkeypatch
    ):
        """Pack with unknown author_agent skips sybil checks and goes through."""
        mock_pr.return_value = {"success": True, "pr_url": "https://github.com/test/pull/1"}
        mock_validate.return_value = []  # No proof gate errors

        pack_dir = tmp_guild["agent_dir"] / "anon-pack"
        pack_dir.mkdir()
        pack = minimal_pack({
            "id": "anon-pack",
            "provenance": {
                "author_agent": "unknown",
                "confidence": "guessed",
                "evidence": "tested in CI",
                "failure_cases": ["wrong label"],
            }
        })
        (pack_dir / "pack.yaml").write_text(yaml.dump(pack))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        # "unknown" author is not blocked by sybil checks
        assert result["success"] is True

    @patch.object(publish_module, 'AgentStore')
    @patch.object(publish_module, 'ReputationEngine')
    @patch("borg.core.publish.validate_proof_gates")
    @patch("borg.core.publish.create_github_pr")
    def test_publish_allows_good_agent(
        self, mock_pr, mock_validate, mock_engine_cls, mock_store_cls,
        tmp_guild, monkeypatch
    ):
        """action_publish allows VALIDATED agent with OK free-rider."""
        mock_pr.return_value = {"success": True, "pr_url": "https://github.com/test/pull/1"}
        mock_validate.return_value = []  # No proof gate errors

        good_profile = make_profile(
            agent_id="good-agent",
            contribution_score=30.0,
            access_tier=AccessTier.VALIDATED,
            free_rider_score=1.5,
            free_rider_status=FreeRiderStatus.OK,
        )

        mock_engine = MagicMock()
        mock_engine.build_profile.return_value = good_profile
        mock_engine_cls.return_value = mock_engine

        pack_dir = tmp_guild["agent_dir"] / "good-pack"
        pack_dir.mkdir()
        pack = minimal_pack({
            "id": "good-pack",
            "provenance": {
                "author_agent": "good-agent",
                "confidence": "tested",
                "evidence": "tested in CI",
                "failure_cases": ["wrong label"],
            }
        })
        (pack_dir / "pack.yaml").write_text(yaml.dump(pack))

        result = json.loads(publish_module.action_publish(path=str(pack_dir / "pack.yaml")))

        assert result["success"] is True
        assert result["published"] is True
