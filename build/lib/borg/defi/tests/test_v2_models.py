"""Borg DeFi V2 — Tests for data models."""

import pytest
from datetime import datetime, timedelta
from borg.defi.v2.models import (
    StrategyQuery,
    StrategyRecommendation,
    ExecutionOutcome,
    CollectiveStats,
    DeFiStrategyPack,
    EntryCriteria,
    ActionSpec,
    RiskAssessment,
    AgentReputation,
)


class TestEntryCriteria:
    """Tests for EntryCriteria dataclass."""

    def test_default_constructor(self):
        ec = EntryCriteria(tokens=["USDC"], chains=["base"])
        assert ec.tokens == ["USDC"]
        assert ec.chains == ["base"]
        assert ec.min_amount_usd == 0
        assert ec.risk_tolerance == ["low", "medium"]

    def test_full_constructor(self):
        ec = EntryCriteria(
            tokens=["USDC", "USDT"],
            chains=["ethereum", "base"],
            min_amount_usd=100,
            risk_tolerance=["low"],
        )
        assert ec.tokens == ["USDC", "USDT"]
        assert ec.chains == ["ethereum", "base"]
        assert ec.min_amount_usd == 100
        assert ec.risk_tolerance == ["low"]


class TestActionSpec:
    """Tests for ActionSpec dataclass."""

    def test_default_constructor(self):
        action = ActionSpec(type="lend", protocol="aave-v3")
        assert action.type == "lend"
        assert action.protocol == "aave-v3"
        assert action.steps == []

    def test_with_steps(self):
        action = ActionSpec(
            type="lend",
            protocol="aave-v3",
            steps=["Supply USDC to Aave V3", "Monitor health factor"],
        )
        assert len(action.steps) == 2
        assert "Supply USDC" in action.steps[0]


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_default_constructor(self):
        risk = RiskAssessment()
        assert risk.il_risk is False
        assert risk.rug_score == 0.0
        assert risk.protocol_age_days == 0
        assert risk.audit_status == ""

    def test_full_constructor(self):
        risk = RiskAssessment(
            il_risk=True,
            rug_score=0.2,
            protocol_age_days=365,
            audit_status="multiple audits",
        )
        assert risk.il_risk is True
        assert risk.rug_score == 0.2
        assert risk.protocol_age_days == 365
        assert "audits" in risk.audit_status


class TestCollectiveStats:
    """Tests for CollectiveStats dataclass."""

    def test_default_constructor(self):
        stats = CollectiveStats()
        assert stats.total_outcomes == 0
        assert stats.profitable == 0
        assert stats.alpha == 1.0
        assert stats.beta == 1.0
        assert stats.reputation == 0.5  # 1/(1+1)

    def test_reputation_calculation(self):
        stats = CollectiveStats(alpha=12, beta=2)
        assert abs(stats.reputation - 0.857) < 0.001  # 12/(12+2)

    def test_empty_reputation(self):
        stats = CollectiveStats(alpha=0, beta=0)
        assert stats.reputation == 0.0

    def test_last_5_returns_default(self):
        stats = CollectiveStats()
        assert stats.last_5_returns == []

    def test_loss_patterns_default(self):
        stats = CollectiveStats()
        assert stats.loss_patterns == []


