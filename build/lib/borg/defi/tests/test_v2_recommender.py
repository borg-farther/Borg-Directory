"""Borg DeFi V2 — Tests for recommender."""

import pytest
import tempfile
import shutil
import math
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from borg.defi.v2.recommender import (
    DeFiRecommender,
    temporal_weight,
    normalize,
    calculate_confidence,
    beta_sample,
    detect_drift,
    calculate_confidence_interval,
    DEFAULT_HALF_LIFE_DAYS,
    PRIOR_ALPHA,
    PRIOR_BETA,
)
from borg.defi.v2.models import (
    DeFiStrategyPack,
    StrategyQuery,
    ExecutionOutcome,
    CollectiveStats,
    EntryCriteria,
    ActionSpec,
    RiskAssessment,
)
from borg.defi.v2.pack_store import PackStore
from borg.defi.v2.outcome_store import OutcomeStore


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def recommender(temp_dir):
    """Create a DeFiRecommender with temporary directories."""
    packs_dir = temp_dir / "packs"
    outcomes_dir = temp_dir / "outcomes"
    breaker_dir = temp_dir / "breaker"
    return DeFiRecommender(packs_dir=packs_dir, outcomes_dir=outcomes_dir,
                          circuit_breaker_state_dir=breaker_dir)


@pytest.fixture
def sample_pack_aave():
    """Create a sample Aave pack."""
    return DeFiStrategyPack(
        id="yield/aave-usdc-base",
        name="Aave V3 USDC Lending on Base",
        version=3,
        entry=EntryCriteria(
            tokens=["USDC", "USDT"],
            chains=["base", "ethereum"],
            min_amount_usd=100,
            risk_tolerance=["low", "medium"],
        ),
        action=ActionSpec(
            type="lend",
            protocol="aave-v3",
            steps=["Supply USDC to Aave V3 on Base", "Monitor health factor"],
        ),
        exit_guidance="No lock period. Withdraw whenever needed.",
        collective=CollectiveStats(
            total_outcomes=12,
            profitable=11,
            alpha=12,
            beta=2,
            avg_return_pct=4.2,
            median_return_pct=4.0,
            std_dev=1.2,
            min_return_pct=-0.3,
            max_return_pct=5.8,
            avg_duration_days=30.0,
            last_5_returns=[4.1, 3.8, 5.2, 4.5, 3.9],
            trend="stable",
        ),
        risk=RiskAssessment(
            il_risk=False,
            rug_score=0.0,
            protocol_age_days=890,
            audit_status="multiple audits",
        ),
        updated_at=datetime(2026, 3, 30, 12, 0, 0),
        created_at=datetime(2026, 2, 15, 0, 0, 0),
    )


@pytest.fixture
def sample_pack_kamino():
    """Create a sample Kamino pack."""
    return DeFiStrategyPack(
        id="yield/kamino-usdc-sol",
        name="Kamino CLMM USDC-SOL",
        version=2,
        entry=EntryCriteria(
            tokens=["USDC", "SOL"],
            chains=["solana"],
            min_amount_usd=50,
            risk_tolerance=["medium", "high"],
        ),
        action=ActionSpec(
            type="lp",
            protocol="kamino",
            steps=["Add liquidity to USDC-SOL pool"],
        ),
        exit_guidance="Pull liquidity when APY drops below 5%",
        collective=CollectiveStats(
            total_outcomes=8,
            profitable=6,
            alpha=7,
            beta=3,
            avg_return_pct=8.5,
            median_return_pct=7.8,
            std_dev=3.2,
            min_return_pct=-2.1,
            max_return_pct=15.2,
            avg_duration_days=45.0,
            last_5_returns=[10.2, 8.5, 7.2, 6.8, 9.1],
            trend="improving",
        ),
        risk=RiskAssessment(
            il_risk=True,
            rug_score=0.15,
            protocol_age_days=365,
            audit_status="single audit",
        ),
        updated_at=datetime(2026, 3, 29, 10, 0, 0),
        created_at=datetime(2026, 1, 15, 0, 0, 0),
    )


