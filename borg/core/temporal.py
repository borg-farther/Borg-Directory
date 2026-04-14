"""
Temporal decay for Thompson Sampling.
Applies exponential decay to trace retrieval scores based on age.
Real traces (source != 'seed_pack') decay with a 90-day half-life.
Synthetic/seed_pack traces are timeless — no decay applied.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional


def recency_weight(
    created_at_str: str,
    half_life_days: int = 90,
    floor: float = 0.1,
    source: Optional[str] = None,
) -> float:
    """
    Exponential decay: a trace loses half its weight every `half_life_days`.

    Args:
        created_at_str: ISO timestamp of the trace creation.
        half_life_days: Days until weight drops to 0.5. Default 90.
        floor: Minimum weight as fraction of base score (prevents total suppression).
        source: Trace source. If 'seed_pack', no decay is applied (timeless).

    Returns:
        Float multiplier in [floor, 1.0]. 1.0 for seed_pack or on parse failure.
    """
    # Seed/synthetic traces are reference material — timeless
    if source == 'seed_pack':
        return 1.0

    if not created_at_str:
        return 1.0

    try:
        ts = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        age_days = (datetime.now(timezone.utc) - ts).days
        decay = math.exp(-math.log(2) * age_days / half_life_days)
        return max(decay, floor)
    except Exception:
        return 1.0