class TestDeFiStrategyPack:
    """Tests for DeFiStrategyPack dataclass."""

    def test_default_constructor(self):
        pack = DeFiStrategyPack(id="test/pack", name="Test Pack")
        assert pack.id == "test/pack"
        assert pack.name == "Test Pack"
        assert pack.version == 1
        assert pack.entry is None
        assert pack.action is None
        assert pack.collective is None

    def test_full_constructor(self):
        entry = EntryCriteria(tokens=["USDC"], chains=["base"], min_amount_usd=100)
        action = ActionSpec(type="lend", protocol="aave-v3", steps=["Step 1"])
        collective = CollectiveStats(total_outcomes=10, profitable=8)
        risk = RiskAssessment(il_risk=False)

        pack = DeFiStrategyPack(
            id="yield/aave-usdc-base",
            name="Aave V3 USDC",
            version=3,
            entry=entry,
            action=action,
            exit_guidance="No lock period",
            collective=collective,
            risk=risk,
        )

        assert pack.id == "yield/aave-usdc-base"
        assert pack.name == "Aave V3 USDC"
        assert pack.version == 3
        assert pack.entry.tokens == ["USDC"]
        assert pack.action.type == "lend"
        assert pack.collective.total_outcomes == 10
        assert pack.risk.il_risk is False

    def test_to_dict(self):
        pack = DeFiStrategyPack(
            id="test/pack",
            name="Test",
            entry=EntryCriteria(tokens=["USDC"], chains=["base"]),
            action=ActionSpec(type="lend", protocol="aave"),
        )
        d = pack.to_dict()
        assert d["id"] == "test/pack"
        assert d["entry"]["tokens"] == ["USDC"]
        assert d["action"]["protocol"] == "aave"
        assert "collective" in d
        assert "risk" in d

    def test_from_dict(self):
        data = {
            "id": "test/pack",
            "name": "Test Pack",
            "version": 2,
            "entry": {
                "tokens": ["USDC", "ETH"],
                "chains": ["base", "ethereum"],
                "min_amount_usd": 50,
                "risk_tolerance": ["medium", "high"],
            },
            "action": {
                "type": "lp",
                "protocol": "kamino",
                "steps": ["Add liquidity"],
            },
            "exit": "Anytime",
            "collective": {
                "total_outcomes": 15,
                "profitable": 12,
                "alpha": 13,
                "beta": 4,
                "avg_return_pct": 4.5,
            },
            "risk": {
                "il_risk": True,
                "rug_score": 0.1,
            },
            "updated_at": "2026-03-30T10:00:00",
        }
        pack = DeFiStrategyPack.from_dict(data)
        assert pack.id == "test/pack"
        assert pack.name == "Test Pack"
        assert pack.version == 2
        assert pack.entry.tokens == ["USDC", "ETH"]
        assert pack.action.type == "lp"
        assert pack.collective.total_outcomes == 15
        assert pack.collective.alpha == 13
        assert pack.risk.il_risk is True

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = DeFiStrategyPack(
            id="yield/test",
            name="Test Strategy",
            version=5,
            entry=EntryCriteria(
                tokens=["SOL"],
                chains=["solana"],
                min_amount_usd=100,
                risk_tolerance=["high"],
            ),
            action=ActionSpec(
                type="stake",
                protocol="marinade",
                steps=["Stake SOL", "Earn APY"],
            ),
            exit_guidance="Unstake anytime",
            collective=CollectiveStats(
                total_outcomes=20,
                profitable=18,
                alpha=19,
                beta=3,
                avg_return_pct=6.2,
                median_return_pct=6.0,
                std_dev=1.5,
                min_return_pct=2.0,
                max_return_pct=8.5,
                avg_duration_days=30.0,
                last_5_returns=[5.5, 6.0, 6.5, 5.8, 6.2],
                trend="stable",
            ),
            risk=RiskAssessment(
                il_risk=False,
                rug_score=0.05,
                protocol_age_days=730,
                audit_status="verified",
            ),
            updated_at=datetime(2026, 3, 30, 12, 0, 0),
            created_at=datetime(2026, 1, 1, 0, 0, 0),
        )

        # Convert to dict and back
        d = original.to_dict()
        restored = DeFiStrategyPack.from_dict(d)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.entry.tokens == original.entry.tokens
        assert restored.action.protocol == original.action.protocol
        assert restored.collective.total_outcomes == original.collective.total_outcomes
        assert restored.risk.il_risk == original.risk.il_risk

    def test_from_dict_minimal(self):
        """Test from_dict with minimal data."""
        data = {"id": "minimal", "name": "Minimal Pack"}
        pack = DeFiStrategyPack.from_dict(data)
        assert pack.id == "minimal"
        assert pack.name == "Minimal Pack"
        assert pack.version == 1
        assert pack.entry is None


class TestStrategyQuery:
    """Tests for StrategyQuery dataclass."""

    def test_default_constructor(self):
        query = StrategyQuery(token="USDC")
        assert query.token == "USDC"
        assert query.chain is None
        assert query.amount_usd == 0
        assert query.risk_tolerance == "medium"
        assert query.duration_days is None

    def test_full_constructor(self):
        query = StrategyQuery(
            token="ETH",
            chain="ethereum",
            amount_usd=1000,
            risk_tolerance="high",
            duration_days=30,
        )
        assert query.token == "ETH"
        assert query.chain == "ethereum"
        assert query.amount_usd == 1000
        assert query.risk_tolerance == "high"
        assert query.duration_days == 30


