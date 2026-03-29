"""
Guild v2 reputation engine (M2.4).

Computes contribution scores, access tiers, free-rider detection,
and reputation gain/loss events.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from borg.db.store import AgentStore

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Module-level dojo session feedback function (for borg.dojo.pipeline integration)
# -------------------------------------------------------------------------

def apply_session_feedback(analysis) -> None:
    """Apply dojo SessionAnalysis feedback to reputation scores.

    This is a module-level wrapper that creates a temporary ReputationEngine
    to apply session-level feedback. Used by borg.dojo.pipeline._feed_reputation().

    Args:
        analysis: SessionAnalysis from borg.dojo.pipeline.
    """
    try:
        store = AgentStore()
        engine = ReputationEngine(store)
        engine.apply_session_feedback(analysis)
        store.close()
    except Exception as e:
        logger.warning("apply_session_feedback failed: %s", e)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Contribution weights (per type)
ACTION_WEIGHTS = {
    "pack_publication": 10,
    "quality_review": 3,
    "bug_report": 2,
    "documentation": 2,
    "governance_vote": 1,
}

# Reputation delta for pack publication by confidence level
PUBLISH_DELTA_BY_CONFIDENCE = {
    "guessed": 1,
    "inferred": 3,
    "tested": 7,
    "validated": 15,
}

# Reputation delta for quality review (scored 1-5)
QUALITY_REVIEW_DELTA = {
    1: 0,
    2: 1,
    3: 2,
    4: 4,
    5: 5,
}

# Recency decay lambda per epoch (30 days)
RECENCY_LAMBDA = 0.95

# Inactivity decay: -5% per month after 90 days, floor at 50% of peak
INACTIVITY_PENALTY_RATE = 0.05  # 5% per month
INACTIVITY_GRACE_DAYS = 90
INACTIVITY_FLOOR_RATIO = 0.5


# ---------------------------------------------------------------------------
# Access tiers
# ---------------------------------------------------------------------------

class AccessTier(Enum):
    COMMUNITY = "community"      # score < 10
    VALIDATED = "validated"      # score 10-50
    CORE = "core"                # score 50-200
    GOVERNANCE = "governance"    # score > 200

    @classmethod
    def from_score(cls, score: float) -> "AccessTier":
        if score < 10:
            return cls.COMMUNITY
        elif score <= 50:
            return cls.VALIDATED
        elif score <= 200:
            return cls.CORE
        else:
            return cls.GOVERNANCE


# ---------------------------------------------------------------------------
# Free-rider thresholds
# ---------------------------------------------------------------------------

class FreeRiderStatus(Enum):
    OK = "ok"           # score <= 20
    FLAGGED = "flagged" # score 21-50
    THROTTLED = "throttled"  # score 51-100
    RESTRICTED = "restricted"  # score > 100

    @classmethod
    def from_score(cls, score: float) -> "FreeRiderStatus":
        if score <= 20:
            return cls.OK
        elif score <= 50:
            return cls.FLAGGED
        elif score <= 100:
            return cls.THROTTLED
        else:
            return cls.RESTRICTED


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ContributionAction:
    """A single contribution action by an agent."""
    action_type: str           # e.g. "pack_publication", "quality_review"
    quality: float = 1.0       # 0.0 – 1.0 multiplier
    confidence: str = "inferred"  # for pack_publication
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ReputationProfile:
    """Full reputation profile for an agent."""
    agent_id: str
    contribution_score: float = 0.0
    access_tier: AccessTier = AccessTier.COMMUNITY
    free_rider_score: float = 0.0
    free_rider_status: FreeRiderStatus = FreeRiderStatus.OK
    peak_score: float = 0.0
    last_active_at: Optional[datetime] = None
    packs_published: int = 0
    quality_reviews_given: int = 0
    bug_reports_filed: int = 0
    documentation_contributions: int = 0
    governance_votes_cast: int = 0
    packs_consumed: int = 0


# ---------------------------------------------------------------------------
# ReputationEngine
# ---------------------------------------------------------------------------

class ReputationEngine:
    """
    Computes and maintains reputation scores for guild agents.

    Parameters
    ----------
    store : AgentStore
        Persistent store for guild data.
    """

    def __init__(self, store: AgentStore) -> None:
        self.store = store

    # -----------------------------------------------------------------------
    # Contribution scoring
    # -----------------------------------------------------------------------

    def _recency_decay(self, created_at: datetime, now: Optional[datetime] = None) -> float:
        """
        Compute recency decay factor.
        
        Returns lambda^epochs where one epoch = 30 days.
        lambda = 0.95 per epoch.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        # Ensure both are timezone-aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        age_seconds = (now - created_at).total_seconds()
        EPOCH_SECONDS = 30 * 24 * 3600  # 30 days
        epochs = age_seconds / EPOCH_SECONDS
        return RECENCY_LAMBDA ** epochs

    def contribution_score(
        self,
        agent_id: str,
        actions: list[ContributionAction],
        now: Optional[datetime] = None,
    ) -> float:
        """
        Compute weighted contribution score for an agent.
        
        score = sum of: weight(type) * quality * recency_decay(age)
        """
        total = 0.0
        for action in actions:
            weight = ACTION_WEIGHTS.get(action.action_type, 0)
            if weight == 0:
                continue
            decay = self._recency_decay(action.created_at, now)
            total += weight * action.quality * decay
        return total

    # -----------------------------------------------------------------------
    # Access tier
    # -----------------------------------------------------------------------

    def compute_tier(self, score: float) -> AccessTier:
        """Determine access tier from contribution score."""
        return AccessTier.from_score(score)

    # -----------------------------------------------------------------------
    # Free-rider detection
    # -----------------------------------------------------------------------

    def free_rider_score(
        self,
        packs_consumed: int,
        packs_contributed: int,
        quality_reviews: int,
    ) -> float:
        """
        Compute free-rider score.
        
        free_rider_score = packs_consumed / max(1, packs_contributed + quality_reviews)
        """
        denominator = max(1, packs_contributed + quality_reviews)
        return packs_consumed / denominator

    def free_rider_status(self, score: float) -> FreeRiderStatus:
        """Determine free-rider status from score."""
        return FreeRiderStatus.from_score(score)

    # -----------------------------------------------------------------------
    # Reputation deltas
    # -----------------------------------------------------------------------

    def delta_pack_published(self, confidence: str) -> int:
        """Reputation delta when a pack is published."""
        return PUBLISH_DELTA_BY_CONFIDENCE.get(confidence, 1)

    def delta_quality_review(self, quality: int) -> int:
        """Reputation delta when a quality review is submitted (quality 1-5)."""
        return QUALITY_REVIEW_DELTA.get(quality, 0)

    def delta_pack_used_by_others(self, current_uses: int) -> int:
        """
        Reputation delta when a pack is used by others.
        Capped at +50 per pack per epoch.
        """
        if current_uses >= 50:
            return 0
        return 1

    def delta_pack_failure(self) -> int:
        """Reputation delta when a pack failure is recorded."""
        return -2

    def delta_calibration_failure(self) -> int:
        """Reputation delta when calibration is below threshold (per epoch)."""
        return -5

    def compute_inactivity_decay(
        self,
        peak_score: float,
        last_active_at: datetime,
        now: Optional[datetime] = None,
    ) -> float:
        """
        Compute decayed score due to inactivity.
        
        After 90 days of inactivity, apply -5% per month, floor at 50% of peak.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        if last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        inactive_seconds = (now - last_active_at).total_seconds()
        inactive_days = inactive_seconds / (24 * 3600)
        
        if inactive_days <= INACTIVITY_GRACE_DAYS:
            return peak_score
        
        # Months of inactivity beyond grace period
        excess_days = inactive_days - INACTIVITY_GRACE_DAYS
        months = excess_days / 30.0
        penalty_ratio = min(months * INACTIVITY_PENALTY_RATE, 1.0 - INACTIVITY_FLOOR_RATIO)
        
        return peak_score * (1.0 - penalty_ratio)

    # -----------------------------------------------------------------------
    # Full profile computation
    # -----------------------------------------------------------------------

    def _parse_ts(self, ts_str: Optional[str]) -> Optional[datetime]:
        """Parse an ISO timestamp string to datetime."""
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    def build_profile(
        self,
        agent_id: str,
        now: Optional[datetime] = None,
    ) -> ReputationProfile:
        """
        Build a complete reputation profile for an agent.
        
        This reads all relevant data from the store and computes
        contribution score, access tier, and free-rider status.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        agent = self.store.get_agent(agent_id)
        if not agent:
            return ReputationProfile(agent_id=agent_id)

        # Collect packs published by this agent
        packs = self.store.list_packs(author_agent=agent_id, limit=1000)
        packs_published = len(packs)

        # Collect feedback / quality reviews by this agent
        # Real store: outcome IN ('success', 'partial', 'failure')
        # We use 'success' outcome as quality reviews
        feedback = self.store.list_feedback(author_agent=agent_id, limit=1000)
        # Filter to quality-review-type feedback via metadata or treat all as reviews
        quality_reviews_given = len(feedback)

        # Bug reports: feedback with 'failure' outcome
        bug_reports_filed = sum(1 for f in feedback if f.get("outcome") == "failure")

        # Pack consumptions (executions where this agent is the operator)
        executions = self.store.list_executions(agent_id=agent_id, limit=1000)
        packs_consumed = len(executions)

        # Build contribution actions
        actions: list[ContributionAction] = []

        for pack in packs:
            created_str = pack.get("created_at")
            created_at = self._parse_ts(created_str) or datetime.now(timezone.utc)
            
            # quality_score stored as a metadata field or defaults to 0
            meta = pack.get("metadata") or {}
            quality_score = meta.get("quality_score", 0) if isinstance(meta, dict) else 0
            
            actions.append(ContributionAction(
                action_type="pack_publication",
                quality=quality_score / 10.0,  # Normalize to 0-1
                confidence=pack.get("confidence", "inferred"),
                created_at=created_at,
            ))

        for fb in feedback:
            created_str = fb.get("created_at")
            created_at = self._parse_ts(created_str) or datetime.now(timezone.utc)
            
            # Extract quality from metadata if available
            meta = fb.get("metadata") or {}
            quality = meta.get("quality", 3) if isinstance(meta, dict) else 3
            
            actions.append(ContributionAction(
                action_type="quality_review",
                quality=quality / 5.0,  # Normalize to 0-1
                created_at=created_at,
            ))

        # Compute contribution score
        contribution_score_val = self.contribution_score(agent_id, actions, now)

        # Compute access tier
        access_tier = self.compute_tier(contribution_score_val)

        # Compute free-rider score
        fr_score = self.free_rider_score(
            packs_consumed=packs_consumed,
            packs_contributed=packs_published,
            quality_reviews=quality_reviews_given,
        )
        fr_status = self.free_rider_status(fr_score)

        # Peak score from agent record
        peak_score = float(agent.get("contribution_score") or 0)

        # Last active
        last_active_str = agent.get("last_active_at")
        last_active = self._parse_ts(last_active_str)

        return ReputationProfile(
            agent_id=agent_id,
            contribution_score=contribution_score_val,
            access_tier=access_tier,
            free_rider_score=fr_score,
            free_rider_status=fr_status,
            peak_score=peak_score,
            last_active_at=last_active,
            packs_published=packs_published,
            quality_reviews_given=quality_reviews_given,
            bug_reports_filed=bug_reports_filed,
            packs_consumed=packs_consumed,
        )

    # -----------------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------------

    def apply_pack_published(
        self,
        agent_id: str,
        pack_id: str,
        confidence: str = "inferred",
    ) -> ReputationProfile:
        """Record a pack publication and update agent stats."""
        delta = self.delta_pack_published(confidence)
        agent = self.store.get_agent(agent_id)
        if agent:
            current_score = float(agent.get("contribution_score") or 0)
            new_score = current_score + delta
            peak = max(float(agent.get("contribution_score") or 0), new_score)
            packs_pub = int(agent.get("packs_published") or 0) + 1
            self.store.update_agent_stats(
                agent_id,
                contribution_score=new_score,
                packs_published=packs_pub,
                last_active_at=datetime.now(timezone.utc).isoformat(),
                metadata={"peak_score": peak},
            )
        return self.build_profile(agent_id)

    def apply_quality_review(
        self,
        agent_id: str,
        feedback_id: str,
        quality: int,
    ) -> ReputationProfile:
        """Record a quality review and update agent stats."""
        delta = self.delta_quality_review(quality)
        agent = self.store.get_agent(agent_id)
        if agent:
            current_score = float(agent.get("contribution_score") or 0)
            new_score = current_score + delta
            fb_given = int(agent.get("feedback_given") or 0) + 1
            self.store.update_agent_stats(
                agent_id,
                contribution_score=new_score,
                feedback_given=fb_given,
                last_active_at=datetime.now(timezone.utc).isoformat(),
            )
        return self.build_profile(agent_id)

    def apply_pack_consumed(
        self,
        agent_id: str,
        pack_id: str,
    ) -> ReputationProfile:
        """Record that an agent consumed (used) a pack."""
        agent = self.store.get_agent(agent_id)
        if agent:
            packs_con = int(agent.get("packs_consumed") or 0) + 1
            self.store.update_agent_stats(
                agent_id,
                packs_consumed=packs_con,
                last_active_at=datetime.now(timezone.utc).isoformat(),
            )
        return self.build_profile(agent_id)

    def apply_pack_failure(self, agent_id: str, pack_id: str) -> ReputationProfile:
        """Record a pack execution failure and apply reputation penalty."""
        delta = self.delta_pack_failure()  # -2
        agent = self.store.get_agent(agent_id)
        if agent:
            current_score = float(agent.get("contribution_score") or 0)
            new_score = max(0, current_score + delta)
            self.store.update_agent_stats(
                agent_id,
                contribution_score=new_score,
                last_active_at=datetime.now(timezone.utc).isoformat(),
            )
        return self.build_profile(agent_id)

    # -------------------------------------------------------------------------
    # Dojo session feedback integration
    # -------------------------------------------------------------------------

    def apply_session_feedback(self, analysis) -> None:
        """Apply dojo SessionAnalysis feedback to reputation scores.

        This integrates session-level success rates from hermes-dojo into
        the reputation engine, penalizing agents with low success rates.

        Args:
            analysis: SessionAnalysis from borg.dojo.pipeline.
        """
        try:
            # Check schema version for forward compatibility
            if not hasattr(analysis, "schema_version"):
                logger.debug("SessionAnalysis has no schema_version — skipping")
                return
            if analysis.schema_version > 1:
                logger.warning(
                    "Unsupported dojo schema version %d — skipping session feedback",
                    analysis.schema_version,
                )
                return
            if not hasattr(analysis, "overall_success_rate"):
                logger.debug("SessionAnalysis missing overall_success_rate — skipping")
                return

            # Factor session success rate into agent contribution scores
            # Low success rates indicate the agent needs improvement
            success_rate = getattr(analysis, "overall_success_rate", 0.0)
            sessions_analyzed = getattr(analysis, "sessions_analyzed", 0)

            if sessions_analyzed == 0:
                return

            # Penalty factor: agents with <60% success rate get a reputation hit
            # The penalty is scaled by how far below 60% they are
            if success_rate < 60.0 and success_rate >= 0.0:
                deficit = 60.0 - success_rate
                # Scale penalty: -1 per 10% deficit, max -5 per session batch
                penalty = min(5.0, deficit / 10.0 * 1.0)
                # Apply to all agents (we don't have per-agent breakdown in SessionAnalysis)
                # In a full implementation this would update specific agents
                logger.info(
                    "Dojo session feedback: %.1f%% success rate (%d sessions) — "
                    "no per-agent penalty applied (requires agent_id mapping)",
                    success_rate,
                    sessions_analyzed,
                )
            elif success_rate >= 80.0:
                # Bonus for high success rates
                logger.info(
                    "Dojo session feedback: %.1f%% success rate (%d sessions) — healthy",
                    success_rate,
                    sessions_analyzed,
                )
        except Exception as e:
            logger.warning("apply_session_feedback failed: %s", e)
