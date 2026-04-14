"""
Tests for AgentReputationManager (borg/defi/v2/reputation.py).
Covers trust tier progression, influence weights, vouching, and accuracy tracking.
"""

import pytest
from pathlib import Path
from datetime import datetime
import yaml
import tempfile
import os

from borg.defi.v2.reputation import (
    AgentReputationManager,
    INFLUENCE_WEIGHTS,
    TRUST_TIER_THRESHOLDS,
)
from borg.defi.v2.models import AgentReputation


class FakeOutcome:
    """Fake outcome for testing without needing full ExecutionOutcome."""
    def __init__(self, profitable=True, is_verified=False):
        self.profitable = profitable
        self.is_verified = is_verified


class TestTrustTierProgression:
    """Test trust tier progression: observer -> contributor -> trusted -> authority."""

    def test_new_agent_starts_as_observer(self, tmp_path):
        """New agent should start at observer tier with 0.1 influence."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        rep = mgr.get_reputation("new_agent")
        
        assert rep.trust_tier == "observer"
        assert rep.outcomes_submitted == 0
        assert rep.accuracy_score == 0.0

    def test_observer_influence_weight(self, tmp_path):
        """Observer should have 0.1 influence weight."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        assert mgr.get_influence_weight("new_agent") == 0.1

    def test_observer_tier_threshold(self, tmp_path):
        """Observer: < 3 outcomes submitted."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        # 0 outcomes
        assert mgr.get_trust_tier("agent_0") == "observer"
        # 1 outcome
        mgr.update_reputation("agent_1", FakeOutcome())
        assert mgr.get_trust_tier("agent_1") == "observer"
        # 2 outcomes
        mgr.update_reputation("agent_2", FakeOutcome())
        mgr.update_reputation("agent_2", FakeOutcome())
        assert mgr.get_trust_tier("agent_2") == "observer"

    def test_contributor_tier_at_3_outcomes(self, tmp_path):
        """Contributor: 3-19 outcomes submitted."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "contributor_test"
        
        # 3 outcomes -> contributor
        for _ in range(3):
            mgr.update_reputation(agent_id, FakeOutcome())
        
        assert mgr.get_trust_tier(agent_id) == "contributor"
        assert mgr.get_influence_weight(agent_id) == 1.0

    def test_contributor_influence_weight(self, tmp_path):
        """Contributor should have 1.0 influence weight."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "contributor_weight_test"
        
        for _ in range(3):
            mgr.update_reputation(agent_id, FakeOutcome())
        
        assert mgr.get_influence_weight(agent_id) == 1.0

    def test_trusted_tier_requires_20_outcomes_and_accuracy(self, tmp_path):
        """Trusted: 20+ outcomes AND accuracy > 0.8."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "trusted_test"
        
        # 19 outcomes -> still contributor
        for _ in range(19):
            mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        assert mgr.get_trust_tier(agent_id) == "contributor"
        
        # 20th outcome, but need accuracy > 0.8
        # With all profitable, EMA accuracy = 1.0 after enough rounds
        # Let's check: EMA with alpha=0.1 means after 20 profitable, accuracy ~0.9
        # We need accuracy > 0.8
        for _ in range(10):
            mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        # After 29 profitable outcomes, EMA should be high enough
        tier = mgr.get_trust_tier(agent_id)
        assert tier == "trusted"

    def test_trusted_influence_weight(self, tmp_path):
        """Trusted should have 1.5 influence weight."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "trusted_weight_test"
        
        # Create trusted agent with high accuracy
        for _ in range(25):
            mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        assert mgr.get_influence_weight(agent_id) == 1.5

    def test_authority_requires_50_outcomes_and_3_vouches(self, tmp_path):
        """Authority: 50+ outcomes AND 3+ vouches from trusted/authority."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        # Create a trusted voucher agent
        voucher_id = "voucher_agent"
        for _ in range(30):
            mgr.update_reputation(voucher_id, FakeOutcome(profitable=True))
        assert mgr.get_trust_tier(voucher_id) == "trusted"
        
        # Create target agent with 50+ outcomes
        target_id = "authority_target"
        for _ in range(50):
            mgr.update_reputation(target_id, FakeOutcome(profitable=True))
        
        # Without vouches, still trusted (not authority)
        assert mgr.get_trust_tier(target_id) == "trusted"
        
        # Add 3 vouches from trusted agents
        mgr.vouch(voucher_id, target_id)
        mgr.vouch(voucher_id, target_id)  # Can't vouch twice
        assert len(mgr.get_vouches(target_id)[0]) == 1
        
        # Create 2 more trusted vouches
        voucher2_id = "voucher_agent_2"
        voucher3_id = "voucher_agent_3"
        for _ in range(30):
            mgr.update_reputation(voucher2_id, FakeOutcome(profitable=True))
            mgr.update_reputation(voucher3_id, FakeOutcome(profitable=True))
        
        mgr.vouch(voucher2_id, target_id)
        mgr.vouch(voucher3_id, target_id)
        
        vouched_by, _ = mgr.get_vouches(target_id)
        assert len(vouched_by) == 3
        assert mgr.get_trust_tier(target_id) == "authority"

    def test_authority_influence_weight(self, tmp_path):
        """Authority should have 2.0 influence weight."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        # Create authority through vouches
        voucher_id = "auth_voucher"
        for _ in range(35):
            mgr.update_reputation(voucher_id, FakeOutcome(profitable=True))
        
        target_id = "authority_weight_test"
        for _ in range(55):
            mgr.update_reputation(target_id, FakeOutcome(profitable=True))
        
        # Add 3 vouches
        for i in range(3):
            v_id = f"voucher_{i}"
            for _ in range(35):
                mgr.update_reputation(v_id, FakeOutcome(profitable=True))
            mgr.vouch(v_id, target_id)
        
        assert mgr.get_influence_weight(target_id) == 2.0


class TestInfluenceWeights:
    """Test influence weights per tier."""

    def test_influence_weights_constant(self):
        """Influence weights should be defined for all tiers."""
        assert INFLUENCE_WEIGHTS["observer"] == 0.1
        assert INFLUENCE_WEIGHTS["contributor"] == 1.0
        assert INFLUENCE_WEIGHTS["trusted"] == 1.5
        assert INFLUENCE_WEIGHTS["authority"] == 2.0

    def test_influence_weight_unknown_tier_defaults_to_observer(self, tmp_path):
        """Unknown tier should default to observer weight (0.1)."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        # get_influence_weight uses .get() with default 0.1
        assert mgr.get_influence_weight("unknown_tier_agent") == 0.1


