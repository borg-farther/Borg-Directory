"""
Borg DeFi — DeFi skill packs for the Hermes+Borg agent ecosystem.

Modules:
    - data_models: Dataclasses for DeFi data (WhaleAlert, YieldOpportunity, Position, etc)
    - api_clients: Async API clients for DeFi data providers
        - defillama: DeFiLlama yields API (free, no auth)
        - dexscreener: DexScreener pairs API (free, no auth)
        - helius: Helius Solana RPC (API key required)
        - birdeye: Birdeye token prices (API key required)
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
]
