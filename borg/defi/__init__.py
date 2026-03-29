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
    # Liquidation watcher
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
]
