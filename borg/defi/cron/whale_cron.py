"""
Whale Cron — Scheduled whale activity scanning.

Wraps WhaleTracker to scan all chains (Solana via Helius, EVM via Alchemy)
for whale activity and returns formatted Telegram-ready alert strings.

Usage:
    alerts = await run_whale_scan()
    # With state persistence:
    state = CronState()
    alerts = await run_whale_scan(state=state)
"""

import logging
import time
from typing import Any, Dict, List, Optional

from borg.defi.whale_tracker import WhaleTracker
from borg.defi.cron.state import CronState

logger = logging.getLogger(__name__)


async def run_whale_scan(
    tracked_wallets: Optional[Dict[str, str]] = None,
    min_usd_threshold: float = 50_000.0,
    alert_cooldown: int = 300,
    helius_client: Optional[Any] = None,
    alchemy_clients: Optional[Dict[str, Any]] = None,
    state: Optional[CronState] = None,
) -> List[str]:
    """
    Scan all chains for whale activity and return formatted alerts.

    Args:
        tracked_wallets: Dict of wallet address -> label for tracking.
                         If None, uses an empty tracker (no alerts will fire).
        min_usd_threshold: Minimum USD value to trigger an alert (default $50K).
        alert_cooldown: Seconds between alerts for the same wallet (default 300).
        helius_client: Helius API client for Solana scanning.
                       If None, scanning will return empty results.
        alchemy_clients: Dict of chain name -> Alchemy client for EVM scanning.
                         Keys: 'ethereum', 'base', 'arbitrum', etc.
                         If None, EVM scanning is skipped.
        state: Optional CronState for cooldown tracking across runs.

    Returns:
        List of formatted Telegram message strings, one per whale alert.
        Returns empty list if no alerts generated.
    """
    # Instantiate tracker
    tracker = WhaleTracker(
        tracked_wallets=tracked_wallets or {},
        min_usd_threshold=min_usd_threshold,
        alert_cooldown=alert_cooldown,
    )

    alerts: List[str] = []

    try:
        # Check cooldowns from state if provided
        if state is not None:
            cooldowns = state.get("wallet_cooldowns", {})
            for wallet, last_alert_time in cooldowns.items():
                if time.time() - last_alert_time < alert_cooldown:
                    # Mark wallet as in cooldown
                    tracker._wallet_last_alert[wallet] = last_alert_time

        # Scan Solana if helius_client provided
        if helius_client is not None:
            solana_alerts = await tracker.scan_solana(helius_client)
            for alert in solana_alerts:
                formatted = tracker.format_telegram(alert)
                alerts.append(formatted)
                logger.debug(f"Whale alert: {alert.wallet} {alert.action} ${alert.amount_usd:,.0f}")

        # Scan EVM chains if alchemy_clients provided
        if alchemy_clients is not None:
            for chain, client in alchemy_clients.items():
                evm_alerts = await tracker.scan_evm(client, chain)
                for alert in evm_alerts:
                    formatted = tracker.format_telegram(alert)
                    alerts.append(formatted)
                    logger.debug(f"Whale alert: {alert.wallet} {alert.action} ${alert.amount_usd:,.0f}")

        # Also support scanning all at once
        if helius_client is not None and alchemy_clients is not None:
            all_alerts = await tracker.scan_all(helius_client, alchemy_clients)
            # Avoid double-adding if we already scanned above
            if not alerts:
                for alert in all_alerts:
                    formatted = tracker.format_telegram(alert)
                    alerts.append(formatted)

        # Update cooldowns in state if provided
        if state is not None and alerts:
            cooldowns = state.get("wallet_cooldowns", {})
            for alert in alerts:
                # Extract wallet from formatted alert if possible
                if hasattr(alert, 'wallet'):
                    cooldowns[alert.wallet] = time.time()
                elif hasattr(alert, 'address'):
                    cooldowns[alert.address] = time.time()
            state.set("wallet_cooldowns", cooldowns)

    except Exception as e:
        logger.error(f"Whale scan error: {e}")

    logger.info(f"Whale scan complete: {len(alerts)} alerts")
    return alerts