class TestTemporalWeight:
    """Tests for temporal_weight function."""

    def test_fresh_outcome(self):
        """Test that fresh outcomes have high weight."""
        weight = temporal_weight(0)
        assert weight == 1.0

    def test_half_life(self):
        """Test that outcome at half-life has 0.5 weight."""
        weight = temporal_weight(DEFAULT_HALF_LIFE_DAYS)
        assert abs(weight - 0.5) < 0.001

    def test_two_half_lives(self):
        """Test outcome at 2x half-life has 0.25 weight."""
        weight = temporal_weight(2 * DEFAULT_HALF_LIFE_DAYS)
        assert abs(weight - 0.25) < 0.001

    def test_negative_age(self):
        """Test that negative age is treated as 0."""
        weight = temporal_weight(-10)
        assert weight == 1.0

    def test_custom_half_life(self):
        """Test with custom half-life."""
        weight = temporal_weight(15, half_life_days=15)
        assert abs(weight - 0.5) < 0.001

    def test_old_outcome(self):
        """Test that old outcomes have low weight."""
        weight = temporal_weight(180)
        assert weight < 0.1


class TestNormalize:
    """Tests for normalize function."""

    def test_single_value(self):
        """Test normalizing a single value."""
        result = normalize(5.0, min_val=0, max_val=10)
        assert result == 0.5

    def test_value_at_min(self):
        """Test value at minimum."""
        result = normalize(0.0, min_val=0, max_val=10)
        assert result == 0.0

    def test_value_at_max(self):
        """Test value at maximum."""
        result = normalize(10.0, min_val=0, max_val=10)
        assert result == 1.0

    def test_list_normalization(self):
        """Test normalizing a list of values."""
        result = normalize([0.0, 5.0, 10.0])
        assert result == [0.0, 0.5, 1.0]

    def test_empty_list(self):
        """Test normalizing empty list."""
        result = normalize([])
        assert result == 0.0

    def test_same_min_max(self):
        """Test when min equals max."""
        result = normalize(5.0, min_val=5, max_val=5)
        assert result == 0.0


class TestCalculateConfidence:
    """Tests for calculate_confidence function."""

    def test_no_collective(self):
        """Test with no collective stats."""
        pack = DeFiStrategyPack(id="test", name="Test")
        assert calculate_confidence(pack) == 0.0

    def test_zero_outcomes(self):
        """Test with zero outcomes."""
        pack = DeFiStrategyPack(
            id="test",
            name="Test",
            collective=CollectiveStats(total_outcomes=0),
        )
        assert calculate_confidence(pack) == 0.0

    def test_low_sample_size(self):
        """Test with small sample size."""
        pack = DeFiStrategyPack(
            id="test",
            name="Test",
            collective=CollectiveStats(total_outcomes=2),
        )
        assert calculate_confidence(pack) == 0.2  # 0.1 * 2

    def test_adequate_sample_size(self):
        """Test with adequate sample size."""
        pack = DeFiStrategyPack(
            id="test",
            name="Test",
            collective=CollectiveStats(
                total_outcomes=10,
                avg_return_pct=5.0,
                std_dev=1.0,
            ),
        )
        confidence = calculate_confidence(pack)
        assert 0 < confidence < 1.0

    def test_high_variance_penalty(self):
        """Test that high variance reduces confidence."""
        # Low variance
        pack_low_var = DeFiStrategyPack(
            id="test1",
            name="Test",
            collective=CollectiveStats(
                total_outcomes=10,
                avg_return_pct=10.0,
                std_dev=1.0,  # CV = 0.1
            ),
        )
        # High variance
        pack_high_var = DeFiStrategyPack(
            id="test2",
            name="Test",
            collective=CollectiveStats(
                total_outcomes=10,
                avg_return_pct=10.0,
                std_dev=5.0,  # CV = 0.5
            ),
        )
        conf_low = calculate_confidence(pack_low_var)
        conf_high = calculate_confidence(pack_high_var)
        assert conf_low > conf_high


