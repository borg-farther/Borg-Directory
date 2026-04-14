"""
Base client for DeFi API clients.

Provides common functionality: aiohttp session management, retry logic,
rate limit handling, error handling, and response caching.
"""

import asyncio
import logging
import re
import time
from collections import OrderedDict
from typing import Optional, Dict, Any, Tuple
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


class TTLCache:
    """
    In-memory cache with TTL and LRU eviction for API responses.

    Thread-safe for typical async usage. Cache key is (url, sorted_params).
    """

    DEFAULT_TTL = 300  # 5 minutes
    DEFAULT_MAX_SIZE = 1000

    def __init__(self, ttl: int = DEFAULT_TTL, max_size: int = DEFAULT_MAX_SIZE):
        """
        Initialize TTLCache.

        Args:
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
            max_size: Maximum number of entries (default: 1000)
        """
        self._ttl = ttl
        self._max_size = max_size
        self._cache: OrderedDict[Tuple[str, Any], Tuple[Any, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    @property
    def ttl(self) -> int:
        """Get the TTL in seconds."""
        return self._ttl

    @property
    def max_size(self) -> int:
        """Get the maximum cache size."""
        return self._max_size

    @property
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)

    def _make_key(self, url: str, params: Optional[Dict[str, Any]] = None) -> Tuple[str, Any]:
        """Create a cache key from URL and params. Converts values to hashable types."""
        if params:
            # Convert each value to a hashable representation
            def hashable_value(v):
                if isinstance(v, dict):
                    return tuple(sorted((k, hashable_value(v2)) for k, v2 in v.items()))
                elif isinstance(v, list):
                    return tuple(hashable_value(item) for item in v)
                elif isinstance(v, set):
                    return frozenset(hashable_value(item) for item in v)
                else:
                    return v
            sorted_params = tuple(sorted((k, hashable_value(v)) for k, v in params.items()))
        else:
            sorted_params = ()
        return (url, sorted_params)

    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cached entry has expired."""
        return time.time() - timestamp > self._ttl

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Get cached value if exists and not expired."""
        key = self._make_key(url, params)
        if key not in self._cache:
            return None

        value, timestamp = self._cache[key]
        if self._is_expired(timestamp):
            del self._cache[key]
            logger.debug(f"Cache expired for {url}")
            return None

        self._cache.move_to_end(key)
        logger.debug(f"Cache hit for {url}")
        return value

    def set(self, url: str, value: Any, params: Optional[Dict[str, Any]] = None) -> None:
        """Store value in cache with current timestamp."""
        key = self._make_key(url, params)
        if key in self._cache:
            del self._cache[key]

        while len(self._cache) >= self._max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug(f"Cache evicted: {evicted_key[0]}")

        self._cache[key] = (value, time.time())
        logger.debug(f"Cache set for {url}")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def clear_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if self._is_expired(timestamp)
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache entries")
        return len(expired_keys)

    def invalidate(self, url: str, params: Optional[Dict[str, Any]] = None) -> bool:
        """Invalidate a specific cache entry. Returns True if found and removed."""
        key = self._make_key(url, params)
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated for {url}")
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = len(self._cache)
        expired = sum(1 for _, ts in self._cache.values() if self._is_expired(ts))
        return {
            "size": total,
            "max_size": self._max_size,
            "ttl": self._ttl,
            "expired_entries": expired,
            "valid_entries": total - expired,
        }


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
        cache_ttl: int = TTLCache.DEFAULT_TTL,
        cache_max_size: int = TTLCache.DEFAULT_MAX_SIZE,
    ):
        """
        Initialize the base API client.

        Args:
            base_url: Override base URL for the API
            api_key: API key for authenticated APIs (stored securely, never logged)
            timeout: aiohttp timeout configuration
            cache_ttl: Cache time-to-live in seconds (default: 300 = 5 minutes, 0 to disable)
            cache_max_size: Maximum cache entries (default: 1000)
        """
        self._base_url = base_url
        self._api_key=api_key
        self._timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._session_created = False
        # Initialize cache (disabled if cache_ttl=0)
        self._cache_ttl = cache_ttl
        self._cache_max_size = cache_max_size
        self._cache: Optional[TTLCache] = None if cache_ttl == 0 else TTLCache(ttl=cache_ttl, max_size=cache_max_size)

    @property
    def cache(self) -> Optional[TTLCache]:
        """Get the cache instance."""
        return self._cache

    def clear_cache(self) -> None:
        """Clear the response cache."""
        if self._cache:
            self._cache.clear()

    def _make_cache_key(self, url: str, **kwargs) -> tuple:
        """Create a cache key from URL and kwargs."""
        # Sort kwargs for consistent key generation
        sorted_items = tuple(sorted(kwargs.items())) if kwargs else ()
        return (url, sorted_items)

    def _get_cached(self, url: str, **kwargs) -> Optional[Any]:
        """Get cached response if available and not expired."""
        if not self._cache:
            return None
        return self._cache.get(url, kwargs)

    def _set_cached(self, url: str, response: Any, **kwargs) -> None:
        """Store response in cache."""
        if self._cache and response is not None:
            self._cache.set(url, response, kwargs)

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
        - Caching: responses cached for configured TTL

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            retries: Number of retries remaining
            **kwargs: Additional arguments for aiohttp request

        Returns:
            Parsed JSON response or None on error
        """
        # Check cache first (only for GET requests)
        if method.upper() == "GET":
            cached = self._get_cached(url, **kwargs)
            if cached is not None:
                logger.debug(f"Cache hit for {url}")
                return cached

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
                            result = await response.json()
                            # Cache successful GET responses
                            if method.upper() == "GET":
                                self._set_cached(url, result, **kwargs)
                            return result
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
