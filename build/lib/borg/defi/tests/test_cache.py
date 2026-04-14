"""
Tests for TTLCache and caching integration in BaseAPIClient.

Run with:
    pytest borg/defi/tests/test_cache.py -v --tb=short
"""

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.api_clients.base import BaseAPIClient, TTLCache


# ---------------------------------------------------------------------
# TTLCache Unit Tests
# ---------------------------------------------------------------------


class TestTTLCacheInit:
    """Tests for TTLCache initialization."""

    def test_init_default_values(self):
        """Test default TTL and max_size."""
        cache = TTLCache()
        assert cache.ttl == 300
        assert cache.max_size == 1000
        assert cache.size == 0

    def test_init_custom_values(self):
        """Test custom TTL and max_size."""
        cache = TTLCache(ttl=60, max_size=500)
        assert cache.ttl == 60
        assert cache.max_size == 500
        assert cache.size == 0

    def test_init_zero_ttl_creates_cache(self):
        """Test that zero TTL still creates a cache object (just not used)."""
        cache = TTLCache(ttl=0, max_size=100)
        assert cache.ttl == 0
        assert cache.max_size == 100


class TestTTLCacheGetSet:
    """Tests for TTLCache get/set operations."""

    def test_set_and_get(self):
        """Test basic set and get."""
        cache = TTLCache(ttl=300)
        cache.set("https://api.test.com/endpoint", {"data": "value"})
        result = cache.get("https://api.test.com/endpoint")
        assert result == {"data": "value"}

    def test_get_missing_key(self):
        """Test get with missing key returns None."""
        cache = TTLCache(ttl=300)
        result = cache.get("https://api.test.com/nonexistent")
        assert result is None

    def test_get_with_params(self):
        """Test get with query params."""
        cache = TTLCache(ttl=300)
        url = "https://api.test.com/endpoint"
        params = {"chain": "solana", "token": "SOL"}
        cache.set(url, {"price": 100}, params)
        result = cache.get(url, params)
        assert result == {"price": 100}

    def test_get_with_different_params(self):
        """Test that different params give different cache entries."""
        cache = TTLCache(ttl=300)
        url = "https://api.test.com/endpoint"
        cache.set(url, {"price": 100}, {"chain": "solana"})
        cache.set(url, {"price": 200}, {"chain": "ethereum"})
        assert cache.get(url, {"chain": "solana"}) == {"price": 100}
        assert cache.get(url, {"chain": "ethereum"}) == {"price": 200}

    def test_params_order_independent(self):
        """Test that param order doesn't matter for cache key."""
        cache = TTLCache(ttl=300)
        url = "https://api.test.com/endpoint"
        cache.set(url, {"price": 100}, {"chain": "solana", "token": "SOL"})
        result = cache.get(url, {"token": "SOL", "chain": "solana"})
        assert result == {"price": 100}

    def test_set_updates_existing(self):
        """Test that set updates existing entry."""
        cache = TTLCache(ttl=300)
        url = "https://api.test.com/endpoint"
        cache.set(url, {"v": 1})
        cache.set(url, {"v": 2})
        assert cache.size == 1
        assert cache.get(url) == {"v": 2}


class TestTTLCacheExpiration:
    """Tests for TTLCache TTL expiration."""

    def test_expired_entry_returns_none(self):
        """Test that expired entries return None."""
        cache = TTLCache(ttl=1)  # 1 second TTL
        cache.set("https://api.test.com/endpoint", {"data": "value"})
        time.sleep(1.1)
        result = cache.get("https://api.test.com/endpoint")
        assert result is None

    def test_unexpired_entry_returns_value(self):
        """Test that unexpired entries return value."""
        cache = TTLCache(ttl=300)
        cache.set("https://api.test.com/endpoint", {"data": "value"})
        time.sleep(0.1)
        result = cache.get("https://api.test.com/endpoint")
        assert result == {"data": "value"}

    def test_clear_expired(self):
        """Test clear_expired removes only expired entries."""
        cache = TTLCache(ttl=1)
        cache.set("https://api.test.com/endpoint1", {"data": "1"})
        time.sleep(1.1)
        cache.set("https://api.test.com/endpoint2", {"data": "2"})  # not expired

        removed = cache.clear_expired()
        assert removed == 1
        assert cache.get("https://api.test.com/endpoint1") is None
        assert cache.get("https://api.test.com/endpoint2") == {"data": "2"}