class TestBetaSample:
    """Tests for beta_sample function."""

    def test_prior(self):
        """Test sampling from prior Beta(1,1)."""
        # With prior of 1,1, mean should be ~0.5
        samples = [beta_sample(1, 1) for _ in range(100)]
        mean = sum(samples) / len(samples)
        assert 0.3 < mean < 0.7

    def test_biased_positive(self):
        """Test sampling from biased positive Beta."""
        samples = [beta_sample(10, 2) for _ in range(100)]
        mean = sum(samples) / len(samples)
        assert 0.7 < mean < 0.9  # 10/(10+2) = 0.833

    def test_biased_negative(self):
        """Test sampling from biased negative Beta."""
        samples = [beta_sample(2, 10) for _ in range(100)]
        mean = sum(samples) / len(samples)
        assert 0.1 < mean < 0.3  # 2/(2+10) = 0.167

    def test_invalid_alpha(self):
        """Test with invalid alpha."""
        result = beta_sample(0, 5)
        assert result == 0.0

    def test_invalid_beta(self):
        """Test with invalid beta."""
        result = beta_sample(5, 0)
        assert result == 1.0


class TestDetectDrift:
    """Tests for detect_drift function."""

    def test_no_collective(self):
        """Test with no collective stats."""
        pack = DeFiStrategyPack(id="test", name="Test")
        assert detect_drift(pack) is None

    def test_low_sample_size(self):
        """Test with insufficient data for drift detection."""
        pack = DeFiStrategyPack(
            id="test",
            name="Test",
            collective=CollectiveStats(total_outcomes=5),
        )
        assert detect_drift(pack) is None

    def test_no_recent_returns(self):
        """Test with no recent returns."""
        pack = DeFiStrategyPack(
            id="test",
            name="Test",
            collective=CollectiveStats(total_outcomes=10, last_5_returns=[]),
        )
        assert detect_drift(pack) is None

    def test_stable_trend(self):
        """Test detecting stable trend (no drift)."""
        pack = DeFiStrategyPack(
            id="test",
            name="Test",
            collective=CollectiveStats(
                total_outcomes=15,
                avg_return_pct=5.0,
                std_dev=0.5,
                last_5_returns=[5.1, 4.9, 5.0, 5.2, 4.8],
            ),
        )
        assert detect_drift(pack) is None


class TestConfidenceInterval:
    """Tests for calculate_confidence_interval function."""

    def test_prior(self):
        """Test CI for prior Beta(1,1)."""
        ci = calculate_confidence_interval(1, 1)
        assert ci[0] >= 0.0
        assert ci[1] <= 1.0
        assert ci[0] < ci[1]

    def test_high_confidence(self):
        """Test CI for high confidence (many samples)."""
        ci = calculate_confidence_interval(100, 10)
        assert ci[1] - ci[0] < 0.3  # Narrow interval

    def test_low_confidence(self):
        """Test CI for low confidence (few samples)."""
        ci = calculate_confidence_interval(2, 2)
        assert ci[1] - ci[0] > 0.3  # Wide interval


class TestDeFiRecommenderInit:
    """Tests for DeFiRecommender initialization."""

    def test_default_init(self):
        """Test default initialization."""
        rec = DeFiRecommender()
        assert rec.pack_store is not None
        assert rec.outcome_store is not None

    def test_custom_dirs(self, temp_dir):
        """Test initialization with custom directories."""
        packs_dir = temp_dir / "packs"
        outcomes_dir = temp_dir / "outcomes"
        rec = DeFiRecommender(packs_dir=packs_dir, outcomes_dir=outcomes_dir)
        assert rec.pack_store.packs_dir == packs_dir
        assert rec.outcome_store.outcomes_dir == outcomes_dir