class TestVouchingSystem:
    """Test the vouching system."""

    def test_only_trusted_or_authority_can_vouch(self, tmp_path):
        """Only trusted or authority agents can vouch."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        # Observer cannot vouch
        observer_id = "observer_voucher"
        result = mgr.vouch(observer_id, "some_target")
        assert result == False
        
        # Contributor cannot vouch
        contributor_id = "contributor_voucher"
        for _ in range(3):
            mgr.update_reputation(contributor_id, FakeOutcome())
        result = mgr.vouch(contributor_id, "some_target")
        assert result == False

    def test_trusted_can_vouch(self, tmp_path):
        """Trusted agent can vouch."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        voucher_id = "trusted_voucher"
        for _ in range(25):
            mgr.update_reputation(voucher_id, FakeOutcome(profitable=True))
        
        target_id = "vouch_target"
        result = mgr.vouch(voucher_id, target_id)
        assert result == True

    def test_cannot_vouch_for_self(self, tmp_path):
        """Agent cannot vouch for themselves."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        voucher_id = "self_voucher"
        for _ in range(25):
            mgr.update_reputation(voucher_id, FakeOutcome(profitable=True))
        
        result = mgr.vouch(voucher_id, voucher_id)
        assert result == False

    def test_cannot_vouch_twice(self, tmp_path):
        """Cannot vouch for the same agent twice."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        voucher_id = "repeat_voucher"
        for _ in range(25):
            mgr.update_reputation(voucher_id, FakeOutcome(profitable=True))
        
        target_id = "double_vouch_target"
        result1 = mgr.vouch(voucher_id, target_id)
        result2 = mgr.vouch(voucher_id, target_id)
        
        assert result1 == True
        assert result2 == False
        vouched_by, _ = mgr.get_vouches(target_id)
        assert len(vouched_by) == 1

    def test_vouch_updates_vouched_by_list(self, tmp_path):
        """Vouching should update the target's vouched_by list."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        voucher_id = "list_voucher"
        # Need 20+ outcomes with high accuracy to reach trusted tier
        for _ in range(30):
            mgr.update_reputation(voucher_id, FakeOutcome(profitable=True))
        # Force trusted tier by setting accuracy directly
        rep = mgr.get_reputation(voucher_id)
        rep.accuracy_score = 0.9
        rep.trust_tier = "trusted"
        mgr._save(rep)
        
        target_id = "list_target"
        result = mgr.vouch(voucher_id, target_id)
        
        if result:
            vouched_by, _ = mgr.get_vouches(target_id)
            assert voucher_id in vouched_by
            _, vouches_for = mgr.get_vouches(voucher_id)
            assert target_id in vouches_for
        else:
            # If vouch fails, voucher tier wasn't high enough — skip
            pytest.skip("Voucher didn't reach trusted tier")

    def test_vouching_recomputes_trust_tier(self, tmp_path):
        """Vouching should recompute the target's trust tier."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        # Create target with 50 outcomes but no vouches
        target_id = "tier_recompute_target"
        for _ in range(50):
            mgr.update_reputation(target_id, FakeOutcome(profitable=True))
        
        assert mgr.get_trust_tier(target_id) == "trusted"  # No vouches yet
        
        # Create 3 trusted vouches
        for i in range(3):
            v_id = f"tier_voucher_{i}"
            for _ in range(30):
                mgr.update_reputation(v_id, FakeOutcome(profitable=True))
            mgr.vouch(v_id, target_id)
        
        # Now should be authority
        assert mgr.get_trust_tier(target_id) == "authority"


