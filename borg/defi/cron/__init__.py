"""
Borg DeFi Cron — Entry points for scheduled DeFi signal scanning.

This package provides thin async orchestrators that wrap the underlying
DeFi modules (whale_tracker, yield_scanner, alpha_signal, etc.) and
return formatted alert strings ready for delivery (Telegram, Discord, etc.).

Each cron module exposes a single async function that:
1. Instantiates the required scanner/engine
2. Performs the scan
3. Formats alerts for delivery
4. Returns a list of formatted strings

Usage:
    import asyncio
    from borg.defi.cron import run_whale_scan, run_yield_scan, run_alpha_scan

    async def main():
        # Run individual scans
        whale_alerts = await run_whale_scan()
        yield_alerts = await run_yield_scan()
        alpha_alerts = await run_alpha_scan()

        # Send to Telegram, Discord, etc.
        for alert in whale_alerts:
            await send_telegram(alert)

    asyncio.run(main())
"""

from borg.defi.cron.whale_cron import run_whale_scan
from borg.defi.cron.yield_cron import run_yield_scan
from borg.defi.cron.alpha_cron import run_alpha_scan
from borg.defi.cron.portfolio_cron import run_portfolio_report
from borg.defi.cron.liquidation_cron import run_liquidation_scan
from borg.defi.cron.risk_cron import run_risk_check

__all__ = [
    "run_whale_scan",
    "run_yield_scan",
    "run_alpha_scan",
    "run_portfolio_report",
    "run_liquidation_scan",
    "run_risk_check",
]