class TestDeFiRecommenderGetPack:
    """Tests for get_pack method."""

    def test_get_pack(self, recommender, sample_pack_aave):
        """Test getting an existing pack."""
        recommender.pack_store.save_pack(sample_pack_aave)
        pack = recommender.get_pack(sample_pack_aave.id)
        assert pack is not None
        assert pack.id == sample_pack_aave.id

    def test_get_nonexistent_pack(self, recommender):
        """Test getting a pack that doesn't exist."""
        pack = recommender.get_pack("nonexistent/pack")
        assert pack is None


class TestDeFiRecommenderRecommend:
    """Tests for recommend method."""

    def test_recommend_empty(self, recommender):
        """Test recommendation with no packs."""
        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query)
        assert recs == []

    def test_recommend_single_pack(self, recommender, sample_pack_aave):
        """Test recommendation with a single pack."""
        recommender.pack_store.save_pack(sample_pack_aave)
        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query)

        assert len(recs) == 1
        assert recs[0].pack_id == sample_pack_aave.id
        assert recs[0].rank == 1

    def test_recommend_multiple_packs(self, recommender, sample_pack_aave, sample_pack_kamino):
        """Test recommendation with multiple packs."""
        recommender.pack_store.save_pack(sample_pack_aave)
        recommender.pack_store.save_pack(sample_pack_kamino)

        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query)

        assert len(recs) == 2
        assert recs[0].rank == 1
        assert recs[1].rank == 2

    def test_recommend_filter_by_token(self, recommender, sample_pack_aave, sample_pack_kamino):
        """Test that recommendations filter by token."""
        recommender.pack_store.save_pack(sample_pack_aave)
        recommender.pack_store.save_pack(sample_pack_kamino)

        # Query for SOL should only return kamino pack
        query = StrategyQuery(token="SOL")
        recs = recommender.recommend(query)

        assert len(recs) == 1
        assert recs[0].pack_id == sample_pack_kamino.id

    def test_recommend_filter_by_chain(self, recommender, sample_pack_aave, sample_pack_kamino):
        """Test that recommendations filter by chain."""
        recommender.pack_store.save_pack(sample_pack_aave)
        recommender.pack_store.save_pack(sample_pack_kamino)

        query = StrategyQuery(token="USDC", chain="solana")
        recs = recommender.recommend(query)

        assert len(recs) == 1
        assert recs[0].pack_id == sample_pack_kamino.id

    def test_recommend_filter_by_risk(self, recommender, sample_pack_aave, sample_pack_kamino):
        """Test that recommendations filter by risk tolerance."""
        recommender.pack_store.save_pack(sample_pack_aave)
        recommender.pack_store.save_pack(sample_pack_kamino)

        # Query for low risk should only return aave pack
        query = StrategyQuery(token="USDC", risk_tolerance="low")
        recs = recommender.recommend(query)

        assert len(recs) == 1
        assert recs[0].pack_id == sample_pack_aave.id

    def test_recommend_limit(self, recommender, sample_pack_aave, sample_pack_kamino):
        """Test that recommendations are limited."""
        recommender.pack_store.save_pack(sample_pack_aave)
        recommender.pack_store.save_pack(sample_pack_kamino)

        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query, limit=1)

        assert len(recs) == 1

    def test_recommend_with_warning(self, recommender, sample_pack_aave):
        """Test that packs with warnings are excluded."""
        recommender.pack_store.save_pack(sample_pack_aave)

        # Add a warning for the aave pack
        warning = {
            "id": f"warning/{sample_pack_aave.id}/20260330",
            "type": "collective_warning",
            "severity": "high",
            "pack_id": sample_pack_aave.id,
            "reason": "Multiple losses",
            "guidance": "Avoid",
            "created_at": "2026-03-30T10:00:00",
            "expires_at": "2026-04-29T10:00:00",
        }
        recommender.pack_store.save_warning(warning)

        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query)

        assert len(recs) == 0  # Warned pack should be excluded

    def test_recommend_preserves_metadata(self, recommender, sample_pack_aave):
        """Test that recommendation preserves pack metadata."""
        recommender.pack_store.save_pack(sample_pack_aave)

        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query)

        assert len(recs) == 1
        rec = recs[0]
        assert rec.protocol == "aave-v3"
        assert rec.action_type == "lend"
        assert rec.avg_return_pct == 4.2
        assert rec.il_risk is False
        assert rec.exit_guidance == sample_pack_aave.exit_guidance


