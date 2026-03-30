"""
Borg DeFi — DeFi skill packs for the Hermes+Borg agent ecosystem.

Optional dependency: pip install agent-borg[defi]

All imports are lazy — this module can be imported without aiohttp/cryptography
installed, but will raise ImportError with a helpful message when you try to
use any DeFi class.
"""
from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Static analysis / IDE support — these imports are never executed at runtime
    from borg.defi.data_models import (
        WhaleAlert, YieldOpportunity, Position, DeFiPackMetadata,
        TokenPrice, OHLCV, Transaction, DexPair,
    )
    from borg.defi.api_clients.defillama import DeFiLlamaClient
    from borg.defi.api_clients.dexscreener import DexScreenerClient
    from borg.defi.api_clients.helius import HeliusClient
    from borg.defi.api_clients.birdeye import BirdeyeClient
    from borg.defi.api_clients.goplus import GoPlusClient
    from borg.defi.api_clients.alchemy import AlchemyClient
    from borg.defi.api_clients.arkham import ArkhamClient
    from borg.defi.whale_tracker import WhaleTracker
    from borg.defi.yield_scanner import YieldScanner
    from borg.defi.portfolio_monitor import PortfolioMonitor
    from borg.defi.swap_executor import SwapExecutor
    from borg.defi.lp_manager import LPManager
    from borg.defi.alpha_signal import AlphaSignalEngine
    from borg.defi.risk_engine import RiskEngine
    from borg.defi.strategy_backtester import StrategyBacktester
    from borg.defi.dojo_bridge import DojoBridge
    from borg.defi.mev.jito import JitoClient
    from borg.defi.mev.flashbots import FlashbotsClient
    from borg.defi.cron.state import CronState
    from borg.defi.cron.delivery import deliver_alerts


def _check_defi_deps():
    """Check that defi optional dependencies are installed."""
    try:
        import aiohttp  # noqa: F401
    except ImportError:
        raise ImportError(
            "Borg DeFi requires the 'defi' extra. Install with:\n"
            "  pip install agent-borg[defi]"
        ) from None


# Lazy attribute map: name -> (module_path, attr_name)
_LAZY_IMPORTS = {
    # Data models (no external deps, always available)
    "WhaleAlert": ("borg.defi.data_models", "WhaleAlert"),
    "YieldOpportunity": ("borg.defi.data_models", "YieldOpportunity"),
    "Position": ("borg.defi.data_models", "Position"),
    "DeFiPackMetadata": ("borg.defi.data_models", "DeFiPackMetadata"),
    "TokenPrice": ("borg.defi.data_models", "TokenPrice"),
    "OHLCV": ("borg.defi.data_models", "OHLCV"),
    "Transaction": ("borg.defi.data_models", "Transaction"),
    "DexPair": ("borg.defi.data_models", "DexPair"),
    # API clients (need aiohttp)
    "DeFiLlamaClient": ("borg.defi.api_clients.defillama", "DeFiLlamaClient"),
    "DexScreenerClient": ("borg.defi.api_clients.dexscreener", "DexScreenerClient"),
    "HeliusClient": ("borg.defi.api_clients.helius", "HeliusClient"),
    "BirdeyeClient": ("borg.defi.api_clients.birdeye", "BirdeyeClient"),
    "GoPlusClient": ("borg.defi.api_clients.goplus", "GoPlusClient"),
    "AlchemyClient": ("borg.defi.api_clients.alchemy", "AlchemyClient"),
    "ArkhamClient": ("borg.defi.api_clients.arkham", "ArkhamClient"),
    # Core modules
    "WhaleTracker": ("borg.defi.whale_tracker", "WhaleTracker"),
    "YieldScanner": ("borg.defi.yield_scanner", "YieldScanner"),
    "PortfolioMonitor": ("borg.defi.portfolio_monitor", "PortfolioMonitor"),
    "SwapExecutor": ("borg.defi.swap_executor", "SwapExecutor"),
    "LPManager": ("borg.defi.lp_manager", "LPManager"),
    "AlphaSignalEngine": ("borg.defi.alpha_signal", "AlphaSignalEngine"),
    "RiskEngine": ("borg.defi.risk_engine", "RiskEngine"),
    "StrategyBacktester": ("borg.defi.strategy_backtester", "StrategyBacktester"),
    "DojoBridge": ("borg.defi.dojo_bridge", "DojoBridge"),
    # MEV
    "JitoClient": ("borg.defi.mev.jito", "JitoClient"),
    "FlashbotsClient": ("borg.defi.mev.flashbots", "FlashbotsClient"),
    # Strategy
    "StrategySelector": ("borg.defi.strategy_selector", "StrategySelector"),
    # Cron
    "CronState": ("borg.defi.cron.state", "CronState"),
    "deliver_alerts": ("borg.defi.cron.delivery", "deliver_alerts"),
    "run_whale_scan": ("borg.defi.cron.whale_cron", "run_whale_scan"),
    "run_yield_scan": ("borg.defi.cron.yield_cron", "run_yield_scan"),
    "run_alpha_scan": ("borg.defi.cron.alpha_cron", "run_alpha_scan"),
    "run_portfolio_report": ("borg.defi.cron.portfolio_cron", "run_portfolio_report"),
    "run_liquidation_scan": ("borg.defi.cron.liquidation_cron", "run_liquidation_scan"),
    "run_risk_check": ("borg.defi.cron.risk_cron", "run_risk_check"),
    # Liquidation watcher top-level functions
    "LiquidationTarget": ("borg.defi.liquidation_watcher", "LiquidationTarget"),
    "scan_aave_positions": ("borg.defi.liquidation_watcher", "scan_aave_positions"),
    "scan_compound_positions": ("borg.defi.liquidation_watcher", "scan_compound_positions"),
    "scan_all_positions": ("borg.defi.liquidation_watcher", "scan_all_positions"),
    "run_watcher": ("borg.defi.liquidation_watcher", "run_watcher"),
    "Protocol": ("borg.defi.liquidation_watcher", "Protocol"),
}

# Data model names that don't need aiohttp
_NO_DEPS_NEEDED = {
    "WhaleAlert", "YieldOpportunity", "Position", "DeFiPackMetadata",
    "TokenPrice", "OHLCV", "Transaction", "DexPair",
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        if name not in _NO_DEPS_NEEDED:
            _check_defi_deps()
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_LAZY_IMPORTS.keys())
