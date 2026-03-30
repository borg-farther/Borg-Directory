"""
MEV Protection Module for Borg DeFi.

Provides MEV protection through:
- Jito (Solana): Send bundles to Jito block engine for Solana transactions
- Flashbots Protect (EVM): Send bundles to Flashbots relay for Ethereum/EVM transactions

Usage:
    # Solana MEV protection via Jito
    jito = JitoClient()
    tip_accounts = await jito.get_tip_accounts()
    bundle_id = await jito.send_bundle(base64_txs)
    
    # EVM MEV protection via Flashbots
    flashbots = FlashbotsClient(signing_key=private_key)
    bundle_hash = await flashbots.send_bundle(signed_txs, target_block)
"""

from borg.defi.mev.jito import JitoClient
from borg.defi.mev.flashbots import FlashbotsClient

__all__ = [
    "JitoClient",
    "FlashbotsClient",
]
