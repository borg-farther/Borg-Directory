"""
Tests for guild/db/analytics.py (M2.5).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from borg.db.store import AgentStore
from borg.db.analytics import (
    AnalyticsEngine,
    PackUsageStats,
    AdoptionMetrics,
    EcosystemHealth,
    TimeSeriesResult,
    TimeSeriesPoint,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test_guild_analytics.db"


@pytest.fixture
def store(tmp_db: Path) -> AgentStore:
    s = AgentStore(str(tmp_db))
    yield s
    s.close()


@pytest.fixture
def analytics(store: AgentStore) -> AnalyticsEngine:
    return AnalyticsEngine(store)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def backdate_row(db_path: Path, table: str, pk_col: str, pk_val: str, ts_col: str, ts_val: str):
    """Backdate a row's timestamp column."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(f"UPDATE {table} SET {ts_col} = ? WHERE {pk_col} = ?", (ts_val, pk_val))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Pack usage stats
# ---------------------------------------------------------------------------

class TestPackUsageStats:
    """Tests for pack_usage_stats()."""

    def test_no_executions(self, analytics: AnalyticsEngine, store: AgentStore):
        """Pack with no executions → all zeros."""
        store.register_agent("isolated-agent", operator="iso-op")
        store.add_pack(
            "pack-isolated", version="1.0.0",
            yaml_content="name: IsolatedPack",
            author_agent="isolated-agent",
        )
        stats = analytics.pack_usage_stats("pack-isolated")
        assert stats.pull_count == 0
        assert stats.apply_count == 0
        assert stats.completion_rate == 0.0

    def test_executions_counted(self, analytics: AnalyticsEngine, store: AgentStore, tmp_db: Path):
        """Executions are counted correctly."""
        store.register_agent("pop-agent", operator="pop-op")
        store.add_pack(
            "pack-popular", version="1.0.0",
            yaml_content="name: PopularPack",
            author_agent="pop-agent",
        )
        for i in range(5):
            store.record_execution(
                f"exec-{i}",
                session_id=f"sess-{i}",
                pack_id="pack-popular",
                agent_id="pop-agent",
                status="completed",
            )
        stats = analytics.pack_usage_stats("pack-popular")
        assert stats.pull_count == 5
        assert stats.success_count == 5
        assert stats.failure_count == 0
        assert stats.completion_rate == 1.0

    def test_mixed_success_failure(self, analytics: AnalyticsEngine, store: AgentStore):
        """Mixed completed/failed → correct completion rate."""
        store.register_agent("flaky-agent", operator="flaky-op")
        store.add_pack(
            "pack-flaky", version="1.0.0",
            yaml_content="name: FlakyPack",
            author_agent="flaky-agent",
        )
        for i in range(6):
            status = "completed" if i < 4 else "failed"
            store.record_execution(
                f"exec-{i}",
                session_id=f"sess-{i}",
                pack_id="pack-flaky",
                agent_id="flaky-agent",
                status=status,
            )
        stats = analytics.pack_usage_stats("pack-flaky")
        assert stats.success_count == 4
        assert stats.failure_count == 2
        assert stats.completion_rate == pytest.approx(4 / 6)

    def test_all_failed(self, analytics: AnalyticsEngine, store: AgentStore):
        """All failures → completion_rate = 0 (not NaN)."""
        store.register_agent("broken-agent", operator="broken-op")
        store.add_pack(
            "pack-broken", version="1.0.0",
            yaml_content="name: BrokenPack",
            author_agent="broken-agent",
        )
        for i in range(3):
            store.record_execution(
                f"exec-{i}",
                session_id=f"sess-{i}",
                pack_id="pack-broken",
                agent_id="broken-agent",
                status="failed",
            )
        stats = analytics.pack_usage_stats("pack-broken")
        assert stats.completion_rate == 0.0

    def test_nonexistent_pack(self, analytics: AnalyticsEngine):
        """Non-existent pack returns zero stats."""
        stats = analytics.pack_usage_stats("does-not-exist")
        assert stats.pull_count == 0
        assert stats.completion_rate == 0.0


# ---------------------------------------------------------------------------
# Adoption metrics
# ---------------------------------------------------------------------------

