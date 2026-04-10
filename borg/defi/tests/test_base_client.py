"""
Tests for BaseAPIClient.

Covers:
- BaseAPIClient init (base_url, api_key, timeout)
- Session creation and cleanup
- API key sanitization in logs
- Basic error handling

Run with:
    pytest borg/defi/tests/test_base_client.py -v --tb=short
"""

import asyncio
import logging
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.api_clients.base import BaseAPIClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_url():
    """Base URL for API testing."""
    return "https://api.test.defi/v1"


@pytest.fixture
def api_key():
    """Test API key."""
    return "test_api_key_1234567890abcdef"


@pytest.fixture
def client(base_url, api_key):
    """Create BaseAPIClient instance."""
    return BaseAPIClient(base_url=base_url, api_key=api_key)


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestBaseAPIClientInit:
    """Tests for BaseAPIClient initialization."""

    def test_init_with_base_url(self, base_url):
        """Test initialization with base_url."""
        client = BaseAPIClient(base_url=base_url)
        assert client._base_url == base_url
        assert client._session is None

    def test_init_with_api_key(self, api_key):
        """Test initialization with api_key."""
        client = BaseAPIClient(api_key=api_key)
        assert client._api_key == api_key

    def test_init_with_timeout(self):
        """Test initialization with custom timeout."""
        custom_timeout = aiohttp.ClientTimeout(total=60)
        client = BaseAPIClient(timeout=custom_timeout)
        assert client._timeout == custom_timeout

    def test_init_with_all_params(self, base_url, api_key):
        """Test initialization with all parameters."""
        custom_timeout = aiohttp.ClientTimeout(total=45)
        client = BaseAPIClient(
            base_url=base_url,
            api_key=api_key,
            timeout=custom_timeout,
        )
        assert client._base_url == base_url
        assert client._api_key == api_key
        assert client._timeout == custom_timeout

    def test_init_default_values(self):
        """Test initialization with default values."""
        client = BaseAPIClient()
        assert client._base_url is None
        assert client._api_key is None
        assert client._session is None
        assert client._session_created is False


# ---------------------------------------------------------------------------
# Session Management Tests
# ---------------------------------------------------------------------------


class TestSessionManagement:
    """Tests for session creation and cleanup."""

    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self, client):
        """Test _ensure_session creates a new session."""
        session = await client._ensure_session()
        assert session is not None
        assert isinstance(session, aiohttp.ClientSession)
        assert client._session_created is True
        await client.close()

    @pytest.mark.asyncio
    async def test_ensure_session_reuses_session(self, client):
        """Test _ensure_session reuses existing session."""
        session1 = await client._ensure_session()
        session2 = await client._ensure_session()
        assert session1 is session2
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager_creates_session(self, base_url):
        """Test context manager creates and closes session."""
        async with BaseAPIClient(base_url=base_url) as client:
            assert client._session is not None
            assert client._session_created is True
        assert client._session is None

    @pytest.mark.asyncio
    async def test_close_closes_session(self, client):
        """Test close() properly closes session."""
        await client._ensure_session()
        assert client._session is not None
        await client.close()
        assert client._session is None
        assert client._session_created is False

    @pytest.mark.asyncio
    async def test_close_when_no_session(self, client):
        """Test close() when no session exists (no-op)."""
        await client.close()
        assert client._session is None


# ---------------------------------------------------------------------------
# API Key Sanitization Tests
# ---------------------------------------------------------------------------


