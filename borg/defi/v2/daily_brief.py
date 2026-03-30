"""
Borg DeFi V2 — Daily Brief Generator.

Portfolio-first daily digest. Replaces V1 data firehose crons
with one concise message that answers "what should I know today?"

Under 2000 chars. Telegram-friendly. No chunking needed.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from borg.defi.v2.recommender import DeFiRecommender
from borg.defi.v2.models import StrategyQuery

logger = logging.getLogger(__name__)

DEFAULT_PACKS_DIR = Path.home() / ".hermes" / "borg" / "defi" / "packs"


async def generate_daily_brief(
    packs_dir: Path = DEFAULT_PACKS_DIR,
    risk_tolerance: str = "medium",
    chains: Optional[List[str]] = None,
    tokens: Optional[List[str]] = None,
) -> str:
    """
    Generate a concise daily brief from V2 collective intelligence.

    Returns a Telegram-ready message under 2000 chars.
    """
    now = datetime.now(timezone.utc).strftime("%a %d %b %H:%M UTC")
    lines = [f"🧠 BORG DAILY BRIEF — {now}\n"]

    recommender = DeFiRecommender(packs_dir=packs_dir)

    # Section 1: Top recommendations
    query_tokens = tokens or ["USDC", "ETH", "SOL"]
    query_chains = chains or ["base", "ethereum", "solana"]

    all_recs = []
    for token in query_tokens[:3]:
        for chain in query_chains[:2]:
            try:
                recs = recommender.recommend(
                    StrategyQuery(token=token, chain=chain, risk_tolerance=risk_tolerance),
                    limit=1,
                )
                all_recs.extend(recs)
            except Exception:
                pass

    if all_recs:
        # Deduplicate and take top 3
        seen = set()
        top = []
        for r in sorted(all_recs, key=lambda x: x.confidence, reverse=True):
            if r.pack_id not in seen:
                seen.add(r.pack_id)
                top.append(r)
            if len(top) >= 3:
                break

        lines.append("📊 TOP STRATEGIES (collective evidence):")
        for r in top:
            win_rate = f"{r.profitable_count}/{r.agent_count}" if r.agent_count > 0 else "?"
            conf = "🟢" if r.confidence > 0.6 else "🟡" if r.confidence > 0.3 else "🔴"
            lines.append(
                f"  {conf} {r.protocol} | {r.avg_return_pct:.1f}% avg | "
                f"{win_rate} profitable"
            )
    else:
        lines.append("📊 No strategies with sufficient collective data yet.")
        lines.append("   The collective grows with each agent's outcomes.")

    # Section 2: Active warnings
    warnings = recommender.get_active_warnings()
    if warnings:
        lines.append(f"\n⚠️ ACTIVE WARNINGS ({len(warnings)}):")
        for w in warnings[:3]:
            pack_id = w.get("pack_id", w.get("id", "unknown"))
            reason = w.get("reason", w.get("guidance", ""))[:60]
            lines.append(f"  🚨 {pack_id}: {reason}")
    else:
        lines.append("\n✅ No active warnings.")

    # Section 3: Collective stats
    all_packs = recommender.pack_store.list_packs()
    total_outcomes = sum(p.collective.total_outcomes for p in all_packs)
    high_conf = sum(1 for p in all_packs if p.collective.total_outcomes >= 10)
    tripped = recommender.circuit_breaker.get_tripped_packs() if hasattr(recommender, 'circuit_breaker') and recommender.circuit_breaker else []

    lines.append(f"\n📈 COLLECTIVE: {len(all_packs)} packs | {total_outcomes} outcomes | {high_conf} high-confidence")
    if tripped:
        lines.append(f"   🔴 {len(tripped)} packs circuit-breaker tripped")

    # Section 4: Market pulse (from free API if available)
    try:
        from borg.defi.cron.live_scans import _fetch_json
        protocols = await _fetch_json("https://api.llama.fi/protocols")
        if isinstance(protocols, list):
            total_tvl = sum(p.get("tvl", 0) or 0 for p in protocols if (p.get("tvl") or 0) > 10_000_000)
            lines.append(f"\n💰 DeFi TVL: ${total_tvl / 1e9:.0f}B")
    except Exception:
        pass  # Market data is optional

    # Footer
    lines.append("\n— The Collective")

    result = "\n".join(lines)

    # Ensure under 2000 chars
    if len(result) > 1950:
        result = result[:1947] + "..."

    return result


def generate_daily_brief_sync(**kwargs) -> str:
    """Synchronous wrapper for generate_daily_brief."""
    return asyncio.run(generate_daily_brief(**kwargs))


if __name__ == "__main__":
    print(asyncio.run(generate_daily_brief()))
