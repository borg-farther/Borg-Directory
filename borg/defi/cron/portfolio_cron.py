"""
Portfolio Cron — Scheduled portfolio reporting.

Wraps PortfolioMonitor to generate daily portfolio summaries with P&L
and risk alerts for a dict of wallets across multiple chains.

Usage:
    wallets = {
        "solana": ["Wallet1Addr", "Wallet2Addr"],
        "ethereum": ["0x123..."],
    }
    report = await run_portfolio_report(wallets)
"""

import logging
from typing import Any, Dict, List, Optional

from borg.defi.portfolio_monitor import PortfolioMonitor

logger = logging.getLogger(__name__)


async def run_portfolio_report(
    wallets: Dict[str, List[str]],
    helius_api_key: Optional[str] = None,
    alchemy_api_key: Optional[str] = None,
) -> List[str]:
    """
    Generate daily portfolio summary with P&L for all wallets.

    Args:
        wallets: Dict mapping chain name to list of wallet addresses.
                 Supported chains: 'solana', 'ethereum', 'polygon', 'arbitrum', 'base', 'optimism'.
                 Example:
                     {
                         "solana": ["SolWallet1", "SolWallet2"],
                         "ethereum": ["0xABC...", "0xDEF..."],
                     }
        helius_api_key: Helius API key for Solana portfolio fetching.
        alchemy_api_key: Alchemy API key for EVM portfolio fetching.

    Returns:
        List of formatted Telegram message strings.
        First message is the daily portfolio summary.
        Subsequent messages are individual risk alerts (if any).
        Returns a single "no positions" message if no positions found.
    """
    monitor = PortfolioMonitor(
        helius_api_key=helius_api_key,
        alchemy_api_key=alchemy_api_key,
    )

    all_positions: List[Any] = []
    alerts: List[str] = []

    try:
        # Fetch portfolios for each chain
        for chain, wallet_list in wallets.items():
            for wallet in wallet_list:
                try:
                    if chain == "solana":
                        positions = await monitor.get_solana_portfolio(wallet)
                    else:
                        positions = await monitor.get_evm_portfolio(wallet, chain)

                    if positions:
                        all_positions.extend(positions)
                        logger.debug(f"Fetched {len(positions)} positions for {chain} wallet {wallet[:8]}...")

                except Exception as e:
                    logger.error(f"Error fetching {chain} wallet {wallet[:8]}...: {e}")
                    continue

        if not all_positions:
            logger.info("No positions found for any wallet")
            await monitor.close()
            return ["💼 *Daily Portfolio Report*\n\nNo positions found."]

        # Calculate P&L
        pnl_data = monitor.calculate_pnl(all_positions)

        # Generate risk alerts
        risk_alerts = monitor.risk_alerts(all_positions)
        for risk_alert in risk_alerts:
            alerts.append(risk_alert.message)

        # Format daily report
        daily_report = monitor.format_daily_report(all_positions, pnl_data)
        all_messages = [daily_report] + alerts

        # Save snapshot for historical tracking
        monitor.save_snapshot(all_positions)

        logger.info(
            f"Portfolio report complete: {len(all_positions)} positions, "
            f"total value ${pnl_data['total_value_usd']:,.2f}, "
            f"P&L ${pnl_data['total_pnl_usd']:,.2f}"
        )

        return all_messages

    except Exception as e:
        logger.error(f"Portfolio report error: {e}")
        return [f"💼 *Daily Portfolio Report*\n\nError generating report: {e}"]
    finally:
        await monitor.close()