class TestTTLCacheLRU:
    """Tests for TTLCache LRU eviction."""

    def test_max_size_eviction(self):
        """Test that entries are evicted when max_size exceeded."""
        cache = TTLCache(ttl=300, max_size=3)
        cache.set("https://api.test.com/1", {"v": 1})
        cache.set("https://api.test.com/2", {"v": 2})
        cache.set("https://api.test.com/3", {"v": 3})
        cache.set("https://api.test.com/4", {"v": 4})  # should evict #1

        assert cache.size == 3
        assert cache.get("https://api.test.com/1") is None
        assert cache.get("https://api.test.com/4") == {"v": 4}

    def test_lru_ordering(self):
        """Test that accessed entries move to end (most recently used)."""
        cache = TTLCache(ttl=300, max_size=3)
        cache.set("https://api.test.com/1", {"v": 1})
        cache.set("https://api.test.com/2", {"v": 2})
        cache.set("https://api.test.com/3", {"v": 3})

        # Access entry 1 (makes it most recently used)
        cache.get("https://api.test.com/1")

        # Add new entry - should evict entry 2 (least recently used)
        cache.set("https://api.test.com/4", {"v": 4})

        assert cache.get("https://api.test.com/1") == {"v": 1}  # still exists
        assert cache.get("https://api.test.com/2") is None  # evicted
        assert cache.get("https://api.test.com/4") == {"v": 4}


class TestTTLCacheInvalidate:
    """Tests for TTLCache invalidation."""

    def test_invalidate_existing(self):
        """Test invalidating an existing entry."""
        cache = TTLCache(ttl=300)
        cache.set("https://api.test.com/endpoint", {"data": "value"})
        result = cache.invalidate("https://api.test.com/endpoint")
        assert result is True
        assert cache.get("https://api.test.com/endpoint") is None

    def test_invalidate_nonexisting(self):
        """Test invalidating a non-existing entry returns False."""
        cache = TTLCache(ttl=300)
        result = cache.invalidate("https://api.test.com/nonexistent")
        assert result is False

    def test_clear(self):
        """Test clearing all entries."""
        cache = TTLCache(ttl=300)
        cache.set("https://api.test.com/1", {"v": 1})
        cache.set("https://api.test.com/2", {"v": 2})
        cache.clear()
        assert cache.size == 0
        assert cache.get("https://api.test.com/1") is None


class TestTTLCacheStats:
    """Tests for TTLCache statistics."""

    def test_get_stats(self):
        """Test cache statistics."""
        cache = TTLCache(ttl=300, max_size=100)
        cache.set("https://api.test.com/1", {"v": 1})
        cache.set("https://api.test.com/2", {"v": 2})

        stats = cache.get_stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert stats["ttl"] == 300
        assert stats["expired_entries"] == 0
        assert stats["valid_entries"] == 2

    def test_get_stats_with_expired(self):
        """Test stats with expired entries."""
        cache = TTLCache(ttl=1)
        cache.set("https://api.test.com/1", {"v": 1})
        time.sleep(1.1)

        stats = cache.get_stats()
        assert stats["expired_entries"] == 1
        assert stats["valid_entries"] == 0


# ---------------------------------------------------------------------
# BaseAPIClient Caching Integration Tests
# ---------------------------------------------------------------------


class TestBaseAPIClientCacheInit:
    """Tests for BaseAPIClient cache initialization."""

    def test_cache_enabled_by_default(self):
        """Test that cache is enabled by default (5 min TTL)."""
        client = BaseAPIClient()
        assert client._cache is not None
        assert client._cache.ttl == 300

    def test_cache_disabled_with_zero_ttl(self):
        """Test that cache is disabled when ttl=0."""
        client = BaseAPIClient(cache_ttl=0)
        assert client._cache is None

    def test_cache_custom_ttl(self):
        """Test custom cache TTL."""
        client = BaseAPIClient(cache_ttl=60)
        assert client._cache.ttl == 60

    def test_cache_custom_max_size(self):
        """Test custom cache max_size."""
        client = BaseAPIClient(cache_max_size=500)
        assert client._cache.max_size == 500

    def test_cache_property(self):
        """Test cache property returns cache instance."""
        client = BaseAPIClient()
        assert client.cache is client._cache

    def test_cache_property_none_when_disabled(self):
        """Test cache property returns None when disabled."""
        client = BaseAPIClient(cache_ttl=0)
        assert client.cache is None


class TestBaseAPIClientCacheMethods:
    """Tests for BaseAPIClient cache helper methods."""

    def test_clear_cache(self):
        """Test clear_cache method."""
        client = BaseAPIClient()
        client._cache.set("https://api.test.com", {"v": 1})
        assert client._cache.size == 1
        client.clear_cache()
        assert client._cache.size == 0

    def test_clear_cache_when_disabled(self):
        """Test clear_cache when cache is disabled (no-op)."""
        client = BaseAPIClient(cache_ttl=0)
        client.clear_cache()  # should not raise

    def test_make_cache_key(self):
        """Test _make_cache_key creates consistent keys."""
        client = BaseAPIClient()
        key1 = client._make_cache_key("https://api.test.com", chain="sol", token="SOL")
        key2 = client._make_cache_key("https://api.test.com", token="SOL", chain="sol")
        assert key1 == key2

    def test_get_cached_returns_none_when_disabled(self):
        """Test _get_cached returns None when cache disabled."""
        client = BaseAPIClient(cache_ttl=0)
        result = client._get_cached("https://api.test.com")
        assert result is None

    def test_set_cached_ignores_when_disabled(self):
        """Test _set_cached does nothing when cache disabled."""
        client = BaseAPIClient(cache_ttl=0)
        client._set_cached("https://api.test.com", {"v": 1})  # should not raise


