"""
Jito MEV Protection Client for Solana.

Sends bundles to Jito block engine for MEV protection on Solana transactions.

API Docs: https://jito-labs.gitbook.io/mev/
Base URL: https://mainnet.block-engine.jito.wtf/api/v1

No authentication required for basic endpoints.
"""

import logging
from typing import List, Optional, Dict, Any

from borg.defi.api_clients.base import BaseAPIClient

logger = logging.getLogger(__name__)


class JitoClient(BaseAPIClient):
    """Client for Jito block engine API (Solana MEV protection).
    
    Endpoints:
    - POST /bundles - Send a bundle of transactions
    - GET /bundles/{bundle_id} - Get bundle status
    - GET /tip_accounts - Get current tip accounts
    - GET /estimated_tip - Estimate tip for priority
    """

    BASE_URL = "https://mainnet.block-engine.jito.wtf/api/v1"

    # Tip amounts in lamports for different priority levels
    TIP_ESTIMATES = {
        "low": 1000,      # 0.000001 SOL
        "medium": 10000,  # 0.00001 SOL
        "high": 100000,  # 0.0001 SOL
    }

    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """Initialize Jito client.
        
        Args:
            base_url: Override base URL (defaults to Jito mainnet)
            timeout: Request timeout in seconds
        """
        super().__init__(base_url=base_url or self.BASE_URL)
        self._timeout = timeout

    async def send_bundle(self, transactions: List[str]) -> str:
        """Send a bundle of base64-encoded transactions to Jito.
        
        Args:
            transactions: List of base64-encoded signed transactions
            
        Returns:
            Bundle ID string, or empty string on failure
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendBundle",
            "params": [
                transactions  # Array of base64 transactions
            ]
        }
        
        url = f"{self._base_url}/bundles"
        data = await self.post(url, json=payload)
        
        if data and "result" in data:
            bundle_id = data["result"]
            if bundle_id:
                logger.info(f"Jito bundle sent: {bundle_id[:16]}...")
            else:
                logger.warning("Jito bundle send returned empty bundle_id")
            return bundle_id or ""
        
        logger.error(f"Jito bundle send failed: {data}")
        return ""

    async def get_bundle_status(self, bundle_id: str) -> Dict[str, Any]:
        """Check the status of a bundle.
        
        Args:
            bundle_id: The bundle ID returned from send_bundle
            
        Returns:
            Dict with bundle status information:
            {
                "bundle_id": str,
                "status": "pending" | "landed" | "failed",
                "slot": int (if landed),
                "error": str (if failed)
            }
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBundleStatuses",
            "params": [[bundle_id]]
        }
        
        url = f"{self._base_url}/bundles"
        data = await self.post(url, json=payload)
        
        if not data or "result" not in data:
            return {"bundle_id": bundle_id, "status": "unknown", "error": "No response"}
        
        results = data["result"]
        if not results or len(results) == 0:
            return {"bundle_id": bundle_id, "status": "unknown", "error": "Empty result"}
        
        bundle_result = results[0]
        return {
            "bundle_id": bundle_id,
            "status": bundle_result.get("status", {}).get("type", "unknown"),
            "slot": bundle_result.get("status", {}).get("slot"),
            "confirmation": bundle_result.get("confirmation_status"),
            "error": bundle_result.get("err"),
        }

    async def get_tip_accounts(self) -> List[str]:
        """Get current Jito tip accounts.
        
        These accounts accept tips for bundle prioritization.
        
        Returns:
            List of tip account public keys (base58)
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTipAccounts",
            "params": []
        }
        
        url = f"{self._base_url}/rpc"
        data = await self.post(url, json=payload)
        
        if data and "result" in data:
            accounts = data["result"]
            logger.debug(f"Got {len(accounts)} Jito tip accounts")
            return accounts
        
        logger.warning("Failed to get Jito tip accounts, using defaults")
        # Fallback to common Jito tip accounts
        return [
            "Cw8ysy5qK8eGCvU7xqgVPzqD5v3YjnqgFQS3mYJNUStR",
            "4uvnsG27sn9Gq7L9mCfoMcfFXXLCa6i8y8KfsR5U6wL8",
            "Hj3x4bw9Gfo17TMxLj7P9q1Y27nyM8vXgWBz9X8yKkHq",
        ]

    async def estimate_tip(self, priority: str = "medium") -> int:
        """Estimate tip amount in lamports for a given priority.
        
        Args:
            priority: 'low', 'medium', or 'high'
            
        Returns:
            Estimated tip in lamports
        """
        priority_lower = priority.lower()
        if priority_lower not in self.TIP_ESTIMATES:
            logger.warning(f"Unknown priority '{priority}', using 'medium'")
            priority_lower = "medium"
        
        # Return the configured estimate
        # In production, could query actual recent tips from the block engine
        return self.TIP_ESTIMATES[priority_lower]
