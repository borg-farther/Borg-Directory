"""
Borg DeFi — DeFi skill packs for the Hermes+Borg agent ecosystem.

Modules:
    - data_models: Dataclasses for DeFi data (WhaleAlert, YieldOpportunity, Position, etc)
    - api_clients: Async API clients for DeFi data providers
        - defillama: DeFiLlama yields API (free, no auth)
        - dexscreener: DexScreener pairs API (free, no auth)
        - helius: Helius Solana RPC (API key required)
        - birdeye: Birdeye token prices (API key required)
    - liquidation_watcher: Aave V3 / Compound V3 liquidation opportunity detection
    - whale_tracker: Whale wallet monitoring across chains (Phase 1)
    - yield_scanner: DeFiLlama yield opportunity scanning (Phase 1)
    - portfolio_monitor: Cross-chain portfolio tracking with P&L (Phase 2)
    - liquidation_watcher: Aave V3 / Compound V3 liquidation detection (Phase 2)
    - alpha_signal: Smart money, volume spikes, new pairs, bridge flows (Phase 3)
    - risk_engine: Correlation, protocol risk, concentration, drawdown (Phase 3)
    - strategy_backtester: Historical backtesting for DeFi strategies (Phase 3)
    - cron: Scheduled task entry points for all signal types (Phase 3)
"""

from borg.defi.data_models import (
    WhaleAlert,
    YieldOpportunity,
    Position,
    DeFiPackMetadata,
    TokenPrice,
    OHLCV,
    Transaction,
    DexPair,
)

from borg.defi.api_clients.defillama import DeFiLlamaClient
from borg.defi.api_clients.dexscreener import DexScreenerClient
from borg.defi.api_clients.helius import HeliusClient
from borg.defi.api_clients.birdeye import BirdeyeClient

from borg.defi.liquidation_watcher import (
    LiquidationTarget,
    scan_aave_positions,
    scan_compound_positions,
    scan_all_positions,
    estimate_liquidation_profit,
    format_alert,
    generate_cron_entry,
    run_watcher,
    Protocol,
    LIQUIDATION_THRESHOLD,
)

# Phase 3 modules
from borg.defi.alpha_signal import (
    AlphaSignalEngine,
    SmartMoneyFlow,
    VolumeSpike,
    NewPairAlert,
    BridgeFlow,
)

from borg.defi.risk_engine import (
    RiskEngine,
    CorrelationResult,
    ProtocolRiskResult,
    ConcentrationRiskResult,
    DrawdownResult,
)

from borg.defi.strategy_backtester import (
    StrategyBacktester,
    BacktestTrade,
    BacktestResult,
    WhaleReplayResult,
    LPSimulationResult,
    PerformanceMetrics,
)

# Cron entry points
from borg.defi.cron import (
    run_whale_scan,
    run_yield_scan,
    run_alpha_scan,
    run_portfolio_report,
    run_liquidation_scan,
    run_risk_check,
)

__all__ = [
    # Data models
    "WhaleAlert",
    "YieldOpportunity",
    "Position",
    "DeFiPackMetadata",
    "TokenPrice",
    "OHLCV",
    "Transaction",
    "DexPair",
    # API clients
    "DeFiLlamaClient",
    "DexScreenerClient",
    "HeliusClient",
    "BirdeyeClient",
    # Liquidation watcher (Phase 2)
    "LiquidationTarget",
    "scan_aave_positions",
    "scan_compound_positions",
    "scan_all_positions",
    "estimate_liquidation_profit",
    "format_alert",
    "generate_cron_entry",
    "run_watcher",
    "Protocol",
    "LIQUIDATION_THRESHOLD",
    # Alpha Signal Engine (Phase 3)
    "AlphaSignalEngine",
    "SmartMoneyFlow",
    "VolumeSpike",
    "NewPairAlert",
    "BridgeFlow",
    # Risk Engine (Phase 3)
    "RiskEngine",
    "CorrelationResult",
    "ProtocolRiskResult",
    "ConcentrationRiskResult",
    "DrawdownResult",
    # Strategy Backtester (Phase 3)
    "StrategyBacktester",
    "BacktestTrade",
    "BacktestResult",
    "WhaleReplayResult",
    "LPSimulationResult",
    "PerformanceMetrics",
    # Cron entry points (Phase 3)
    "run_whale_scan",
    "run_yield_scan",
    "run_alpha_scan",
    "run_portfolio_report",
    "run_liquidation_scan",
    "run_risk_check",
]
