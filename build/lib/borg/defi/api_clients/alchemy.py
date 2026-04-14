"""
Alchemy EVM RPC API client.

API key required (from ALCHEMY_API_KEY env var).
Docs: https://docs.alchemy.com/

Provides EVM chain token balances, transfers, metadata, and transaction receipts.
Supports: ethereum, polygon, arbitrum, optimism, base
"""

import os
import logging
from typing import List, Optional, Dict, Any
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

# Alchemy API endpoints
ALCHEMY_NETWORKS = {
    "eth-mainnet": "eth-mainnet.g.alchemy.com",
    "ethereum-mainnet": "eth-mainnet.g.alchemy.com",
    "polygon-mainnet": "polygon-mainnet.g.alchemy.com",
    "arb-mainnet": "arb-mainnet.g.alchemy.com",
    "arbitrum-mainnet": "arb-mainnet.g.alchemy.com",
    "opt-mainnet": "opt-mainnet.g.alchemy.com",
    "optimism-mainnet": "opt-mainnet.g.alchemy.com",
    "base-mainnet": "base-mainnet.g.alchemy.com",
}

# Environment variable for API key
ALCHEMY_API_KEY_ENV = "ALCHEMY_API_KEY"


class AlchemyClient(BaseAPIClient):
    """Client for Alchemy EVM RPC API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        network: str = "eth-mainnet",
        **kwargs,
    ):
        """
        Initialize Alchemy client.

        Args:
            api_key: Alchemy API key. If not provided, reads from ALCHEMY_API_KEY env var.
            network: Network name (eth-mainnet, polygon-mainnet, arb-mainnet, opt-mainnet, base-mainnet)
        """
        env_key = os.environ.get(ALCHEMY_API_KEY_ENV)
        key = api_key or env_key
        if not key:
            logger.warning("Alchemy API key not provided. Set ALCHEMY_API_KEY env var.")

        self._api_key = key
        self._network = network

        # Build base URL
        if network in ALCHEMY_NETWORKS:
            host = ALCHEMY_NETWORKS[network]
        else:
            host = f"{network}.g.alchemy.com"

        base_url = f"https://{host}/v2/{key}" if key else f"https://{host}/v2/"
        super().__init__(base_url=base_url, api_key=key, **kwargs)

    def _get_rpc_url(self) -> str:
        """Get the RPC URL for JSON-RPC calls."""
        if self._api_key:
            return f"https://{ALCHEMY_NETWORKS.get(self._network, self._network)}/v2/{self._api_key}"
        return ""

    def _build_headers(self) -> Dict[str, str]:
        """Build headers for requests."""
        return {"Content-Type": "application/json"}

    async def _rpc_call(
        self,
        method: str,
        params: List[Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Make a JSON-RPC call to Alchemy.

        Args:
            method: RPC method name
            params: List of parameters

        Returns:
            RPC response result or None on error
        """
        if not self._api_key:
            logger.error("Alchemy API key required for RPC calls")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        rpc_url = self._get_rpc_url()
        try:
            data = await self.post(rpc_url, json=payload)
            if data and "result" in data:
                return data["result"]
            return data
        except Exception as e:
            logger.error(f"Alchemy RPC {method} failed: {e}")
            return None

    async def get_token_balances(
        self,
        address: str,
        token_type: str = "erc20",
    ) -> List[Dict[str, Any]]:
        """
        Get token balances for an address.

        Uses Alchemy's token balance API.

        POST https://{network}.g.alchemy.com/v2/{api_key}

        Args:
            address: Wallet address
            token_type: Token type (erc20, erc721, erc1155)

        Returns:
            List of token balance dicts with contractAddress, tokenBalance, etc.
        """
        if token_type == "erc20":
            method = "alchemy_getTokenBalances"
        elif token_type == "erc721":
            method = "alchemy_getNFTs"
        else:
            method = "alchemy_getTokenMetadata"

        try:
            # For ERC20, use getTokenBalances
            if token_type == "erc20":
                result = await self._rpc_call(
                    "alchemy_getTokenBalances",
                    [address, "erc20"],
                )
            else:
                result = await self._rpc_call(
                    method,
                    [address],
                )

            if result:
                return result.get("tokenBalances", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get token balances for {address}: {e}")
            return []

    async def get_asset_transfers(
        self,
        address: str,
        category: str = "erc20",
        from_block: str = "0x0",
        to_block: str = "latest",
    ) -> List[Dict[str, Any]]:
        """
        Get asset transfers for an address.

        POST https://{network}.g.alchemy.com/v2/{api_key}

        Args:
            address: Wallet address
            category: Transfer category (erc20, erc721, erc1155, native)
            from_block: Starting block (hex string like '0x0')
            to_block: Ending block (hex string or 'latest')

        Returns:
            List of transfer dicts
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getAssetTransfers",
            "params": [
                {
                    "fromBlock": from_block,
                    "toBlock": to_block,
                    "fromAddress": address,
                    "category": [category],
                }
            ],
        }

        rpc_url = self._get_rpc_url()
        try:
            data = await self.post(rpc_url, json=payload)
            if data and "result" in data:
                return data["result"].get("transfers", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get asset transfers for {address}: {e}")
            return []

    async def get_token_metadata(
        self,
        contract_address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a token contract.

        POST https://{network}.g.alchemy.com/v2/{api_key}

        Args:
            contract_address: Token contract address

        Returns:
            Token metadata dict with decimals, name, symbol, etc.
        """
        result = await self._rpc_call(
            "alchemy_getTokenMetadata",
            [contract_address],
        )
        return result

    async def get_transaction_receipts(
        self,
        tx_hashes: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Get transaction receipts for multiple transactions.

        Uses eth_getTransactionReceipt for each hash.

        Args:
            tx_hashes: List of transaction hashes

        Returns:
            List of transaction receipt dicts
        """
        receipts = []

        for tx_hash in tx_hashes:
            try:
                receipt = await self._rpc_call(
                    "eth_getTransactionReceipt",
                    [tx_hash],
                )
                if receipt:
                    receipts.append(receipt)
            except Exception as e:
                logger.error(f"Failed to get receipt for {tx_hash[:10]}: {e}")
                continue

        return receipts

    async def get_block_number(self) -> Optional[str]:
        """
        Get the current block number.

        Returns:
            Block number as hex string (e.g., '0x10d4f20')
        """
        result = await self._rpc_call("eth_blockNumber", [])
        return result

    async def get_balance(self, address: str) -> Optional[str]:
        """
        Get native balance for an address.

        Args:
            address: Wallet address

        Returns:
            Balance in wei as hex string
        """
        result = await self._rpc_call("eth_getBalance", [address, "latest"])
        return result

    async def call(
        self,
        to: str,
        data: str,
        from_block: str = "latest",
    ) -> Optional[str]:
        """
        Make a read-only call to a contract.

        Args:
            to: Contract address
            data: Call data (hex encoded)
            from_block: Block to read from

        Returns:
            Return data as hex string
        """
        result = await self._rpc_call(
            "eth_call",
            [{"to": to, "data": data}, from_block],
        )
        return result

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    async def get_erc20_transfers(
        self,
        address: str,
        from_block: str = "0x0",
        to_block: str = "latest",
    ) -> List[Dict[str, Any]]:
        """Get ERC20 token transfers for an address."""
        return await self.get_asset_transfers(address, "erc20", from_block, to_block)

    async def get_native_transfers(
        self,
        address: str,
        from_block: str = "0x0",
        to_block: str = "latest",
    ) -> List[Dict[str, Any]]:
        """Get native ETH transfers for an address."""
        return await self.get_asset_transfers(address, "native", from_block, to_block)

    async def get_nft_transfers(
        self,
        address: str,
        from_block: str = "0x0",
        to_block: str = "latest",
    ) -> List[Dict[str, Any]]:
        """Get NFT transfers for an address."""
        return await self.get_asset_transfers(address, "erc721", from_block, to_block)

    @staticmethod
    def hex_to_int(hex_str: str) -> int:
        """Convert hex string to integer."""
        if not hex_str or hex_str == "0x":
            return 0
        try:
            return int(hex_str, 16)
        except ValueError:
            return 0

    @staticmethod
    def wei_to_eth(wei: str) -> float:
        """Convert wei to ETH."""
        return AlchemyClient.hex_to_int(wei) / 1e18
