"""
Seed packs — bootstrap data for Borg DeFi V2.

Creates 5 initial strategy packs with realistic synthetic outcome data
to seed the recommender system. These represent real protocols with
plausible historical performance.

Seed packs:
1. yield/aave-usdc-base      — Aave V3 USDC lending on Base (safest)
2. yield/aave-usdc-ethereum  — Aave V3 USDC on Ethereum
3. yield/compound-usdc-ethereum — Compound V3 USDC
4. yield/kamino-usdc-sol     — Kamino CLMM USDC (higher risk, IL)
5. yield/marinade-sol        — Marinade SOL staking
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import math

from borg.defi.v2.pack_store import PackStore, DeFiStrategyPack
from borg.defi.v2.models import LossPattern, EntryCriteria, ActionSpec, CollectiveStats, RiskAssessment, now_iso, days_ago


def _generate_outcomes(
    n: int,
    avg_return: float,
    std_dev: float,
    min_val: float = None,
    max_val: float = None,
    profitable_ratio: float = 0.9,
    seed: int = 42,
) -> List[float]:
    """Generate synthetic but realistic returns using truncated normal distribution."""
    random.seed(seed)
    outcomes = []

    for _ in range(n):
        # Generate from normal distribution, reject outliers
        while True:
            val = random.gauss(avg_return, std_dev)
            # Most outcomes should be within reasonable bounds
            if min_val is not None and val < min_val:
                continue
            if max_val is not None and val > max_val:
                continue
            outcomes.append(round(val, 2))
            break

    # Ensure roughly the right number of profitable outcomes
    profitable_count = int(n * profitable_ratio)
    # Sort and make the least profitable ones losses
    outcomes.sort()
    for i in range(n - profitable_count):
        outcomes[i] = -abs(outcomes[i])  # Ensure losses are negative

    random.shuffle(outcomes)
    return outcomes


def _compute_stats(returns: List[float]) -> dict:
    """Compute aggregate statistics from a list of returns."""
    import statistics

    profitable = sum(1 for r in returns if r > 0)
    return {
        "total_outcomes": len(returns),
        "profitable": profitable,
        "avg_return_pct": round(statistics.mean(returns), 2),
        "median_return_pct": round(statistics.median(returns), 2),
        "std_dev": round(statistics.stdev(returns) if len(returns) > 1 else 0.0, 2),
        "min_return_pct": round(min(returns), 2),
        "max_return_pct": round(max(returns), 2),
        "last_5_returns": [round(r, 1) for r in returns[-5:]],
    }


def _create_seed_pack(
    pack_id: str,
    name: str,
    version: int,
    tokens: List[str],
    chains: List[str],
    risk_tolerance: List[str],
    action_type: str,
    protocol: str,
    steps: List[str],
    exit_type: str,
    exit_guidance: str,
    n_outcomes: int,
    avg_return: float,
    std_dev: float,
    avg_duration_days: int,
    il_risk: bool,
    rug_score: float,
    protocol_age_days: int,
    audit_status: str,
    min_return_override: float = None,
    max_return_override: float = None,
    profitable_ratio: float = 0.9,
) -> DeFiStrategyPack:
    """Factory function to create a seed pack with synthetic outcomes."""

    # Generate synthetic returns
    returns = _generate_outcomes(
        n_outcomes,
        avg_return,
        std_dev,
        min_val=min_return_override,
        max_val=max_return_override,
        profitable_ratio=profitable_ratio,
        seed=hash(pack_id) % 100000,
    )

    stats = _compute_stats(returns)

    # Determine alpha/beta for Bayesian reputation
    wins = stats["profitable"]
    losses = stats["total_outcomes"] - wins
    alpha = wins + 1  # Jeffreys prior
    beta = losses + 1

    # Confidence interval (Wilson)
    p = wins / stats["total_outcomes"]
    n = stats["total_outcomes"]
    z = 1.96
    denominator = 1 + z**2 / n
    center = p + z**2 / (2 * n)
    spread = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    lower = max(0.0, (center - spread) / denominator)
    upper = min(1.0, (center + spread) / denominator)

    # Loss patterns (only for non-safes)
    loss_patterns = []
    if rug_score > 0.1 or il_risk:
        loss_patterns.append(
            LossPattern(
                pattern="impermanent loss during volatile periods",
                count=1,
                mitigation="monitor position and rebalance if needed",
            )
        )

    # Determine trend from last_5_returns
    last_5 = stats["last_5_returns"]
    recent_mean = sum(last_5) / len(last_5)
    if recent_mean > avg_return + std_dev:
        trend = "improving"
    elif recent_mean < avg_return - std_dev:
        trend = "degrading"
    else:
        trend = "stable"

    return DeFiStrategyPack(
        id=pack_id,
        name=name,
        version=version,
        entry=EntryCriteria(
            tokens=tokens,
            chains=chains,
            min_amount_usd=100,
            risk_tolerance=risk_tolerance,
        ),
        action=ActionSpec(
            type=action_type,
            protocol=protocol,
            steps=steps,
        ),
        exit_guidance=exit_guidance,
        collective=CollectiveStats(
            total_outcomes=stats["total_outcomes"],
            profitable=stats["profitable"],
            alpha=alpha,
            beta=beta,
            avg_return_pct=stats["avg_return_pct"],
            median_return_pct=stats["median_return_pct"],
            std_dev=stats["std_dev"],
            min_return_pct=stats["min_return_pct"],
            max_return_pct=stats["max_return_pct"],
            avg_duration_days=float(avg_duration_days),
            last_5_returns=stats["last_5_returns"],
            trend=trend,
            loss_patterns=[{"pattern": lp.pattern, "count": lp.count, "mitigation": lp.mitigation} for lp in loss_patterns],
        ),
        risk=RiskAssessment(
            il_risk=il_risk,
            rug_score=rug_score,
            protocol_age_days=protocol_age_days,
            audit_status=audit_status,
        ),
        updated_at=now_iso(),
        created_at=days_ago(protocol_age_days),
    )


def create_seed_packs(packs_dir: Path) -> List[DeFiStrategyPack]:
    """
    Create 5 initial seed packs with realistic synthetic data.

    Returns the list of created packs.
    """
    packs_dir = Path(packs_dir)
    store = PackStore(packs_dir)

    packs = []

    # 1. yield/aave-usdc-base — Aave V3 USDC on Base (safest)
    pack1 = _create_seed_pack(
        pack_id="yield/aave-usdc-base",
        name="Aave V3 USDC Lending on Base",
        version=3,
        tokens=["USDC", "USDT", "DAI"],
        chains=["base"],
        risk_tolerance=["low", "medium"],
        action_type="lend",
        protocol="aave-v3",
        steps=[
            "Supply USDC to Aave V3 on Base",
            "Monitor health factor if borrowing against it",
        ],
        exit_type="anytime",
        exit_guidance="No lock period. Withdraw whenever needed.",
        n_outcomes=12,
        avg_return=4.2,
        std_dev=1.2,
        avg_duration_days=30,
        il_risk=False,
        rug_score=0.0,
        protocol_age_days=500,
        audit_status="multiple audits, no critical findings",
        min_return_override=-0.5,
        max_return_override=6.0,
        profitable_ratio=0.92,
    )
    packs.append(pack1)

    # 2. yield/aave-usdc-ethereum — Aave V3 USDC on Ethereum
    pack2 = _create_seed_pack(
        pack_id="yield/aave-usdc-ethereum",
        name="Aave V3 USDC Lending on Ethereum",
        version=4,
        tokens=["USDC", "USDT", "DAI"],
        chains=["ethereum"],
        risk_tolerance=["low", "medium"],
        action_type="lend",
        protocol="aave-v3",
        steps=[
            "Supply USDC to Aave V3 on Ethereum mainnet",
            "Consider supply/borrow optimization for better yields",
        ],
        exit_type="anytime",
        exit_guidance="No lock period. Withdraw whenever needed.",
        n_outcomes=15,
        avg_return=3.8,
        std_dev=1.1,
        avg_duration_days=30,
        il_risk=False,
        rug_score=0.0,
        protocol_age_days=890,
        audit_status="multiple audits, no critical findings",
        min_return_override=-0.4,
        max_return_override=5.5,
        profitable_ratio=0.93,
    )
    packs.append(pack2)

    # 3. yield/compound-usdc-ethereum — Compound V3 USDC
    pack3 = _create_seed_pack(
        pack_id="yield/compound-usdc-ethereum",
        name="Compound V3 USDC Supply",
        version=2,
        tokens=["USDC"],
        chains=["ethereum"],
        risk_tolerance=["low", "medium"],
        action_type="lend",
        protocol="compound-v3",
        steps=[
            "Supply USDC to Compound V3 on Ethereum",
            "Claim COMP rewards regularly",
        ],
        exit_type="anytime",
        exit_guidance="No lock period. Withdraw at any time.",
        n_outcomes=8,
        avg_return=3.5,
        std_dev=0.9,
        avg_duration_days=30,
        il_risk=False,
        rug_score=0.0,
        protocol_age_days=1100,
        audit_status="extensive audits, no critical findings",
        min_return_override=-0.3,
        max_return_override=4.8,
        profitable_ratio=0.88,
    )
    packs.append(pack3)

    # 4. yield/kamino-usdc-sol — Kamino CLMM USDC (higher risk, IL)
    pack4 = _create_seed_pack(
        pack_id="yield/kamino-usdc-sol",
        name="Kamino CLMM USDC-SOL Liquidity Pool",
        version=2,
        tokens=["USDC", "SOL"],
        chains=["solana"],
        risk_tolerance=["medium", "high"],
        action_type="lp",
        protocol="kamino",
        steps=[
            "Deposit USDC (and SOL for stability) into Kamino CLMM",
            "Monitor position and rebalance as needed",
        ],
        exit_type="anytime",
        exit_guidance="Withdraw liquidity when risk becomes excessive or for rebalancing.",
        n_outcomes=7,
        avg_return=23.0,
        std_dev=12.0,
        avg_duration_days=45,
        il_risk=True,
        rug_score=0.05,
        protocol_age_days=365,
        audit_status="1 audit, minor findings resolved",
        min_return_override=-15.0,
        max_return_override=55.0,
        profitable_ratio=0.85,
    )
    packs.append(pack4)

    # 5. yield/marinade-sol — Marinade FIN stake
    pack5 = _create_seed_pack(
        pack_id="yield/marinade-sol",
        name="Marinade FIN SOL Staking",
        version=2,
        tokens=["SOL"],
        chains=["solana"],
        risk_tolerance=["low", "medium"],
        action_type="stake",
        protocol="marinade",
        steps=[
            "Stake SOL via Marinade FIN",
            "Receive mSOL derivative (earning staking rewards)",
        ],
        exit_type="anytime",
        exit_guidance="Unstake via Marinade (small delay for validator queue).",
        n_outcomes=10,
        avg_return=6.5,
        std_dev=1.5,
        avg_duration_days=30,
        il_risk=False,
        rug_score=0.0,
        protocol_age_days=720,
        audit_status="2 audits, no critical findings",
        min_return_override=4.0,
        max_return_override=9.5,
        profitable_ratio=1.0,
    )
    packs.append(pack5)

    # Save all packs
    for pack in packs:
        store.save_pack(pack)

    return packs


def verify_seed_packs(packs_dir: Path) -> bool:
    """
    Verify that seed packs were created correctly.
    Returns True if all 5 packs load without errors.
    """
    store = PackStore(packs_dir)

    expected_ids = [
        "yield/aave-usdc-base",
        "yield/aave-usdc-ethereum",
        "yield/compound-usdc-ethereum",
        "yield/kamino-usdc-sol",
        "yield/marinade-sol",
    ]

    for pack_id in expected_ids:
        pack = store.load_pack(pack_id)
        if pack is None:
            print(f"Missing pack: {pack_id}")
            return False

        # Verify basic stats
        if pack.collective.total_outcomes <= 0:
            print(f"Invalid outcomes for {pack_id}")
            return False
        if pack.collective.avg_return_pct <= 0:
            print(f"Invalid avg_return for {pack_id}")
            return False
        if pack.collective.reputation <= 0 or pack.collective.reputation > 1:
            print(f"Invalid reputation for {pack_id}")
            return False

    return True
