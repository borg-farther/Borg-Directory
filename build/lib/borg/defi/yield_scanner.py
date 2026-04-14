"""Yield scanner module for Borg DeFi.

Scans DeFi protocols for yield opportunities using DeFiLlama API.
"""

import asyncio
import logging
import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

import aiohttp

from borg.defi.data_models import YieldOpportunity, YieldChange

logger = logging.getLogger(__name__)


# Chains that have impermanent loss risk (LP pools)
IL_CHAINS = {"solana", "ethereum", "arbitrum", "base", "polygon", "optimism"}


def _calculate_risk_adjusted_score(apy: float, risk_score: float, tvl: float) -> float:
    """Calculate risk-adjusted yield score.
    
    Score = APY * (1 - risk_score) * log(TVL) / baseline
    """
    if tvl <= 0:
        return 0.0
    # log base 10 of TVL, normalized to ~10M = 1.0
    tvl_score = math.log10(tvl + 1) / 7  # 10M -> 7, 100M -> 8
    return apy * (1 - risk_score) * tvl_score


class YieldScanner:
    """Scans DeFi protocols for yield opportunities.
    
    Uses DeFiLlama API (free, no auth required).
    API: GET https://yields.llama.fi/pools returns 10k+ pools
    """
    
    DEFI_LLAMA_URL = "https://yields.llama.fi/pools"
    STABLECOINS = {"usdc", "usdt", "dai", "frax", "lusd", "busd", "ust"}
    
    def __init__(
        self,
        min_tvl: float = 1_000_000,
        max_risk: float = 0.5,
        chains: Optional[List[str]] = None,
    ):
        """Initialize yield scanner.
        
        Args:
            min_tvl: Minimum TVL in USD to include pool
            max_risk: Maximum risk score (0-1) to include
            chains: Optional list of chains to filter (None = all)
        """
        self.min_tvl = min_tvl
        self.max_risk = max_risk
        self.chains = chains
        self._session: Optional[aiohttp.ClientSession] = None
        self._previous_pools: Dict[str, float] = {}  # pool_id -> apy
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def scan_defillama(self) -> List[YieldOpportunity]:
        """Scan yields via DeFiLlama API.
        
        GET https://yields.llama.fi/pools
        Returns: 10k+ pools with APY, TVL, chain, project
        
        Returns:
            List of YieldOpportunity objects
        """
        session = await self._get_session()
        
        try:
            async with session.get(self.DEFI_LLAMA_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 429:
                    logger.warning("DeFiLlama rate limited")
                    return []
                if resp.status != 200:
                    logger.error(f"DeFiLlama API error: {resp.status}")
                    return []
                
                data = await resp.json()
                return self._parse_defillama_response(data)
        except asyncio.TimeoutError:
            logger.error("DeFiLlama API timeout")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"DeFiLlama API client error: {e}")
            return []
        except Exception as e:
            logger.error(f"DeFiLlama unexpected error: {e}")
            return []
    
    def _parse_defillama_response(self, data: Dict[str, Any]) -> List[YieldOpportunity]:
        """Parse DeFiLlama API response into YieldOpportunity objects.
        
        Args:
            data: JSON response from DeFiLlama
            
        Returns:
            List of YieldOpportunity
        """
        opportunities = []
        pools = data.get("data", [])
        
        seen_pools = set()
        
        for pool in pools:
            try:
                pool_id = pool.get("pool", "")
                if not pool_id or pool_id in seen_pools:
                    continue
                seen_pools.add(pool_id)
                
                chain = pool.get("chain", "").lower()
                protocol = pool.get("project", "")
                symbol = pool.get("symbol", "")
                pool_name = pool.get("pool", "")
                
                # Skip if no symbol or protocol
                if not symbol or not protocol:
                    continue
                
                # Get TVL
                tvl_data = pool.get("tvlUsd", 0)
                tvl = float(tvl_data) if tvl_data else 0.0
                
                # Skip pools below TVL threshold
                if tvl < self.min_tvl:
                    continue
                
                # Get APY
                apy_data = pool.get("apy", 0)
                apy = float(apy_data) if apy_data else 0.0
                
                # Skip negative APY
                if apy < 0:
                    continue
                
                # Filter by chain if specified
                if self.chains and chain not in self.chains:
                    continue
                
                # Determine IL risk
                # LP pools have 2 tokens and are on supported chains
                il_risk = False
                if pool.get("poolMeta"):
                    meta = pool.get("poolMeta", "").lower()
                    if "lp" in meta or "pair" in meta:
                        il_risk = True
                
                # Simplified: if symbol contains "-" it's likely an LP token
                if "-" in symbol and chain in IL_CHAINS:
                    il_risk = True
                
                # Calculate risk score
                # Higher TVL = lower risk, Higher APY = potentially higher risk
                base_risk = 0.3
                if il_risk:
                    base_risk += 0.2
                if tvl < 10_000_000:
                    base_risk += 0.1
                if apy > 100:
                    base_risk += 0.2
                risk_score = min(1.0, max(0.0, base_risk))
                
                # Skip if above risk threshold
                if risk_score > self.max_risk:
                    continue
                
                # Build URL
                url = f"https://defillama.com/yields/pool/{pool_id}"
                
                # Get timestamp
                timestamp = pool.get("updated", datetime.now().timestamp())
                
                opp = YieldOpportunity(
                    protocol=protocol,
                    chain=chain,
                    pool=pool_name,
                    token=symbol,
                    apy=apy,
                    tvl=tvl,
                    risk_score=risk_score,
                    il_risk=il_risk,
                    url=url,
                    last_updated=timestamp,
                    symbol=symbol,
                    pool_id=pool_id,
                )
                opportunities.append(opp)
                
            except Exception as e:
                logger.debug(f"Error parsing pool: {e}")
                continue
        
        return opportunities
    
    async def scan_solana_yields(self) -> List[YieldOpportunity]:
        """Scan Solana-specific yields: Kamino, Marinade, Raydium, Orca.
        
        Returns:
            List of YieldOpportunity for Solana protocols
        """
        # First get all from DeFiLlama and filter
        all_opps = await self.scan_defillama()
        solana_opps = [o for o in all_opps if o.chain == "solana"]
        
        # Known Solana protocols we want to highlight
        solana_protocols = {"kamino", "marinade", "raydium", "orca", "jupiter", "saber"}
        
        solana_specific = []
        for opp in solana_opps:
            if any(p in opp.protocol.lower() for p in solana_protocols):
                solana_specific.append(opp)
        
        return solana_specific
    
    def rank_opportunities(
        self,
        opps: List[YieldOpportunity],
        min_tvl: Optional[float] = None,
        max_risk: Optional[float] = None,
    ) -> List[YieldOpportunity]:
        """Rank opportunities by risk-adjusted yield.
        
        Score = APY * (1 - risk_score) * log(TVL) / baseline
        
        Args:
            opps: List of YieldOpportunity to rank
            min_tvl: Optional override for min TVL filter
            max_risk: Optional override for max risk filter
            
        Returns:
            Sorted list of YieldOpportunity (highest score first)
        """
        min_tvl = min_tvl if min_tvl is not None else self.min_tvl
        max_risk = max_risk if max_risk is not None else self.max_risk
        
        # Filter first
        filtered = [
            o for o in opps
            if o.tvl >= min_tvl and o.risk_score <= max_risk
        ]
        
        # Calculate scores and sort
        scored = []
        for opp in filtered:
            score = _calculate_risk_adjusted_score(opp.apy, opp.risk_score, opp.tvl)
            scored.append((score, opp))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [opp for _, opp in scored]
    
    def filter_by_chain(self, opps: List[YieldOpportunity], chain: str) -> List[YieldOpportunity]:
        """Filter opportunities by chain.
        
        Args:
            opps: List of YieldOpportunity
            chain: Chain name to filter by (e.g., 'solana', 'ethereum')
            
        Returns:
            Filtered list of YieldOpportunity
        """
        chain = chain.lower()
        return [o for o in opps if o.chain == chain]
    
    def filter_stablecoins(self, opps: List[YieldOpportunity]) -> List[YieldOpportunity]:
        """Filter to only stablecoin pools.
        
        Args:
            opps: List of YieldOpportunity
            
        Returns:
            Filtered list with only stablecoin pools
        """
        result = []
        for opp in opps:
            token_upper = opp.token.upper()
            if any(s.upper() in token_upper for s in self.STABLECOINS):
                result.append(opp)
        return result
    
    def detect_yield_changes(
        self,
        current: List[YieldOpportunity],
        previous: List[YieldOpportunity],
        threshold_pct: float = 20.0,
    ) -> List[YieldChange]:
        """Detect significant yield changes.
        
        Args:
            current: Current yield opportunities
            previous: Previous yield opportunities (from last scan)
            threshold_pct: Percentage change threshold to trigger alert (default 20%)
            
        Returns:
            List of YieldChange objects for significant changes
        """
        # Build previous lookup
        prev_lookup = {o.pool_id: o.apy for o in previous if o.pool_id}
        current_lookup = {o.pool_id: o for o in current if o.pool_id}
        
        changes = []
        
        for pool_id, current_opp in current_lookup.items():
            if pool_id not in prev_lookup:
                continue
            
            prev_apy = prev_lookup[pool_id]
            curr_apy = current_opp.apy
            
            if prev_apy <= 0:
                continue
            
            change_pct = ((curr_apy - prev_apy) / prev_apy) * 100
            
            # Only report if change exceeds threshold
            if abs(change_pct) < threshold_pct:
                continue
            
            is_spike = curr_apy > prev_apy
            
            change = YieldChange(
                pool_id=pool_id,
                protocol=current_opp.protocol,
                chain=current_opp.chain,
                previous_apy=prev_apy,
                current_apy=curr_apy,
                change_pct=change_pct,
                is_spike=is_spike,
            )
            changes.append(change)
        
        # Sort by absolute change percentage
        changes.sort(key=lambda x: abs(x.change_pct), reverse=True)
        return changes
    
    def format_telegram(self, opps: List[YieldOpportunity], top_n: int = 5) -> str:
        """Format top opportunities for Telegram.
        
        Args:
            opps: List of YieldOpportunity (should be pre-ranked)
            top_n: Number of top opportunities to include
            
        Returns:
            Formatted Telegram message string
        """
        if not opps:
            return "📊 *Yield Scanner*\n\nNo yield opportunities found matching your criteria."
        
        lines = ["📊 *Yield Scanner*"]
        lines.append(f"_Scanned {len(opps)} opportunities_\n")
        
        for i, opp in enumerate(opps[:top_n], 1):
            # Risk indicator
            risk_emoji = "🟢" if opp.risk_score < 0.3 else "🟡" if opp.risk_score < 0.6 else "🔴"
            il_indicator = " ⚠️ IL" if opp.il_risk else ""
            
            lines.append(
                f"{i}. {risk_emoji} *{opp.protocol}*"
            )
            lines.append(f"   💰 {opp.pool}: *{opp.apy:.1f}%* APY")
            lines.append(f"   📈 TVL: ${opp.tvl/1e6:.1f}M{il_indicator}")
            lines.append(f"   🔗 [View Pool]({opp.url})")
            lines.append("")
        
        if len(opps) > top_n:
            lines.append(f"_...and {len(opps) - top_n} more opportunities_")
        
        return "\n".join(lines)
    
    def format_yield_alert(self, change: YieldChange) -> str:
        """Format a yield change alert for Telegram.
        
        Args:
            change: YieldChange object
            
        Returns:
            Formatted alert string
        """
        direction = "📈 *YIELD SPIKE*" if change.is_spike else "📉 *YIELD DROP*"
        emoji = "🚀" if change.is_spike else "⚠️"
        
        return (
            f"{emoji} {direction}\n"
            f"*{change.protocol}* on {change.chain}\n"
            f"APY: {change.previous_apy:.1f}% → *{change.current_apy:.1f}%*\n"
            f"Change: {change.change_pct:+.1f}%\n"
            f"🔗 [View Pool](https://defillama.com/yields/pool/{change.pool_id})"
        )