class TestAdoptionMetrics:
    """Tests for adoption_metrics() and ecosystem_adoption()."""

    def test_unique_operators(self, analytics: AnalyticsEngine, store: AgentStore):
        """Same agent counted once per pack."""
        store.register_agent("collab-agent", operator="collab-op")
        store.add_pack(
            "pack-collab", version="1.0.0",
            yaml_content="name: CollabPack",
            author_agent="collab-agent",
        )
        for i in range(5):
            store.record_execution(
                f"exec-collab-{i}",
                session_id=f"sess-collab-{i}",
                pack_id="pack-collab",
                agent_id="collab-agent",
                status="completed",
            )
        metrics = analytics.adoption_metrics("pack-collab")
        assert metrics.unique_operators == 1

    def test_multiple_operators(self, analytics: AnalyticsEngine, store: AgentStore):
        """Multiple distinct agents."""
        for i in range(5):
            store.register_agent(f"agent-{i}", operator=f"op-{i}")
        store.add_pack(
            "pack-social", version="1.0.0",
            yaml_content="name: SocialPack",
            author_agent="agent-0",
        )
        for i in range(5):
            store.record_execution(
                f"exec-{i}",
                session_id=f"sess-{i}",
                pack_id="pack-social",
                agent_id=f"agent-{i}",
                status="completed",
            )
        metrics = analytics.adoption_metrics("pack-social")
        assert metrics.unique_operators == 5

    def test_unique_agents_via_feedback(self, analytics: AnalyticsEngine, store: AgentStore):
        """Feedback authors counted as unique agents."""
        store.register_agent("pack-author", operator="pa-op")
        store.register_agent("reviewer-1", operator="r1-op")
        store.register_agent("reviewer-2", operator="r2-op")
        store.add_pack(
            "pack-reviewed", version="1.0.0",
            yaml_content="name: ReviewedPack",
            author_agent="pack-author",
        )
        store.add_feedback(
            "fb-1",
            pack_id="pack-reviewed",
            author_agent="reviewer-1",
            outcome="success",
        )
        store.add_feedback(
            "fb-2",
            pack_id="pack-reviewed",
            author_agent="reviewer-2",
            outcome="success",
        )
        metrics = analytics.adoption_metrics("pack-reviewed")
        assert metrics.unique_agents == 2

    def test_ecosystem_adoption(self, analytics: AnalyticsEngine, store: AgentStore):
        """Aggregate across all packs."""
        store.register_agent("x-agent", operator="x-op")
        store.register_agent("y-agent", operator="y-op")
        store.add_pack(
            "pack-a", version="1.0.0",
            yaml_content="name: PackA",
            author_agent="x-agent",
        )
        store.add_pack(
            "pack-b", version="1.0.0",
            yaml_content="name: PackB",
            author_agent="y-agent",
        )
        store.record_execution(
            "exec-1", session_id="s1",
            pack_id="pack-a", agent_id="x-agent", status="completed",
        )
        store.record_execution(
            "exec-2", session_id="s2",
            pack_id="pack-b", agent_id="y-agent", status="completed",
        )
        store.record_execution(
            "exec-3", session_id="s3",
            pack_id="pack-b", agent_id="x-agent", status="completed",
        )
        metrics = analytics.ecosystem_adoption()
        assert metrics.unique_operators == 2  # x-agent and y-agent


# ---------------------------------------------------------------------------
# Ecosystem health
# ---------------------------------------------------------------------------

