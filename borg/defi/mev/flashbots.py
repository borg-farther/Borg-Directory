"""
Flashbots Protect Client for EVM chains.

Sends bundles to Flashbots relay for MEV protection on Ethereum/EVM transactions.

API Docs: https://docs.flashbots.net/
Base URL: https://relay.flashbots.net

Requires EIP-191 signature for authentication via X-Flashbots-Signature header.
"""

import logging
from typing import List, Optional, Dict, Any
import time

from borg.defi.api_clients.base import BaseAPIClient

logger = logging.getLogger(__name__)


class FlashbotsClient(BaseAPIClient):
    """Client for Flashbots Protect API (EVM MEV protection).
    
    Endpoints:
    - POST / - Send a bundle
    - GET /bundle_stats/{bundle_hash} - Get bundle statistics
    - GET /user_stats - Get user reputation stats
    - POST /simulate - Simulate a bundle
    
    Authentication:
    - Requires EIP-191 signature of the request
    - Signature format: personal_sign(prefix + request_body, signing_key)
    """

    BASE_URL = "https://relay.flashbots.net"

    def __init__(self, signing_key: Optional[str] = None, base_url: Optional[str] = None, timeout: int = 30):
        """Initialize Flashbots client.
        
        Args:
            signing_key: Private key for EIP-191 signing (hex string, 0x-prefixed)
            base_url: Override base URL
            timeout: Request timeout in seconds
        """
        super().__init__(base_url=base_url or self.BASE_URL)
        self._signing_key = signing_key
        self._timeout = timeout

    def _get_headers(self, body_hash: str) -> Dict[str, str]:
        """Generate Flashbots authentication headers.
        
        Args:
            body_hash: SHA256 hash of the request body (hex string)
            
        Returns:
            Headers dict with X-Flashbots-Signature
        """
        headers = {
            "Content-Type": "application/json",
            "X-Flashbots-Signature": f"{self._signing_key}:{body_hash}" if self._signing_key else ""
        }
        return headers

    async def send_bundle(
        self,
        signed_txs: List[str],
        target_block: int,
        min_block_number: Optional[int] = None,
        max_block_number: Optional[int] = None,
    ) -> str:
        """Send a bundle of signed transactions to Flashbots.
        
        Args:
            signed_txs: List of signed transaction data (0x-prefixed hex)
            target_block: The block number to target for inclusion
            min_block_number: Minimum block (defaults to target_block)
            max_block_number: Maximum block (defaults to target_block + 10)
            
        Returns:
            Bundle hash string, or empty string on failure
        """
        if min_block_number is None:
            min_block_number = target_block
        if max_block_number is None:
            max_block_number = target_block + 10

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_sendBundle",
            "params": [
                {
                    "txs": signed_txs,
                    "blockNumber": hex(target_block),
                    "minTimestamp": 0,
                    "maxTimestamp": int(time.time()) + 120,
                    "revertingTxHashes": [],
                }
            ]
        }
        
        data = await self.post(self._base_url, json=payload)
        
        if data and "result" in data:
            bundle_hash = data["result"]
            logger.info(f"Flashbots bundle sent: {bundle_hash[:16]}...")
            return bundle_hash
        
        logger.error(f"Flashbots bundle send failed: {data}")
        return ""

    async def get_bundle_stats(self, bundle_hash: str) -> Dict[str, Any]:
        """Get statistics for a sent bundle.
        
        Args:
            bundle_hash: The bundle hash returned from send_bundle
            
        Returns:
            Dict with bundle statistics:
            {
                "bundle_hash": str,
                "is_high_priority": bool,
                "Simulated": dict (simulation results),
                "Sealed": bool (whether block was sealed),
                "高度": dict (block details if sealed)
            }
        """
        url = f"{self._base_url}/bundle_stats/{bundle_hash}"
        data = await self.get(url)
        
        if data:
            return {
                "bundle_hash": bundle_hash,
                "is_high_priority": data.get("isHighPriority", False),
                "simulated": data.get("Simulated", {}),
                "sealed": data.get("Sealed", False),
                "block_details": data.get("恭敬"),
            }
        
        return {"bundle_hash": bundle_hash, "error": "Failed to get stats"}

    async def get_user_stats(self, signing_key: str) -> Dict[str, Any]:
        """Get reputation and statistics for a user.
        
        Args:
            signing_key: The signing key (public address) to query stats for
            
        Returns:
            Dict with user statistics:
            {
                "address": str,
                "total_escrowed": str,
                "pending_escrowed": str,
                "escrow_balance": str,
                "reputation": int,
                "blocks_built": int,
                "bundles_submitted": int,
                "avg_revert_time": int
            }
        """
        url = f"{self._base_url}/user_stats"
        headers = {
            "X-Flashbots-Signature": f"{signing_key}"
        }
        
        # The body hash for GET requests is the address being queried
        data = await self.get(url, headers=headers)
        
        if data:
            return {
                "address": data.get("address", signing_key),
                "total_escrowed": data.get("totalEscrowed", "0"),
                "pending_escrowed": data.get("pendingEscrowed", "0"),
                "reputation": data.get("reputation", 0),
                "blocks_built": data.get("blocksBuilt", 0),
                "bundles_submitted": data.get("bundlesSubmitted", 0),
                "avg_revert_time": data.get("avgRevertTime", 0),
            }
        
        return {"address": signing_key, "error": "Failed to get user stats"}

    async def simulate_bundle(
        self,
        signed_txs: List[str],
        block_number: int,
        state_block_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Simulate a bundle before sending.
        
        Args:
            signed_txs: List of signed transaction data (0x-prefixed hex)
            block_number: Block number to simulate against
            state_block_number: Block number for state (defaults to block_number)
            
        Returns:
            Dict with simulation results:
            {
                "success": bool,
                "state_diff": dict,
                "gas_used": int,
                "logs": list,
                "error": str (if failed)
            }
        """
        if state_block_number is None:
            state_block_number = block_number

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_callBundle",
            "params": [
                {
                    "txs": signed_txs,
                    "blockNumber": hex(block_number),
                    "stateBlockNumber": hex(state_block_number),
                }
            ]
        }
        
        data = await self.post(self._base_url, json=payload)
        
        if data and "result" in data:
            result = data["result"]
            return {
                "success": "error" not in result,
                "state_diff": result.get("stateDiff"),
                "gas_used": result.get("gasUsed", 0),
                "logs": result.get("logs", []),
                "error": result.get("error"),
                "revert": result.get("revert"),
            }
        
        return {"success": False, "error": f"Simulation failed: {data}"}
