"""
Yield Cron — Scheduled yield opportunity scanning.

Wraps YieldScanner to scan DeFiLlama for yield opportunities,
detect yield changes, and return formatted Telegram-ready alert strings.

Usage:
    alerts = await run_yield_scan()
    # Returns top opportunities + any yield change alerts
"""

import logging
from typing import List, Optional

from borg.defi.yield_scanner import YieldScanner

logger = logging.getLogger(__name__)


async def run_yield_scan(
    min_tvl: float = 1_000_000.0,
    max_risk: float = 0.5,
    chains: Optional[List[str]] = None,
    top_n: int = 5,
    change_threshold_pct: float = 20.0,
) -> List[str]:
    """
    Scan DeFiLlama for yield opportunities and yield changes.

    Args:
        min_tvl: Minimum TVL in USD to include a pool (default $1M).
        max_risk: Maximum risk score (0-1) to include a pool (default 0.5).
        chains: Optional list of chains to filter (None = all chains).
                e.g., ['solana', 'ethereum', 'arbitrum']
        top_n: Number of top opportunities to include in the report (default 5).
        change_threshold_pct: Percentage change to trigger a yield change alert (default 20%).

    Returns:
        List of formatted Telegram message strings.
        First message is the top opportunities report.
        Subsequent messages are individual yield change alerts.
        Returns empty list if no opportunities found.
    """
    scanner = YieldScanner(
        min_tvl=min_tvl,
        max_risk=max_risk,
        chains=chains,
    )

    alerts: List[str] = []

    try:
        # Scan DeFiLlama for current opportunities
        opportunities = await scanner.scan_defillama()

        if not opportunities:
            logger.info("No yield opportunities found matching criteria")
            await scanner.close()
            return ["📊 *Yield Scanner*\n\nNo yield opportunities found matching your criteria."]

        # Rank opportunities by risk-adjusted yield
        ranked = scanner.rank_opportunities(opportunities)

        # Format top opportunities
        opportunities_report = scanner.format_telegram(ranked, top_n=top_n)
        alerts.append(opportunities_report)

        # Detect yield changes (compare to previous scan stored in scanner)
        if scanner._previous_pools:
            changes = scanner.detect_yield_changes(
                current=opportunities,
                previous=list(scanner._previous_pools.values()) if hasattr(scanner._previous_pools, 'values') else [],
                threshold_pct=change_threshold_pct,
            )

            for change in changes:
                change_alert = scanner.format_yield_alert(change)
                alerts.append(change_alert)
                logger.debug(f"Yield change: {change.protocol} {change.chain} {change.change_pct:+.1f}%")

        # Update previous pools for next scan
        scanner._previous_pools = {o.pool_id: o for o in opportunities if o.pool_id}

        logger.info(f"Yield scan complete: {len(opportunities)} opportunities, {len(alerts)} alert messages")

    except Exception as e:
        logger.error(f"Yield scan error: {e}")
    finally:
        await scanner.close()

    return alerts
