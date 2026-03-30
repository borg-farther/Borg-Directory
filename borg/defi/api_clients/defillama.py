"""
DeFiLlama API client.

Free API, no auth required.
Endpoint: GET https://yields.llama.fi/pools

Returns pool data with: pool, chain, project, symbol, tvlUsd, apy, apyBase, apyReward
"""

import logging
from typing import List, Optional, Dict, Any
from .base import BaseAPIClient
from borg.defi.data_models import YieldOpportunity

logger = logging.getLogger(__name__)

# DeFiLlama API endpoints
DEFI_LLAMA_BASE = "https://yields.llama.fi"
DEFI_LLAMA_BRIDGES_BASE = "https://bridges.llama.fi"
POOLS_ENDPOINT = "/pools"
BRIDGE_VOLUME_ENDPOINT = "/bridgevolume"


class DeFiLlamaClient(BaseAPIClient):
    """Client for DeFiLlama yields API."""

    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """Initialize DeFiLlama client."""
        super().__init__(base_url=base_url or DEFI_LLAMA_BASE, **kwargs)

    async def get_pools(self) -> Optional[Dict[str, Any]]:
        """
        Fetch all pools from DeFiLlama.

        Returns:
            Raw JSON response with pools array or None on error.
        """
        url = f"{self._base_url}{POOLS_ENDPOINT}"
        return await self.get(url)

    async def get_yield_opportunities(
        self,
        min_tvl: float = 0,
        chains: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
    ) -> List[YieldOpportunity]:
        """
        Fetch and parse yield opportunities from DeFiLlama.

        Args:
            min_tvl: Minimum TVL in USD to include
            chains: Optional list of chains to filter (e.g., ['solana', 'ethereum'])
            protocols: Optional list of protocols to filter

        Returns:
            List of YieldOpportunity dataclasses
        """
        data = await self.get_pools()
        if not data or "data" not in data:
            logger.warning("DeFiLlama returned no data")
            return []

        opportunities = []
        chains_lower = [c.lower() for c in chains] if chains else None
        protocols_lower = [p.lower() for p in protocols] if protocols else None

        for pool_data in data.get("data", []):
            try:
                # Apply filters
                tvl = pool_data.get("tvlUsd", 0)
                if tvl < min_tvl:
                    continue

                chain = pool_data.get("chain", "").lower()
                if chains_lower and chain not in chains_lower:
                    continue

                project = pool_data.get("project", "").lower()
                if protocols_lower and project not in protocols_lower:
                    continue

                # Determine IL risk (LP pools typically have apyBase + apyReward)
                # Single-sided lending usually has only apyBase
                il_risk = pool_data.get("category", "").lower() in ["lp", "clm", "amm"]

                opp = YieldOpportunity(
                    protocol=project,
                    chain=chain,
                    pool=pool_data.get("pool", ""),
                    token=pool_data.get("symbol", ""),
                    apy=self._safe_float(pool_data.get("apy")),
                    tvl=tvl,
                    risk_score=self._estimate_risk(pool_data),
                    il_risk=il_risk,
                    url=f"https://defillama.com/yields/pool/{pool_data.get('pool', '')}",
                    last_updated=pool_data.get("updatedAt", 0) or 0,
                )
                opportunities.append(opp)

            except Exception as e:
                logger.debug(f"Skipping pool due to parse error: {e}")
                continue

        logger.info(f"Parsed {len(opportunities)} yield opportunities from DeFiLlama")
        return opportunities

    async def get_pool_by_chain(self, chain: str) -> List[YieldOpportunity]:
        """Get all pools for a specific chain."""
        return await self.get_yield_opportunities(chains=[chain])

    async def get_solana_yields(self) -> List[YieldOpportunity]:
        """Get all Solana yield opportunities."""
        return await self.get_yield_opportunities(chains=["solana"])

    async def get_stablecoin_yields(self, min_tvl: float = 1_000_000) -> List[YieldOpportunity]:
        """Get stablecoin (USDC, USDT, DAI) yield opportunities."""
        all_opps = await self.get_yield_opportunities(min_tvl=min_tvl)
        stablecoins = {"usdc", "usdt", "dai", "usdbc", "usdt.e"}
        return [
            opp for opp in all_opps
            if opp.token.lower().replace("-", "") in stablecoins
            or opp.pool.lower().replace("-", "").replace("_", "") in stablecoins
        ]

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _estimate_risk(pool_data: Dict[str, Any]) -> float:
        """
        Estimate risk score for a pool based on available data.

        Returns float 0.0-1.0 (higher = riskier)
        """
        risk = 0.5  # baseline

        # TVL-based risk (lower TVL = higher risk)
        tvl = pool_data.get("tvlUsd", 0)
        if tvl < 100_000:
            risk += 0.2
        elif tvl < 1_000_000:
            risk += 0.1
        elif tvl > 100_000_000:
            risk -= 0.1

        # Outlier APY detection (very high APY = higher risk)
        apy = DeFiLlamaClient._safe_float(pool_data.get("apy"))
        if apy > 100:
            risk += 0.2
        elif apy > 50:
            risk += 0.1

        # Protocol-based risk
        project = pool_data.get("project", "").lower()
        low_risk_protocols = {"aave", "compound", "morpho", "euler"}
        high_risk_protocols = {"unproven", "newdex", "ponzi"}

        if project in low_risk_protocols:
            risk -= 0.1
        elif project in high_risk_protocols:
            risk += 0.3

        # IL risk already factored in separately
        return max(0.0, min(1.0, risk))

    async def get_bridge_volumes(
        self,
        bridge: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch bridge volume data from DeFiLlama.

        Endpoint: GET https://bridges.llama.fi/bridgevolume

        Args:
            bridge: Optional specific bridge name to filter

        Returns:
            Raw JSON response with bridge volume data or None on error.

        Response structure:
            - data: List of bridge volume records with:
                - bridgeName: str
                - chain: str
                - chains: List[str] (source and destination chains)
                - totalVolumeUsd: float
                - volume24h: float
                - tokenSymbol: str
                - contractAddress: str
        """
        url = f"{DEFI_LLAMA_BRIDGES_BASE}{BRIDGE_VOLUME_ENDPOINT}"
        if bridge:
            url = f"{url}?bridge={bridge}"

        try:
            data = await self.get(url)
            if data and "data" in data:
                logger.info(f"Fetched {len(data.get('data', []))} bridge volume records")
                return data
            logger.warning("DeFiLlama bridge API returned no data")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch bridge volumes: {e}")
            return None