class TestAPISanitization:
    """Tests for API key sanitization in logs."""

    def test_sanitize_explicit_api_key(self, api_key):
        """Test API key in api_key= format is redacted."""
        client = BaseAPIClient(api_key=api_key)
        message = f"api_key={api_key}"
        result = client._sanitize_log(message)
        assert "[REDACTED]" in result
        assert api_key not in result

    def test_sanitize_api_key_with_equals(self):
        """Test api_key=value pattern is redacted."""
        client = BaseAPIClient()
        key_value = "api_key_value_12345678901234567890"  # 36 chars
        message = f"api_key={key_value}"
        result = client._sanitize_log(message)
        assert "[REDACTED]" in result

    def test_sanitize_secret_key(self):
        """Test secret=key is redacted."""
        client = BaseAPIClient()
        secret_value = "secretvalue1234567890"  # 20 chars > 16
        message = f"secret={secret_value}"
        result = client._sanitize_log(message)
        assert "[REDACTED]" in result
        assert secret_value not in result

    def test_sanitize_token_key(self):
        """Test token=key is redacted."""
        client = BaseAPIClient()
        token_value = "tokenvalue123456789012"  # 22 chars > 16
        message = f"token={token_value}"
        result = client._sanitize_log(message)
        assert "[REDACTED]" in result

    def test_sanitize_short_key_not_redacted(self):
        """Test that short key values are not redacted (below 16 char threshold)."""
        client = BaseAPIClient()
        short_key = "abc123"
        message = f"key={short_key}"
        result = client._sanitize_log(message)
        assert short_key in result

    def test_sanitize_private_key_0x(self):
        """Test private keys (0x + 64 hex) are redacted."""
        client = BaseAPIClient()
        private_key = "0x" + "a" * 64
        message = f"private_key={private_key}"
        result = client._sanitize_log(message)
        assert "[REDACTED]" in result
        assert private_key not in result

    def test_sanitize_no_change_on_normal_text(self):
        """Test that normal text without keys is unchanged."""
        client = BaseAPIClient()
        message = "GET https://api.test.com/v1/pools"
        result = client._sanitize_log(message)
        assert result == message

    def test_sanitize_multiple_api_keys(self):
        """Test multiple API keys in one message are redacted."""
        client = BaseAPIClient()
        key1 = "api_key_1234567890123456"
        key2 = "secret_key_1234567890123456"
        message = f"First: api_key={key1}, Second: secret={key2}"
        result = client._sanitize_log(message)
        assert "[REDACTED]" in result
        assert key1 not in result


# ---------------------------------------------------------------------------
# Log Method Tests
# ---------------------------------------------------------------------------


class TestLogMethods:
    """Tests for logging methods."""

    def test_log_request_method_and_url(self, client, caplog):
        """Test _log_request logs method and sanitized URL."""
        with caplog.at_level(logging.DEBUG):
            client._log_request("GET", "https://api.test.com/test")
        
        assert "GET" in caplog.text
        assert "api.test.com" in caplog.text

    def test_log_response_status(self, client, caplog):
        """Test _log_response logs status code."""
        with caplog.at_level(logging.DEBUG):
            client._log_response(200, "https://api.test.com", 100)
        
        assert "200" in caplog.text

    def test_log_error_with_context(self, client, caplog):
        """Test _log_error logs error with context."""
        with caplog.at_level(logging.ERROR):
            client._log_error(Exception("Test error"), "Test context")
        
        assert "Test context" in caplog.text
        assert "Test error" in caplog.text

    def test_log_request_redacts_api_key_in_url(self, client, caplog):
        """Test _log_request sanitizes API keys in URL."""
        with caplog.at_level(logging.DEBUG):
            # URL with api_key as query param - this matches the pattern
            client._log_request(
                "GET",
                "https://api.test.com?api_key=very_long_api_key_value_here_1234567890",
            )
        
        # The long API key in URL should be redacted
        assert "very_long_api_key_value_here_1234567890" not in caplog.text


# ---------------------------------------------------------------------------
# Convenience Method Tests
# ---------------------------------------------------------------------------


class TestConvenienceMethods:
    """Tests for GET/POST convenience methods."""

    @pytest.mark.asyncio
    async def test_get_calls_request_with_retry(self, client):
        """Test get() calls _request_with_retry with correct method."""
        with patch.object(client, '_request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"result": "ok"}
            result = await client.get("https://api.test.com/endpoint")
            
            mock_req.assert_called_once_with("GET", "https://api.test.com/endpoint")
            assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_post_calls_request_with_retry(self, client):
        """Test post() calls _request_with_retry with correct method."""
        with patch.object(client, '_request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"result": "created"}
            result = await client.post("https://api.test.com/endpoint", json={"key": "value"})
            
            mock_req.assert_called_once_with("POST", "https://api.test.com/endpoint", json={"key": "value"})
            assert result == {"result": "created"}
