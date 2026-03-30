"""Borg DeFi V2 — Core recommender with Thompson Sampling."""

import math
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from borg.defi.v2.models import (
    DeFiStrategyPack,
    StrategyQuery,
    StrategyRecommendation,
    ExecutionOutcome,
    CollectiveStats,
)
from borg.defi.v2.pack_store import PackStore
from borg.defi.v2.outcome_store import OutcomeStore

logger = logging.getLogger(__name__)

# Default half-life for temporal decay (days)
DEFAULT_HALF_LIFE_DAYS = 30.0

# Bayesian prior for Beta-Binomial (uninformative prior = 1,1)
PRIOR_ALPHA = 1.0
PRIOR_BETA = 1.0


def temporal_weight(outcome_age_days: float, half_life_days: float = DEFAULT_HALF_LIFE_DAYS) -> float:
    """Calculate temporal weight using exponential decay.

    Recent outcomes matter more. Default half-life: 30 days.
    
    Args:
        outcome_age_days: Age of the outcome in days.
        half_life_days: Half-life for decay (default 30).
        
    Returns:
        Weight between 0 and 1.
    """
    if outcome_age_days < 0:
        outcome_age_days = 0
    return 0.5 ** (outcome_age_days / half_life_days)


def normalize(values: List[float], min_val: float = None, max_val: float = None) -> float:
    """Normalize a value or list to 0-1 range.

    If a single value is given, it's normalized against provided min/max.
    If a list is given, uses its own min/max.
    
    Args:
        values: Single value or list of values to normalize.
        min_val: Optional explicit min.
        max_val: Optional explicit max.
        
    Returns:
        Normalized value(s) between 0 and 1.
    """
    if isinstance(values, list):
        if not values:
            return 0.0
        vals = values
        min_v = min(vals)
        max_v = max(vals)
    else:
        vals = [values]
        min_v = min_val if min_val is not None else 0
        max_v = max_val if max_val is not None else 1

    if max_v == min_v:
        return 0.0 if isinstance(values, list) else 0.0
    
    result = [(v - min_v) / (max_v - min_v) for v in vals]
    return result[0] if not isinstance(values, list) else result


def calculate_confidence(pack: DeFiStrategyPack) -> float:
    """Calculate confidence score based on sample size and consistency.

    0.0 to 1.0 based on sample size and consistency.

    Args:
        pack: Strategy pack to calculate confidence for.
        
    Returns:
        Confidence score between 0 and 1.
    """
    if not pack.collective:
        return 0.0
    
    n = pack.collective.total_outcomes
    if n == 0:
        return 0.0
    if n < 3:
        return 0.1 * n  # 0.1, 0.2
    
    # Base confidence from sample size (logarithmic)
    base = min(1.0, 0.3 + 0.1 * math.log2(n))  # 3→0.46, 10→0.63, 50→0.86
    
    # Penalize high variance
    avg = abs(pack.collective.avg_return_pct)
    if avg < 0.01:
        avg = 0.01
    cv = pack.collective.std_dev / avg  # coefficient of variation
    variance_penalty = max(0, 1 - cv)
    
    return base * (0.7 + 0.3 * variance_penalty)


def beta_sample(alpha: float, beta: float) -> float:
    """Sample from Beta distribution using inverse transform.
    
    Uses the property that if X~Gamma(alpha,1) and Y~Gamma(beta,1),
    then X/(X+Y) ~ Beta(alpha, beta).
    
    Args:
        alpha: Alpha parameter (wins + prior).
        beta: Beta parameter (losses + prior).
        
    Returns:
        Random sample from Beta(alpha, beta).
    """
    # Simple implementation using gamma sampling
    # For production, consider using scipy or numpy
    if alpha <= 0 or beta <= 0:
        return alpha / (alpha + beta) if (alpha + beta) > 0 else 0.5
    
    # Generate gamma samples
    x = _gamma_sample(alpha)
    y = _gamma_sample(beta)
    
    if x + y <= 0:
        return alpha / (alpha + beta)
    
    return x / (x + y)


