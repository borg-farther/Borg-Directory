"""
Arkham Intelligence API client for wallet entity intelligence.

API key required (from ARKHAM_API_KEY env var).
Docs: https://api.arkhamintelligence.com/

Provides entity labels, portfolio data, transfer history, and smart money tracking.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

# Arkham API endpoints
ARKHAM_BASE = "https://api.arkhamintelligence.com"

# Environment variable for API key
ARKHAM_API_KEY_ENV = "ARKHAM_API_KEY"

# Known smart money entity labels to track
KNOWN_SMART_MONEY_LABELS = [
    "Jump Trading",
    "a16z",
    "Paradigm",
    "Three Arrows Capital",
    "Alameda Research",
    "Binance",
    "Coinbase",
    "Kraken",
    "Wintermute",
    "Amber Group",
    "Dragonfly Capital",
    "Sequoia",
    "Multicoin Capital",
    "Framework Ventures",
    "DeFiance Capital",
]


class ArkhamClient(BaseAPIClient):
    """Client for Arkham Intelligence API."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Arkham client.

        Args:
            api_key: Arkham API key. If not provided, reads from ARKHAM_API_KEY env var.
        """
        env_key = os.environ.get(ARKHAM_API_KEY_ENV)
        key = api_key or env_key
        if not key:
            logger.warning("Arkham API key not provided. Set ARKHAM_API_KEY env var.")

        super().__init__(base_url=ARKHAM_BASE, api_key=key, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    async def search_entity(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for an entity by name or address.

        GET https://api.arkhamintelligence.com/search?query={query}

        Args:
            query: Entity name or address to search for

        Returns:
            List of entity dicts with id, name, labels, or None on error
        """
        if not self._api_key:
            logger.error("Arkham API key required for search_entity")
            return None

        url = f"{self._base_url}/search"
        params = {"query": query}

        try:
            data = await self.get(url, params=params, headers=self._get_headers())
            if not data:
                return None

            # Arkham returns results in 'results' or 'entities' field
            if isinstance(data, dict):
                return data.get("results") or data.get("entities") or []
            elif isinstance(data, list):
                return data
            return None

        except Exception as e:
            logger.error(f"Failed to search entity '{query}': {e}")
            return None

    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entity details including name, holdings, and labels.

        GET https://api.arkhamintelligence.com/entities/{entity_id}

        Args:
            entity_id: Arkham entity ID

        Returns:
            Entity dict with name, labels, addresses, holdings, or None on error
        """
        if not self._api_key:
            logger.error("Arkham API key required for get_entity")
            return None

        url = f"{self._base_url}/entities/{entity_id}"

        try:
            data = await self.get(url, headers=self._get_headers())
            if not data:
                return None
            return data

        except Exception as e:
            logger.error(f"Failed to get entity '{entity_id}': {e}")
            return None

    async def get_address_intelligence(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Get intelligence for an address including entity link, labels, and tags.

        GET https://api.arkhamintelligence.com/intelligence/address/{address}

        Args:
            address: Wallet address (0x... for EVM, base58 for Solana)

        Returns:
            Dict with entity link, labels, tags, or None on error
        """
        if not self._api_key:
            logger.error("Arkham API key required for get_address_intelligence")
            return None

        url = f"{self._base_url}/intelligence/address/{address}"

        try:
            data = await self.get(url, headers=self._get_headers())
            if not data:
                return None
            return data

        except Exception as e:
            logger.error(f"Failed to get address intelligence for '{address}': {e}")
            return None

    async def get_portfolio(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get entity portfolio with token holdings.

        GET https://api.arkhamintelligence.com/portfolio/{entity_id}

        Args:
            entity_id: Arkham entity ID

        Returns:
            Dict with portfolio holdings (tokens, amounts, values), or None on error
        """
        if not self._api_key:
            logger.error("Arkham API key required for get_portfolio")
            return None

        url = f"{self._base_url}/portfolio/{entity_id}"

        try:
            data = await self.get(url, headers=self._get_headers())
            if not data:
                return None
            return data

        except Exception as e:
            logger.error(f"Failed to get portfolio for '{entity_id}': {e}")
            return None

    async def get_transfers(
        self, address: str, chain: Optional[str] = None, limit: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get transfer history for an address.

        GET https://api.arkhamintelligence.com/transfers?address={address}&chain={chain}&limit={limit}

        Args:
            address: Wallet address
            chain: Optional chain filter (ethereum, solana, base, arbitrum, etc.)
            limit: Maximum number of transfers to return (default 50)

        Returns:
            List of transfer dicts with from, to, amount, token, timestamp, or None on error
        """
        if not self._api_key:
            logger.error("Arkham API key required for get_transfers")
            return None

        url = f"{self._base_url}/transfers"
        params = {"address": address, "limit": limit}
        if chain:
            params["chain"] = chain

        try:
            data = await self.get(url, params=params, headers=self._get_headers())
            if not data:
                return None

            # Arkham returns transfers in 'transfers' or directly as list
            if isinstance(data, dict):
                return data.get("transfers") or data.get("result") or []
            elif isinstance(data, list):
                return data
            return None

        except Exception as e:
            logger.error(f"Failed to get transfers for '{address}': {e}")
            return None

    async def get_token_holders(
        self, contract: str, chain: str = "ethereum"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get top holders of a token contract.

        GET https://api.arkhamintelligence.com/holders/{contract}?chain={chain}

        Args:
            contract: Token contract address
            chain: Chain name (ethereum, solana, base, arbitrum, etc.)

        Returns:
            List of holder dicts with address, amount, percentage, or None on error
        """
        if not self._api_key:
            logger.error("Arkham API key required for get_token_holders")
            return None

        url = f"{self._base_url}/holders/{contract}"
        params = {"chain": chain}

        try:
            data = await self.get(url, params=params, headers=self._get_headers())
            if not data:
                return None

            # Arkham returns holders in 'holders' or 'result' field
            if isinstance(data, dict):
                return data.get("holders") or data.get("result") or []
            elif isinstance(data, list):
                return data
            return None

        except Exception as e:
            logger.error(f"Failed to get token holders for '{contract}': {e}")
            return None

    async def get_smart_money_wallets(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get known smart money wallets from Arkham.

        Queries Arkham for entities matching known smart money labels
        like 'Jump Trading', 'a16z', 'Paradigm', etc.

        Returns:
            List of smart money entity dicts with id, name, labels, addresses
        """
        if not self._api_key:
            logger.error("Arkham API key required for get_smart_money_wallets")
            return None

        smart_money_entities = []

        for label in KNOWN_SMART_MONEY_LABELS:
            try:
                results = await self.search_entity(label)
                if results and isinstance(results, list):
                    for entity in results:
                        entity_name = entity.get("name", "").lower()
                        entity_labels = entity.get("labels", [])
                        # Match by name or label
                        if (
                            label.lower() in entity_name
                            or label.lower() in [l.lower() for l in entity_labels]
                        ):
                            if entity not in smart_money_entities:
                                smart_money_entities.append(entity)
            except Exception as e:
                logger.debug(f"Failed to search for smart money entity '{label}': {e}")
                continue

        if smart_money_entities:
            logger.info(f"Found {len(smart_money_entities)} smart money entities")
        return smart_money_entities if smart_money_entities else None

    async def enrich_alert_with_entity(
        self, address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich a whale alert address with Arkham entity intelligence.

        Args:
            address: Wallet address from the alert

        Returns:
            Dict with entity_name, labels, tags, is_smart_money, or None
        """
        intelligence = await self.get_address_intelligence(address)
        if not intelligence:
            return None

        # Extract relevant fields for enrichment
        entity_id = intelligence.get("entityId") or intelligence.get("entity_id")
        entity_name = intelligence.get("entityName") or intelligence.get("name")
        labels = intelligence.get("labels", []) or intelligence.get("tags", [])
        is_smart_money = False

        # Check if this is a known smart money entity
        if entity_name:
            for known_label in KNOWN_SMART_MONEY_LABELS:
                if known_label.lower() in entity_name.lower():
                    is_smart_money = True
                    break

        if labels:
            for label in labels:
                if label in KNOWN_SMART_MONEY_LABELS:
                    is_smart_money = True
                    break

        return {
            "entity_id": entity_id,
            "entity_name": entity_name,
            "labels": labels if isinstance(labels, list) else [],
            "is_smart_money": is_smart_money,
            "raw_intelligence": intelligence,
        }

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
