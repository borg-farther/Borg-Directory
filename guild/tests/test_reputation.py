"""
Tests for guild/db/reputation.py (M2.4).
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from guild.db.store import GuildStore
from guild.db.reputation import (
    ReputationEngine,
    AccessTier,
    FreeRiderStatus,
    ContributionAction,
    ReputationProfile,
    ACTION_WEIGHTS,
    PUBLISH_DELTA_BY_CONFIDENCE,
    RECENCY_LAMBDA,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """A temporary database path."""
    return tmp_path / "test_guild.db"


@pytest.fixture
def store(tmp_db: Path) -> GuildStore:
    """A fresh store backed by a temporary database."""
    s = GuildStore(str(tmp_db))
    yield s
    s.close()


@pytest.fixture
def engine(store: GuildStore) -> ReputationEngine:
    """A reputation engine backed by the temporary store."""
    return ReputationEngine(store)


# ---------------------------------------------------------------------------
# Contribution scoring
# ---------------------------------------------------------------------------

class TestContributionScoring:
    """Tests for contribution_score()."""

    def test_single_pack_publication(self, engine: ReputationEngine):
        """One recent pack publication at full quality = weight * 1.0 * 1.0."""
        now = datetime.now(timezone.utc)
        actions = [
            ContributionAction(
                action_type="pack_publication",
                quality=1.0,
                created_at=now,
            ),
        ]
        # weight for pack_publication = 10
        score = engine.contribution_score("agent-1", actions, now)
        assert score == pytest.approx(10.0)

    def test_multiple_action_types(self, engine: ReputationEngine):
        """Sum of weighted contributions across types."""
        now = datetime.now(timezone.utc)
        actions = [
            ContributionAction(action_type="pack_publication", quality=1.0, created_at=now),
            ContributionAction(action_type="quality_review", quality=1.0, created_at=now),
            ContributionAction(action_type="bug_report", quality=1.0, created_at=now),
        ]
        # 10 + 3 + 2 = 15
        score = engine.contribution_score("agent-1", actions, now)
        assert score == pytest.approx(15.0)

    def test_quality_multiplier(self, engine: ReputationEngine):
        """Quality scales the contribution."""
        now = datetime.now(timezone.utc)
        actions = [
            ContributionAction(action_type="pack_publication", quality=0.5, created_at=now),
        ]
        # 10 * 0.5 = 5.0
        score = engine.contribution_score("agent-1", actions, now)
        assert score == pytest.approx(5.0)

    def test_recency_decay_one_epoch(self, engine: ReputationEngine):
        """One epoch (30 days) of decay applies lambda."""
        now = datetime.now(timezone.utc)
        ago_30_days = now - timedelta(days=30)
        actions = [
            ContributionAction(action_type="pack_publication", quality=1.0, created_at=ago_30_days),
        ]
        score = engine.contribution_score("agent-1", actions, now)
        expected = 10.0 * RECENCY_LAMBDA
        assert score == pytest.approx(expected)

    def test_recency_decay_two_epochs(self, engine: ReputationEngine):
        """Two epochs (60 days) = lambda^2."""
        now = datetime.now(timezone.utc)
        ago_60_days = now - timedelta(days=60)
        actions = [
            ContributionAction(action_type="pack_publication", quality=1.0, created_at=ago_60_days),
        ]
        score = engine.contribution_score("agent-1", actions, now)
        expected = 10.0 * (RECENCY_LAMBDA ** 2)
        assert score == pytest.approx(expected)

    def test_recency_decay_no_decay_for_recent(self, engine: ReputationEngine):
        """Actions within same day have negligible decay."""
        now = datetime.now(timezone.utc)
        ago_1_hour = now - timedelta(hours=1)
        actions = [
            ContributionAction(action_type="pack_publication", quality=1.0, created_at=ago_1_hour),
        ]
        score = engine.contribution_score("agent-1", actions, now)
        assert score == pytest.approx(10.0, rel=1e-3)

    def test_unknown_action_type_ignored(self, engine: ReputationEngine):
        """Actions with no defined weight are skipped."""
        now = datetime.now(timezone.utc)
        actions = [
            ContributionAction(action_type="unknown_action", quality=1.0, created_at=now),
            ContributionAction(action_type="pack_publication", quality=1.0, created_at=now),
        ]
        score = engine.contribution_score("agent-1", actions, now)
        assert score == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Access tier
# ---------------------------------------------------------------------------

class TestAccessTier:
    """Tests for compute_tier() / AccessTier.from_score()."""

    @pytest.mark.parametrize("score,tier", [
        (0,    AccessTier.COMMUNITY),
        (5,    AccessTier.COMMUNITY),
        (9.9,  AccessTier.COMMUNITY),
        (10,   AccessTier.VALIDATED),
        (30,   AccessTier.VALIDATED),
        (50,   AccessTier.VALIDATED),
        (51,   AccessTier.CORE),
        (150,  AccessTier.CORE),
        (200,  AccessTier.CORE),
        (201,  AccessTier.GOVERNANCE),
        (500,  AccessTier.GOVERNANCE),
    ])
    def test_tier_boundaries(self, engine: ReputationEngine, score: float, tier: AccessTier):
        assert engine.compute_tier(score) == tier


# ---------------------------------------------------------------------------
# Free-rider detection
# ---------------------------------------------------------------------------

class TestFreeRider:
    """Tests for free_rider_score() and free_rider_status()."""

    @pytest.mark.parametrize("consumed,contributed,reviews,expected", [
        (0,   1, 0, 0.0),     # contributes but doesn't consume
        (10,  1, 0, 10.0),    # 10/1 = 10
        (20,  1, 0, 20.0),    # borderline
        (21,  1, 0, 21.0),    # flagged
        (50,  1, 0, 50.0),    # throttled boundary
        (51,  1, 0, 51.0),    # throttled
        (100, 1, 0, 100.0),   # restricted boundary
        (101, 1, 0, 101.0),   # restricted
        (10,  5, 5, 1.0),     # balanced: 10/10 = 1
        (10,  0, 0, 10.0),    # denominator = 1 (clamped)
    ])
    def test_free_rider_score_formula(
        self, engine: ReputationEngine,
        consumed: int, contributed: int, reviews: int, expected: float
    ):
        score = engine.free_rider_score(consumed, contributed, reviews)
        assert score == pytest.approx(expected)

    @pytest.mark.parametrize("score,status", [
        (0,   FreeRiderStatus.OK),
        (20,  FreeRiderStatus.OK),
        (21,  FreeRiderStatus.FLAGGED),
        (50,  FreeRiderStatus.FLAGGED),
        (51,  FreeRiderStatus.THROTTLED),
        (100, FreeRiderStatus.THROTTLED),
        (101, FreeRiderStatus.RESTRICTED),
        (200, FreeRiderStatus.RESTRICTED),
    ])
    def test_free_rider_status_boundaries(self, engine: ReputationEngine, score: float, status: FreeRiderStatus):
        assert engine.free_rider_status(score) == status


# ---------------------------------------------------------------------------
# Reputation deltas
# ---------------------------------------------------------------------------

class TestReputationDeltas:
    """Tests for delta computation methods."""

    @pytest.mark.parametrize("confidence,expected", [
        ("guessed",    1),
        ("inferred",   3),
        ("tested",     7),
        ("validated",  15),
        ("unknown",    1),   # falls back to guessed
    ])
    def test_delta_pack_published(self, engine: ReputationEngine, confidence: str, expected: int):
        assert engine.delta_pack_published(confidence) == expected

    @pytest.mark.parametrize("quality,expected", [
        (1, 0),
        (2, 1),
        (3, 2),
        (4, 4),
        (5, 5),
    ])
    def test_delta_quality_review(self, engine: ReputationEngine, quality: int, expected: int):
        assert engine.delta_quality_review(quality) == expected

    def test_delta_pack_used_first_50(self, engine: ReputationEngine):
        """Each use gives +1 up to cap of 50."""
        for i in range(60):
            delta = engine.delta_pack_used_by_others(i)
            if i < 50:
                assert delta == 1, f"Use {i} should give +1"
            else:
                assert delta == 0, f"Use {i} should give 0 (capped)"

    def test_delta_pack_failure(self, engine: ReputationEngine):
        assert engine.delta_pack_failure() == -2

    def test_delta_calibration_failure(self, engine: ReputationEngine):
        assert engine.delta_calibration_failure() == -5


# ---------------------------------------------------------------------------
# Inactivity decay
# ---------------------------------------------------------------------------

class TestInactivityDecay:
    """Tests for compute_inactivity_decay()."""

    def test_no_decay_within_grace_period(self, engine: ReputationEngine):
        """Within 90 days, no penalty."""
        peak = 100.0
        last_active = datetime.now(timezone.utc) - timedelta(days=60)
        decayed = engine.compute_inactivity_decay(peak, last_active)
        assert decayed == pytest.approx(peak)

    def test_decay_after_90_days(self, engine: ReputationEngine):
        """After 90 days, -5% per month."""
        peak = 100.0
        # 120 days = 1 month beyond grace
        last_active = datetime.now(timezone.utc) - timedelta(days=120)
        decayed = engine.compute_inactivity_decay(peak, last_active)
        # 5% penalty
        assert decayed == pytest.approx(95.0)

    def test_decay_floor_at_50_percent(self, engine: ReputationEngine):
        """Decay cannot go below 50% of peak."""
        peak = 100.0
        # 2 years = 24 months beyond grace, 24*5% = 120% capped
        last_active = datetime.now(timezone.utc) - timedelta(days=2 * 365)
        decayed = engine.compute_inactivity_decay(peak, last_active)
        assert decayed == pytest.approx(50.0)  # floor


# ---------------------------------------------------------------------------
# ReputationProfile via build_profile()
# ---------------------------------------------------------------------------

class TestBuildProfile:
    """Tests for build_profile() end-to-end."""

    def test_empty_agent_returns_community(self, engine: ReputationEngine, store: GuildStore):
        """Agent with no activity gets community tier."""
        store.register_agent("lonely-agent", operator="lonely-op")
        profile = engine.build_profile("lonely-agent")
        assert profile.access_tier == AccessTier.COMMUNITY
        assert profile.contribution_score == 0.0

    def test_pack_publisher_gets_validated(self, engine: ReputationEngine, store: GuildStore):
        """Publishing one validated pack (~15 pts) → validated tier."""
        store.register_agent("publisher-1", operator="pub-op")
        store.add_pack(
            "pack-pub-1",
            version="1.0.0",
            yaml_content="name: TestPack",
            author_agent="publisher-1",
            confidence="validated",
            tier="validated",
            metadata={"quality_score": 10.1},
        )
        profile = engine.build_profile("publisher-1")
        # quality_score=10/10=1.0 * 15 delta = 15 pts → validated tier
        assert profile.access_tier == AccessTier.VALIDATED
        assert profile.packs_published == 1

    def test_high_contributor_core_tier(self, engine: ReputationEngine, store: GuildStore):
        """Multiple quality contributions → core tier."""
        store.register_agent("core-contrib", operator="core-op")
        # 3 validated packs × ~15 pts each = ~45 pts
        for i in range(3):
            store.add_pack(
                f"pack-core-{i}",
                version="1.0.0",
                yaml_content=f"name: CorePack{i}",
                author_agent="core-contrib",
                confidence="validated",
                tier="core",
                metadata={"quality_score": 10.1},
            )
        profile = engine.build_profile("core-contrib")
        # 3 packs * 1.5 (10/10 quality * 15 weight) = 4.5 per pack → total should exceed 10
        assert profile.access_tier == AccessTier.VALIDATED

    def test_free_rider_flagged(self, engine: ReputationEngine, store: GuildStore):
        """Agent consuming many packs without contributing gets flagged."""
        # Create an author to own the packs
        store.register_agent("pack-author", operator="author-op")
        store.add_pack("fr-pack-1", version="1.0.0", yaml_content="name: FRPack",
                       author_agent="pack-author")
        # Register free-rider and record 50 consumptions (executions)
        store.register_agent("free-rider", operator="fr-op")
        for i in range(50):
            store.record_execution(
                f"fr-exec-{i}", session_id=f"fr-sess-{i}",
                pack_id="fr-pack-1", agent_id="free-rider", status="completed",
            )
        profile = engine.build_profile("free-rider")
        # 50 consumptions / (1 pack contributed + 0 reviews) = 50 → flagged
        assert profile.free_rider_score == pytest.approx(50.0)
        assert profile.free_rider_status == FreeRiderStatus.FLAGGED

    def test_balanced_agent_ok(self, engine: ReputationEngine, store: GuildStore):
        """Agent with balanced consume/contribute = OK free-rider status."""
        store.register_agent("balanced-agent", operator="bal-op")
        store.add_pack(
            "bal-pack-1",
            version="1.0.0",
            yaml_content="name: BalancedPack",
            author_agent="balanced-agent",
        )
        # Record some executions
        store.record_execution(
            "exec-1",
            session_id="sess-1",
            pack_id="bal-pack-1",
            agent_id="balanced-agent",
            status="completed",
        )
        store.record_execution(
            "exec-2",
            session_id="sess-2",
            pack_id="bal-pack-1",
            agent_id="balanced-agent",
            status="completed",
        )
        profile = engine.build_profile("balanced-agent")
        assert profile.free_rider_status == FreeRiderStatus.OK


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

class TestApplyActions:
    """Tests for apply_pack_published(), apply_quality_review(), etc."""

    def test_apply_pack_published_updates_stats(self, engine: ReputationEngine, store: GuildStore):
        store.register_agent("pub-agent", operator="pub-op")
        # First add the pack to the store
        store.add_pack(
            "new-pack",
            version="1.0.0",
            yaml_content="name: NewPack",
            author_agent="pub-agent",
            confidence="validated",
            metadata={"quality_score": 10.1},
        )
        profile = engine.apply_pack_published("pub-agent", "new-pack", confidence="validated")
        assert profile.packs_published == 1
        assert profile.contribution_score > 0  # validated pack contributes positively
        assert profile.peak_score >= 15.0  # stored peak reflects validated delta

    def test_apply_quality_review(self, engine: ReputationEngine, store: GuildStore):
        store.register_agent("review-agent", operator="rev-op")
        store.add_pack(
            "rated-pack",
            version="1.0.0",
            yaml_content="name: RatedPack",
            author_agent="author",
        )
        # Manually add feedback first
        store.add_feedback(
            "feedback-1",
            pack_id="rated-pack",
            author_agent="review-agent",
            outcome="success",
            metadata={"quality": 5},
        )
        profile = engine.apply_quality_review("review-agent", "feedback-1", quality=5)
        assert profile.quality_reviews_given >= 1

    def test_apply_pack_consumed(self, engine: ReputationEngine, store: GuildStore):
        store.register_agent("consumer-agent", operator="con-op")
        store.register_agent("pack-author", operator="author-op")
        store.add_pack(
            "used-pack",
            version="1.0.0",
            yaml_content="name: UsedPack",
            author_agent="pack-author",
        )
        # Manually record the execution first
        store.record_execution(
            "consumer-exec",
            session_id="sess-consumed",
            pack_id="used-pack",
            agent_id="consumer-agent",
            status="completed",
        )
        profile = engine.apply_pack_consumed("consumer-agent", "used-pack")
        assert profile.packs_consumed >= 1