class TestStrategyRecommendation:
    """Tests for StrategyRecommendation dataclass."""

    def test_default_constructor(self):
        rec = StrategyRecommendation(pack_id="test/pack")
        assert rec.pack_id == "test/pack"
        assert rec.rank == 0
        assert rec.confidence == 0.0
        assert rec.rug_warnings == []

    def test_full_constructor(self):
        rec = StrategyRecommendation(
            pack_id="yield/aave-usdc",
            rank=1,
            agent_count=12,
            profitable_count=11,
            avg_return_pct=4.2,
            median_return_pct=4.0,
            avg_duration_days=30.0,
            protocol="aave-v3",
            action_type="lend",
            confidence=0.85,
            il_risk=False,
            exit_guidance="No lock",
            rug_warnings=["Warning 1"],
            trend="stable",
            reputation=0.92,
            confidence_interval=(0.62, 0.98),
        )
        assert rec.rank == 1
        assert rec.agent_count == 12
        assert rec.profitable_count == 11
        assert rec.avg_return_pct == 4.2
        assert rec.confidence == 0.85
        assert len(rec.rug_warnings) == 1


class TestExecutionOutcome:
    """Tests for ExecutionOutcome dataclass."""

    def test_default_constructor(self):
        outcome = ExecutionOutcome(
            outcome_id="out-001",
            pack_id="test/pack",
            agent_id="agent-001",
            entered_at=datetime.now(),
        )
        assert outcome.outcome_id == "out-001"
        assert outcome.pack_id == "test/pack"
        assert outcome.duration_days == 0.0
        assert outcome.profitable is False
        assert outcome.lessons == []

    def test_full_constructor(self):
        entered = datetime(2026, 3, 1)
        exited = datetime(2026, 3, 30)
        outcome = ExecutionOutcome(
            outcome_id="out-002",
            pack_id="yield/aave-usdc",
            agent_id="agent-002",
            entered_at=entered,
            exited_at=exited,
            duration_days=29.0,
            return_pct=3.8,
            profitable=True,
            lessons=["Steady yield", "No issues"],
            verification_tx_hash="0xabc123",
            chain="base",
        )
        assert outcome.duration_days == 29.0
        assert outcome.return_pct == 3.8
        assert outcome.profitable is True
        assert len(outcome.lessons) == 2
        assert outcome.verification_tx_hash == "0xabc123"

    def test_to_dict(self):
        entered = datetime(2026, 3, 1, 8, 0, 0)
        outcome = ExecutionOutcome(
            outcome_id="out-003",
            pack_id="test",
            agent_id="agent",
            entered_at=entered,
            return_pct=5.0,
            profitable=True,
        )
        d = outcome.to_dict()
        assert d["outcome_id"] == "out-003"
        assert d["execution"]["return_pct"] == 5.0
        assert d["execution"]["profitable"] is True

    def test_from_dict(self):
        data = {
            "outcome_id": "out-004",
            "pack_id": "yield/test",
            "agent_id": "agent-004",
            "execution": {
                "entered_at": "2026-03-01T08:00:00",
                "exited_at": "2026-03-30T08:00:00",
                "duration_days": 29,
                "return_pct": 4.5,
                "profitable": True,
            },
            "lessons": ["Lesson 1"],
            "verification": {
                "tx_hash_enter": "0xdef",
                "chain": "ethereum",
            },
        }
        outcome = ExecutionOutcome.from_dict(data)
        assert outcome.outcome_id == "out-004"
        assert outcome.pack_id == "yield/test"
        assert outcome.duration_days == 29
        assert outcome.profitable is True
        assert outcome.verification_tx_hash == "0xdef"

    def test_roundtrip(self):
        """Test that to_dict -> from_dict preserves data."""
        original = ExecutionOutcome(
            outcome_id="out-roundtrip",
            pack_id="yield/aave-usdc-base",
            agent_id="agent-abc",
            entered_at=datetime(2026, 3, 1, 8, 0, 0),
            exited_at=datetime(2026, 3, 30, 8, 0, 0),
            duration_days=29.0,
            return_pct=4.2,
            profitable=True,
            lessons=["Steady 4% APY", "Good experience"],
            verification_tx_hash="0x123abc",
            chain="base",
        )

        d = original.to_dict()
        restored = ExecutionOutcome.from_dict(d)

        assert restored.outcome_id == original.outcome_id
        assert restored.pack_id == original.pack_id
        assert restored.agent_id == original.agent_id
        assert restored.duration_days == original.duration_days
        assert restored.return_pct == original.return_pct
        assert restored.profitable == original.profitable
        assert restored.lessons == original.lessons
        assert restored.verification_tx_hash == original.verification_tx_hash

    def test_from_dict_no_verification(self):
        """Test from_dict when no verification data present."""
        data = {
            "outcome_id": "out-005",
            "pack_id": "test",
            "agent_id": "agent",
            "execution": {
                "entered_at": "2026-03-01",
                "duration_days": 10,
                "return_pct": 1.0,
                "profitable": True,
            },
            "lessons": [],
        }
        outcome = ExecutionOutcome.from_dict(data)
        assert outcome.verification_tx_hash is None
        assert outcome.chain is None