class TestEcosystemHealth:
    """Tests for ecosystem_health()."""

    def test_empty_ecosystem(self, analytics: AnalyticsEngine):
        """No data → zeros / empty."""
        health = analytics.ecosystem_health()
        assert health.total_agents == 0
        assert health.total_packs == 0
        assert health.contributor_ratio == 0.0

    def test_total_agents_counted(self, analytics: AnalyticsEngine, store: AgentStore):
        """Agents who authored or operated are counted."""
        store.register_agent("author-agent", operator="auth-op")
        store.register_agent("operator-agent", operator="op-op")
        store.add_pack(
            "pack-auth", version="1.0.0",
            yaml_content="name: AuthPack",
            author_agent="author-agent",
        )
        store.record_execution(
            "exec-1", session_id="s1",
            pack_id="pack-auth", agent_id="operator-agent", status="completed",
        )
        health = analytics.ecosystem_health()
        assert health.total_agents == 2

    def test_tier_distribution(self, analytics: AnalyticsEngine, store: AgentStore):
        """Tiers are counted correctly."""
        store.register_agent("tier-agent", operator="tier-op")
        store.add_pack("pack-comm", version="1.0.0", yaml_content="name: C", author_agent="tier-agent", tier="community")
        store.add_pack("pack-val", version="1.0.0", yaml_content="name: V", author_agent="tier-agent", tier="validated")
        store.add_pack("pack-core", version="1.0.0", yaml_content="name: Co", author_agent="tier-agent", tier="core")
        health = analytics.ecosystem_health()
        assert health.tier_distribution["community"] == 1
        assert health.tier_distribution["validated"] == 1
        assert health.tier_distribution["core"] == 1

    def test_avg_quality_score(self, analytics: AnalyticsEngine, store: AgentStore):
        """Average quality score across packs (from metadata)."""
        store.register_agent("q-agent", operator="q-op")
        store.add_pack(
            "pack-q1", version="1.0.0",
            yaml_content="name: Q1Pack",
            author_agent="q-agent",
            metadata={"quality_score": 8.0},
        )
        store.add_pack(
            "pack-q2", version="1.0.0",
            yaml_content="name: Q2Pack",
            author_agent="q-agent",
            metadata={"quality_score": 4.0},
        )
        health = analytics.ecosystem_health()
        assert health.avg_quality_score == pytest.approx(6.0)

    def test_active_contributors_recent(self, analytics: AnalyticsEngine, store: AgentStore):
        """Contributors active in last 90 days are counted."""
        store.register_agent("active-author", operator="aa-op")
        store.add_pack(
            "pack-active", version="1.0.0",
            yaml_content="name: ActivePack",
            author_agent="active-author",
        )
        health = analytics.ecosystem_health()
        assert health.active_contributors >= 1

    def test_domain_coverage(self, analytics: AnalyticsEngine, store: AgentStore):
        """Domain coverage mirrors tier distribution when no domain set."""
        store.register_agent("dc-agent", operator="dc-op")
        store.add_pack(
            "pack-c1", version="1.0.0",
            yaml_content="name: C1",
            author_agent="dc-agent",
            tier="community",
        )
        store.add_pack(
            "pack-c2", version="1.0.0",
            yaml_content="name: C2",
            author_agent="dc-agent",
            tier="community",
        )
        health = analytics.ecosystem_health()
        assert health.domain_coverage["community"] == 2


# ---------------------------------------------------------------------------
# Time-series aggregations
# ---------------------------------------------------------------------------

