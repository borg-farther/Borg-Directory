"""
Guild v2 analytics engine (M2.5).

Computes pack usage stats, adoption metrics, ecosystem health,
and time-series aggregations.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Sequence

from borg.db.store import AgentStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PackUsageStats:
    """Usage statistics for a single pack."""
    pack_id: str
    pull_count: int = 0
    apply_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    completion_rate: float = 0.0  # success / (success + failure)


@dataclass
class AdoptionMetrics:
    """Adoption metrics for a pack or the whole ecosystem."""
    pack_id: Optional[str]
    unique_agents: int = 0
    unique_operators: int = 0


@dataclass
class EcosystemHealth:
    """Overall ecosystem health metrics."""
    total_agents: int = 0
    active_contributors: int = 0
    active_consumers: int = 0
    contributor_ratio: float = 0.0  # active_contributors / total_agents
    avg_quality_score: float = 0.0
    avg_quality_trend: float = 0.0   # delta vs previous period
    domain_coverage: dict[str, int] = field(default_factory=dict)
    total_packs: int = 0
    tier_distribution: dict[str, int] = field(default_factory=dict)


@dataclass
class TimeSeriesPoint:
    """A single point in a time series."""
    timestamp: str  # ISO format
    period: str     # "daily", "weekly", "monthly"
    metric: str
    value: float
    label: Optional[str] = None


@dataclass
class TimeSeriesResult:
    """A list of time-series points for a metric."""
    metric: str
    period: str
    points: list[TimeSeriesPoint] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AnalyticsEngine
# ---------------------------------------------------------------------------

class AnalyticsEngine:
    """
    Computes analytics and metrics for the guild ecosystem.

    Parameters
    ----------
    store : AgentStore
        Persistent store for guild data.
    """

    def __init__(self, store: AgentStore) -> None:
        self.store = store

    # -----------------------------------------------------------------------
    # Pack usage stats
    # -----------------------------------------------------------------------

    def pack_usage_stats(self, pack_id: str) -> PackUsageStats:
        """
        Compute usage statistics for a pack.

        - pull_count: total executions for this pack
        - apply_count: executions with status "completed" (success or failure)
        - success_count: executions with status "completed"
        - failure_count: executions with status "failed"
        - completion_rate: success / max(1, success + failure)
        """
        executions = self.store.list_executions(pack_id=pack_id, limit=10000)

        pull_count = len(executions)
        success_count = sum(1 for e in executions if e.get("status") == "completed")
        failure_count = sum(1 for e in executions if e.get("status") == "failed")
        apply_count = success_count + failure_count

        completion_rate = success_count / max(1, success_count + failure_count)

        return PackUsageStats(
            pack_id=pack_id,
            pull_count=pull_count,
            apply_count=apply_count,
            success_count=success_count,
            failure_count=failure_count,
            completion_rate=completion_rate,
        )

    def all_pack_usage_stats(self) -> list[PackUsageStats]:
        """Compute usage stats for all packs."""
        packs = self.store.list_packs(limit=10000)
        return [self.pack_usage_stats(p["id"]) for p in packs]

    # -----------------------------------------------------------------------
    # Adoption metrics
    # -----------------------------------------------------------------------

    def adoption_metrics(self, pack_id: str) -> AdoptionMetrics:
        """
        Compute adoption metrics for a pack.

        - unique_agents: agents who authored feedback on this pack
        - unique_operators: agents who executed this pack
        """
        executions = self.store.list_executions(pack_id=pack_id, limit=10000)
        feedback = self.store.list_feedback(pack_id=pack_id, limit=10000)

        unique_operators = len({e.get("agent_id") for e in executions if e.get("agent_id")})
        unique_agents = len({f.get("author_agent") for f in feedback if f.get("author_agent")})

        return AdoptionMetrics(
            pack_id=pack_id,
            unique_agents=unique_agents,
            unique_operators=unique_operators,
        )

    def ecosystem_adoption(self) -> AdoptionMetrics:
        """Aggregate adoption metrics across the entire ecosystem."""
        executions = self.store.list_executions(limit=10000)
        unique_operators = len({e.get("agent_id") for e in executions if e.get("agent_id")})

        feedback_list = self.store.list_feedback(limit=10000)
        unique_agents = len({f.get("author_agent") for f in feedback_list if f.get("author_agent")})

        return AdoptionMetrics(
            pack_id=None,
            unique_agents=unique_agents,
            unique_operators=unique_operators,
        )

    # -----------------------------------------------------------------------
    # Ecosystem health
    # -----------------------------------------------------------------------

    def _parse_ts(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse an ISO timestamp string to datetime."""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    def ecosystem_health(self, now: Optional[datetime] = None) -> EcosystemHealth:
        """
        Compute overall ecosystem health metrics.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # Collect all agents
        agents = self.store.list_agents(limit=10000)
        total_agents = len(agents)

        packs = self.store.list_packs(limit=10000)
        executions = self.store.list_executions(limit=10000)
        feedback_list = self.store.list_feedback(limit=10000)

        # Active contributors (authored a pack or feedback in last 90 days)
        cutoff = now.timestamp() - (90 * 24 * 3600)

        recent_pack_authors: set[str] = set()
        for p in packs:
            ts = self._parse_ts(p.get("created_at"))
            if ts and ts.timestamp() >= cutoff:
                if p.get("author_agent"):
                    recent_pack_authors.add(p["author_agent"])

        recent_feedback_authors: set[str] = set()
        for f in feedback_list:
            ts = self._parse_ts(f.get("created_at"))
            if ts and ts.timestamp() >= cutoff:
                if f.get("author_agent"):
                    recent_feedback_authors.add(f["author_agent"])

        active_contributors = len(recent_pack_authors | recent_feedback_authors)

        # Active consumers (executed a pack in last 90 days)
        active_consumers = len({
            e.get("agent_id") for e in executions
            if e.get("agent_id") and self._is_recent(e.get("started_at"), cutoff)
        })

        # Average quality score (from metadata or 0)
        quality_scores = []
        for p in packs:
            meta = p.get("metadata")
            if meta and isinstance(meta, dict) and meta.get("quality_score") is not None:
                quality_scores.append(float(meta["quality_score"]))
            elif p.get("quality_score") is not None:
                quality_scores.append(float(p["quality_score"]))

        avg_quality_score = sum(quality_scores) / max(1, len(quality_scores))

        # Tier distribution
        tier_counts: dict[str, int] = defaultdict(int)
        for p in packs:
            tier_counts[p.get("tier", "community")] += 1

        # Domain coverage (using domain field or tier as proxy)
        domain_counts: dict[str, int] = defaultdict(int)
        for p in packs:
            domain = p.get("domain") or p.get("tier", "unknown")
            domain_counts[domain] += 1

        return EcosystemHealth(
            total_agents=total_agents,
            active_contributors=active_contributors,
            active_consumers=active_consumers,
            contributor_ratio=active_contributors / max(1, total_agents),
            avg_quality_score=avg_quality_score,
            avg_quality_trend=0.0,  # Placeholder - needs historical data
            domain_coverage=dict(domain_counts),
            total_packs=len(packs),
            tier_distribution=dict(tier_counts),
        )

    def _is_recent(self, ts_str: Optional[str], cutoff: float) -> bool:
        """Check if a timestamp string is more recent than cutoff timestamp."""
        if not ts_str:
            return False
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
            return ts >= cutoff
        except ValueError:
            return False

    # -----------------------------------------------------------------------
    # Time-series aggregations
    # -----------------------------------------------------------------------

    def _daily_buckets(
        self,
        items: Sequence[dict],
        now: Optional[datetime] = None,
        days: int = 30,
    ) -> dict[str, list[dict]]:
        """Group items into daily buckets by created_at/started_at."""
        if now is None:
            now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (days * 24 * 3600)
        buckets: dict[str, list[dict]] = defaultdict(list)

        for item in items:
            # Try created_at first, fall back to started_at
            created_str = item.get("created_at") or item.get("started_at")
            if not created_str:
                continue
            try:
                ts = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts.timestamp() < cutoff:
                continue
            key = ts.strftime("%Y-%m-%d")
            buckets[key].append(item)
        return buckets

    def _weekly_buckets(
        self,
        items: Sequence[dict],
        now: Optional[datetime] = None,
        weeks: int = 12,
    ) -> dict[str, list[dict]]:
        """Group items into weekly buckets."""
        if now is None:
            now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (weeks * 7 * 24 * 3600)
        buckets: dict[str, list[dict]] = defaultdict(list)

        for item in items:
            created_str = item.get("created_at") or item.get("started_at")
            if not created_str:
                continue
            try:
                ts = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts.timestamp() < cutoff:
                continue
            # ISO week key using %W
            key = f"{ts.year}-W{ts.strftime('%W')}"
            buckets[key].append(item)
        return buckets

    def _monthly_buckets(
        self,
        items: Sequence[dict],
        now: Optional[datetime] = None,
        months: int = 12,
    ) -> dict[str, list[dict]]:
        """Group items into monthly buckets."""
        if now is None:
            now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - (months * 30 * 24 * 3600)
        buckets: dict[str, list[dict]] = defaultdict(list)

        for item in items:
            created_str = item.get("created_at") or item.get("started_at")
            if not created_str:
                continue
            try:
                ts = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts.timestamp() < cutoff:
                continue
            key = ts.strftime("%Y-%m")
            buckets[key].append(item)
        return buckets

    def timeseries_pack_publishes(
        self,
        period: str = "daily",
        days: int = 30,
    ) -> TimeSeriesResult:
        """Time series of pack publications."""
        packs = self.store.list_packs(limit=10000)
        now = datetime.now(timezone.utc)

        if period == "daily":
            buckets = self._daily_buckets(packs, now, days)
        elif period == "weekly":
            buckets = self._weekly_buckets(packs, now, days)
        elif period == "monthly":
            buckets = self._monthly_buckets(packs, now, days)
        else:
            buckets = {}

        points = [
            TimeSeriesPoint(
                timestamp=key,
                period=period,
                metric="pack_publishes",
                value=float(len(items)),
            )
            for key, items in sorted(buckets.items())
        ]
        return TimeSeriesResult(metric="pack_publishes", period=period, points=points)

    def timeseries_executions(
        self,
        period: str = "daily",
        days: int = 30,
    ) -> TimeSeriesResult:
        """Time series of pack executions."""
        executions = self.store.list_executions(limit=10000)
        now = datetime.now(timezone.utc)

        if period == "daily":
            buckets = self._daily_buckets(executions, now, days)
        elif period == "weekly":
            buckets = self._weekly_buckets(executions, now, days)
        elif period == "monthly":
            buckets = self._monthly_buckets(executions, now, days)
        else:
            buckets = {}

        points = [
            TimeSeriesPoint(
                timestamp=key,
                period=period,
                metric="executions",
                value=float(len(items)),
            )
            for key, items in sorted(buckets.items())
        ]
        return TimeSeriesResult(metric="executions", period=period, points=points)

    def timeseries_quality_scores(
        self,
        period: str = "daily",
        days: int = 30,
    ) -> TimeSeriesResult:
        """Time series of average quality scores per period."""
        packs = self.store.list_packs(limit=10000)
        now = datetime.now(timezone.utc)

        if period == "daily":
            buckets = self._daily_buckets(packs, now, days)
        elif period == "weekly":
            buckets = self._weekly_buckets(packs, now, days)
        elif period == "monthly":
            buckets = self._monthly_buckets(packs, now, days)
        else:
            buckets = {}

        points = []
        for key, items in sorted(buckets.items()):
            scores = []
            for p in items:
                meta = p.get("metadata")
                if meta and isinstance(meta, dict) and meta.get("quality_score") is not None:
                    scores.append(float(meta["quality_score"]))
                elif p.get("quality_score") is not None:
                    scores.append(float(p["quality_score"]))
            avg = sum(scores) / max(1, len(scores))
            points.append(TimeSeriesPoint(
                timestamp=key,
                period=period,
                metric="avg_quality_score",
                value=avg,
            ))
        return TimeSeriesResult(metric="avg_quality_score", period=period, points=points)

    def timeseries_active_agents(
        self,
        period: str = "daily",
        days: int = 30,
    ) -> TimeSeriesResult:
        """Time series of unique active agents per period."""
        executions = self.store.list_executions(limit=10000)
        now = datetime.now(timezone.utc)

        if period == "daily":
            buckets = self._daily_buckets(executions, now, days)
        elif period == "weekly":
            buckets = self._weekly_buckets(executions, now, days)
        elif period == "monthly":
            buckets = self._monthly_buckets(executions, now, days)
        else:
            buckets = {}

        points = []
        for key, items in sorted(buckets.items()):
            unique = len({e.get("agent_id") for e in items if e.get("agent_id")})
            points.append(TimeSeriesPoint(
                timestamp=key,
                period=period,
                metric="active_agents",
                value=float(unique),
            ))
        return TimeSeriesResult(metric="active_agents", period=period, points=points)

    def timeseries(
        self,
        metric: str,
        period: str = "daily",
        days: int = 30,
    ) -> TimeSeriesResult:
        """
        Generic time-series interface.

        Parameters
        ----------
        metric : str
            One of: "pack_publishes", "executions", "avg_quality_score", "active_agents"
        period : str
            One of: "daily", "weekly", "monthly"
        days : int
            Number of days to look back

        Returns
        -------
        TimeSeriesResult
        """
        if metric == "pack_publishes":
            return self.timeseries_pack_publishes(period, days)
        elif metric == "executions":
            return self.timeseries_executions(period, days)
        elif metric == "avg_quality_score":
            return self.timeseries_quality_scores(period, days)
        elif metric == "active_agents":
            return self.timeseries_active_agents(period, days)
        else:
            return TimeSeriesResult(metric=metric, period=period, points=[])

    # -------------------------------------------------------------------------
    # Dojo learning curve integration
    # -------------------------------------------------------------------------

    def timeseries_dojo_metrics(
        self,
        period: str = "daily",
        days: int = 30,
    ) -> TimeSeriesResult:
        """Time series of dojo learning curve metrics.

        Returns success rate, error count, user corrections, and skill gap
        trends from the dojo learning curve tracker.

        Args:
            period: "daily", "weekly", or "monthly".
            days: Number of days to look back.

        Returns:
            TimeSeriesResult with dojo learning curve data points.
        """
        try:
            from borg.dojo.learning_curve import LearningCurveTracker

            tracker = LearningCurveTracker()
            history = tracker.load_history()

            if not history:
                return TimeSeriesResult(
                    metric="dojo_learning_curve",
                    period=period,
                    points=[],
                )

            # Filter history to requested time range
            now = datetime.now(timezone.utc)
            cutoff = now.timestamp() - (days * 24 * 3600)

            filtered: list = []
            for snap in history:
                ts = getattr(snap, "timestamp", 0)
                if ts >= cutoff:
                    filtered.append(snap)

            if not filtered:
                return TimeSeriesResult(
                    metric="dojo_learning_curve",
                    period=period,
                    points=[],
                )

            # Build a bucket key for each snapshot based on period
            def bucket_key(snap) -> str:
                ts = getattr(snap, "timestamp", 0)
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                if period == "daily":
                    return dt.strftime("%Y-%m-%d")
                elif period == "weekly":
                    return f"{dt.year}-W{dt.strftime('%W')}"
                else:
                    return dt.strftime("%Y-%m")

            # Group by bucket and average
            buckets: dict = defaultdict(list)
            for snap in filtered:
                key = bucket_key(snap)
                buckets[key].append(snap)

            points = []
            for key in sorted(buckets.keys()):
                snaps = buckets[key]
                n = len(snaps)
                avg_success = sum(getattr(s, "overall_success_rate", 0) for s in snaps) / n
                total_errors = sum(getattr(s, "total_errors", 0) for s in snaps)
                total_corrections = sum(getattr(s, "user_corrections", 0) for s in snaps)
                skill_gaps = sum(getattr(s, "skill_gaps_count", 0) for s in snaps)

                points.append(
                    TimeSeriesPoint(
                        timestamp=key,
                        period=period,
                        metric="dojo_success_rate",
                        value=avg_success,
                        label=f"errors={total_errors}, corrections={total_corrections}, gaps={skill_gaps}",
                    )
                )

            return TimeSeriesResult(
                metric="dojo_learning_curve",
                period=period,
                points=points,
            )
        except ImportError:
            # Dojo not installed — return empty result
            return TimeSeriesResult(
                metric="dojo_learning_curve",
                period=period,
                points=[],
            )
        except Exception as e:
            logger.warning("timeseries_dojo_metrics failed: %s", e)
            return TimeSeriesResult(
                metric="dojo_learning_curve",
                period=period,
                points=[],
            )