class TestAgentReputation:
    """Tests for AgentReputation dataclass."""

    def test_default_constructor(self):
        rep = AgentReputation(agent_id="agent-001")
        assert rep.agent_id == "agent-001"
        assert rep.outcomes_submitted == 0
        assert rep.outcomes_verified == 0
        assert rep.accuracy_score == 0.0
        assert rep.trust_tier == "observer"
        assert rep.influence_weight == 1.0
        assert rep.vouched_by == []
        assert rep.vouches_for == []

    def test_full_constructor(self):
        rep = AgentReputation(
            agent_id="agent-002",
            outcomes_submitted=50,
            outcomes_verified=30,
            accuracy_score=0.87,
            trust_tier="trusted",
            influence_weight=1.5,
            vouched_by=["agent-001", "agent-003"],
            vouches_for=["agent-004"],
        )
        assert rep.outcomes_submitted == 50
        assert rep.outcomes_verified == 30
        assert rep.accuracy_score == 0.87
        assert rep.trust_tier == "trusted"
        assert rep.influence_weight == 1.5
        assert len(rep.vouched_by) == 2

    def test_to_dict(self):
        rep = AgentReputation(
            agent_id="agent-test",
            outcomes_submitted=10,
            trust_tier="contributor",
        )
        d = rep.to_dict()
        assert d["agent_id"] == "agent-test"
        assert d["outcomes_submitted"] == 10
        assert d["trust_tier"] == "contributor"

    def test_from_dict(self):
        data = {
            "agent_id": "agent-010",
            "outcomes_submitted": 25,
            "outcomes_verified": 15,
            "accuracy_score": 0.82,
            "trust_tier": "trusted",
            "influence_weight": 1.5,
            "vouched_by": ["agent-001"],
            "vouches_for": [],
        }
        rep = AgentReputation.from_dict(data)
        assert rep.agent_id == "agent-010"
        assert rep.outcomes_submitted == 25
        assert rep.accuracy_score == 0.82
        assert rep.trust_tier == "trusted"

    def test_roundtrip(self):
        """Test to_dict -> from_dict preserves data."""
        original = AgentReputation(
            agent_id="agent-full",
            outcomes_submitted=100,
            outcomes_verified=75,
            accuracy_score=0.91,
            trust_tier="authority",
            influence_weight=2.0,
            vouched_by=["agent-1", "agent-2", "agent-3"],
            vouches_for=["agent-4", "agent-5"],
        )

        d = original.to_dict()
        restored = AgentReputation.from_dict(d)

        assert restored.agent_id == original.agent_id
        assert restored.outcomes_submitted == original.outcomes_submitted
        assert restored.outcomes_verified == original.outcomes_verified
        assert restored.accuracy_score == original.accuracy_score
        assert restored.trust_tier == original.trust_tier
        assert restored.influence_weight == original.influence_weight
        assert restored.vouched_by == original.vouched_by
        assert restored.vouches_for == original.vouches_for
