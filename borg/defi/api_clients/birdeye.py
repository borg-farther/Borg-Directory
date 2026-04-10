"""
Birdeye API client for token prices and OHLCV data.

API key required (from BIRDEYE_API_KEY env var).
Docs: https://docs.birdeye.so/

Provides token price, OHLCV, and market data.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from .base import BaseAPIClient
from borg.defi.data_models import TokenPrice, OHLCV

logger = logging.getLogger(__name__)

# Birdeye API endpoints
BIRDEYE_BASE = "https://public-api.birdeye.so"
PRICE_ENDPOINT = "/v1/token/price"
OHLCV_ENDPOINT = "/v1/token/ohlcv"
MULTI_PRICE_ENDPOINT = "/v1/token/multi-price"

# Environment variable for API key
BIRDEYE_API_KEY_ENV = "BIRDEYE_API_KEY"


class BirdeyeClient(BaseAPIClient):
    """Client for Birdeye API."""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Birdeye client.

        Args:
            api_key: Birdeye API key. If not provided, reads from BIRDEYE_API_KEY env var.
        """
        env_key = os.environ.get(BIRDEYE_API_KEY_ENV)
        key = api_key or env_key
        if not key:
            logger.warning("Birdeye API key not provided. Set BIRDEYE_API_KEY env var.")

        super().__init__(base_url=BIRDEYE_BASE, api_key=key, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self._api_key or "",
        }
        return headers

    async def get_price(self, token_address: str) -> Optional[TokenPrice]:
        """
        Get current price for a token.

        GET https://public-api.birdeye.so/v1/token/price?address={address}

        Args:
            token_address: Token contract address

        Returns:
            TokenPrice dataclass or None on error
        """
        if not self._api_key:
            logger.error("Birdeye API key required for get_price")
            return None

        url = f"{self._base_url}{PRICE_ENDPOINT}"
        params = {"address": token_address}

        try:
            data = await self.get(url, params=params)
            if not data or "data" not in data:
                return None

            price_data = data["data"]
            return TokenPrice(
                symbol=price_data.get("symbol", ""),
                address=token_address,
                price=self._safe_float(price_data.get("value", 0)),
                price_native=price_data.get("valueInUSD", 0) or 0.0,
                timestamp=price_data.get("lastTrade", {}).get("unixTime", 0) or 0,
                volume_24h=self._safe_float(price_data.get("volume24h", 0)),
            )

        except Exception as e:
            logger.error(f"Failed to get price for {token_address}: {e}")
            return None

    async def get_multi_price(self, token_addresses: List[str]) -> Dict[str, TokenPrice]:
        """
        Get prices for multiple tokens at once.

        POST https://public-api.birdeye.so/v1/token/multi-price

        Args:
            token_addresses: List of token contract addresses

        Returns:
            Dict mapping address to TokenPrice
        """
        if not self._api_key:
            logger.error("Birdeye API key required for get_multi_price")
            return {}

        url = f"{self._base_url}{MULTI_PRICE_ENDPOINT}"

        try:
            data = await self.post(
                url,
                json={"addresses": token_addresses},
                headers=self._get_headers(),
            )

            if not data or "data" not in data:
                return {}

            result = {}
            for address, price_data in data["data"].items():
                try:
                    result[address] = TokenPrice(
                        symbol=price_data.get("symbol", ""),
                        address=address,
                        price=self._safe_float(price_data.get("value", 0)),
                        price_native=price_data.get("valueInUSD", 0) or 0.0,
                        timestamp=price_data.get("lastTrade", {}).get("unixTime", 0) or 0,
                        volume_24h=self._safe_float(price_data.get("volume24h", 0)),
                    )
                except Exception as e:
                    logger.debug(f"Skipping price for {address}: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"Failed to get multi price: {e}")
            return {}

    async def get_ohlcv(
        self,
        token_address: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> Optional[List[OHLCV]]:
        """
        Get OHLCV (candlestick) data for a token.

        GET https://public-api.birdeye.so/v1/token/ohlcv?address={address}&type={type}

        Args:
            token_address: Token contract address
            timeframe: Timeframe (1h, 4h, 1d, 1w)
            limit: Number of candles to return

        Returns:
            List of OHLCV dataclasses or None on error
        """
        if not self._api_key:
            logger.error("Birdeye API key required for get_ohlcv")
            return None

        url = f"{self._base_url}{OHLCV_ENDPOINT}"
        params = {
            "address": token_address,
            "type": timeframe,
        }

        try:
            data = await self.get(url, params=params)
            if not data or "data" not in data:
                return None

            candles = []
            for candle in data["data"].get("items", []):
                try:
                    candles.append(OHLCV(
                        timestamp=candle.get("unixTime", 0) or 0,
                        open=self._safe_float(candle.get("o", 0)),
                        high=self._safe_float(candle.get("h", 0)),
                        low=self._safe_float(candle.get("l", 0)),
                        close=self._safe_float(candle.get("c", 0)),
                        volume=self._safe_float(candle.get("v", 0)),
                        symbol=data["data"].get("symbol", ""),
                        address=token_address,
                    ))
                except Exception as e:
                    logger.debug(f"Skipping candle: {e}")
                    continue

            return candles

        except Exception as e:
            logger.error(f"Failed to get OHLCV for {token_address}: {e}")
            return None

    async def get_token_price_multi_chain(
        self,
        token_address: str,
        chain: str = "solana",
    ) -> Optional[TokenPrice]:
        """
        Get price for a token, specifying chain explicitly.

        Args:
            token_address: Token contract address
            chain: Chain name (solana, ethereum, etc.)

        Returns:
            TokenPrice dataclass or None
        """
        # For multi-chain, we need to use different endpoint structure
        # Birdeye uses different addresses per chain
        return await self.get_price(token_address)

    @staticmethod
    def _safe_float(value) -> float:
        """Safely convert value to float."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