class TestBaseAPIClientCachingInRequest:
    """Tests for caching in actual API requests."""

    @pytest.mark.asyncio
    async def test_get_request_caches_response(self):
        """Test that GET requests cache successful responses."""
        client = BaseAPIClient(cache_ttl=300)

        # Use a real async mock for the HTTP layer
        async def mock_http_request(*args, **kwargs):
            return {"data": "response_value"}

        # Patch at the aiohttp session level
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.content_length = 50
            mock_response.json = AsyncMock(return_value={"data": "response_value"})
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            # First GET request
            result1 = await client.get("https://api.test.com/endpoint")

            # Verify HTTP was called once
            assert mock_session.request.call_count == 1

            # Second GET request - should hit cache
            result2 = await client.get("https://api.test.com/endpoint")

            # Should still return same value
            assert result1 == result2 == {"data": "response_value"}

            # HTTP should only have been called once (cache hit)
            assert mock_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_post_request_not_cached(self):
        """Test that POST requests are not cached."""
        client = BaseAPIClient(cache_ttl=300)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "created"})
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            # Make POST request (not cached - should only call HTTP once)
            result = await client.post("https://api.test.com/endpoint", json={"key": "value"})

            # Should call HTTP once (POST is not cached)
            assert mock_session.request.call_count == 1
            assert result == {"data": "created"}

            # Cache should be empty (POST responses not cached)
            assert client._cache.size == 0

    @pytest.mark.asyncio
    async def test_cache_not_used_when_disabled(self):
        """Test that cache is bypassed when ttl=0."""
        client = BaseAPIClient(cache_ttl=0)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"data": "value"})
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            # Make two requests
            await client.get("https://api.test.com/endpoint")
            await client.get("https://api.test.com/endpoint")

            # HTTP should be called twice (no caching)
            assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_failed_request_not_cached(self):
        """Test that failed requests (returning None) are not cached."""
        client = BaseAPIClient(cache_ttl=300)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 500
            mock_response.content_length = 0
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            await client.get("https://api.test.com/endpoint")

            # Cache should be empty (None values not cached)
            assert client._cache.size == 0

    @pytest.mark.asyncio
    async def test_different_urls_cached_separately(self):
        """Test that different URLs have separate cache entries."""
        client = BaseAPIClient(cache_ttl=300)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(side_effect=[
                {"data": "value1"},
                {"data": "value2"}
            ])
            mock_response.content_length = 10
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            result1 = await client.get("https://api.test.com/endpoint1")
            result2 = await client.get("https://api.test.com/endpoint2")

            assert result1 == {"data": "value1"}
            assert result2 == {"data": "value2"}
            # Two HTTP calls for two different URLs
            assert mock_session.request.call_count == 2

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_request(self):
        """Test that second identical request hits cache."""
        client = BaseAPIClient(cache_ttl=300)

        call_count = 0

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.content_length = 10

            async def mock_json():
                nonlocal call_count
                call_count += 1
                return {"data": f"request_{call_count}"}

            mock_response.json = mock_json
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            result1 = await client.get("https://api.test.com/endpoint")
            result2 = await client.get("https://api.test.com/endpoint")
            result3 = await client.get("https://api.test.com/endpoint")

            assert result1 == {"data": "request_1"}
            assert result2 == {"data": "request_1"}  # cached
            assert result3 == {"data": "request_1"}  # cached
            assert call_count == 1  # Only one HTTP request made


# ---------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------


class TestCacheIntegration:
    """Integration tests for cache with real client behavior."""

    @pytest.mark.asyncio
    async def test_client_with_all_cache_options(self):
        """Test client initialization with various cache options."""
        client = BaseAPIClient(
            base_url="https://api.test.com",
            cache_ttl=120,
            cache_max_size=500,
        )

        assert client._cache is not None
        assert client._cache.ttl == 120
        assert client._cache.max_size == 500

        # Verify caching works via cache stats
        stats_before = client.cache.get_stats()
        assert stats_before["size"] == 0

    @pytest.mark.asyncio
    async def test_cache_accessible_for_inspection(self):
        """Test that cache stats are accessible for monitoring."""
        client = BaseAPIClient(cache_ttl=300, cache_max_size=100)

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.content_length = 10

            call_count = 0
            async def mock_json():
                nonlocal call_count
                call_count += 1
                return {"data": f"request_{call_count}"}

            mock_response.json = mock_json
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session

            await client.get("/endpoint1")
            await client.get("/endpoint2")
            await client.get("/endpoint1")  # cache hit

            stats = client.cache.get_stats()
            assert stats["size"] == 2
            assert stats["valid_entries"] == 2
