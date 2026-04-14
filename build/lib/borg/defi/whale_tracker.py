"""
Whale Tracker — Monitor high-value wallet movements across chains.

Scans Solana (via Helius) and EVM chains (via Alchemy) for whale activity.
Generates alerts with signal scoring based on whale history.
Integrates Arkham Intelligence for entity labels and smart money detection.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from borg.defi.data_models import WhaleAlert
from borg.defi.api_clients.arkham import ArkhamClient


@dataclass
class WhaleHistory:
    """Historical performance data for a tracked whale wallet."""
    wallet: str
    label: str
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl_usd: float = 0.0
    last_trade_timestamp: float = 0.0
    win_rate: float = 0.5  # Default neutral

    def update_from_trade(self, profitable: bool, pnl: float = 0.0):
        """Update history after a trade outcome is known."""
        self.total_trades += 1
        if profitable:
            self.winning_trades += 1
        self.total_pnl_usd += pnl
        self.last_trade_timestamp = time.time()
        if self.total_trades > 0:
            self.win_rate = self.winning_trades / self.total_trades


@dataclass
class WhaleTracker:
    """Monitor whale wallets and generate alerts.

    Attributes:
        tracked_wallets: Dict of wallet address -> label
        min_usd_threshold: Minimum USD value to trigger alert (default $50K)
        alert_cooldown: Seconds between alerts for same wallet (default 300 = 5min)
        whale_history: Dict of wallet -> WhaleHistory for signal scoring
        arkham_api_key: Optional Arkham API key for entity intelligence
        arkham_client: Optional ArkhamClient instance (created from arkham_api_key)
        smart_money_cache: Cached smart money entities
    """

    tracked_wallets: Dict[str, str] = field(default_factory=dict)
    min_usd_threshold: float = 50_000.0
    alert_cooldown: int = 300  # 5 minutes
    whale_history: Dict[str, WhaleHistory] = field(default_factory=dict)
    _cooldown_cache: Dict[str, float] = field(default_factory=dict)
    arkham_api_key: Optional[str] = field(default=None)
    arkham_client: Optional[Any] = field(default=None, repr=False)
    _smart_money_cache: Optional[List[Dict[str, Any]]] = field(default=None)

    # Explorer URLs by chain
    EXPLORER_URLS: Dict[str, str] = field(default_factory=lambda: {
        "solana": "https://solscan.io/tx/{}",
        "ethereum": "https://etherscan.io/tx/{}",
        "base": "https://basescan.org/tx/{}",
        "arbitrum": "https://arbiscan.io/tx/{}",
    })

    def __post_init__(self):
        """Initialize cooldown cache, whale history, and optionally Arkham client."""
        self._cooldown_cache: Dict[str, float] = {}
        # Initialize history for all tracked wallets
        for wallet, label in self.tracked_wallets.items():
            if wallet not in self.whale_history:
                self.whale_history[wallet] = WhaleHistory(wallet=wallet, label=label)
        # Initialize Arkham client if API key provided
        if self.arkham_api_key:
            self.arkham_client = ArkhamClient(api_key=self.arkham_api_key)

    def _is_under_cooldown(self, wallet: str) -> bool:
        """Check if wallet is under cooldown period."""
        if wallet not in self._cooldown_cache:
            return False
        elapsed = time.time() - self._cooldown_cache[wallet]
        return elapsed < self.alert_cooldown

    def _set_cooldown(self, wallet: str) -> None:
        """Set cooldown for wallet."""
        self._cooldown_cache[wallet] = time.time()

    def _get_wallet_label(self, wallet: str) -> str:
        """Get label for wallet, or truncated address if unknown."""
        if wallet in self.tracked_wallets:
            return self.tracked_wallets[wallet]
        # Return truncated address for unknown wallets
        return f"{wallet[:6]}...{wallet[-4:]}"

    def _explorer_url(self, alert: WhaleAlert) -> str:
        """Get block explorer URL for transaction."""
        base_url = self.EXPLORER_URLS.get(alert.chain, "https://etherscan.io/tx/{}")
        return base_url.format(alert.tx_hash)

    def _hash_wallet_for_collective(self, wallet: str) -> str:
        """Create a hashed identifier for wallet when sharing externally."""
        return hashlib.sha256(wallet.encode()).hexdigest()[:16]

    def score_signal(self, alert: WhaleAlert) -> float:
        """Score signal strength using whale history.

        Known whales with high win rates get higher scores.
        Large moves (> $500K) from unknown whales are flagged for discovery.

        Args:
            alert: The whale alert to score

        Returns:
            Signal strength 0.0-1.0
        """
        # Base score from amount (logarithmic scale)
        amount_score = min(1.0, 1.0 + (alert.amount_usd / 1_000_000) * 0.1)

        # Check if we have history for this wallet
        if alert.wallet in self.whale_history:
            history = self.whale_history[alert.wallet]
            # Historical accuracy factor: win_rate * 0.5 + 0.25 baseline
            history_factor = (history.win_rate * 0.5) + 0.25
            # Recency factor: more recent = more relevant
            recency = 1.0
            if history.last_trade_timestamp > 0:
                days_since = (time.time() - history.last_trade_timestamp) / 86400
                recency = max(0.5, 1.0 - (days_since * 0.05))  # Decay over time
            # Combine factors
            signal = (history_factor * 0.6) + (recency * 0.2) + (amount_score * 0.2)
            return min(1.0, max(0.0, signal))
        else:
            # Unknown wallet - neutral base score
            # Large moves from unknown wallets get discovery flag
            base_score = 0.5
            # Scale by amount for unknown wallets
            if alert.amount_usd > 500_000:
                # Flag for discovery - this is a significant unknown whale
                base_score = 0.6
            elif alert.amount_usd > 100_000:
                base_score = 0.55
            return min(1.0, base_score * amount_score)

    async def scan_solana(self, helius_client: Any, min_timestamp: float = 0) -> List[WhaleAlert]:
        """Scan Solana whale activity via Helius.

        Args:
            helius_client: Helius API client instance
            min_timestamp: Only return txs after this timestamp

        Returns:
            List of WhaleAlert objects
        """
        alerts: List[WhaleAlert] = []

        # Iterate through all tracked Solana wallets
        for wallet in self.tracked_wallets:
            # Check cooldown
            if self._is_under_cooldown(wallet):
                continue

            # Fetch transactions from Helius
            try:
                txs = await helius_client.get_transactions(wallet, min_timestamp)
            except Exception:
                continue

            for tx in txs:
                # Parse transaction
                alert = self._parse_solana_tx(tx)
                if alert is None:
                    continue

                # Check threshold
                if alert.amount_usd < self.min_usd_threshold:
                    continue

                # Score the signal
                alert.signal_strength = self.score_signal(alert)

                # Set cooldown
                self._set_cooldown(wallet)

                alerts.append(alert)

        return alerts

    async def scan_evm(self, alchemy_client: Any, chain: str, min_timestamp: float = 0) -> List[WhaleAlert]:
        """Scan EVM chain whale activity via Alchemy.

        Args:
            alchemy_client: Alchemy API client instance
            chain: Chain name (ethereum|base|arbitrum)
            min_timestamp: Only return txs after this timestamp

        Returns:
            List of WhaleAlert objects
        """
        alerts: List[WhaleAlert] = []

        for wallet in self.tracked_wallets:
            # Check cooldown
            if self._is_under_cooldown(wallet):
                continue

            try:
                transfers = await alchemy_client.get_asset_transfers(wallet, chain, min_timestamp)
            except Exception:
                continue

            for transfer in transfers:
                alert = self._parse_evm_transfer(transfer, chain)
                if alert is None:
                    continue

                if alert.amount_usd < self.min_usd_threshold:
                    continue

                alert.signal_strength = self.score_signal(alert)
                self._set_cooldown(wallet)
                alerts.append(alert)

        return alerts

    async def scan_all(self, helius_client: Any, alchemy_clients: Dict[str, Any]) -> List[WhaleAlert]:
        """Scan all chains and return combined whale alerts.

        Args:
            helius_client: Helius API client for Solana
            alchemy_clients: Dict of chain name -> Alchemy client

        Returns:
            Combined list of WhaleAlert from all chains
        """
        all_alerts: List[WhaleAlert] = []

        # Scan Solana
        solana_alerts = await self.scan_solana(helius_client)
        all_alerts.extend(solana_alerts)

        # Scan each EVM chain
        for chain, client in alchemy_clients.items():
            evm_alerts = await self.scan_evm(client, chain)
            all_alerts.extend(evm_alerts)

        return all_alerts

    def _parse_solana_tx(self, tx: Dict) -> Optional[WhaleAlert]:
        """Parse a Helius enhanced transaction into a WhaleAlert.

        Args:
            tx: Raw transaction dict from Helius

        Returns:
            WhaleAlert or None if not parseable
        """
        try:
            # Extract basic info
            tx_type = tx.get("type", "")
            if tx_type not in ("swap", "transfer"):
                return None

            signature = tx.get("signature", "")
            timestamp = tx.get("timestamp", 0)
            accounts = tx.get("accounts", [])
            fee = tx.get("fee", 0)

            # Get wallet (first account usually)
            wallet = accounts[0] if accounts else ""

            # Determine action and tokens
            if tx_type == "swap":
                token_balances = tx.get("token_balances", {})
                token_in = token_balances.get("from_token", "UNKNOWN")
                token_out = token_balances.get("to_token", "UNKNOWN")
                amount_usd = self._estimate_swap_value(token_balances)
                action = "swap"
                context = f"Swapped {token_in} for {token_out}"
            else:  # transfer
                token_in = tx.get("token", "SOL")
                token_out = ""
                amount_usd = tx.get("value_usd", 0)
                action = "transfer"
                context = f"Transferred {amount_usd:,.0f} in {token_in}"

            return WhaleAlert(
                wallet=self._get_wallet_label(wallet),
                chain="solana",
                action=action,
                token_in=token_in,
                token_out=token_out,
                amount_usd=amount_usd,
                timestamp=timestamp,
                tx_hash=signature,
                context=context,
                signal_strength=0.5,  # Will be updated by score_signal
            )
        except Exception:
            return None

    def _parse_evm_transfer(self, transfer: Dict, chain: str) -> Optional[WhaleAlert]:
        """Parse an Alchemy asset transfer into a WhaleAlert.

        Args:
            transfer: Raw transfer dict from Alchemy
            chain: Chain name

        Returns:
            WhaleAlert or None if not parseable
        """
        try:
            tx_hash = transfer.get("hash", "")
            timestamp = transfer.get("timestamp", 0)
            from_addr = transfer.get("from", "")
            to_addr = transfer.get("to", "")
            value = transfer.get("value", 0)
            asset = transfer.get("asset", "ETH")
            raw_value = float(value) if value else 0.0

            # Determine if this is a swap or transfer
            # (In real implementation, would decode events from DEX routers)
            action = "transfer"
            token_in = asset
            token_out = ""
            amount_usd = raw_value  # Would convert using price data

            # Simple heuristic: if we have both from and to with value, it's a swap
            if from_addr and to_addr and raw_value > 0:
                action = "swap"
                token_out = asset
                context = f"Swapped {raw_value:,.0f} {asset}"
            else:
                context = f"Transferred {raw_value:,.0f} {asset}"

            return WhaleAlert(
                wallet=self._get_wallet_label(from_addr or to_addr),
                chain=chain,
                action=action,
                token_in=token_in,
                token_out=token_out,
                amount_usd=amount_usd,
                timestamp=timestamp,
                tx_hash=tx_hash,
                context=context,
                signal_strength=0.5,
            )
        except Exception:
            return None

    def _estimate_swap_value(self, token_balances: Dict) -> float:
        """Estimate USD value of a swap from token balances."""
        # In production, would use Birdeye price data
        # For now, return a placeholder calculation
        from_val = token_balances.get("from_amount_usd", 0)
        to_val = token_balances.get("to_amount_usd", 0)
        return max(from_val, to_val)

    def format_telegram(self, alert: WhaleAlert) -> str:
        """Format alert for Telegram delivery.

        Args:
            alert: The whale alert to format

        Returns:
            Formatted Telegram message string
        """
        # Action emoji
        action_emoji = {
            "swap": "🟢",
            "transfer": "🔵",
            "mint": "🟣",
            "burn": "🔴",
            "stake": "🟠",
            "unstake": "🟡",
        }.get(alert.action, "⚪")

        # Signal strength fire emojis
        fire_count = int(alert.signal_strength * 5)
        fire_emojis = "🔥" * fire_count if fire_count > 0 else "➖"

        # Explorer link
        explorer_link = self._explorer_url(alert)

        return (
            f"🐋 *Whale Alert*\n"
            f"{action_emoji} {alert.context}\n"
            f"💰 ${alert.amount_usd:,.0f}\n"
            f"📊 Signal: {fire_emojis}\n"
            f"🔗 [{alert.chain}]({explorer_link})"
        )

    def format_discord(self, alert: WhaleAlert) -> str:
        """Format alert for Discord delivery.

        Args:
            alert: The whale alert to format

        Returns:
            Formatted Discord message string with markdown
        """
        # Action emoji (Discord-compatible)
        action_emoji = {
            "swap": "🟢",
            "transfer": "🔵",
            "mint": "🟣",
            "burn": "🔴",
            "stake": "🟠",
            "unstake": "🟡",
        }.get(alert.action, "⚪")

        # Signal strength indicator
        signal_bars = int(alert.signal_strength * 5)
        signal_str = "▮" * signal_bars + "▯" * (5 - signal_bars)

        # Explorer link
        explorer_link = self._explorer_url(alert)

        # Discord uses different markdown
        return (
            f"🐋 **Whale Alert**\n"
            f"{action_emoji} *{alert.context}*\n"
            f"💰 **${alert.amount_usd:,.0f}**\n"
            f"📊 Signal: {signal_str}\n"
            f"🔗 [{alert.chain}]({explorer_link})"
        )

    def format_for_collective(self, alert: WhaleAlert) -> Dict[str, Any]:
        """Format alert for sharing with collective (PII-safe).

        Args:
            alert: The whale alert to format

        Returns:
            Dict suitable for collective sharing (no raw addresses)
        """
        return {
            "wallet_hash": self._hash_wallet_for_collective(
                alert.wallet if not alert.wallet.startswith("0x") else alert.wallet
            ),
            "chain": alert.chain,
            "action": alert.action,
            "token_in": alert.token_in,
            "token_out": alert.token_out,
            "amount_usd": alert.amount_usd,
            "signal_strength": alert.signal_strength,
            "context": alert.context,
        }

    def check_discovery(self, alert: WhaleAlert) -> bool:
        """Check if this is a new whale discovery (large move from unknown wallet).

        Args:
            alert: The whale alert to check

        Returns:
            True if this is a discovery candidate (> $500K from unknown whale)
        """
        # Unknown wallet + large move = potential discovery
        is_known = alert.wallet in self.tracked_wallets
        large_move = alert.amount_usd > 500_000

        return not is_known and large_move

    async def enrich_alert_with_arkham(self, alert: WhaleAlert) -> WhaleAlert:
        """Enrich a whale alert with Arkham entity intelligence.

        If Arkham API key is available, fetches entity labels and tags
        for the wallet address and updates the alert's context and signal strength.

        Args:
            alert: The whale alert to enrich

        Returns:
            Enriched WhaleAlert with entity labels and updated signal strength
        """
        if not self.arkham_client:
            return alert

        try:
            # Extract raw address from wallet label (if it's a truncated address)
            address = alert.wallet
            if "..." in address:
                # Can't enrich without full address - skip
                return alert

            entity_info = await self.arkham_client.enrich_alert_with_entity(address)
            if not entity_info:
                return alert

            entity_name = entity_info.get("entity_name")
            labels = entity_info.get("labels", [])
            is_smart_money = entity_info.get("is_smart_money", False)

            # Build enriched context
            enrichment_parts = []
            if entity_name:
                enrichment_parts.append(f"Entity: {entity_name}")
            if labels:
                enrichment_parts.append(f"Labels: {', '.join(labels[:3])}")
            if is_smart_money:
                enrichment_parts.append("Smart Money")

            if enrichment_parts:
                alert.context = f"{alert.context} | {' | '.join(enrichment_parts)}"

            # Boost signal strength for smart money
            if is_smart_money:
                alert.signal_strength = min(1.0, alert.signal_strength * 1.3)

            return alert

        except Exception as e:
            # Don't fail the alert due to enrichment error
            return alert

    async def get_smart_money_wallets(self) -> Optional[List[Dict[str, Any]]]:
        """Get known smart money wallets from Arkham.

        Returns cached results if available, otherwise queries Arkham
        for entities matching known smart money labels.

        Returns:
            List of smart money entity dicts with id, name, labels, addresses,
            or None if Arkham is not configured
        """
        if not self.arkham_client:
            return None

        # Return cached results if available
        if self._smart_money_cache is not None:
            return self._smart_money_cache

        try:
            self._smart_money_cache = await self.arkham_client.get_smart_money_wallets()
            return self._smart_money_cache
        except Exception:
            return None

    async def discover_new_whales(
        self, min_usd: float = 100_000, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Discover potential new whale wallets from recent large transfers.

        Uses Arkham to find large transfers from unknown wallets that may
        represent undiscovered smart money or whale activity.

        Args:
            min_usd: Minimum USD value to consider (default $100K)
            limit: Maximum number of discoveries to return

        Returns:
            List of potential whale discoveries with entity info
        """
        discoveries = []

        if not self.arkham_client:
            return discoveries

        # For tracked wallets, check if any have Arkham entity data
        for wallet in self.tracked_wallets:
            if wallet.startswith("0x") or len(wallet) > 40:
                # EVM or long address format
                try:
                    entity_info = await self.arkham_client.enrich_alert_with_entity(wallet)
                    if entity_info and entity_info.get("is_smart_money"):
                        discoveries.append({
                            "address": wallet,
                            "entity_name": entity_info.get("entity_name"),
                            "labels": entity_info.get("labels", []),
                            "source": "tracked_wallets",
                        })
                except Exception:
                    continue

            if len(discoveries) >= limit:
                break

        return discoveries
