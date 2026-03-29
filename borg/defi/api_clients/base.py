"""
Base client for DeFi API clients.

Provides common functionality: aiohttp session management, retry logic,
rate limit handling, and error handling.
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any
import aiohttp
from aiohttp import ClientTimeout, ClientError

logger = logging.getLogger(__name__)

# Patterns to detect API keys in logs (for security auditing)
API_KEY_PATTERNS = [
    r"(?i)(api[_-]?key|apikey|api-key)[\s:]*=[\s]*['\"]?[\w\-]{16,}['\"]?",
    r"(?i)(secret|token|auth)[\s:]*=[\s]*['\"]?[\w\-]{16,}['\"]?",
    r"BIRDEYE[\-_]API[\s:]*KEY",
    r"HELIUS[\-_]API[\s:]*KEY",
    r"0x[a-fA-F0-9]{64}",  # Private keys
]


class BaseAPIClient:
    """Base class for all DeFi API clients."""

    BASE_TIMEOUT = ClientTimeout(total=30, connect=10)
    MAX_RETRIES = 3
    RATE_LIMIT_RETRY_AFTER = 60

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: ClientTimeout = BASE_TIMEOUT,
    ):
        """
        Initialize the base API client.

        Args:
            base_url: Override base URL for the API
            api_key: API key for authenticated APIs (stored securely, never logged)
            timeout: aiohttp timeout configuration
        """
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_created = False

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure aiohttp session exists and is reusable."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            self._session_created = True
        return self._session

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            self._session_created = False

    def _sanitize_log(self, message: str) -> str:
        """Remove API keys/secrets from log messages for security."""
        sanitized = message
        for pattern in API_KEY_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)
        return sanitized

    def _log_request(self, method: str, url: str, **kwargs):
        """Log request details safely (no API keys)."""
        safe_url = self._sanitize_log(url)
        safe_kwargs = {k: self._sanitize_log(str(v)) for k, v in kwargs.items()}
        logger.debug(f"API Request: {method} {safe_url} | params: {safe_kwargs}")

    def _log_response(self, status: int, url: str, data_size: int = 0):
        """Log response details safely."""
        safe_url = self._sanitize_log(url)
        logger.debug(f"API Response: {status} | {safe_url} | size: {data_size}")

    def _log_error(self, error: Exception, context: str):
        """Log error details safely."""
        error_msg = self._sanitize_log(str(error))
        logger.error(f"{context}: {error_msg}")

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        retries: int = MAX_RETRIES,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP request with retry logic.

        Handles:
        - Timeouts: retries 3x
        - Rate limits (429): respects Retry-After header
        - Malformed JSON: returns None, logs error
        - Network errors: retries 3x

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            retries: Number of retries remaining
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Parsed JSON response or None on error
        """
        self._log_request(method, url, **kwargs)

        last_error = None

        for attempt in range(retries):
            try:
                session = await self._ensure_session()

                async with session.request(method, url, **kwargs) as response:
                    self._log_response(response.status, url, response.content_length)

                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", self.RATE_LIMIT_RETRY_AFTER))
                        logger.warning(f"Rate limited. Waiting {retry_after}s before retry.")
                        await asyncio.sleep(retry_after)
                        continue

                    # Handle success
                    if response.status == 200:
                        try:
                            return await response.json()
                        except Exception as e:
                            self._log_error(e, "JSON parse error")
                            return None

                    # Handle client errors
                    if 400 <= response.status < 500:
                        error_text = await response.text()
                        self._log_error(Exception(error_text), f"Client error {response.status}")
                        return None

                    # Handle server errors - retry
                    if response.status >= 500:
                        last_error = Exception(f"Server error: {response.status}")
                        if attempt < retries - 1:
                            await asyncio.sleep(1 * (attempt + 1))
                            continue
                        return None

            except asyncio.TimeoutError as e:
                last_error = e
                self._log_error(e, f"Timeout on attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                return None

            except ClientError as e:
                last_error = e
                self._log_error(e, f"Connection error on attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                return None

            except Exception as e:
                last_error = e
                self._log_error(e, f"Unexpected error on attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                return None

        # All retries exhausted
        if last_error:
            self._log_error(last_error, f"Failed after {retries} retries")
        return None

    async def get(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Convenience method for GET requests."""
        return await self._request_with_retry("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Convenience method for POST requests."""
        return await self._request_with_retry("POST", url, **kwargs)