class TestDeFiRecommenderRecordOutcome:
    """Tests for record_outcome method."""

    def test_record_outcome_creates_pack_if_missing(self, recommender):
        """Test that recording outcome for missing pack fails gracefully."""
        outcome = ExecutionOutcome(
            outcome_id="out-new",
            pack_id="new/pack",
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            duration_days=30.0,
            return_pct=5.0,
            profitable=True,
        )
        # Should not crash, but won't update any pack
        recommender.record_outcome(outcome)

    def test_record_profitable_outcome(self, recommender, sample_pack_aave):
        """Test recording a profitable outcome."""
        recommender.pack_store.save_pack(sample_pack_aave)

        initial_outcomes = sample_pack_aave.collective.total_outcomes
        initial_alpha = sample_pack_aave.collective.alpha

        outcome = ExecutionOutcome(
            outcome_id="out-new-profitable",
            pack_id=sample_pack_aave.id,
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            exited_at=datetime(2026, 3, 31),
            duration_days=30.0,
            return_pct=4.5,
            profitable=True,
        )

        recommender.record_outcome(outcome)

        # Reload pack and check updates
        updated = recommender.get_pack(sample_pack_aave.id)
        assert updated.collective.total_outcomes == initial_outcomes + 1
        assert updated.collective.alpha == initial_alpha + 1
        assert updated.collective.profitable == sample_pack_aave.collective.profitable + 1

    def test_record_unprofitable_outcome(self, recommender, sample_pack_aave):
        """Test recording an unprofitable outcome."""
        recommender.pack_store.save_pack(sample_pack_aave)

        initial_beta = sample_pack_aave.collective.beta

        outcome = ExecutionOutcome(
            outcome_id="out-new-loss",
            pack_id=sample_pack_aave.id,
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            exited_at=datetime(2026, 3, 31),
            duration_days=30.0,
            return_pct=-1.5,
            profitable=False,
        )

        recommender.record_outcome(outcome)

        updated = recommender.get_pack(sample_pack_aave.id)
        assert updated.collective.beta == initial_beta + 1

    def test_record_outcome_bumps_version(self, recommender, sample_pack_aave):
        """Test that recording an outcome bumps pack version."""
        recommender.pack_store.save_pack(sample_pack_aave)
        initial_version = sample_pack_aave.version

        outcome = ExecutionOutcome(
            outcome_id="out-version-bump",
            pack_id=sample_pack_aave.id,
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            duration_days=30.0,
            return_pct=5.0,
            profitable=True,
        )

        recommender.record_outcome(outcome)

        updated = recommender.get_pack(sample_pack_aave.id)
        assert updated.version == initial_version + 1

    def test_record_outcome_updates_last_5_returns(self, recommender, sample_pack_aave):
        """Test that last_5_returns is updated."""
        recommender.pack_store.save_pack(sample_pack_aave)

        # Add several outcomes
        for i in range(3):
            outcome = ExecutionOutcome(
                outcome_id=f"out-return-{i}",
                pack_id=sample_pack_aave.id,
                agent_id=f"agent-{i}",
                entered_at=datetime(2026, 3, 1) + timedelta(days=i * 5),
                duration_days=30.0,
                return_pct=4.0 + i * 0.5,
                profitable=True,
            )
            recommender.record_outcome(outcome)

        updated = recommender.get_pack(sample_pack_aave.id)
        assert len(updated.collective.last_5_returns) == 3

    def test_record_outcome_creates_warning_on_low_reputation(self, recommender):
        """Test that low reputation triggers warning propagation."""
        # Create a pack with beta >= 4 and reputation < 0.4
        pack = DeFiStrategyPack(
            id="warning-test/pack",
            name="Warning Test Pack",
            collective=CollectiveStats(
                total_outcomes=10,
                profitable=3,  # reputation = 3/12 = 0.25
                alpha=4,  # 3 wins + 1 prior
                beta=8,   # 7 losses + 1 prior
                avg_return_pct=1.0,
            ),
        )
        recommender.pack_store.save_pack(pack)

        # Record another loss
        outcome = ExecutionOutcome(
            outcome_id="out-warning-trigger",
            pack_id=pack.id,
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            duration_days=30.0,
            return_pct=-2.0,
            profitable=False,
        )
        recommender.record_outcome(outcome)

        # Check warnings
        warnings = recommender.get_active_warnings()
        warning_pack_ids = [w.get("pack_id") for w in warnings]
        assert pack.id in warning_pack_ids


