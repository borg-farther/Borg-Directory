"""
Helius Solana RPC API client.

API key required (from HELIUS_API_KEY env var).
Docs: https://docs.helius.xyz/

Provides enhanced transaction parsing, wallet activity, and DAS API access.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from .base import BaseAPIClient
from borg.defi.data_models import Transaction, WhaleAlert

logger = logging.getLogger(__name__)

# Helius API endpoints
HELIUS_BASE = "https://api.helius.xyz/v0"
HELIUS_RPC = "https://mainnet.helius-rpc.com"

# Environment variable for API key
HELIUS_API_KEY_ENV = "HELIUS_API_KEY"


class HeliusClient(BaseAPIClient):
    """Client for Helius Solana RPC and API."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Helius client.

        Args:
            api_key: Helius API key. If not provided, reads from HELIUS_API_KEY env var.
        """
        env_key = os.environ.get(HELIUS_API_KEY_ENV)
        key = api_key or env_key
        if not key:
            logger.warning("Helius API key not provided. Set HELIUS_API_KEY env var.")

        super().__init__(base_url=HELIUS_BASE, api_key=key, **kwargs)
        self._rpc_url = f"{HELIUS_RPC}?api-key={key}" if key else None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def get_transactions_for_address(
        self,
        address: str,
        limit: int = 100,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get recent transactions for a wallet address.

        Uses Helius enhanced transactions API.
        GET https://api.helius.xyz/v0/addresses/{address}/transactions

        Args:
            address: Wallet public key
            limit: Max transactions to return

        Returns:
            List of transaction dicts or None on error
        """
        if not self._api_key:
            logger.error("Helius API key required for get_transactions_for_address")
            return None

        url = f"{self._base_url}/addresses/{address}/transactions"
        params = {"limit": limit}

        try:
            data = await self.get(url, params=params)
            if data and isinstance(data, list):
                return data
            return None
        except Exception as e:
            logger.error(f"Failed to get transactions for {address}: {e}")
            return None

    async def parse_whale_alerts(
        self,
        address: str,
        min_usd: float = 50_000,
    ) -> List[WhaleAlert]:
        """
        Parse whale alerts from wallet transaction history.

        Args:
            address: Wallet public key
            min_usd: Minimum USD value to trigger alert

        Returns:
            List of WhaleAlert dataclasses
        """
        transactions = await self.get_transactions_for_address(address)
        if not transactions:
            return []

        alerts = []
        for tx in transactions:
            try:
                alert = self._parse_transaction_to_alert(tx, address)
                if alert and alert.amount_usd >= min_usd:
                    alerts.append(alert)
            except Exception as e:
                logger.debug(f"Skipping tx due to parse error: {e}")
                continue

        logger.info(f"Parsed {len(alerts)} whale alerts for {address}")
        return alerts

    def _parse_transaction_to_alert(self, tx: Dict[str, Any], wallet: str) -> Optional[WhaleAlert]:
        """Parse a Helius enhanced transaction into a WhaleAlert."""
        try:
            # Extract transaction type and details
            tx_type = tx.get("type", "unknown")
            signature = tx.get("signature", "")
            timestamp = tx.get("timestamp", 0)
            fee = tx.get("fee", 0)

            # Parse token transfers
            token_transfers = tx.get("tokenTransfers", [])
            native_transfers = tx.get("nativeTransfers", [])

            if not token_transfers and not native_transfers:
                return None

            # Determine action type
            action = self._determine_action(tx_type, token_transfers)

            # Get token in/out
            token_in = ""
            token_out = ""
            amount_usd = 0.0

            if token_transfers:
                for transfer in token_transfers:
                    if transfer.get("fromUserAccount") == wallet:
                        token_out = transfer.get("mintSymbol", transfer.get("mint", ""))
                        amount_usd += self._safe_float(transfer.get("amount", 0))
                    elif transfer.get("toUserAccount") == wallet:
                        token_in = transfer.get("mintSymbol", transfer.get("mint", ""))
                        amount_usd += self._safe_float(transfer.get("amount", 0))

            if native_transfers:
                for transfer in native_transfers:
                    if transfer.get("fromUserAccount") == wallet:
                        token_out = "SOL"
                        amount_usd += self._safe_float(transfer.get("amount", 0)) / 1e9 * tx.get("slot", 1)
                    elif transfer.get("toUserAccount") == wallet:
                        token_in = "SOL"

            # Estimate USD value if not provided
            if amount_usd == 0 and native_transfers:
                sol_amount = sum(
                    self._safe_float(t.get("amount", 0)) / 1e9
                    for t in native_transfers
                )
                # Use rough SOL price estimate
                amount_usd = sol_amount * 100  # Approximate

            # Build context string
            context = f"{action} "
            if token_in:
                context += f"{token_in} → {token_out}" if token_out else f"received {token_in}"
            elif token_out:
                context += f"sent {token_out}"
            context += f" via {tx.get('source', 'unknown')}"

            return WhaleAlert(
                wallet=wallet,
                chain="solana",
                action=action,
                token_in=token_in,
                token_out=token_out,
                amount_usd=amount_usd,
                timestamp=timestamp,
                tx_hash=signature,
                context=context,
                signal_strength=0.5,  # Will be updated by scoring
            )

        except Exception as e:
            logger.debug(f"Failed to parse transaction: {e}")
            return None

    def _determine_action(self, tx_type: str, token_transfers: List) -> str:
        """Determine action type from transaction."""
        type_lower = tx_type.lower() if tx_type else ""

        if "swap" in type_lower or "exchange" in type_lower:
            return "swap"
        elif "transfer" in type_lower:
            if len(token_transfers) > 1:
                return "swap"
            return "transfer"
        elif "mint" in type_lower:
            return "mint"
        elif "burn" in type_lower:
            return "burn"
        elif "stake" in type_lower:
            return "stake"
        elif "unstake" in type_lower:
            return "unstake"
        return "unknown"

    async def get_enhanced_transaction(self, signature: str) -> Optional[Transaction]:
        """
        Get enhanced transaction details by signature.

        Args:
            signature: Transaction signature

        Returns:
            Transaction dataclass or None
        """
        if not self._api_key or not self._rpc_url:
            logger.error("Helius API key required for get_enhanced_transaction")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {"maxSupportedTransactionVersion": 0}
            ]
        }

        try:
            data = await self.post(self._rpc_url, json=payload)
            if not data or "result" not in data:
                return None

            result = data["result"]
            return self._parse_rpc_transaction(result)

        except Exception as e:
            logger.error(f"Failed to get enhanced transaction {signature}: {e}")
            return None

    def _parse_rpc_transaction(self, tx: Dict[str, Any]) -> Transaction:
        """Parse RPC transaction response into Transaction dataclass."""
        meta = tx.get("meta", {})
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])

        # Determine status
        status = "success"
        if meta.get("err"):
            status = "failed"

        # Build account list
        accounts = []
        if tx.get("transaction", {}).get("message", {}).get("accountKeys"):
            accounts = tx["transaction"]["message"]["accountKeys"]

        # Build token balance changes
        token_balances = {}
        for post in post_balances:
            mint = post.get("mint", "")
            account = post.get("owner", "")
            if mint and account:
                if account not in token_balances:
                    token_balances[account] = {}
                token_balances[account][mint] = self._safe_float(post.get("uiTokenAmount", {}).get("amount", 0))

        # Determine transaction type
        tx_type = self._determine_tx_type(tx)

        return Transaction(
            signature=tx.get("signature", ""),
            slot=tx.get("slot", 0),
            timestamp=tx.get("blockTime", 0),
            fee=meta.get("fee", 0),
            status=status,
            type=tx_type,
            accounts=accounts,
            token_balances=token_balances,
            error=str(meta.get("err")) if meta.get("err") else None,
        )

    def _determine_tx_type(self, tx: Dict[str, Any]) -> str:
        """Determine transaction type from parsed transaction."""
        # This is a simplified type detection
        # In production, you'd want to inspect instructions
        logs = tx.get("meta", {}).get("logMessages", [])
        log_str = " ".join(logs).lower() if logs else ""

        if "swap" in log_str or "raydium" in log_str or "orca" in log_str:
            return "swap"
        elif "transfer" in log_str:
            return "transfer"
        return "unknown"

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
