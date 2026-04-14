"""
DexScreener API client.

Free API, no auth required.
Endpoint: GET https://api.dexscreener.com/latest/dex/search?q={query}

Returns pair data with: pairAddress, baseToken, quoteToken, priceUsd, volume, etc.
"""

import logging
from typing import List, Optional, Dict, Any
from .base import BaseAPIClient
from borg.defi.data_models import DexPair

logger = logging.getLogger(__name__)

# DexScreener API endpoints
DEX_SCREENER_BASE = "https://api.dexscreener.com"
SEARCH_ENDPOINT = "/latest/dex/search"
PAIRS_ENDPOINT = "/latest/dex/pairs"

# Chain name mapping
CHAIN_MAPPING = {
    "solana": "solana",
    "ethereum": "ethereum",
    "base": "base",
    "arbitrum": "arbitrum",
    "polygon": "polygon",
    "bsc": "bsc",
    "avalanche": "avalanche",
}


class DexScreenerClient(BaseAPIClient):
    """Client for DexScreener API."""

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """Initialize DexScreener client."""
        super().__init__(base_url=base_url or DEX_SCREENER_BASE, **kwargs)

    async def search_pairs(self, query: str) -> Optional[List[DexPair]]:
        """
        Search for trading pairs by token symbol or address.

        Args:
            query: Token symbol (e.g., 'SOL') or contract address

        Returns:
            List of DexPair dataclasses or None on error
        """
        url = f"{self._base_url}{SEARCH_ENDPOINT}"
        params = {"q": query}

        data = await self.get(url, params=params)
        if not data:
            return None

        pairs = self._parse_pairs(data)
        logger.info(f"Found {len(pairs)} pairs for query: {query}")
        return pairs

    async def get_pairs_by_chain(self, chain: str) -> List[DexPair]:
        """
        Get recent pairs for a specific chain.

        Args:
            chain: Chain name (solana, ethereum, base, arbitrum, etc.)

        Returns:
            List of DexPair dataclasses
        """
        chain_lower = chain.lower()
        url = f"{self._base_url}{PAIRS_ENDPOINT}/{chain_lower}"

        data = await self.get(url)
        if not data:
            return []

        pairs = self._parse_pairs(data)
        logger.info(f"Found {len(pairs)} pairs for chain: {chain}")
        return pairs

    async def get_token_pairs(self, token_address: str) -> List[DexPair]:
        """
        Get all trading pairs for a specific token.

        Args:
            token_address: Token contract address

        Returns:
            List of DexPair dataclasses
        """
        return await self.search_pairs(token_address)

    async def get_sol_pairs(self) -> List[DexPair]:
        """Get all Solana trading pairs."""
        return await self.get_pairs_by_chain("solana")

    def _parse_pairs(self, data: Any) -> List[DexPair]:
        """
        Parse DexScreener API response into DexPair dataclasses.

        The API returns { "pairs": [...] } where each pair has nested
        baseToken and quoteToken objects.
        """
        if not data:
            return []

        pairs_data = data.get("pairs", []) if isinstance(data, dict) else data
        if not isinstance(pairs_data, list):
            return []

        pairs = []
        for pair_data in pairs_data:
            try:
                # Skip if essential fields missing
                if not pair_data.get("pairAddress"):
                    continue

                base_token = pair_data.get("baseToken", {})
                quote_token = pair_data.get("quoteToken", {})

                # Determine chain fromDEX or chainId
                chain = pair_data.get("chainId", "").lower()
                if not chain:
                    # Try to infer from dexId
                    dex_id = pair_data.get("dexId", "").lower()
                    if "solana" in dex_id:
                        chain = "solana"
                    elif "raydium" in dex_id:
                        chain = "solana"
                    else:
                        chain = "unknown"

                pair = DexPair(
                    pair_address=pair_data.get("pairAddress", ""),
                    base_token=base_token.get("symbol", ""),
                    base_token_address=base_token.get("address", ""),
                    quote_token=quote_token.get("symbol", ""),
                    quote_token_address=quote_token.get("address", ""),
                    price_usd=self._safe_float(pair_data.get("priceUsd")),
                    volume_24h=self._safe_float(pair_data.get("volume", {}).get("h24", 0)),
                    liquidity_usd=self._safe_float(pair_data.get("liquidity", {}).get("usd", 0)),
                    tx_count_24h=pair_data.get("txns", {}).get("h24", {}).get("buys", 0) +
                                pair_data.get("txns", {}).get("h24", {}).get("sells", 0),
                    price_change_24h=self._safe_float(pair_data.get("priceChange", {}).get("h24", 0)),
                    chain=chain,
                    dex=pair_data.get("dexId", ""),
                    timestamp=pair_data.get("pairCreatedAt", 0) or 0,
                )
                pairs.append(pair)

            except Exception as e:
                logger.debug(f"Skipping pair due to parse error: {e}")
                continue

        return pairs

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