class TestDeFiRecommenderGetActiveWarnings:
    """Tests for get_active_warnings method."""

    def test_no_warnings(self, recommender):
        """Test when no warnings exist."""
        warnings = recommender.get_active_warnings()
        assert warnings == []

    def test_expired_warning_filtered(self, recommender):
        """Test that expired warnings are filtered out."""
        # Create an expired warning
        warning = {
            "id": "warning/expired",
            "type": "collective_warning",
            "severity": "high",
            "pack_id": "test/pack",
            "reason": "Test",
            "guidance": "Test guidance",
            "created_at": "2026-01-01T10:00:00",
            "expires_at": "2026-01-15T10:00:00",  # Expired
        }
        recommender.pack_store.save_warning(warning)

        warnings = recommender.get_active_warnings()
        assert len(warnings) == 0

    def test_valid_warning_returned(self, recommender):
        """Test that valid warnings are returned."""
        warning = {
            "id": "warning/valid",
            "type": "collective_warning",
            "severity": "high",
            "pack_id": "test/pack",
            "reason": "Test",
            "guidance": "Test guidance",
            "created_at": "2026-03-01T10:00:00",
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        }
        recommender.pack_store.save_warning(warning)

        warnings = recommender.get_active_warnings()
        assert len(warnings) == 1
        assert warnings[0]["id"] == "warning/valid"


class TestDeFiRecommenderGetStats:
    """Tests for stats methods."""

    def test_get_collective_stats(self, recommender, sample_pack_aave):
        """Test getting collective stats for a pack."""
        recommender.pack_store.save_pack(sample_pack_aave)

        stats = recommender.get_collective_stats(sample_pack_aave.id)
        assert stats is not None
        assert stats.total_outcomes == sample_pack_aave.collective.total_outcomes

    def test_get_collective_stats_nonexistent(self, recommender):
        """Test getting stats for nonexistent pack."""
        stats = recommender.get_collective_stats("nonexistent")
        assert stats is None

    def test_get_pack_count(self, recommender, sample_pack_aave, sample_pack_kamino):
        """Test getting pack count."""
        assert recommender.get_pack_count() == 0

        recommender.pack_store.save_pack(sample_pack_aave)
        assert recommender.get_pack_count() == 1

        recommender.pack_store.save_pack(sample_pack_kamino)
        assert recommender.get_pack_count() == 2

    def test_get_outcome_count(self, recommender, sample_pack_aave):
        """Test getting outcome count."""
        recommender.pack_store.save_pack(sample_pack_aave)

        assert recommender.get_outcome_count() == 0

        outcome = ExecutionOutcome(
            outcome_id="out-count-test",
            pack_id=sample_pack_aave.id,
            agent_id="agent-001",
            entered_at=datetime(2026, 3, 1),
            duration_days=30.0,
            return_pct=5.0,
            profitable=True,
        )
        recommender.record_outcome(outcome)

        assert recommender.get_outcome_count() == 1