def _gamma_sample(shape: float) -> float:
    """Sample from Gamma distribution using Marsaglia and Tsang's method.
    
    Args:
        shape: Shape parameter (alpha).
        
    Returns:
        Random sample from Gamma(shape, 1).
    """
    if shape < 1:
        return _gamma_sample(shape + 1) * random.random() ** (1 / shape)
    
    # Use Marsaglia and Tsang's method for shape >= 1
    d = shape - 1/3
    c = 1 / math.sqrt(9 * d)
    
    while True:
        while True:
            x = random.gauss(0, 1)
            v = 1 + c * x
            if v > 0:
                break
        v = v ** 3
        u = random.random()
        if u < 1 - 0.0331 * (x ** 4):
            return d * v
        if math.log(u) < 0.5 * x ** 2 + d * (1 - v + math.log(v)):
            return d * v


def detect_drift(pack: DeFiStrategyPack) -> Optional[str]:
    """Detect concept drift in recent performance vs historical.

    Flag if recent performance diverges from historical using Z-test.

    Args:
        pack: Strategy pack to check for drift.
        
    Returns:
        Drift description string or None if no drift detected.
    """
    if not pack.collective or pack.collective.total_outcomes < 10:
        return None
    
    recent = pack.collective.last_5_returns
    if len(recent) < 5:
        return None
    
    historical_mean = pack.collective.avg_return_pct
    recent_mean = sum(recent) / len(recent)
    
    std_err = pack.collective.std_dev / math.sqrt(len(recent))
    if std_err <= 0:
        return None
    
    z = (recent_mean - historical_mean) / std_err
    
    if z < -2.0:
        return f"DEGRADING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}%"
    if z > 2.0:
        return f"IMPROVING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}%"
    return None


def calculate_confidence_interval(alpha: float, beta_param: float, confidence: float = 0.95) -> tuple:
    """Calculate confidence interval for Beta distribution.

    Uses a simple approximation based on the normal distribution.

    Args:
        alpha: Alpha parameter.
        beta_param: Beta parameter.
        confidence: Confidence level (default 0.95 for 95% CI).
        
    Returns:
        Tuple of (lower, upper) bounds.
    """
    mean = alpha / (alpha + beta_param) if (alpha + beta_param) > 0 else 0.5
    std = math.sqrt((alpha * beta_param) / ((alpha + beta_param) ** 2 * (alpha + beta_param + 1)))
    
    # Normal approximation for 95% CI
    z = 1.96  # for 95% CI
    lower = max(0.0, mean - z * std)
    upper = min(1.0, mean + z * std)
    
    return (lower, upper)


