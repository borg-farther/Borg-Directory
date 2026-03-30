"""
Alpha Signal Engine — Smart money flow detection and on-chain pattern recognition.

Monitors:
- Smart money flow: track known smart wallets accumulating tokens
- Volume spikes: unusual volume before announcements
- New DEX pairs: pair creation monitoring
- Bridge flows: cross-chain flow patterns

Uses DexScreener for new pairs, Birdeye for volume data, Helius for Solana wallet tracking.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from collections import defaultdict

from borg.defi.data_models import DexPair, TokenPrice, OHLCV

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class SmartMoneyFlow:
    """Represents a smart money flow event.

    Attributes:
        wallet: Wallet address or label
        chain: Blockchain network
        token: Token symbol being accumulated
        token_address: Token contract address
        flow_type: Type (accumulate|distribute|neutral)
        amount_usd: USD value of the flow
        position_change: Change in position (tokens)
        avg_entry: Average entry price (if known)
        current_price: Current token price
        timestamp: Unix timestamp
        tx_hash: Transaction hash
        confidence: Signal confidence 0-1
    """
    wallet: str
    chain: str
    token: str
    token_address: str
    flow_type: str  # accumulate|distribute|neutral
    amount_usd: float
    position_change: float
    avg_entry: float = 0.0
    current_price: float = 0.0
    timestamp: float = 0.0
    tx_hash: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet": self.wallet,
            "chain": self.chain,
            "token": self.token,
            "token_address": self.token_address,
            "flow_type": self.flow_type,
            "amount_usd": self.amount_usd,
            "position_change": self.position_change,
            "avg_entry": self.avg_entry,
            "current_price": self.current_price,
            "timestamp": self.timestamp,
            "tx_hash": self.tx_hash,
            "confidence": self.confidence,
        }


@dataclass
class VolumeSpike:
    """Represents an unusual volume spike event.

    Attributes:
        token_address: Token contract address
        token_symbol: Token symbol
        chain: Blockchain network
        volume_24h: Current 24h volume
        volume_change_pct: Percentage change from baseline
        baseline_volume: Average baseline volume
        price_change_pct: Price change percentage
        spike_type: Type (pre-announcement|suspected|organic)
        timestamp: Unix timestamp
        confidence: Signal confidence 0-1
    """
    token_address: str
    token_symbol: str
    chain: str
    volume_24h: float
    volume_change_pct: float
    baseline_volume: float
    price_change_pct: float = 0.0
    spike_type: str = "unknown"  # pre-announcement|suspected|organic|unknown
    timestamp: float = 0.0
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "chain": self.chain,
            "volume_24h": self.volume_24h,
            "volume_change_pct": self.volume_change_pct,
            "baseline_volume": self.baseline_volume,
            "price_change_pct": self.price_change_pct,
            "spike_type": self.spike_type,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


@dataclass
class NewPairAlert:
    """Represents a new DEX pair creation alert.

    Attributes:
        pair: DexPair dataclass
        is_suspicious: Whether the pair looks suspicious
        red_flags: List of red flags
        created_timestamp: Unix timestamp when detected
    """
    pair: DexPair
    is_suspicious: bool = False
    red_flags: List[str] = field(default_factory=list)
    created_timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair": self.pair.to_dict(),
            "is_suspicious": self.is_suspicious,
            "red_flags": self.red_flags,
            "created_timestamp": self.created_timestamp,
        }


@dataclass
class BridgeFlow:
    """Represents a cross-chain bridge flow.

    Attributes:
        wallet: Wallet address
        source_chain: Source blockchain
        destination_chain: Destination blockchain
        token: Token symbol
        token_address: Token contract address
        amount_usd: USD value of the bridge transfer
        flow_type: Type (bridge_in|bridge_out|cross_chain)
        bridge_name: Name of the bridge protocol
        timestamp: Unix timestamp
        tx_hash: Transaction hash
        confidence: Signal confidence 0-1
    """
    wallet: str
    source_chain: str
    destination_chain: str
    token: str
    token_address: str
    amount_usd: float
    flow_type: str  # bridge_in|bridge_out|cross_chain
    bridge_name: str = ""
    timestamp: float = 0.0
    tx_hash: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet": self.wallet,
            "source_chain": self.source_chain,
            "destination_chain": self.destination_chain,
            "token": self.token,
            "token_address": self.token_address,
            "amount_usd": self.amount_usd,
            "flow_type": self.flow_type,
            "bridge_name": self.bridge_name,
            "timestamp": self.timestamp,
            "tx_hash": self.tx_hash,
            "confidence": self.confidence,
        }


# ============================================================================
# Smart Money Wallet Database
# ============================================================================

@dataclass
class SmartMoneyWallet:
    """Represents a tracked smart money wallet.

    Attributes:
        address: Wallet address
        label: Human-readable label
        chain: Blockchain network
        category: Category (fund|miner|cex|dex|unknown)
        total_trades: Total number of trades
        win_rate: Historical win rate
        avg_trade_size: Average trade size in USD
        last_activity: Unix timestamp of last activity
        tags: Additional tags
    """
    address: str
    label: str
    chain: str
    category: str = "unknown"  # fund|miner|cex|dex|unknown
    total_trades: int = 0
    win_rate: float = 0.5
    avg_trade_size: float = 0.0
    last_activity: float = 0.0
    tags: List[str] = field(default_factory=list)


# ============================================================================
# Alpha Signal Engine
# ============================================================================

class AlphaSignalEngine:
    """Engine for detecting alpha signals from on-chain data.

    Detects:
    - Smart money flow: track known smart wallets accumulating tokens
    - Volume spikes: unusual volume before announcements
    - New DEX pairs: pair creation monitoring
    - Bridge flows: cross-chain flow patterns

    Attributes:
        smart_money_wallets: Dict of tracked smart money wallets
        volume_baseline_hours: Hours to calculate volume baseline
        volume_spike_threshold: Multiplier to consider a spike
        new_pair_lookback: Minutes to look back for new pairs
        scan_interval: Seconds between scans (default 60)
    """

    # Chain name mapping for API clients
    CHAIN_MAPPING: Dict[str, str] = {
        "solana": "solana",
        "ethereum": "ethereum",
        "base": "base",
        "arbitrum": "arbitrum",
        "polygon": "polygon",
        "bsc": "bsc",
    }

    # Bridge protocol signatures (simplified)
    KNOWN_BRIDGES: Dict[str, Dict[str, Any]] = {
        "wormhole": {"source": "solana", "destinations": ["ethereum", "base", "arbitrum"]},
        "cctp": {"source": "ethereum", "destinations": ["solana", "base", "arbitrum"]},
        "stargate": {"source": "ethereum", "destinations": ["base", "arbitrum", "polygon"]},
        "across": {"source": "ethereum", "destinations": ["base", "arbitrum"]},
        "hop": {"source": "ethereum", "destinations": ["base", "polygon"]},
    }

    def __init__(
        self,
        smart_money_wallets: Optional[Dict[str, SmartMoneyWallet]] = None,
        volume_baseline_hours: int = 24,
        volume_spike_threshold: float = 3.0,
        new_pair_lookback_minutes: int = 30,
        scan_interval: int = 60,
    ):
        """
        Initialize the Alpha Signal Engine.

        Args:
            smart_money_wallets: Dict of wallet address -> SmartMoneyWallet
            volume_baseline_hours: Hours for volume baseline calculation
            volume_spike_threshold: Multiplier for spike detection
            new_pair_lookback_minutes: Minutes to look back for new pairs
            scan_interval: Seconds between periodic scans
        """
        self.smart_money_wallets: Dict[str, SmartMoneyWallet] = (
            smart_money_wallets or {}
        )
        self.volume_baseline_hours = volume_baseline_hours
        self.volume_spike_threshold = volume_spike_threshold
        self.new_pair_lookback_minutes = new_pair_lookback_minutes
        self.scan_interval = scan_interval

        # Volume history for baseline calculation
        self._volume_history: Dict[str, List[float]] = defaultdict(list)
        self._last_scan: Dict[str, float] = {}
        self._known_pairs: Set[str] = set()  # Track known pair addresses

        # Signal cache to avoid duplicates
        self._signal_cache: Dict[str, float] = {}

    # =========================================================================
    # Smart Money Flow Detection
    # =========================================================================

    async def detect_smart_money_flow(
        self,
        helius_client: Any,
        birdeye_client: Any,
        min_usd_threshold: float = 10_000,
    ) -> List[SmartMoneyFlow]:
        """
        Detect smart money flow from tracked wallets.

        Monitors known smart money wallets for accumulation/distribution patterns.

        Args:
            helius_client: Helius API client for Solana
            birdeye_client: Birdeye API client for prices
            min_usd_threshold: Minimum USD value to trigger detection

        Returns:
            List of SmartMoneyFlow events
        """
        flows: List[SmartMoneyFlow] = []
        current_time = time.time()

        for address, wallet_info in self.smart_money_wallets.items():
            if wallet_info.chain != "solana":
                continue

            # Rate limit per wallet
            cache_key = f"smart_money_{address}"
            if self._is_in_cache(cache_key, cooldown=60):
                continue

            try:
                # Get recent transactions
                transactions = await helius_client.get_transactions_for_address(
                    address, limit=50
                )
                if not transactions:
                    continue

                # Analyze for accumulation/distribution
                for tx in transactions:
                    flow = await self._analyze_smart_money_tx(
                        tx, wallet_info, birdeye_client, min_usd_threshold
                    )
                    if flow:
                        flows.append(flow)
                        self._set_cache(cache_key, current_time)

                # Update last activity
                if transactions:
                    wallet_info.last_activity = transactions[0].get("timestamp", current_time)
                    wallet_info.total_trades += len(transactions)

            except Exception as e:
                logger.debug(f"Error scanning smart money wallet {address}: {e}")
                continue

        logger.info(f"Detected {len(flows)} smart money flows")
        return flows

    async def _analyze_smart_money_tx(
        self,
        tx: Dict[str, Any],
        wallet: SmartMoneyWallet,
        birdeye_client: Any,
        min_threshold: float,
    ) -> Optional[SmartMoneyFlow]:
        """Analyze a single transaction for smart money flow patterns."""
        try:
            tx_type = tx.get("type", "")
            signature = tx.get("signature", "")
            timestamp = tx.get("timestamp", 0)
            token_transfers = tx.get("tokenTransfers", [])

            if not token_transfers:
                return None

            for transfer in token_transfers:
                token_address = transfer.get("mint", "")
                if transfer.get("fromUserAccount") == wallet.address:
                    # Outflow - possible distribution
                    flow_type = "distribute"
                elif transfer.get("toUserAccount") == wallet.address:
                    # Inflow - possible accumulation
                    flow_type = "accumulate"
                else:
                    continue

                # Estimate amount
                raw_amount = self._safe_float(transfer.get("amount", 0))
                decimals = transfer.get("decimals", 9)
                token_amount = raw_amount / (10 ** decimals)

                # Get token price
                current_price = 0.0
                try:
                    price_data = await birdeye_client.get_price(token_address)
                    if price_data:
                        current_price = price_data.price
                except Exception:
                    pass

                amount_usd = token_amount * current_price

                if amount_usd < min_threshold:
                    continue

                # Determine confidence based on wallet history
                confidence = self._calculate_flow_confidence(wallet, amount_usd, flow_type)

                return SmartMoneyFlow(
                    wallet=wallet.label or wallet.address[:12],
                    chain=wallet.chain,
                    token=transfer.get("symbol", token_address[:8]),
                    token_address=token_address,
                    flow_type=flow_type,
                    amount_usd=amount_usd,
                    position_change=token_amount if flow_type == "accumulate" else -token_amount,
                    current_price=current_price,
                    timestamp=timestamp,
                    tx_hash=signature,
                    confidence=confidence,
                )

        except Exception as e:
            logger.debug(f"Error analyzing smart money tx: {e}")

        return None

    def _calculate_flow_confidence(
        self, wallet: SmartMoneyWallet, amount_usd: float, flow_type: str
    ) -> float:
        """Calculate confidence score for a flow signal."""
        base_confidence = 0.5

        # Category-based boost
        category_boosts = {
            "fund": 0.25,
            "miner": 0.15,
            "cex": 0.10,
            "dex": 0.05,
        }
        base_confidence += category_boosts.get(wallet.category, 0)

        # Win rate boost
        if wallet.win_rate > 0.6:
            base_confidence += 0.1
        elif wallet.win_rate < 0.4:
            base_confidence -= 0.1

        # Trade size significance
        if wallet.avg_trade_size > 0:
            size_ratio = amount_usd / wallet.avg_trade_size
            if size_ratio > 2:
                base_confidence += 0.1

        return max(0.0, min(1.0, base_confidence))

    # =========================================================================
    # Volume Spike Detection
    # =========================================================================

    async def detect_volume_spikes(
        self,
        birdeye_client: Any,
        tokens: List[str],
        chains: Optional[List[str]] = None,
    ) -> List[VolumeSpike]:
        """
        Detect unusual volume spikes for tokens.

        Identifies volume spikes that often precede announcements or indicate
        organic price movement.

        Args:
            birdeye_client: Birdeye API client for volume data
            tokens: List of token addresses to monitor
            chains: List of chains to check (default: ["solana"])

        Returns:
            List of VolumeSpike events
        """
        chains = chains or ["solana"]
        spikes: List[VolumeSpike] = []
        current_time = time.time()

        for token_address in tokens:
            for chain in chains:
                cache_key = f"volume_{token_address}_{chain}"
                if self._is_in_cache(cache_key, cooldown=300):
                    continue

                try:
                    # Get current price and volume
                    price_data = await birdeye_client.get_price(token_address)
                    if not price_data:
                        continue

                    current_volume = price_data.volume_24h
                    current_price = price_data.price

                    # Get OHLCV for baseline calculation
                    ohlcv_data = await birdeye_client.get_ohlcv(
                        token_address, timeframe="1h", limit=self.volume_baseline_hours
                    )

                    # Calculate baseline
                    baseline_volume = self._calculate_volume_baseline(ohlcv_data)

                    # Check for spike
                    if baseline_volume > 0:
                        volume_ratio = current_volume / baseline_volume

                        if volume_ratio >= self.volume_spike_threshold:
                            # Determine spike type based on price correlation
                            spike_type = self._classify_volume_spike(
                                ohlcv_data, volume_ratio
                            )

                            # Calculate price change
                            price_change = 0.0
                            if ohlcv_data and len(ohlcv_data) >= 2:
                                price_change = (
                                    (ohlcv_data[-1].close - ohlcv_data[0].open)
                                    / ohlcv_data[0].open
                                ) * 100

                            spike = VolumeSpike(
                                token_address=token_address,
                                token_symbol=price_data.symbol or token_address[:8],
                                chain=chain,
                                volume_24h=current_volume,
                                volume_change_pct=(volume_ratio - 1) * 100,
                                baseline_volume=baseline_volume,
                                price_change_pct=price_change,
                                spike_type=spike_type,
                                timestamp=current_time,
                                confidence=min(0.9, volume_ratio / 5),
                            )
                            spikes.append(spike)
                            self._set_cache(cache_key, current_time)

                except Exception as e:
                    logger.debug(f"Error detecting volume spike for {token_address}: {e}")
                    continue

        logger.info(f"Detected {len(spikes)} volume spikes")
        return spikes

    def _calculate_volume_baseline(self, ohlcv_data: Optional[List[OHLCV]]) -> float:
        """Calculate average volume from OHLCV data."""
        if not ohlcv_data or len(ohlcv_data) < 2:
            return 0.0

        volumes = [c.volume for c in ohlcv_data]
        # Use median to avoid outliers
        sorted_volumes = sorted(volumes)
        mid = len(sorted_volumes) // 2
        if len(sorted_volumes) % 2 == 0:
            return (sorted_volumes[mid - 1] + sorted_volumes[mid]) / 2
        return sorted_volumes[mid]

    def _classify_volume_spike(self, ohlcv_data: Optional[List[OHLCV]], volume_ratio: float) -> str:
        """Classify the type of volume spike."""
        if not ohlcv_data or len(ohlcv_data) < 4:
            return "unknown"

        # Check if price is trending with volume (organic)
        recent_candles = ohlcv_data[-4:]
        price_trend = sum(
            1 if c.close > c.open else -1 for c in recent_candles
        )

        if price_trend > 2 and volume_ratio > 3:
            return "organic"
        elif price_trend < -2 and volume_ratio > 3:
            return "suspected"
        else:
            return "pre-announcement"

    # =========================================================================
    # New Pair Monitoring
    # =========================================================================

    async def monitor_new_pairs(
        self,
        dexscreener_client: Any,
        chains: Optional[List[str]] = None,
        min_liquidity: float = 10_000,
    ) -> List[NewPairAlert]:
        """
        Monitor DEX pair creation for new pairs.

        Detects newly created pairs and flags suspicious ones based on
        liquidity, honeypot patterns, and other indicators.

        Args:
            dexscreener_client: DexScreener API client
            chains: List of chains to monitor (default: ["solana", "ethereum", "base"])

        Returns:
            List of NewPairAlert events
        """
        chains = chains or ["solana", "ethereum", "base", "arbitrum"]
        alerts: List[NewPairAlert] = []
        current_time = time.time()
        lookback_seconds = self.new_pair_lookback_minutes * 60

        for chain in chains:
            try:
                # Get recent pairs for chain
                pairs = await dexscreener_client.get_pairs_by_chain(chain)
                if not pairs:
                    continue

                for pair in pairs:
                    # Skip if already known
                    if pair.pair_address in self._known_pairs:
                        continue

                    # Check if new (within lookback window)
                    pair_age = current_time - pair.timestamp if pair.timestamp > 0 else float('inf')
                    if pair_age > lookback_seconds:
                        # Mark as known for future checks
                        self._known_pairs.add(pair.pair_address)
                        continue

                    # Check liquidity threshold
                    if pair.liquidity_usd < min_liquidity:
                        self._known_pairs.add(pair.pair_address)
                        continue

                    # Analyze for suspicious patterns
                    is_suspicious, red_flags = self._analyze_new_pair(pair)

                    alert = NewPairAlert(
                        pair=pair,
                        is_suspicious=is_suspicious,
                        red_flags=red_flags,
                        created_timestamp=pair.timestamp or current_time,
                    )
                    alerts.append(alert)

                    # Add to known pairs
                    self._known_pairs.add(pair.pair_address)

            except Exception as e:
                logger.debug(f"Error monitoring new pairs on {chain}: {e}")
                continue

        logger.info(f"Found {len(alerts)} new pairs, {sum(1 for a in alerts if a.is_suspicious)} suspicious")
        return alerts

    def _analyze_new_pair(
        self, pair: DexPair
    ) -> tuple[bool, List[str]]:
        """Analyze a new pair for suspicious characteristics."""
        red_flags: List[str] = []
        is_suspicious = False

        # Check liquidity - very low liquidity is suspicious
        if pair.liquidity_usd < 50_000:
            red_flags.append("low_liquidity")
            is_suspicious = True

        # Check for new token (no trading history)
        if pair.tx_count_24h == 0:
            red_flags.append("no_trades")
            is_suspicious = True

        # Check for extreme price changes (potential manipulation)
        if abs(pair.price_change_24h) > 100:
            red_flags.append("extreme_price_change")
            is_suspicious = True

        # Check for very low liquidity with high volume (possible honeypot)
        if pair.liquidity_usd > 0 and pair.volume_24h / pair.liquidity_usd > 5:
            red_flags.append("high_volume_liquidity_ratio")

        # Check for unknown DEX
        unknown_dexes = ["unknown", "unknown dex"]
        if pair.dex.lower() in unknown_dexes:
            red_flags.append("unknown_dex")

        # Very new pair with no baseline liquidity
        if pair.volume_24h == 0 and pair.liquidity_usd < 100_000:
            red_flags.append("no_volume_initial")

        return is_suspicious, red_flags

    # =========================================================================
    # Bridge Flow Detection
    # =========================================================================

    async def detect_bridge_flows(
        self,
        helius_client: Any,
        birdeye_client: Any,
        min_usd_threshold: float = 25_000,
    ) -> List[BridgeFlow]:
        """
        Detect cross-chain bridge flows.

        Monitors for patterns indicating bridge transfers between chains,
        often predictive of volume or price movements.

        Args:
            helius_client: Helius API client for Solana transactions
            birdeye_client: Birdeye API client for token prices
            min_usd_threshold: Minimum USD value to trigger detection

        Returns:
            List of BridgeFlow events
        """
        flows: List[BridgeFlow] = []
        current_time = time.time()

        # Monitor tracked wallets for bridge activity
        for address, wallet_info in self.smart_money_wallets.items():
            cache_key = f"bridge_{address}"
            if self._is_in_cache(cache_key, cooldown=120):
                continue

            try:
                transactions = await helius_client.get_transactions_for_address(
                    address, limit=100
                )
                if not transactions:
                    continue

                for tx in transactions:
                    flow = await self._analyze_bridge_tx(
                        tx, wallet_info, birdeye_client, min_usd_threshold
                    )
                    if flow:
                        flows.append(flow)
                        self._set_cache(cache_key, current_time)

            except Exception as e:
                logger.debug(f"Error detecting bridge flows for {address}: {e}")
                continue

        logger.info(f"Detected {len(flows)} bridge flows")
        return flows

    async def _analyze_bridge_tx(
        self,
        tx: Dict[str, Any],
        wallet: SmartMoneyWallet,
        birdeye_client: Any,
        min_threshold: float,
    ) -> Optional[BridgeFlow]:
        """Analyze a transaction for bridge flow patterns."""
        try:
            signature = tx.get("signature", "")
            timestamp = tx.get("timestamp", 0)
            source = tx.get("source", "").lower()

            # Detect bridge protocol from source
            bridge_name = ""
            dest_chain = ""

            for bridge, config in self.KNOWN_BRIDGES.items():
                if bridge in source:
                    bridge_name = bridge
                    dest_chain = config["destinations"][0] if config["destinations"] else "unknown"
                    break

            # Check for cross-chain transfers via token transfers
            token_transfers = tx.get("tokenTransfers", [])
            native_transfers = tx.get("nativeTransfers", [])

            if token_transfers:
                for transfer in token_transfers:
                    token_address = transfer.get("mint", "")
                    token_symbol = transfer.get("symbol", "UNKNOWN")
                    raw_amount = self._safe_float(transfer.get("amount", 0))
                    decimals = transfer.get("decimals", 9)
                    token_amount = raw_amount / (10 ** decimals)

                    # Get USD value
                    amount_usd = 0.0
                    try:
                        price_data = await birdeye_client.get_price(token_address)
                        if price_data:
                            amount_usd = token_amount * price_data.price
                    except Exception:
                        pass

                    if amount_usd < min_threshold:
                        continue

                    # Determine direction
                    is_outflow = transfer.get("fromUserAccount") == wallet.address

                    return BridgeFlow(
                        wallet=wallet.label or wallet.address[:12],
                        source_chain="solana" if not is_outflow else dest_chain,
                        destination_chain=dest_chain if not is_outflow else "solana",
                        token=token_symbol,
                        token_address=token_address,
                        amount_usd=amount_usd,
                        flow_type="bridge_out" if is_outflow else "bridge_in",
                        bridge_name=bridge_name or "unknown",
                        timestamp=timestamp,
                        tx_hash=signature,
                        confidence=0.6 if bridge_name else 0.4,
                    )

            # Check native SOL transfers (common for bridge to Ethereum)
            if native_transfers:
                for transfer in native_transfers:
                    sol_amount = self._safe_float(transfer.get("amount", 0)) / 1e9
                    # Rough SOL price
                    sol_price = 100
                    amount_usd = sol_amount * sol_price

                    if amount_usd < min_threshold:
                        continue

                    is_outflow = transfer.get("fromUserAccount") == wallet.address

                    return BridgeFlow(
                        wallet=wallet.label or wallet.address[:12],
                        source_chain="solana" if not is_outflow else "ethereum",
                        destination_chain="ethereum" if not is_outflow else "solana",
                        token="SOL",
                        token_address="So11111111111111111111111111111111111111112",
                        amount_usd=amount_usd,
                        flow_type="bridge_out" if is_outflow else "bridge_in",
                        bridge_name=bridge_name or "wormhole",  # Common for SOL bridges
                        timestamp=timestamp,
                        tx_hash=signature,
                        confidence=0.5,
                    )

        except Exception as e:
            logger.debug(f"Error analyzing bridge tx: {e}")

        return None

    # =========================================================================
    # Combined Scan
    # =========================================================================

    async def scan_all(
        self,
        helius_client: Any,
        birdeye_client: Any,
        dexscreener_client: Any,
        tokens: Optional[List[str]] = None,
    ) -> Dict[str, List[Any]]:
        """
        Run all alpha signal detections in parallel.

        Args:
            helius_client: Helius API client
            birdeye_client: Birdeye API client
            dexscreener_client: DexScreener API client
            tokens: List of token addresses for volume monitoring

        Returns:
            Dict with keys: 'smart_money_flows', 'volume_spikes', 'new_pairs', 'bridge_flows'
        """
        tokens = tokens or []

        # Run all detections in parallel
        results = await asyncio.gather(
            self.detect_smart_money_flow(helius_client, birdeye_client),
            self.detect_volume_spikes(birdeye_client, tokens) if tokens else asyncio.sleep(0),
            self.monitor_new_pairs(dexscreener_client),
            self.detect_bridge_flows(helius_client, birdeye_client),
            return_exceptions=True,
        )

        return {
            "smart_money_flows": results[0] if not isinstance(results[0], Exception) else [],
            "volume_spikes": results[1] if not isinstance(results[1], Exception) else [],
            "new_pairs": results[2] if not isinstance(results[2], Exception) else [],
            "bridge_flows": results[3] if not isinstance(results[3], Exception) else [],
        }

    # =========================================================================
    # Formatting
    # =========================================================================

    def format_smart_money_telegram(self, flow: SmartMoneyFlow) -> str:
        """Format smart money flow for Telegram."""
        emoji = "📈" if flow.flow_type == "accumulate" else "📉"
        return (
            f"{emoji} *Smart Money Flow*\n"
            f"🏦 {flow.wallet}\n"
            f"💎 {flow.token} ({flow.flow_type})\n"
            f"💰 ${flow.amount_usd:,.0f}\n"
            f"📊 Confidence: {flow.confidence:.0%}"
        )

    def format_volume_spike_telegram(self, spike: VolumeSpike) -> str:
        """Format volume spike for Telegram."""
        return (
            f"📊 *Volume Spike Detected*\n"
            f"💎 {spike.token_symbol}\n"
            f"📈 Vol: ${spike.volume_24h:,.0f} ({spike.volume_change_pct:+.0f}%)\n"
            f"💵 Price: {spike.price_change_pct:+.1f}%\n"
            f"🏷️ Type: {spike.spike_type}"
        )

    def format_new_pair_telegram(self, alert: NewPairAlert) -> str:
        """Format new pair alert for Telegram."""
        warning = "⚠️ SUSPICIOUS" if alert.is_suspicious else "🆕 New"
        flags = ", ".join(alert.red_flags[:3]) if alert.red_flags else "None"

        return (
            f"{warning} *New Pair Detected*\n"
            f"🔄 {alert.pair.base_token}/{alert.pair.quote_token}\n"
            f"💧 Liquidity: ${alert.pair.liquidity_usd:,.0f}\n"
            f"📊 Vol: ${alert.pair.volume_24h:,.0f}\n"
            f"⚑ Flags: {flags}"
        )

    def format_bridge_flow_telegram(self, flow: BridgeFlow) -> str:
        """Format bridge flow for Telegram."""
        arrow = "→" if flow.flow_type == "bridge_out" else "←"
        return (
            f"🌉 *Bridge Flow*\n"
            f"🏦 {flow.wallet}\n"
            f"{flow.source_chain} {arrow} {flow.destination_chain}\n"
            f"💎 {flow.amount_usd:,.0f} {flow.token}\n"
            f"🔗 {flow.bridge_name}"
        )

    # =========================================================================
    # Cache Helpers
    # =========================================================================

    def _is_in_cache(self, key: str, cooldown: int) -> bool:
        """Check if key is in signal cache and not expired."""
        if key not in self._signal_cache:
            return False
        return (time.time() - self._signal_cache[key]) < cooldown

    def _set_cache(self, key: str, timestamp: float) -> None:
        """Set cache entry with timestamp."""
        self._signal_cache[key] = timestamp

    def clear_cache(self) -> None:
        """Clear the signal cache."""
        self._signal_cache.clear()

    # =========================================================================
    # Static Helpers
    # =========================================================================

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
    def _safe_str(value, default: str = "") -> str:
        """Safely convert value to string."""
        if value is None:
            return default
        return str(value)