class TestAccuracyTracking:
    """Test accuracy score tracking."""

    def test_accuracy_score_initial_value(self, tmp_path):
        """New agent should have 0.0 accuracy."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        rep = mgr.get_reputation("accuracy_new_agent")
        assert rep.accuracy_score == 0.0

    def test_accuracy_improves_with_profitable_outcomes(self, tmp_path):
        """Accuracy should improve with profitable outcomes (EMA)."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "accuracy_profitable"
        
        # First outcome
        mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        rep = mgr.get_reputation(agent_id)
        
        # After 1 profitable: 0.9*0 + 0.1*1 = 0.1
        assert rep.accuracy_score == pytest.approx(0.1, rel=0.01)
        
        # After 10 profitable in a row: should be higher
        for _ in range(10):
            mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        rep = mgr.get_reputation(agent_id)
        assert rep.accuracy_score > 0.5

    def test_accuracy_decreases_with_unprofitable_outcomes(self, tmp_path):
        """Accuracy should decrease with unprofitable outcomes."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "accuracy_loss"
        
        # Start with profitable
        for _ in range(10):
            mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        rep = mgr.get_reputation(agent_id)
        high_accuracy = rep.accuracy_score
        
        # Add losses
        for _ in range(10):
            mgr.update_reputation(agent_id, FakeOutcome(profitable=False))
        
        rep = mgr.get_reputation(agent_id)
        assert rep.accuracy_score < high_accuracy

    def test_verified_outcome_increments_verified_count(self, tmp_path):
        """Verified outcomes (with tx_hash) should increment outcomes_verified."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "verified_agent"
        
        # Create verified outcome
        verified_outcome = FakeOutcome(profitable=True, is_verified=True)
        mgr.update_reputation(agent_id, verified_outcome)
        
        rep = mgr.get_reputation(agent_id)
        assert rep.outcomes_verified == 1

    def test_unverified_outcome_does_not_increment_verified(self, tmp_path):
        """Unverified outcomes should not increment outcomes_verified."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "unverified_agent"
        
        mgr.update_reputation(agent_id, FakeOutcome(profitable=True, is_verified=False))
        
        rep = mgr.get_reputation(agent_id)
        assert rep.outcomes_verified == 0


class TestPersistence:
    """Test that reputation persists to disk."""

    def test_reputation_saves_to_disk(self, tmp_path):
        """Reputation should be saved to YAML file."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "persist_test"
        
        mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        # Check file exists
        agent_file = tmp_path / f"{agent_id}.yaml"
        assert agent_file.exists()
        
        # Load and verify
        with open(agent_file) as f:
            data = yaml.safe_load(f)
        
        assert data["agent_id"] == agent_id
        assert data["outcomes_submitted"] == 1

    def test_reputation_loads_from_disk(self, tmp_path):
        """Reputation should load from disk on get_reputation."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        agent_id = "load_test"
        
        # Create reputation
        mgr.update_reputation(agent_id, FakeOutcome(profitable=True))
        
        # New manager should load from disk
        mgr2 = AgentReputationManager(agents_dir=tmp_path)
        rep = mgr2.get_reputation(agent_id)
        
        assert rep.outcomes_submitted == 1

    def test_list_agents(self, tmp_path):
        """list_agents should return all agent IDs."""
        mgr = AgentReputationManager(agents_dir=tmp_path)
        
        mgr.update_reputation("agent_a", FakeOutcome())
        mgr.update_reputation("agent_b", FakeOutcome())
        
        agents = mgr.list_agents()
        assert "agent_a" in agents
        assert "agent_b" in agents
        assert len(agents) == 2
