"""
Alpha Cron — Scheduled alpha signal detection.

Wraps AlphaSignalEngine to run all 4 detection methods:
- Smart money flow detection
- Volume spike detection
- New DEX pair monitoring
- Bridge flow detection

Returns formatted Telegram-ready alert strings.

Usage:
    alerts = await run_alpha_scan()
    # With state persistence for signal caching:
    state = CronState()
    alerts = await run_alpha_scan(state=state)
"""

import logging
from typing import Any, Dict, List, Optional

from borg.defi.alpha_signal import AlphaSignalEngine
from borg.defi.cron.state import CronState

logger = logging.getLogger(__name__)


async def run_alpha_scan(
    smart_money_wallets: Optional[Dict[str, Any]] = None,
    tokens: Optional[List[str]] = None,
    chains: Optional[List[str]] = None,
    helius_client: Optional[Any] = None,
    birdeye_client: Optional[Any] = None,
    dexscreener_client: Optional[Any] = None,
    min_smart_money_threshold: float = 10_000.0,
    min_bridge_threshold: float = 25_000.0,
    volume_spike_threshold: float = 3.0,
    new_pair_min_liquidity: float = 10_000.0,
    state: Optional[CronState] = None,
) -> List[str]:
    """
    Run all alpha signal detections and return formatted alerts.

    Args:
        smart_money_wallets: Dict of wallet address -> SmartMoneyWallet for tracking.
        tokens: List of token addresses for volume spike monitoring.
        chains: List of chains to monitor for new pairs (default: ['solana', 'ethereum', 'base', 'arbitrum']).
        helius_client: Helius API client for Solana wallet/bridge scanning.
        birdeye_client: Birdeye API client for price/volume data.
        dexscreener_client: DexScreener API client for new pair monitoring.
        min_smart_money_threshold: Minimum USD value for smart money flow alerts (default $10K).
        min_bridge_threshold: Minimum USD value for bridge flow alerts (default $25K).
        volume_spike_threshold: Multiplier for volume spike detection (default 3.0x baseline).
        new_pair_min_liquidity: Minimum liquidity for new pair alerts (default $10K).
        state: Optional CronState for tracking seen signals (avoid duplicates).

    Returns:
        List of formatted Telegram message strings, one per alpha signal.
        Returns empty list if no signals detected.
    """
    # Build engine with configuration
    engine = AlphaSignalEngine(
        smart_money_wallets=smart_money_wallets or {},
        volume_spike_threshold=volume_spike_threshold,
    )

    alerts: List[str] = []

    try:
        # Load seen signals from state to avoid duplicates
        seen_signals = set()
        if state is not None:
            seen_signals = set(state.get("seen_signals", []))

        # Run all detection methods in parallel via scan_all
        if helius_client is not None and birdeye_client is not None and dexscreener_client is not None:
            results = await engine.scan_all(
                helius_client=helius_client,
                birdeye_client=birdeye_client,
                dexscreener_client=dexscreener_client,
                tokens=tokens or [],
            )

            # Process smart money flows
            for flow in results.get("smart_money_flows", []):
                signal_id = f"sm_{flow.wallet}_{flow.timestamp}"
                if signal_id not in seen_signals and flow.amount_usd >= min_smart_money_threshold:
                    formatted = engine.format_smart_money_telegram(flow)
                    alerts.append(formatted)
                    seen_signals.add(signal_id)
                    logger.debug(f"Smart money flow: {flow.wallet} {flow.flow_type} ${flow.amount_usd:,.0f}")

            # Process volume spikes
            for spike in results.get("volume_spikes", []):
                signal_id = f"vs_{spike.token_symbol}_{spike.timestamp}"
                if signal_id not in seen_signals:
                    formatted = engine.format_volume_spike_telegram(spike)
                    alerts.append(formatted)
                    seen_signals.add(signal_id)
                    logger.debug(f"Volume spike: {spike.token_symbol} {spike.volume_change_pct:+.0f}%")

            # Process new pairs
            for pair_alert in results.get("new_pairs", []):
                signal_id = f"np_{pair_alert.pair.base_token}_{pair_alert.timestamp}"
                if signal_id not in seen_signals:
                    formatted = engine.format_new_pair_telegram(pair_alert)
                    alerts.append(formatted)
                    seen_signals.add(signal_id)
                    logger.debug(f"New pair: {pair_alert.pair.base_token}/{pair_alert.pair.quote_token}")

            # Process bridge flows
            for flow in results.get("bridge_flows", []):
                signal_id = f"bf_{flow.wallet}_{flow.timestamp}"
                if signal_id not in seen_signals and flow.amount_usd >= min_bridge_threshold:
                    formatted = engine.format_bridge_flow_telegram(flow)
                    alerts.append(formatted)
                    seen_signals.add(signal_id)
                    logger.debug(f"Bridge flow: {flow.wallet} {flow.source_chain}->{flow.destination_chain} ${flow.amount_usd:,.0f}")

        else:
            # Fallback: run individual detections if clients available
            if helius_client is not None and birdeye_client is not None:
                # Smart money detection
                smart_money = await engine.detect_smart_money_flow(
                    helius_client, birdeye_client, min_smart_money_threshold
                )
                for flow in smart_money:
                    signal_id = f"sm_{flow.wallet}_{flow.timestamp}"
                    if signal_id not in seen_signals:
                        alerts.append(engine.format_smart_money_telegram(flow))
                        seen_signals.add(signal_id)

                # Bridge flow detection
                bridge_flows = await engine.detect_bridge_flows(
                    helius_client, birdeye_client, min_bridge_threshold
                )
                for flow in bridge_flows:
                    signal_id = f"bf_{flow.wallet}_{flow.timestamp}"
                    if signal_id not in seen_signals:
                        alerts.append(engine.format_bridge_flow_telegram(flow))
                        seen_signals.add(signal_id)

            # Volume spikes
            if birdeye_client is not None and tokens:
                volume_spikes = await engine.detect_volume_spikes(
                    birdeye_client, tokens, chains or ["solana"]
                )
                for spike in volume_spikes:
                    signal_id = f"vs_{spike.token_symbol}_{spike.timestamp}"
                    if signal_id not in seen_signals:
                        alerts.append(engine.format_volume_spike_telegram(spike))
                        seen_signals.add(signal_id)

            # New pairs
            if dexscreener_client is not None:
                new_pairs = await engine.monitor_new_pairs(
                    dexscreener_client, chains, new_pair_min_liquidity
                )
                for pair_alert in new_pairs:
                    signal_id = f"np_{pair_alert.pair.base_token}_{pair_alert.timestamp}"
                    if signal_id not in seen_signals:
                        alerts.append(engine.format_new_pair_telegram(pair_alert))
                        seen_signals.add(signal_id)

        # Save seen signals to state
        if state is not None and seen_signals:
            # Limit the size of seen_signals to avoid unbounded growth
            MAX_SEEN_SIGNALS = 1000
            if len(seen_signals) > MAX_SEEN_SIGNALS:
                seen_signals = set(list(seen_signals)[-MAX_SEEN_SIGNALS:])
            state.set("seen_signals", list(seen_signals))

    except Exception as e:
        logger.error(f"Alpha scan error: {e}")

    logger.info(f"Alpha scan complete: {len(alerts)} signals detected")
    return alerts