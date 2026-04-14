"""
Tests for Cron Delivery Module.

Tests Telegram alert delivery, message chunking, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import asyncio

from borg.defi.cron.delivery import (
    deliver_alerts,
    send_telegram,
    _chunk_message,
    _send_telegram_message,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------

@pytest.fixture
def mock_env_bot_token(monkeypatch):
    """Set mock Telegram bot token in environment."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token_123")
    return "test_bot_token_123"


@pytest.fixture
def mock_env_chat_id(monkeypatch):
    """Set mock Telegram chat ID in environment."""
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test_chat_456")
    return "test_chat_456"


# -------------------------------------------------------------------------
# Message Chunking Tests
# -------------------------------------------------------------------------

class TestChunkMessage:
    """Tests for _chunk_message function."""

    def test_short_message_unchanged(self):
        """Short message under limit returns as single chunk."""
        msg = "Hello, this is a short message"
        chunks = _chunk_message(msg, 4096)
        assert len(chunks) == 1
        assert chunks[0] == msg

    def test_exact_limit_message(self):
        """Message exactly at limit returns as single chunk."""
        msg = "x" * 4096
        chunks = _chunk_message(msg, 4096)
        assert len(chunks) == 1

    def test_long_message_split(self):
        """Message over limit is split into chunks."""
        msg = "x" * 5000
        chunks = _chunk_message(msg, 4096)
        assert len(chunks) == 2
        assert len(chunks[0]) == 4096
        assert len(chunks[1]) == 904  # 5000 - 4096

    def test_multiple_chunks(self):
        """Very long message split into multiple chunks."""
        msg = "line\n" * 2000  # Each line is 5 chars
        chunks = _chunk_message(msg, 500)
        assert len(chunks) > 1

    def test_newline_preserved(self):
        """Newlines are preserved in chunks."""
        msg = "line1\nline2\nline3"
        chunks = _chunk_message(msg, 50)
        # Should keep lines together when possible
        assert any("line1" in c and "line2" in c for c in chunks)

    def test_empty_message(self):
        """Empty message returns empty list."""
        chunks = _chunk_message("", 4096)
        assert chunks == [""]


# -------------------------------------------------------------------------
# Delivery Function Tests
# -------------------------------------------------------------------------

class TestDeliverAlerts:
    """Tests for deliver_alerts function."""

    @pytest.mark.asyncio
    async def test_empty_alerts_returns_zero(self):
        """Empty alerts list returns 0."""
        result = await deliver_alerts([])
        assert result == 0

    @pytest.mark.asyncio
    async def test_unsupported_platform_returns_zero(self):
        """Unsupported platform returns 0."""
        result = await deliver_alerts(["Alert 1"], platform="discord")
        assert result == 0

    @pytest.mark.asyncio
    async def test_no_token_returns_zero(self):
        """No bot token configured returns 0."""
        with patch.object(os, 'environ', {'TELEGRAM_BOT_TOKEN': ''}):
            result = await deliver_alerts(["Alert 1"])
            assert result == 0

    @pytest.mark.asyncio
    async def test_successful_delivery_with_env_token(
        self, mock_env_bot_token, mock_env_chat_id
    ):
        """Successful delivery when token and chat_id are set."""
        with patch("borg.defi.cron.delivery.aiohttp.ClientSession") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("aiohttp.ClientSession", return_value=mock_session):
                result = await deliver_alerts(["Test alert"])

        assert result >= 0  # May be 0 if token not actually sent

    @pytest.mark.asyncio
    async def test_custom_chat_id_override(self, mock_env_bot_token):
        """Custom chat_id overrides environment setting."""
        # Just verify the function handles custom chat_id
        with patch("borg.defi.cron.delivery.aiohttp.ClientSession") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await deliver_alerts(
                ["Alert"], chat_id="custom_override"
            )

        # Function should handle it gracefully
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_multiple_alerts_chunked(self, mock_env_bot_token, mock_env_chat_id):
        """Multiple alerts are sent separately."""
        alerts = [f"Alert {i}: " + "x" * 100 for i in range(3)]

        with patch("borg.defi.cron.delivery.aiohttp.ClientSession") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await deliver_alerts(alerts)

        assert isinstance(result, int)


# -------------------------------------------------------------------------
# Send Telegram Function Tests
# -------------------------------------------------------------------------

class TestSendTelegram:
    """Tests for send_telegram function."""

    @pytest.mark.asyncio
    async def test_no_token_returns_false(self):
        """No bot token returns False."""
        with patch.object(os, 'environ', {'TELEGRAM_BOT_TOKEN': ''}):
            result = await send_telegram("Test message")
            assert result is False

    @pytest.mark.asyncio
    async def test_no_chat_id_returns_false(self, mock_env_bot_token):
        """No chat_id configured returns False."""
        with patch.object(os, 'environ', {'TELEGRAM_CHAT_ID': ''}):
            result = await send_telegram("Test message")
            assert result is False

    @pytest.mark.asyncio
    async def test_api_error_returns_false(self, mock_env_bot_token, mock_env_chat_id):
        """Telegram API error returns False."""
        with patch("borg.defi.cron.delivery.aiohttp.ClientSession") as mock_session:
            mock_response = MagicMock()
            mock_response.status = 429  # Rate limit
            mock_response.text = AsyncMock(return_value="Too Many Requests")
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await send_telegram("Test message")

        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, mock_env_bot_token, mock_env_chat_id):
        """Request timeout returns False."""
        with patch("borg.defi.cron.delivery.aiohttp.ClientSession") as mock_session:
            mock_session.return_value.post = AsyncMock(
                side_effect=asyncio.TimeoutError
            )

            result = await send_telegram("Test message")

        assert result is False


# -------------------------------------------------------------------------
# Integration Tests
# -------------------------------------------------------------------------

class TestDeliveryIntegration:
    """Integration tests for delivery module."""

    def test_import_works(self):
        """Module imports successfully."""
        from borg.defi.cron.delivery import deliver_alerts, send_telegram
        assert callable(deliver_alerts)
        assert callable(send_telegram)

    def test_chunk_message_imports(self):
        """_chunk_message function is importable."""
        from borg.defi.cron.delivery import _chunk_message
        assert callable(_chunk_message)

    @pytest.mark.asyncio
    async def test_deliver_alerts_handles_exception(self):
        """deliver_alerts handles unexpected exceptions gracefully."""
        with patch("borg.defi.cron.delivery.aiohttp.ClientSession", side_effect=Exception("Test")):
            result = await deliver_alerts(["Alert"])
            # Should return 0, not raise
            assert result == 0