class TestTimeSeries:
    """Tests for timeseries_*() methods."""

    def test_timeseries_pack_publishes_daily(self, analytics: AnalyticsEngine, store: AgentStore, tmp_db: Path):
        """Daily publishing counts per day."""
        store.register_agent("pub-agent", operator="pub-op")
        now = datetime.now(timezone.utc)
        # Create packs today and 10 days ago
        for i, days_offset in enumerate([0, 0, 0, 10]):
            past = now - timedelta(days=days_offset)
            pack_id = f"pack-d{days_offset}-{i}"
            store.add_pack(
                pack_id, version="1.0.0",
                yaml_content=f"name: {pack_id}",
                author_agent="pub-agent",
            )
            backdate_row(tmp_db, "packs", "id", pack_id, "created_at", past.isoformat())

        ts = analytics.timeseries_pack_publishes(period="daily", days=30)
        assert ts.metric == "pack_publishes"
        assert ts.period == "daily"
        assert len(ts.points) >= 2  # at least 2 distinct days
        today_key = now.strftime("%Y-%m-%d")
        today_point = next((p for p in ts.points if p.timestamp == today_key), None)
        if today_point:
            assert today_point.value == 3.0

    def test_timeseries_executions_daily(self, analytics: AnalyticsEngine, store: AgentStore, tmp_db: Path):
        """Daily execution counts."""
        store.register_agent("exec-agent", operator="exec-op")
        store.add_pack(
            "pack-exec", version="1.0.0",
            yaml_content="name: ExecPack",
            author_agent="exec-agent",
        )
        now = datetime.now(timezone.utc)
        for i, hours_offset in enumerate([0, 0, 24, 48]):
            past = now - timedelta(hours=hours_offset)
            exec_id = f"exec-h{hours_offset}-{i}"
            store.record_execution(
                exec_id,
                session_id=f"sess-{i}",
                pack_id="pack-exec",
                agent_id="exec-agent",
                status="completed",
            )
            backdate_row(tmp_db, "executions", "id", exec_id, "started_at", past.isoformat())

        ts = analytics.timeseries_executions(period="daily", days=30)
        assert ts.metric == "executions"
        assert len(ts.points) >= 2

    def test_timeseries_quality_scores(self, analytics: AnalyticsEngine, store: AgentStore):
        """Average quality score per period."""
        store.register_agent("qs-agent", operator="qs-op")
        store.add_pack(
            "pack-qs-a", version="1.0.0",
            yaml_content="name: QsA",
            author_agent="qs-agent",
            metadata={"quality_score": 10.0},
        )
        store.add_pack(
            "pack-qs-b", version="1.0.0",
            yaml_content="name: QsB",
            author_agent="qs-agent",
            metadata={"quality_score": 5.0},
        )
        ts = analytics.timeseries_quality_scores(period="daily", days=30)
        assert ts.metric == "avg_quality_score"
        assert len(ts.points) >= 1

    def test_timeseries_active_agents(self, analytics: AnalyticsEngine, store: AgentStore):
        """Unique active agents per day."""
        store.register_agent("act-agent", operator="act-op")
        store.add_pack(
            "pack-act", version="1.0.0",
            yaml_content="name: ActPack",
            author_agent="act-agent",
        )
        for i in range(3):
            store.record_execution(
                f"exec-act-{i}",
                session_id=f"sact-{i}",
                pack_id="pack-act",
                agent_id="act-agent",
                status="completed",
            )
        ts = analytics.timeseries_active_agents(period="daily", days=30)
        assert ts.metric == "active_agents"
        assert len(ts.points) >= 1

    def test_timeseries_weekly(self, analytics: AnalyticsEngine, store: AgentStore, tmp_db: Path):
        """Weekly aggregation works."""
        store.register_agent("w-agent", operator="w-op")
        now = datetime.now(timezone.utc)
        for i, days_offset in enumerate([0, 7, 14]):
            past = now - timedelta(days=days_offset)
            pack_id = f"pack-w{days_offset}-{i}"
            store.add_pack(pack_id, version="1.0.0", yaml_content=f"name: {pack_id}", author_agent="w-agent")
            backdate_row(tmp_db, "packs", "id", pack_id, "created_at", past.isoformat())
        ts = analytics.timeseries_pack_publishes(period="weekly", days=60)
        assert ts.period == "weekly"
        assert len(ts.points) >= 1

    def test_timeseries_monthly(self, analytics: AnalyticsEngine, store: AgentStore, tmp_db: Path):
        """Monthly aggregation works."""
        store.register_agent("m-agent", operator="m-op")
        now = datetime.now(timezone.utc)
        for i, days_offset in enumerate([0, 30, 60]):
            past = now - timedelta(days=days_offset)
            pack_id = f"pack-m{days_offset}-{i}"
            store.add_pack(pack_id, version="1.0.0", yaml_content=f"name: {pack_id}", author_agent="m-agent")
            backdate_row(tmp_db, "packs", "id", pack_id, "created_at", past.isoformat())
        ts = analytics.timeseries_pack_publishes(period="monthly", days=180)
        assert ts.period == "monthly"
        assert len(ts.points) >= 1

    def test_timeseries_generic_interface(self, analytics: AnalyticsEngine, store: AgentStore):
        """timeseries() routes to correct method."""
        store.register_agent("g-agent", operator="g-op")
        store.add_pack(
            "pack-g", version="1.0.0",
            yaml_content="name: GPack",
            author_agent="g-agent",
        )
        store.record_execution(
            "exec-g", session_id="sg",
            pack_id="pack-g", agent_id="g-agent", status="completed",
        )
        result = analytics.timeseries("executions", period="daily", days=30)
        assert isinstance(result, TimeSeriesResult)
        assert result.metric == "executions"

    def test_timeseries_unknown_metric(self, analytics: AnalyticsEngine):
        """Unknown metric returns empty result."""
        result = analytics.timeseries("unknown_metric", period="daily", days=30)
        assert result.points == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestAnalyticsEdgeCases:
    """Edge cases and error handling."""

    def test_all_pack_usage_stats_empty(self, analytics: AnalyticsEngine):
        """all_pack_usage_stats on empty store returns empty list."""
        result = analytics.all_pack_usage_stats()
        assert result == []

    def test_timeseries_empty_store(self, analytics: AnalyticsEngine):
        """Time series on empty store returns empty points."""
        ts = analytics.timeseries_pack_publishes(period="daily", days=30)
        assert ts.points == []

    def test_ecosystem_health_no_quality_scores(self, analytics: AnalyticsEngine, store: AgentStore):
        """Packs without quality_score use 0."""
        store.register_agent("noq-agent", operator="noq-op")
        store.add_pack(
            "pack-noq", version="1.0.0",
            yaml_content="name: NoQPack",
            author_agent="noq-agent",
        )
        health = analytics.ecosystem_health()
        assert health.avg_quality_score == 0.0
