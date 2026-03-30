"""
Concept drift detection for Borg DeFi V2 — flags when recent performance diverges from historical.

Uses Z-test: compare the mean of the last 5 returns against the historical mean.
Flags if |z| > 2.0 (95% confidence).

Also provides trend detection: 'improving', 'stable', or 'degrading'.
"""

from __future__ import annotations

import statistics
import math
from typing import List, Optional

from borg.defi.v2.pack_store import DeFiStrategyPack


def detect_drift(pack: DeFiStrategyPack) -> Optional[str]:
    """
    Detect concept drift in a strategy pack.

    Uses Z-test: compares the mean of the last 5 returns vs the historical mean.
    Returns a description string if drift is detected, None otherwise.

    Drift is flagged when |z| > 2.0 (approximately 95% confidence).

    Requires at least 10 total outcomes for a meaningful comparison.
    """
    if pack.total_outcomes < 10:
        return None

    if len(pack.last_5_returns) < 5:
        return None

    recent = pack.last_5_returns
    historical_mean = pack.avg_return_pct

    # Need standard deviation
    if pack.std_dev <= 0:
        return None

    # Z-test: z = (recent_mean - historical_mean) / (std_dev / sqrt(n))
    recent_mean = statistics.mean(recent)
    standard_error = pack.std_dev / math.sqrt(len(recent))
    z = (recent_mean - historical_mean) / standard_error

    if z < -2.0:
        return (
            f"DEGRADING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}% "
            f"(z={z:.2f})"
        )
    if z > 2.0:
        return (
            f"IMPROVING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}% "
            f"(z={z:.2f})"
        )

    return None


def detect_trend(returns: List[float]) -> str:
    """
    Detect trend from a list of returns.

    Uses simple linear regression slope to determine if returns are:
      'improving'  — positive trend
      'stable'     — no significant trend
      'degrading'  — negative trend

    A slope > 0.2 is considered improving, < -0.2 is degrading.
    """
    if len(returns) < 3:
        return "stable"

    n = len(returns)
    x = list(range(n))  # [0, 1, 2, ..., n-1]
    y = returns

    # Compute slope using least squares
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denominator = sum((xi - x_mean) ** 2 for xi in x)

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Classify
    if slope > 0.2:
        return "improving"
    elif slope < -0.2:
        return "degrading"
    else:
        return "stable"


def detect_drift_from_returns(
    last_5_returns: List[float],
    historical_mean: float,
    std_dev: float,
    total_outcomes: int,
) -> Optional[str]:
    """
    Standalone drift detection from raw data.

    Use this when you have returns data but not a full pack object.
    """
    if total_outcomes < 10:
        return None

    if len(last_5_returns) < 5:
        return None

    if std_dev <= 0:
        return None

    recent_mean = statistics.mean(last_5_returns)
    standard_error = std_dev / math.sqrt(len(last_5_returns))
    z = (recent_mean - historical_mean) / standard_error

    if z < -2.0:
        return f"DEGRADING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}%"
    if z > 2.0:
        return f"IMPROVING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}%"

    return None


def compute_z_score(
    sample: List[float], population_mean: float, population_std: float
) -> float:
    """
    Compute Z-score for a sample mean against a population.

    z = (sample_mean - population_mean) / (population_std / sqrt(n))
    """
    if len(sample) == 0:
        return 0.0

    sample_mean = statistics.mean(sample)
    n = len(sample)
    standard_error = population_std / math.sqrt(n)

    if standard_error == 0:
        return 0.0

    return (sample_mean - population_mean) / standard_error
