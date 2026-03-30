"""
GoPlus Security API client.

Free API, no auth required for basic endpoints.
Docs: https://docs.gopluslabs.io/

Provides token security analysis, address screening, and approval checks.
"""

import logging
from typing import Optional, Dict, Any, List
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

# GoPlus API endpoints
GOPLUS_BASE = "https://api.gopluslabs.com/api/v1"

# Chain name to GoPlus chain ID mapping
CHAIN_ID_MAPPING = {
    "eth": "1",
    "ethereum": "1",
    "bsc": "56",
    "bnb": "56",
    "polygon": "137",
    "matic": "137",
    "arb": "42161",
    "arbitrum": "42161",
    "opt": "10",
    "optimism": "10",
    "base": "8453",
    "avax": "43114",
    "avalanche": "43114",
    "fantom": "250",
    "ftm": "250",
    "cronos": "25",
    "linea": "59144",
    "zksync": "324",
    "polygon_zkevm": "1101",
    "scroll": "534352",
    "mantle": "5000",
}

# Reverse mapping: chain ID to name
CHAIN_NAME_MAPPING = {v: k for k, v in CHAIN_ID_MAPPING.items()}


class GoPlusClient(BaseAPIClient):
    """Client for GoPlus Security API."""

    def __init__(self, **kwargs):
        """Initialize GoPlus client. No API key required for basic endpoints."""
        super().__init__(base_url=GOPLUS_BASE, **kwargs)

    def _get_chain_id(self, chain_id_or_name: str) -> str:
        """Convert chain name or ID to GoPlus chain ID string."""
        if chain_id_or_name in CHAIN_ID_MAPPING:
            return CHAIN_ID_MAPPING[chain_id_or_name]
        if chain_id_or_name in CHAIN_NAME_MAPPING:
            return chain_id_or_name
        # Assume it's already a numeric ID
        return chain_id_or_name

    async def token_security(
        self,
        chain_id: str,
        contract_address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get token security analysis.

        Checks honeypot status, mint authority, proxy contract,
        trading tax, holder analysis, and more.

        GET https://api.gopluslabs.com/api/v1/token_security/{chain_id}/{contract_address}

        Args:
            chain_id: Chain name (e.g., 'eth', 'bsc', 'polygon') or GoPlus chain ID
            contract_address: Token contract address

        Returns:
            Token security dict or None on error

        Key fields in response:
            - is_honeypot: bool
            - is_proxy: bool
            - is_mintable: bool
            - owner_address: str
            - token_name: str
            - token_symbol: str
            - total_supply: str
            - holder_count: str
            - transfer_tax: str
            - sell_tax: str
            - buy_tax: str
            - honeypot_with_same_token: bool
            - trading_honeypot: str
            - trust_list: str
        """
        chain = self._get_chain_id(chain_id)
        url = f"{self._base_url}/token_security/{chain}/{contract_address}"

        try:
            data = await self.get(url)
            if data and "result" in data:
                return data["result"]
            return data
        except Exception as e:
            logger.error(f"Failed to get token security for {contract_address}: {e}")
            return None

    async def address_security(
        self,
        chain_id: str,
        address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if an address is flagged as malicious.

        GET https://api.gopluslabs.com/api/v1/address_security/{chain_id}/{address}

        Args:
            chain_id: Chain name or GoPlus chain ID
            address: Wallet or contract address

        Returns:
            Address security dict or None on error

        Key fields:
            - is_malicious: bool
            - malicious_description: str
            - tags: list of threat tags
        """
        chain = self._get_chain_id(chain_id)
        url = f"{self._base_url}/address_security/{chain}/{address}"

        try:
            data = await self.get(url)
            if data and "result" in data:
                return data["result"]
            return data
        except Exception as e:
            logger.error(f"Failed to check address security for {address}: {e}")
            return None

    async def approval_security(
        self,
        chain_id: str,
        address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Check token approval risk for an address.

        Shows which tokens have been approved and their risk levels.

        GET https://api.gopluslabs.com/api/v1/token_approval_security/{chain_id}/{address}

        Args:
            chain_id: Chain name or GoPlus chain ID
            address: Wallet address to check approvals for

        Returns:
            Approval security dict or None on error

        Key fields:
            - token_approvals: list of approved tokens with risk scores
        """
        chain = self._get_chain_id(chain_id)
        url = f"{self._base_url}/token_approval_security/{chain}/{address}"

        try:
            data = await self.get(url)
            if data and "result" in data:
                return data["result"]
            return data
        except Exception as e:
            logger.error(f"Failed to check approval security for {address}: {e}")
            return None

    async def nft_security(
        self,
        chain_id: str,
        contract_address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get NFT collection security analysis.

        GET https://api.gopluslabs.com/api/v1/nft_security/{chain_id}/{contract_address}

        Args:
            chain_id: Chain name or GoPlus chain ID
            contract_address: NFT contract address

        Returns:
            NFT security dict or None on error

        Key fields:
            - is_nft: bool
            - nft_type: str (erc721, erc1155)
            - owner_count: str
            - total_supply: str
            - is_mintable: bool
            - creator_address: str
        """
        chain = self._get_chain_id(chain_id)
        url = f"{self._base_url}/nft_security/{chain}/{contract_address}"

        try:
            data = await self.get(url)
            if data and "result" in data:
                return data["result"]
            return data
        except Exception as e:
            logger.error(f"Failed to get NFT security for {contract_address}: {e}")
            return None

    async def multiple_token_security(
        self,
        chain_id: str,
        contract_addresses: List[str],
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Get token security for multiple tokens at once.

        POST https://api.gopluslabs.com/api/v1/token_security/{chain_id}

        Args:
            chain_id: Chain name or GoPlus chain ID
            contract_addresses: List of token contract addresses

        Returns:
            Dict mapping address to token security data, or None on error
        """
        chain = self._get_chain_id(chain_id)
        url = f"{self._base_url}/token_security/{chain}"

        try:
            data = await self.post(
                url,
                json={"address_list": contract_addresses},
            )
            if data and "result" in data:
                return data["result"]
            return data
        except Exception as e:
            logger.error(f"Failed to get multiple token security: {e}")
            return None

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def is_honeypot(self, result: Dict[str, Any]) -> bool:
        """
        Check if token is a honeypot from GoPlus result.

        Args:
            result: Token security result dict

        Returns:
            True if token appears to be a honeypot
        """
        if not result:
            return False

        # Primary honeypot indicators
        is_hp = result.get("is_honeypot", "")
        if str(is_hp).lower() == "true":
            return True

        # Check trading honeypot status
        trading_hp = result.get("trading_honeypot", "")
        if str(trading_hp).lower() == "honeypot":
            return True

        # Check if can't sell (another honeypot indicator)
        can_sell = result.get("can_sell", "true")
        if str(can_sell).lower() == "false":
            return True

        return False

    def risk_score(self, result: Dict[str, Any]) -> float:
        """
        Calculate risk score (0-100) from GoPlus result.

        Higher score = more risky

        Args:
            result: Token security result dict

        Returns:
            Risk score 0-100
        """
        if not result:
            return 100.0  # Unknown = high risk

        score = 0.0

        # Honeypot = max risk
        if self.is_honeypot(result):
            return 100.0

        # Proxy contract
        if result.get("is_proxy", "").lower() == "true":
            score += 25

        # Mintable by owner
        if result.get("is_mintable", "").lower() == "true":
            score += 15

        # Transfer/sell tax
        try:
            sell_tax = float(result.get("sell_tax", 0) or 0)
            score += min(sell_tax * 2, 30)  # Up to 30 points for high sell tax
        except (ValueError, TypeError):
            pass

        try:
            transfer_tax = float(result.get("transfer_tax", 0) or 0)
            score += min(transfer_tax * 2, 20)  # Up to 20 points for transfer tax
        except (ValueError, TypeError):
            pass

        # Owner percentage (high ownership = higher risk)
        try:
            owner_percent = float(result.get("owner_address_balance_percent", 0) or 0)
            if owner_percent > 50:
                score += 20
            elif owner_percent > 30:
                score += 10
        except (ValueError, TypeError):
            pass

        # Locked LP percentage (low = higher risk)
        try:
            lp_lock_percent = float(result.get("lp_total_percent", 100) or 100)
            if lp_lock_percent < 10:
                score += 25
            elif lp_lock_percent < 25:
                score += 15
            elif lp_lock_percent < 50:
                score += 5
        except (ValueError, TypeError):
            pass

        return min(score, 100.0)

    def get_warnings(self, result: Dict[str, Any]) -> List[str]:
        """
        Get list of warning messages from GoPlus result.

        Args:
            result: Token security result dict

        Returns:
            List of warning strings
        """
        warnings = []

        if not result:
            return ["Unable to fetch token security data"]

        if self.is_honeypot(result):
            warnings.append("Token is flagged as a honeypot - cannot sell")

        if result.get("is_proxy", "").lower() == "true":
            warnings.append("Token uses proxy contract - increased risk")

        if result.get("is_mintable", "").lower() == "true":
            warnings.append("Token is mintable - owner can create unlimited supply")

        try:
            sell_tax = float(result.get("sell_tax", 0) or 0)
            if sell_tax > 10:
                warnings.append(f"High sell tax: {sell_tax}%")
        except (ValueError, TypeError):
            pass

        try:
            transfer_tax = float(result.get("transfer_tax", 0) or 0)
            if transfer_tax > 10:
                warnings.append(f"High transfer tax: {transfer_tax}%")
        except (ValueError, TypeError):
            pass

        try:
            owner_percent = float(result.get("owner_address_balance_percent", 0) or 0)
            if owner_percent > 50:
                warnings.append(f"High owner token holdings: {owner_percent}%")
        except (ValueError, TypeError):
            pass

        try:
            lp_lock_percent = float(result.get("lp_total_percent", 100) or 100)
            if lp_lock_percent < 10:
                warnings.append(f"Low LP lock: only {lp_lock_percent}% locked")
        except (ValueError, TypeError):
            pass

        return warnings
