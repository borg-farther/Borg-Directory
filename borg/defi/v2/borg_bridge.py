"""
Borg bridge — integration between DeFi V2 and borg core search.

Provides natural language DeFi search via borg_search_defi() which:
1. Parses natural language queries
2. Calls the recommender
3. Formats results for Telegram/agent display

Examples:
    borg_search_defi("yield strategies on base")
    borg_search_defi("best strategy for idle USDC")
    borg_search_defi("warnings for solana protocols")
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from borg.defi.v2.models import StrategyQuery, StrategyRecommendation, now_iso
from borg.defi.v2.recommender import DeFiRecommender
from borg.defi.v2.pack_store import PackStore
from borg.defi.v2.warnings import WarningManager
from borg.defi.v2.drift import detect_drift


# Token aliases for natural language
TOKEN_ALIASES = {
    "usdc": "USDC",
    "usd coin": "USDC",
    "usdt": "USDT",
    "tether": "USDT",
    "dai": "DAI",
    "sol": "SOL",
    "solana": "SOL",
    "eth": "ETH",
    "ethereum": "ETH",
    "btc": "BTC",
    "bitcoin": "BTC",
    "weth": "WETH",
    "wbeth": "WBETH",
}

# Chain aliases
CHAIN_ALIASES = {
    "base": "base",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "solana": "solana",
    "sol": "solana",
    "arbitrum": "arbitrum",
    "arb": "arbitrum",
    "polygon": "polygon",
    "matic": "polygon",
    "avalanche": "avalanche",
    "avax": "avalanche",
    "optimism": "optimism",
    "op": "optimism",
}

# Risk aliases
RISK_ALIASES = {
    "safe": "low",
    "safest": "low",
    "low risk": "low",
    "low": "low",
    "medium": "medium",
    "moderate": "medium",
    "high": "high",
    "high risk": "high",
    "degen": "degen",
    "degem": "degen",
    "yolo": "degen",
}

# Action type keywords
ACTION_KEYWORDS = {
    "lend": "lend",
    "lending": "lend",
    "supply": "lend",
    "yield": "lend",
    "lp": "lp",
    "liquidity": "lp",
    "add liquidity": "lp",
    "swap": "swap",
    "exchange": "swap",
    "trade": "swap",
    "stake": "stake",
    "staking": "stake",
    "farm": "lp",
}


def parse_natural_query(query: str) -> StrategyQuery:
    """
    Parse a natural language query into a StrategyQuery.

    Extracts: token, chain, risk, action_type from free text.

    Examples:
        "yield strategies on base"         -> token=USDC, chain=base
        "best strategy for idle USDC"      -> token=USDC, risk=low
        "high yield on solana"             -> chain=solana
        "safe lending on ethereum"         -> token?, chain=ethereum, risk=low
        "LP on arbitrum"                   -> action_type=lp, chain=arbitrum
    """
    query_lower = query.lower()
    tokens_found = []
    chains_found = []
    risks_found = []
    action_type = None
    protocol = None

    # Extract tokens
    for alias, token in TOKEN_ALIASES.items():
        if alias in query_lower:
            if token not in tokens_found:
                tokens_found.append(token)

    # Extract chains
    for alias, chain in CHAIN_ALIASES.items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, query_lower):
            if chain not in chains_found:
                chains_found.append(chain)

    # Extract risk
    for alias, risk in RISK_ALIASES.items():
        if alias in query_lower:
            if risk not in risks_found:
                risks_found.append(risk)

    # Extract action type
    for keywords, atype in ACTION_KEYWORDS.items():
        if keywords in query_lower:
            action_type = atype
            break

    # Extract protocol names (simple keyword matching)
    PROTOCOLS = ["aave", "compound", "kamino", "marinade", "raydium", "jupiter", "orca"]
    for proto in PROTOCOLS:
        if proto in query_lower:
            protocol = proto
            break

    # Handle "idle USDC" -> assume low risk
    if "idle" in query_lower and tokens_found and not risks_found:
        risks_found.append("low")

    # Build query
    sq = StrategyQuery(
        token=tokens_found[0] if tokens_found else None,
        chain=chains_found[0] if chains_found else None,
        risk_tolerance=risks_found[0] if risks_found else "medium",
        action_type=action_type,
        protocol=protocol,
    )

    return sq

def borg_search_defi(query: str) -> str:
    """
    Natural language DeFi search via borg.

    Returns formatted recommendations string.

    Examples:
        borg_search_defi("yield strategies on base")
        borg_search_defi("best strategy for idle USDC")
    """
    # Parse query
    sq = parse_natural_query(query)

    # Get recommender
    try:
        recommender = DeFiRecommender()
    except Exception:
        # If dirs don't exist, return empty
        return "No DeFi data available. Initialize with create_seed_packs()."

    # Check for warnings
    warnings_manager = WarningManager()
    active_warnings = warnings_manager.get_active_warnings(
        chain=sq.chain,
        protocol=sq.protocol,
    )

    # Get recommendations
    recs = recommender.recommend(sq)

    # Check for drift alerts
    drift_alerts = []
    for rec in recs:
        pack = recommender.get_pack(rec.pack_id)
        if pack:
            drift = detect_drift(pack)
            if drift:
                drift_alerts.append({"pack_id": rec.pack_id, "drift": drift})

    # Format and return
    return format_brief(recs, active_warnings, drift_alerts)


def format_recommendation(rec: StrategyRecommendation) -> str:
    """
    Format a single recommendation for human-readable output (Telegram/agent).
    """
    lines = []

    # Header
    lines.append(f"  {rec.name or rec.pack_id}")
    lines.append(f"  {rec.protocol} on {rec.chain} | {rec.token}")

    # Key stats
    win_rate = (
        f"{(rec.profitable_count / rec.total_outcomes * 100):.0f}%"
        if rec.total_outcomes > 0
        else "N/A"
    )
    lines.append(
        f"  {rec.total_outcomes} outcomes | {win_rate} profitable | "
        f"{rec.avg_return_pct:.1f}% avg return"
    )

    # Risk
    risk_tags = ", ".join(rec.risk_tolerance)
    lines.append(f"  Risk: {risk_tags}" + (f" | IL: Yes" if rec.il_risk else ""))

    # Trend
    trend_emoji = {"improving": "+", "stable": "~", "degrading": "-"}[rec.trend]
    lines.append(f"  Trend: {trend_emoji} {rec.trend}")

    # Confidence
    conf_pct = rec.confidence * 100
    lines.append(f"  Confidence: {conf_pct:.0f}%")

    # Warnings and drift
    if rec.warning:
        lines.append(f"  WARNING: {rec.warning}")
    if rec.drift_alert:
        lines.append(f"  DRIFT: {rec.drift_alert}")

    # Score breakdown (optional, only if available)
    if rec.score_components:
        sc = rec.score_components
        lines.append(
            f"  Score: {sc.get('total', 0):.2f} "
            f"(Thompson={sc.get('thompson', 0):.2f}, "
            f"Return={sc.get('return', 0):.2f}, "
            f"Confidence={sc.get('confidence', 0):.2f})"
        )

    return "\n".join(lines)


def format_brief(
    recs: List[StrategyRecommendation],
    warnings: List[Dict[str, Any]],
    drift_alerts: List[Dict[str, str]],
) -> str:
    """
    Format a daily digest of recommendations, warnings, and drift alerts.
    """
    lines = []

    lines.append("=" * 50)
    lines.append("Borg DeFi Daily Brief")
    lines.append("=" * 50)

    # Warnings section
    if warnings:
        lines.append(f"\n⚠️  ACTIVE WARNINGS ({len(warnings)})")
        lines.append("-" * 40)
        for w in warnings[:5]:
            lines.append(f"  [{w['severity'].upper()}] {w['pack_id']}")
            lines.append(f"  {w['reason']}")
            lines.append(f"  Guidance: {w['guidance']}")
            lines.append("")

    # Drift alerts section
    if drift_alerts:
        lines.append(f"\n📉 DRIFT ALERTS ({len(drift_alerts)})")
        lines.append("-" * 40)
        for alert in drift_alerts[:5]:
            lines.append(f"  {alert['pack_id']}: {alert['drift']}")
        lines.append("")

    # Recommendations section
    if recs:
        lines.append(f"\n📊 TOP RECOMMENDATIONS ({len(recs)})")
        lines.append("-" * 40)
        for i, rec in enumerate(recs, 1):
            lines.append(f"\n{i}. {rec.name or rec.pack_id}")
            lines.append(format_recommendation(rec))
    else:
        lines.append("\nNo recommendations found for your query.")

    lines.append("\n" + "=" * 50)

    return "\n".join(lines)