class TestDeFiRecommenderIntegration:
    """Integration tests for the full recommendation loop."""

    def test_full_loop_recommend_record(self, recommender, sample_pack_aave):
        """Test the full recommend -> execute -> record loop."""
        # 1. Initial state
        recommender.pack_store.save_pack(sample_pack_aave)
        
        query = StrategyQuery(token="USDC")
        recs = recommender.recommend(query)
        assert len(recs) == 1
        initial_return = recs[0].avg_return_pct

        # 2. Record a new profitable outcome
        outcome = ExecutionOutcome(
            outcome_id="out-integration-1",
            pack_id=sample_pack_aave.id,
            agent_id="agent-integration",
            entered_at=datetime(2026, 3, 1),
            exited_at=datetime(2026, 3, 31),
            duration_days=30.0,
            return_pct=5.0,  # Better than average
            profitable=True,
        )
        recommender.record_outcome(outcome)

        # 3. Get updated recommendation
        recs = recommender.recommend(query)
        # Note: The recorded outcome changes the pack's aggregate stats
        # which may affect the score
        assert len(recs) == 1

    def test_thompson_sampling_explores_new_strategies(self, temp_dir):
        """Test that Thompson Sampling explores new packs with few outcomes.
        
        Thompson Sampling balances exploration (new packs) vs exploitation (proven packs).
        A truly new pack with Beta(1,1) prior can sometimes beat established packs
        when its sampled win rate is high, despite lower confidence.
        """
        # Create a pack with no outcomes (new strategy) but very promising returns
        new_pack = DeFiStrategyPack(
            id="yield/new-strategy",
            name="New Strategy",
            collective=CollectiveStats(
                total_outcomes=0,
                profitable=0,
                alpha=1,  # Prior
                beta=1,  # Prior
                avg_return_pct=15.0,  # Very promising but unproven (high return potential)
            ),
        )

        # Create a mediocre established pack (lower returns but many outcomes)
        established_pack = DeFiStrategyPack(
            id="yield/established-strategy",
            name="Established Strategy",
            collective=CollectiveStats(
                total_outcomes=50,
                profitable=25,  # Only 50% win rate
                alpha=26,
                beta=26,
                avg_return_pct=3.0,  # Lower returns
            ),
        )

        # Save packs
        packs_dir = temp_dir / "packs"
        outcomes_dir = temp_dir / "outcomes"
        recommender = DeFiRecommender(packs_dir=packs_dir, outcomes_dir=outcomes_dir)
        recommender.pack_store.save_pack(new_pack)
        recommender.pack_store.save_pack(established_pack)

        # Run many recommendations - Thompson Sampling should sometimes pick new_pack
        # because the Beta(1,1) prior can sample high win rates, and the high
        # avg_return_pct (15%) normalizes to near 1.0
        query = StrategyQuery(token="USDC")

        new_pack_selected = 0
        for _ in range(50):  # More iterations for statistical significance
            recs = recommender.recommend(query, limit=1)
            if recs and recs[0].pack_id == new_pack.id:
                new_pack_selected += 1

        # With high avg_return_pct (15%) and Thompson Sampling exploring,
        # the new pack should be selected at least some of the time
        # (This is probabilistic but should happen reasonably often)
        assert new_pack_selected > 0, f"Thompson Sampling should explore new strategies, got {new_pack_selected}/50"

    def test_min_amount_filter(self, recommender, sample_pack_aave):
        """Test that min_amount_usd filter works."""
        recommender.pack_store.save_pack(sample_pack_aave)

        # Query with amount below minimum
        query = StrategyQuery(token="USDC", amount_usd=50)  # Min is 100
        recs = recommender.recommend(query)
        assert len(recs) == 0

        # Query with amount at minimum
        query = StrategyQuery(token="USDC", amount_usd=100)
        recs = recommender.recommend(query)
        assert len(recs) == 1

    def test_duration_days_in_query(self, recommender, sample_pack_aave):
        """Test that duration_days in query is accepted."""
        recommender.pack_store.save_pack(sample_pack_aave)

        query = StrategyQuery(token="USDC", duration_days=30)
        recs = recommender.recommend(query)
        # Duration is informational for now, not a filter
        assert len(recs) == 1
