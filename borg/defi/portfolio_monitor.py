"""Portfolio monitor module for Borg DeFi.

Tracks portfolio positions across chains, calculates P&L, and generates risk alerts.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

import aiohttp

from borg.defi.data_models import Position, RiskAlert, PortfolioSummary

logger = logging.getLogger(__name__)


class PortfolioMonitor:
    """Track portfolio positions and generate alerts.
    
    Supports Solana (via Helius DAS API) and EVM chains (via Alchemy).
    """
    
    HELIUS_URL = "https://mainnet.helius-rpc.com"
    ALCHEMY_URL_TEMPLATE = "https://eth-{chain}.g.alchemy.com/v2/{api_key}"
    
    def __init__(
        self,
        helius_api_key: Optional[str] = None,
        alchemy_api_key: Optional[str] = None,
        daily_change_callback: Optional[callable] = None,
    ):
        """Initialize portfolio monitor.
        
        Args:
            helius_api_key: Helius API key for Solana RPC
            alchemy_api_key: Alchemy API key for EVM RPC
            daily_change_callback: Optional callback for daily change data
        """
        self.helius_api_key = helius_api_key
        self.alchemy_api_key = alchemy_api_key
        self.daily_change_callback = daily_change_callback
        self._session: Optional[aiohttp.ClientSession] = None
        self._price_cache: Dict[str, float] = {}
        self._historical_snapshots: List[Dict] = []
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_solana_portfolio(self, wallet: str) -> List[Position]:
        """Get all Solana token holdings via Helius DAS API.
        
        POST https://mainnet.helius-rpc.com/?api-key=KEY
        Method: getAssetsByOwner
        
        Args:
            wallet: Solana wallet address
            
        Returns:
            List of Position objects
        """
        if not self.helius_api_key:
            logger.warning("No Helius API key provided, using mock data")
            return self._get_mock_solana_portfolio(wallet)
        
        session = await self._get_session()
        url = f"{self.HELIUS_URL}/?api-key={self.helius_api_key}"
        
        payload = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "getAssetsByOwner",
            "params": {
                "owner": wallet,
                "encoding": "jsonParsed",
                "limit": 100,
            }
        }
        
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.error(f"Helius API error: {resp.status}")
                    return []
                
                data = await resp.json()
                return self._parse_helius_assets(data, wallet)
        except asyncio.TimeoutError:
            logger.error("Helius API timeout")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"Helius API client error: {e}")
            return []
        except Exception as e:
            logger.error(f"Helius unexpected error: {e}")
            return []
    
    def _parse_helius_assets(self, data: Dict, wallet: str) -> List[Position]:
        """Parse Helius getAssetsByOwner response into Position objects.
        
        Args:
            data: JSON response from Helius
            wallet: Wallet address
            
        Returns:
            List of Position
        """
        positions = []
        
        try:
            items = data.get("result", {}).get("items", [])
            
            for item in items:
                try:
                    # Get token info
                    token_info = item.get("token_info", {})
                    symbol = token_info.get("symbol", "UNKNOWN")
                    decimals = token_info.get("decimals", 0)
                    
                    # Skip if no symbol
                    if not symbol or symbol == "UNKNOWN":
                        continue
                    
                    # Get amount
                    amount = token_info.get("amount", 0)
                    if amount == 0:
                        continue
                    
                    # Adjust for decimals
                    amount_adjusted = amount / (10 ** decimals) if decimals > 0 else amount
                    
                    # Get price if available
                    price = token_info.get("price_info", {}).get("price_per_token", 0)
                    if price:
                        value_usd = amount_adjusted * price
                    else:
                        # Try to get from cache or use 0
                        value_usd = self._price_cache.get(symbol, 0) * amount_adjusted
                    
                    # Get UI properties
                    interface = item.get("interface", "")
                    compression = item.get("compression", {})
                    
                    # Determine position type
                    if " lp " in symbol.lower() or "-LP" in symbol:
                        position_type = "lp"
                    elif interface == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                        position_type = "hold"
                    else:
                        position_type = "hold"
                    
                    # Mock entry price (use current price as placeholder)
                    entry_price = price if price > 0 else self._price_cache.get(symbol, 0)
                    current_price = price if price > 0 else self._price_cache.get(symbol, 0)
                    
                    pos = Position(
                        chain="solana",
                        protocol=self._infer_protocol(symbol),
                        token=symbol,
                        amount=amount_adjusted,
                        value_usd=value_usd,
                        entry_price=entry_price,
                        current_price=current_price,
                        position_type=position_type,
                    )
                    positions.append(pos)
                    
                except Exception as e:
                    logger.debug(f"Error parsing asset: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing Helius response: {e}")
        
        return positions
    
    def _infer_protocol(self, symbol: str) -> str:
        """Infer protocol from token symbol."""
        symbol_upper = symbol.upper()
        
        if any(s in symbol_upper for s in ["SOL", "W SOL"]):
            return "solana"
        if any(s in symbol_upper for s in ["USDC", "USDT"]):
            return "circle" if "USDC" in symbol_upper else "tether"
        if any(s in symbol_upper for s in ["KAM", "KAMINO"]):
            return "kamino"
        if any(s in symbol_upper for s in ["RAY", "RAYDIUM"]):
            return "raydium"
        if any(s in symbol_upper for s in ["MNGO", "MANGO"]):
            return "mango"
        if any(s in symbol_upper for s in ["JITO"]):
            return "jito"
        if any(s in symbol_upper for s in ["BONK"]):
            return "bonk"
        
        return "unknown"
    
    async def get_evm_portfolio(self, wallet: str, chain: str = "ethereum") -> List[Position]:
        """Get EVM holdings via Alchemy getTokenBalances.
        
        Args:
            wallet: EVM wallet address
            chain: Chain name (ethereum, polygon, arbitrum, etc.)
            
        Returns:
            List of Position objects
        """
        if not self.alchemy_api_key:
            logger.warning("No Alchemy API key provided, using mock data")
            return self._get_mock_evm_portfolio(wallet, chain)
        
        session = await self._get_session()
        
        # Map chain names to Alchemy chain IDs
        chain_ids = {
            "ethereum": "eth-mainnet",
            "polygon": "polygon-mainnet",
            "arbitrum": "arb-mainnet",
            "base": "base-mainnet",
            "optimism": "opt-mainnet",
        }
        
        alchemy_chain = chain_ids.get(chain.lower(), "eth-mainnet")
        url = f"https://{alchemy_chain}.g.alchemy.com/v2/{self.alchemy_api_key}"
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getTokenBalances",
            "params": [wallet, "erc20"],
        }
        
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.error(f"Alchemy API error: {resp.status}")
                    return []
                
                data = await resp.json()
                return await self._fetch_evm_token_details(data, wallet, chain, session)
        except asyncio.TimeoutError:
            logger.error("Alchemy API timeout")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"Alchemy API client error: {e}")
            return []
        except Exception as e:
            logger.error(f"Alchemy unexpected error: {e}")
            return []
    
    async def _fetch_evm_token_details(
        self, balance_data: Dict, wallet: str, chain: str, session: aiohttp.ClientSession
    ) -> List[Position]:
        """Fetch detailed token info from Alchemy.
        
        Args:
            balance_data: Response from alchemy_getTokenBalances
            wallet: Wallet address
            chain: Chain name
            session: aiohttp session
            
        Returns:
            List of Position
        """
        positions = []
        token_balances = balance_data.get("result", {}).get("tokenBalances", [])
        
        # Filter out zero balances and tokens without price
        non_zero = [t for t in token_balances if int(t.get("tokenBalance", "0"), 16) > 0]
        
        for token in non_zero[:50]:  # Limit to 50 tokens
            try:
                contract = token.get("contractAddress", "")
                if not contract:
                    continue
                
                # Get metadata
                metadata_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "alchemy_getTokenMetadata",
                    "params": [contract],
                }
                
                async with session.post(
                    f"https://eth-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}",
                    json=metadata_payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        continue
                    
                    metadata = await resp.json()
                    meta = metadata.get("result", {})
                    
                    symbol = meta.get("symbol", "UNKNOWN")
                    decimals = meta.get("decimals", 18)
                    logo = meta.get("logo", "")
                    
                    # Get balance
                    balance_hex = token.get("tokenBalance", "0")
                    balance = int(balance_hex, 16) if balance_hex else 0
                    amount = balance / (10 ** decimals) if decimals > 0 else balance
                    
                    if amount <= 0:
                        continue
                    
                    # Get price from cache or mock
                    price = self._price_cache.get(f"{chain}:{symbol}", 0)
                    value_usd = amount * price
                    
                    # Mock entry price
                    entry_price = price
                    current_price = price
                    
                    pos = Position(
                        chain=chain,
                        protocol=self._infer_evm_protocol(symbol),
                        token=symbol,
                        amount=amount,
                        value_usd=value_usd,
                        entry_price=entry_price,
                        current_price=current_price,
                        position_type="hold",
                    )
                    positions.append(pos)
                    
            except Exception as e:
                logger.debug(f"Error fetching token details: {e}")
                continue
        
        return positions
    
    def _infer_evm_protocol(self, symbol: str) -> str:
        """Infer protocol from EVM token symbol."""
        symbol_upper = symbol.upper()
        
        if symbol_upper in ["WETH", "ETH"]:
            return "ethereum"
        if symbol_upper in ["WBTC", "BTC"]:
            return "bitcoin"
        if any(s in symbol_upper for s in ["USDC", "USDT"]):
            return "circle" if "USDC" in symbol_upper else "tether"
        if "AAVE" in symbol_upper:
            return "aave"
        if "UNI" in symbol_upper:
            return "uniswap"
        if "LINK" in symbol_upper:
            return "chainlink"
        
        return "unknown"
    
    def _get_mock_solana_portfolio(self, wallet: str) -> List[Position]:
        """Return mock Solana portfolio for testing."""
        now = datetime.now().timestamp()
        
        return [
            Position(
                chain="solana",
                protocol="solana",
                token="SOL",
                amount=10.5,
                value_usd=2100.0,
                entry_price=180.0,
                current_price=200.0,
                pnl_usd=210.0,
                pnl_pct=11.1,
                position_type="hold",
            ),
            Position(
                chain="solana",
                protocol="kamino",
                token="USDC-USDC LP",
                amount=5000.0,
                value_usd=5100.0,
                entry_price=1.0,
                current_price=1.02,
                pnl_usd=100.0,
                pnl_pct=2.0,
                position_type="lp",
            ),
            Position(
                chain="solana",
                protocol="marinade",
                token="mSOL",
                amount=3.2,
                value_usd=672.0,
                entry_price=200.0,
                current_price=210.0,
                pnl_usd=32.0,
                pnl_pct=5.0,
                position_type="staking",
            ),
            Position(
                chain="solana",
                protocol="bonk",
                token="BONK",
                amount=1000000.0,
                value_usd=150.0,
                entry_price=0.0002,
                current_price=0.00015,
                pnl_usd=-50.0,
                pnl_pct=-33.3,
                position_type="hold",
            ),
        ]
    
    def _get_mock_evm_portfolio(self, wallet: str, chain: str) -> List[Position]:
        """Return mock EVM portfolio for testing."""
        return [
            Position(
                chain=chain,
                protocol="ethereum",
                token="ETH",
                amount=1.5,
                value_usd=3000.0,
                entry_price=2800.0,
                current_price=2000.0,
                pnl_usd=-1200.0,
                pnl_pct=-28.6,
                position_type="hold",
            ),
            Position(
                chain=chain,
                protocol="aave",
                token="USDC",
                amount=2000.0,
                value_usd=2000.0,
                entry_price=1.0,
                current_price=1.0,
                pnl_usd=0.0,
                pnl_pct=0.0,
                health_factor=1.8,
                position_type="lending",
            ),
        ]
    
    def calculate_pnl(self, positions: List[Position]) -> Dict[str, Any]:
        """Calculate total P&L, daily change, allocation breakdown.
        
        Args:
            positions: List of Position objects
            
        Returns:
            Dict with total_value, total_pnl, pnl_pct, allocations, etc.
        """
        if not positions:
            return {
                "total_value_usd": 0.0,
                "total_pnl_usd": 0.0,
                "total_pnl_pct": 0.0,
                "daily_change_usd": 0.0,
                "daily_change_pct": 0.0,
                "allocations": {},
                "by_chain": {},
                "by_protocol": {},
            }
        
        # Calculate totals
        total_value = sum(p.value_usd for p in positions)
        total_pnl = sum(p.pnl_usd for p in positions)
        
        # Calculate entry value for P&L percentage
        entry_value = sum(p.entry_price * p.amount for p in positions)
        total_pnl_pct = ((total_value / entry_value) - 1) * 100 if entry_value > 0 else 0.0
        
        # Calculate allocations
        allocations = {}
        for p in positions:
            if total_value > 0:
                pct = (p.value_usd / total_value) * 100
                allocations[p.token] = pct
        
        # Group by chain
        by_chain: Dict[str, float] = {}
        for p in positions:
            by_chain[p.chain] = by_chain.get(p.chain, 0.0) + p.value_usd
        
        # Group by protocol
        by_protocol: Dict[str, float] = {}
        for p in positions:
            by_protocol[p.protocol] = by_protocol.get(p.protocol, 0.0) + p.value_usd
        
        # Mock daily change (in production, would compare to yesterday's snapshot)
        daily_change_usd = total_value * 0.01  # Assume 1% daily change
        daily_change_pct = 1.0
        
        return {
            "total_value_usd": total_value,
            "total_pnl_usd": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "daily_change_usd": daily_change_usd,
            "daily_change_pct": daily_change_pct,
            "allocations": allocations,
            "by_chain": by_chain,
            "by_protocol": by_protocol,
            "num_positions": len(positions),
        }
    
    def risk_alerts(self, positions: List[Position]) -> List[RiskAlert]:
        """Generate risk alerts.
        
        Risk criteria:
        - Health factor < 1.5 on lending positions
        - Single token > 30% of portfolio
        - Unrealized loss > 20% on any position
        
        Args:
            positions: List of Position objects
            
        Returns:
            List of RiskAlert objects
        """
        alerts = []
        
        if not positions:
            return alerts
        
        # Calculate total value for concentration checks
        total_value = sum(p.value_usd for p in positions)
        
        for pos in positions:
            # Check health factor (lending positions)
            if pos.health_factor is not None and pos.health_factor < 1.5:
                severity = "critical" if pos.health_factor < 1.0 else "warning"
                alerts.append(RiskAlert(
                    alert_type="health_factor",
                    severity=severity,
                    message=f"⚠️ *HEALTH FACTOR ALERT*\n{pos.protocol} {pos.token}: HF = {pos.health_factor:.2f}",
                    affected_positions=[pos.token],
                ))
            
            # Check concentration
            if total_value > 0:
                concentration_pct = (pos.value_usd / total_value) * 100
                if concentration_pct > 30:
                    alerts.append(RiskAlert(
                        alert_type="concentration",
                        severity="warning" if concentration_pct < 50 else "critical",
                        message=f"⚠️ *CONCENTRATION ALERT*\n{pos.token} is {concentration_pct:.1f}% of portfolio (>30%)",
                        affected_positions=[pos.token],
                    ))
            
            # Check drawdown
            if pos.pnl_pct < -20:
                alerts.append(RiskAlert(
                    alert_type="drawdown",
                    severity="warning" if pos.pnl_pct > -50 else "critical",
                    message=f"📉 *DRAWDOWN ALERT*\n{pos.token}: {pos.pnl_pct:.1f}% loss (${pos.pnl_usd:.2f})",
                    affected_positions=[pos.token],
                ))
        
        return alerts
    
    def format_daily_report(
        self,
        positions: List[Position],
        pnl_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format morning Telegram portfolio summary.
        
        Args:
            positions: List of Position objects
            pnl_data: Optional pre-calculated P&L data
            
        Returns:
            Formatted Telegram message string
        """
        if not positions:
            return "💼 *Daily Portfolio Report*\n\nNo positions found."
        
        pnl_data = pnl_data or self.calculate_pnl(positions)
        alerts = self.risk_alerts(positions)
        
        lines = ["💼 *Daily Portfolio Report*"]
        lines.append("")
        
        # Total value
        total = pnl_data["total_value_usd"]
        pnl = pnl_data["total_pnl_usd"]
        pnl_pct = pnl_data["total_pnl_pct"]
        daily_change = pnl_data.get("daily_change_usd", 0)
        daily_pct = pnl_data.get("daily_change_pct", 0)
        
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        lines.append(
            f"📊 *Total: ${total:,.2f}*\n"
            f"{pnl_emoji} Total P&L: {pnl:+.2f} ({pnl_pct:+.1f}%)\n"
            f"{pnl_emoji} Today: {daily_change:+.2f} ({daily_pct:+.1f}%)"
        )
        lines.append("")
        
        # Top positions
        lines.append("*Top Positions:*")
        sorted_positions = sorted(positions, key=lambda p: p.value_usd, reverse=True)
        for pos in sorted_positions[:5]:
            pnl_emoji = "🟢" if pos.pnl_usd >= 0 else "🔴"
            lines.append(
                f"{pnl_emoji} {pos.token}: ${pos.value_usd:,.2f} "
                f"({pos.pnl_pct:+.1f}%)"
            )
        lines.append("")
        
        # Chain breakdown
        lines.append("*By Chain:*")
        by_chain = pnl_data.get("by_chain", {})
        for chain, value in sorted(by_chain.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total) * 100 if total > 0 else 0
            lines.append(f"  {chain}: ${value:,.2f} ({pct:.1f}%)")
        lines.append("")
        
        # Risk alerts
        if alerts:
            lines.append("*⚠️ Risk Alerts:*")
            for alert in alerts:
                lines.append(alert.message)
                lines.append("")
        
        return "\n".join(lines)
    
    def save_snapshot(self, positions: List[Position]) -> None:
        """Save a snapshot of current positions for historical tracking.
        
        Args:
            positions: List of Position objects
        """
        snapshot = {
            "timestamp": datetime.now().timestamp(),
            "positions": [
                {
                    "chain": p.chain,
                    "protocol": p.protocol,
                    "token": p.token,
                    "amount": p.amount,
                    "value_usd": p.value_usd,
                    "entry_price": p.entry_price,
                    "current_price": p.current_price,
                    "pnl_usd": p.pnl_usd,
                    "pnl_pct": p.pnl_pct,
                }
                for p in positions
            ],
        }
        self._historical_snapshots.append(snapshot)
        
        # Keep only last 30 days of snapshots
        cutoff = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        self._historical_snapshots = [
            s for s in self._historical_snapshots if s["timestamp"] > cutoff
        ]
    
    def get_historical_value(self, days: int = 7) -> List[Dict]:
        """Get historical portfolio value over time.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of {timestamp, total_value} dicts
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        result = []
        for snapshot in self._historical_snapshots:
            if snapshot["timestamp"] > cutoff:
                total = sum(p["value_usd"] for p in snapshot["positions"])
                result.append({
                    "timestamp": snapshot["timestamp"],
                    "total_value": total,
                })
        
        return result
