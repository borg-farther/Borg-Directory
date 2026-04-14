"""
Liquidation Cron — Scheduled liquidation opportunity scanning.

Wraps liquidation_watcher.scan_all_positions() to scan Aave V3
and Compound V3 positions across all supported chains for liquidation
opportunities and returns formatted Telegram-ready alert strings.

Usage:
    alerts = await run_liquidation_scan()
"""

import logging
from typing import List, Optional

from borg.defi.liquidation_watcher import scan_all_positions, format_alert, LiquidationTarget

logger = logging.getLogger(__name__)


async def run_liquidation_scan(
    chains: Optional[List[str]] = None,
    health_threshold: float = 1.1,
    min_profit_usd: float = 100.0,
    format_style: str = "telegram",
) -> List[str]:
    """
    Scan for liquidation opportunities across Aave V3 and Compound V3.

    Args:
        chains: List of chains to scan (default: ['ethereum', 'arbitrum', 'base', 'optimism']).
        health_threshold: Health factor threshold for at-risk positions (default 1.1).
        min_profit_usd: Minimum estimated profit in USD to include an alert (default $100).
        format_style: Message format 'telegram' or 'discord' (default: 'telegram').

    Returns:
        List of formatted Telegram message strings, one per liquidation opportunity.
        Returns empty list if no opportunities found above the profit threshold.
    """
    alerts: List[str] = []

    try:
        # Use scan_all_positions for one-shot scanning (not run_watcher which loops forever)
        targets: List[LiquidationTarget] = await scan_all_positions(
            chains=chains,
            health_threshold=health_threshold,
        )

        for target in targets:
            # Filter by minimum profit
            if target.potential_profit_usd < min_profit_usd:
                continue

            # Format the alert
            formatted = format_alert(target, format=format_style)
            alerts.append(formatted)
            logger.debug(
                f"Liquidation opportunity: {target.protocol} on {target.chain} "
                f"HF={target.health_factor:.4f}, profit=${target.potential_profit_usd:,.2f}"
            )

        logger.info(f"Liquidation scan complete: {len(targets)} at-risk positions, {len(alerts)} profitable alerts")

    except Exception as e:
        logger.error(f"Liquidation scan error: {e}")

    return alerts