class DeFiRecommender:
    """Core recommender using Thompson Sampling and Bayesian reputation.

    This is the main entry point for the DeFi V2 recommendation system.
    """

    def __init__(self, packs_dir=None, outcomes_dir=None):
        """Initialize the recommender.

        Args:
            packs_dir: Optional custom packs directory path.
            outcomes_dir: Optional custom outcomes directory path.
        """
        self.pack_store = PackStore(packs_dir)
        self.outcome_store = OutcomeStore(outcomes_dir)

    def get_pack(self, pack_id: str) -> Optional[DeFiStrategyPack]:
        """Get a specific pack by ID.

        Args:
            pack_id: Pack identifier.

        Returns:
            DeFiStrategyPack if found, None otherwise.
        """
        return self.pack_store.load_pack(pack_id)

    def recommend(self, query: StrategyQuery, limit: int = 5) -> List[StrategyRecommendation]:
        """Generate strategy recommendations using Thompson Sampling.

        Uses Beta-Binomial posterior for Bayesian win rate estimation,
        combined with return, confidence, and freshness signals.

        Args:
            query: StrategyQuery with token, chain, amount, risk tolerance.
            limit: Maximum number of recommendations to return.

        Returns:
            List of StrategyRecommendation objects, ranked by score.
        """
        # Load all matching packs
        candidates = self.pack_store.list_packs(
            token=query.token,
            chain=query.chain,
            risk=query.risk_tolerance,
        )

        # Load active warnings to filter dangerous packs
        active_warnings = self.get_active_warnings(
            chain=query.chain,
            protocol=None
        )
        warned_pack_ids = {w.get("pack_id") for w in active_warnings}

        scored = []
        now = datetime.now()

        for pack in candidates:
            # Skip packs with active warnings
            if pack.id in warned_pack_ids:
                continue

            # Skip packs that don't meet minimum amount
            if pack.entry and query.amount_usd > 0:
                if pack.entry.min_amount_usd > query.amount_usd:
                    continue

            # Get or initialize collective stats
            collective = pack.collective or CollectiveStats()
            
            # Thompson Sample from Beta posterior
            sampled_win_rate = beta_sample(collective.alpha, collective.beta)

            # Calculate component scores
            win_rate_score = sampled_win_rate

            # Normalized return (relative to typical DeFi returns)
            return_score = normalize(collective.avg_return_pct, -10, 20)  # -10% to 20% range

            # Confidence score
            confidence_score = calculate_confidence(pack)

            # Freshness score (based on when last updated)
            freshness_score = 0.5
            if pack.updated_at:
                age_days = (now - pack.updated_at.replace(tzinfo=None)).days
                freshness_score = temporal_weight(age_days)

            # Combined score with weights
            score = (
                win_rate_score * 0.35
                + return_score * 0.30
                + confidence_score * 0.20
                + freshness_score * 0.15
            )

            # Calculate confidence interval
            ci = calculate_confidence_interval(collective.alpha, collective.beta)

            # Get rug warnings for this pack
            rug_warnings = [w.get("guidance", "") for w in active_warnings if w.get("pack_id") == pack.id]

            # Build recommendation
            recommendation = StrategyRecommendation(
                pack_id=pack.id,
                rank=0,  # Will be set after sorting
                agent_count=collective.total_outcomes,
                profitable_count=collective.profitable,
                avg_return_pct=collective.avg_return_pct,
                median_return_pct=collective.median_return_pct,
                avg_duration_days=collective.avg_duration_days,
                protocol=pack.action.protocol if pack.action else "",
                action_type=pack.action.type if pack.action else "",
                confidence=confidence_score,
                il_risk=pack.risk.il_risk if pack.risk else False,
                exit_guidance=pack.exit_guidance,
                rug_warnings=rug_warnings,
                trend=collective.trend,
                reputation=collective.reputation,
                confidence_interval=ci,
            )

            scored.append((recommendation, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Assign ranks and return top N
        recommendations = []
        for i, (rec, score) in enumerate(scored[:limit]):
            rec.rank = i + 1
            recommendations.append(rec)

        return recommendations

    def record_outcome(self, outcome: ExecutionOutcome) -> None:
        """Record an execution outcome and update pack stats.

        This implements the full Bayesian update loop:
        1. Save outcome to disk
        2. Update pack Bayesian stats (alpha/beta)
        3. Recalculate aggregate stats with temporal weighting
        4. Check for drift and warning propagation
        5. Bump version and save pack

        Args:
            outcome: ExecutionOutcome to record.
        """
        # 1. Save outcome to disk
        self.outcome_store.save_outcome(outcome)

        # 2. Load the pack
        pack = self.pack_store.load_pack(outcome.pack_id)
        if not pack:
            logger.error(f"Pack not found for outcome: {outcome.pack_id}")
            return

        # 3. Update Bayesian stats
        if outcome.profitable:
            pack.collective.alpha += 1
        else:
            pack.collective.beta += 1

        pack.collective.total_outcomes += 1
        pack.collective.profitable += (1 if outcome.profitable else 0)

        # 4. Recalculate aggregate stats (with temporal weighting)
        all_outcomes = self.outcome_store.load_outcomes_for_pack(outcome.pack_id)
        now = datetime.now()

        if all_outcomes:
            # Calculate weighted returns
            weighted_returns = []
            for o in all_outcomes:
                if o.entered_at:
                    age_days = (now - o.entered_at.replace(tzinfo=None)).days
                    weight = temporal_weight(age_days)
                    weighted_returns.append((o.return_pct, weight))

            if weighted_returns:
                # Weighted mean
                total_weight = sum(w for _, w in weighted_returns)
                if total_weight > 0:
                    weighted_mean = sum(r * w for r, w in weighted_returns) / total_weight
                    pack.collective.avg_return_pct = round(weighted_mean, 4)

                # Simple stats
                returns = [o.return_pct for o in all_outcomes]
                pack.collective.avg_return_pct = round(sum(returns) / len(returns), 4)
                
                sorted_returns = sorted(returns)
                n = len(sorted_returns)
                if n % 2 == 0:
                    pack.collective.median_return_pct = round((sorted_returns[n//2-1] + sorted_returns[n//2]) / 2, 4)
                else:
                    pack.collective.median_return_pct = round(sorted_returns[n//2], 4)

                pack.collective.min_return_pct = round(min(returns), 4)
                pack.collective.max_return_pct = round(max(returns), 4)

                # Standard deviation
                if len(returns) > 1:
                    mean = sum(returns) / len(returns)
                    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
                    pack.collective.std_dev = round(math.sqrt(variance), 4)

                # Average duration
                durations = [o.duration_days for o in all_outcomes if o.duration_days > 0]
                if durations:
                    pack.collective.avg_duration_days = round(sum(durations) / len(durations), 1)

                # Last 5 returns
                pack.collective.last_5_returns = [o.return_pct for o in all_outcomes[-5:]]

        # 5. Update reputation (it's a computed property, just recalculate)
        # Reputation is alpha / (alpha + beta), which is accessed via property

        # 6. Check for drift
        drift = detect_drift(pack)
        if drift:
            if "DEGRADING" in drift:
                pack.collective.trend = "degrading"
            elif "IMPROVING" in drift:
                pack.collective.trend = "improving"

        # 7. Check for warning propagation
        if pack.collective.beta >= 4 and pack.collective.reputation < 0.4:
            self._propagate_warning(pack, "Low win rate with sufficient sample size")

        # 8. Bump version and save
        pack.version += 1
        pack.updated_at = now
        self.pack_store.save_pack(pack)

    def _propagate_warning(self, pack: DeFiStrategyPack, reason: str) -> None:
        """Auto-generate warning when collective evidence shows danger.

        Args:
            pack: Pack that triggered the warning.
            reason: Reason for the warning.
        """
        now = datetime.now()
        severity = "high" if pack.collective.reputation < 0.3 else "medium"

        warning = {
            "id": f"warning/{pack.id}/{now.strftime('%Y%m%d%H%M%S')}",
            "type": "collective_warning",
            "severity": severity,
            "pack_id": pack.id,
            "reason": reason,
            "evidence": {
                "total_outcomes": pack.collective.total_outcomes,
                "losses": pack.collective.total_outcomes - pack.collective.profitable,
                "loss_patterns": pack.collective.loss_patterns,
                "reputation": pack.collective.reputation,
            },
            "guidance": f"Avoid {pack.name}. {pack.collective.total_outcomes - pack.collective.profitable} agents lost money.",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=30)).isoformat(),
        }

        self.pack_store.save_warning(warning)

    def get_active_warnings(
        self, chain: Optional[str] = None, protocol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active warnings, optionally filtered.

        Args:
            chain: Optional chain filter.
            protocol: Optional protocol filter.

        Returns:
            List of warning dictionaries.
        """
        warnings = self.pack_store.load_warnings()
        now = datetime.now()

        filtered = []
        for w in warnings:
            # Check expiration
            expires = w.get("expires_at")
            if expires:
                try:
                    exp_date = datetime.fromisoformat(expires.replace("Z", "+00:00"))
                    if exp_date < now:
                        continue  # expired
                except:
                    pass

            # Chain filter (warnings don't have chain, so skip if protocol check needed)
            if chain:
                # Would need to load pack to check chain - skip for now
                pass

            # Protocol filter
            if protocol:
                if w.get("pack_id"):
                    # Extract protocol from pack_id or load pack
                    pack_protocol = w.get("pack_id", "").split("/")[-1] if "/" in w.get("pack_id", "") else ""
                    if protocol.lower() not in pack_protocol.lower():
                        continue

            filtered.append(w)

        return filtered

    def get_collective_stats(self, pack_id: str) -> Optional[CollectiveStats]:
        """Get collective stats for a pack.

        Args:
            pack_id: Pack identifier.

        Returns:
            CollectiveStats if pack found, None otherwise.
        """
        pack = self.pack_store.load_pack(pack_id)
        if pack:
            return pack.collective
        return None

    def get_pack_count(self) -> int:
        """Get total number of packs.

        Returns:
            Total count of packs.
        """
        return len(self.pack_store.list_packs())

    def get_outcome_count(self) -> int:
        """Get total number of recorded outcomes.

        Returns:
            Total count of outcomes.
        """
        return self.outcome_store.get_outcome_count()
