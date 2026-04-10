"""
Tests for Arkham Intelligence API client.

Covers:
    - ArkhamClient initialization and headers
    - search_entity
    - get_entity
    - get_address_intelligence
    - get_portfolio
    - get_transfers
    - get_token_holders
    - get_smart_money_wallets
    - enrich_alert_with_entity
    - WhaleTracker Arkham integration

Run with:
    pytest borg/defi/tests/test_arkham.py -v --tb=short
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.api_clients.arkham import ArkhamClient, KNOWN_SMART_MONEY_LABELS
from borg.defi.whale_tracker import WhaleTracker
from borg.defi.data_models import WhaleAlert


# ============================================================================
# Arkham Client Tests
# ============================================================================


class TestArkhamClientInit:
    """Test ArkhamClient initialization."""

    def test_arkham_client_with_api_key(self):
        """test_arkham_client_with_api_key — API key passed and stored."""
        client = ArkhamClient(api_key="test_key_123")
        assert client._api_key == "test_key_123"
        assert client._base_url == "https://api.arkhamintelligence.com"

    def test_arkham_client_env_var(self):
        """test_arkham_client_env_var — reads from ARKHAM_API_KEY env."""
        with patch.dict(os.environ, {"ARKHAM_API_KEY": "env_key_456"}):
            client = ArkhamClient()
            assert client._api_key == "env_key_456"

    def test_arkham_client_no_key_warning(self, caplog):
        """test_arkham_client_no_key_warning — logs warning when no key."""
        with caplog.at_level(logging.WARNING):
            client = ArkhamClient()
            assert client._api_key is None
            assert "ARKHAM_API_KEY" in caplog.text

    def test_arkham_client_headers_with_key(self):
        """test_arkham_client_headers_with_key — headers include X-API-Key."""
        client = ArkhamClient(api_key="test_key")
        headers = client._get_headers()
        assert headers["X-API-Key"] == "test_key"
        assert headers["Content-Type"] == "application/json"

    def test_arkham_client_headers_without_key(self):
        """test_arkham_client_headers_without_key — headers work without key."""
        client = ArkhamClient()
        headers = client._get_headers()
        # Without API key, X-API-Key header is not added (only Content-Type)
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        # X-API-Key should not be present when no key is set
        assert "X-API-Key" not in headers


class TestArkhamSearchEntity:
    """Test search_entity method."""

    @pytest.mark.asyncio
    async def test_search_entity_success(self):
        """test_search_entity_success — returns list of entities."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "results": [
                {"id": "entity_1", "name": "Jump Trading", "labels": ["market maker"]},
                {"id": "entity_2", "name": "a16z", "labels": ["venture capital"]},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.search_entity("trading")

            assert result is not None
            assert len(result) == 2
            assert result[0]["name"] == "Jump Trading"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_entity_no_key(self):
        """test_search_entity_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.search_entity("trading")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_entity_empty_response(self):
        """test_search_entity_empty_response — returns empty list on empty."""
        client = ArkhamClient(api_key="test_key")

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"results": []}
            result = await client.search_entity("nonexistent")
            assert result == []


class TestArkhamGetEntity:
    """Test get_entity method."""

    @pytest.mark.asyncio
    async def test_get_entity_success(self):
        """test_get_entity_success — returns entity details."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "id": "entity_abc",
            "name": "Jump Trading",
            "labels": ["market maker", "institutional"],
            "addresses": ["0x123...abc"],
            "holdings": {"ETH": 1000, "USDC": 500000},
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_entity("entity_abc")

            assert result is not None
            assert result["name"] == "Jump Trading"
            assert "market maker" in result["labels"]
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entity_no_key(self):
        """test_get_entity_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.get_entity("entity_abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self):
        """test_get_entity_not_found — returns None for invalid entity."""
        client = ArkhamClient(api_key="test_key")

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await client.get_entity("invalid_id")
            assert result is None


class TestArkhamAddressIntelligence:
    """Test get_address_intelligence method."""

    @pytest.mark.asyncio
    async def test_address_intelligence_success(self):
        """test_address_intelligence_success — returns intelligence for address."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "entityId": "entity_jump",
            "entityName": "Jump Trading",
            "labels": ["market maker", "institutional"],
            "tags": ["smart money"],
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_address_intelligence("0x123abc...")

            assert result is not None
            assert result["entityName"] == "Jump Trading"
            assert "market maker" in result["labels"]
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_address_intelligence_no_key(self):
        """test_address_intelligence_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.get_address_intelligence("0x123abc...")
        assert result is None

    @pytest.mark.asyncio
    async def test_address_intelligence_smart_money(self):
        """test_address_intelligence_smart_money — detects smart money label."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "entityId": "entity_16z",
            "entityName": "a16z",
            "labels": ["venture capital", "institutional"],
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_address_intelligence("0xabcd...")

            assert result is not None
            assert "venture capital" in result["labels"]


class TestArkhamPortfolio:
    """Test get_portfolio method."""

    @pytest.mark.asyncio
    async def test_get_portfolio_success(self):
        """test_get_portfolio_success — returns portfolio holdings."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "entityId": "entity_abc",
            "holdings": [
                {"token": "ETH", "amount": 1000, "value_usd": 2000000},
                {"token": "USDC", "amount": 500000, "value_usd": 500000},
            ],
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_portfolio("entity_abc")

            assert result is not None
            assert "holdings" in result
            assert len(result["holdings"]) == 2
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_portfolio_no_key(self):
        """test_get_portfolio_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.get_portfolio("entity_abc")
        assert result is None


class TestArkhamTransfers:
    """Test get_transfers method."""

    @pytest.mark.asyncio
    async def test_get_transfers_success(self):
        """test_get_transfers_success — returns list of transfers."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "transfers": [
                {
                    "from": "0xabc...",
                    "to": "0xdef...",
                    "amount": "1000000",
                    "token": "USDC",
                    "timestamp": 1234567890,
                },
                {
                    "from": "0x123...",
                    "to": "0x456...",
                    "amount": "500",
                    "token": "ETH",
                    "timestamp": 1234567891,
                },
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_transfers("0xabc...")

            assert result is not None
            assert len(result) == 2
            assert result[0]["token"] == "USDC"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_transfers_with_chain_filter(self):
        """test_get_transfers_with_chain_filter — passes chain parameter."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {"transfers": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_transfers("0xabc...", chain="ethereum")

            assert result is not None
            call_args = mock_get.call_args
            assert "params" in call_args.kwargs
            assert call_args.kwargs["params"]["chain"] == "ethereum"

    @pytest.mark.asyncio
    async def test_get_transfers_no_key(self):
        """test_get_transfers_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.get_transfers("0xabc...")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_transfers_limit(self):
        """test_get_transfers_limit — respects limit parameter."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {"transfers": [{"hash": "1"}, {"hash": "2"}]}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.get_transfers("0xabc...", limit=25)

            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["limit"] == 25


class TestArkhamTokenHolders:
    """Test get_token_holders method."""

    @pytest.mark.asyncio
    async def test_get_token_holders_success(self):
        """test_get_token_holders_success — returns list of holders."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "holders": [
                {"address": "0xaaa...", "amount": 1000000, "percentage": 10.5},
                {"address": "0xbbb...", "amount": 800000, "percentage": 8.2},
            ]
        }

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await client.get_token_holders("0xtoken...")

            assert result is not None
            assert len(result) == 2
            assert result[0]["percentage"] == 10.5
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_holders_custom_chain(self):
        """test_get_token_holders_custom_chain — uses specified chain."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {"holders": []}

        with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            await client.get_token_holders("0xtoken...", chain="base")

            call_args = mock_get.call_args
            assert call_args.kwargs["params"]["chain"] == "base"

    @pytest.mark.asyncio
    async def test_get_token_holders_no_key(self):
        """test_get_token_holders_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.get_token_holders("0xtoken...")
        assert result is None


class TestArkhamSmartMoney:
    """Test get_smart_money_wallets method."""

    @pytest.mark.asyncio
    async def test_get_smart_money_wallets_success(self):
        """test_get_smart_money_wallets_success — returns matched entities."""
        client = ArkhamClient(api_key="test_key")

        # Mock search_entity to return Jump Trading for "Jump Trading" query
        async def mock_search(query):
            if "Jump" in query:
                return [
                    {
                        "id": "jump_entity",
                        "name": "Jump Trading",
                        "labels": ["market maker"],
                    }
                ]
            elif "a16z" in query:
                return [
                    {
                        "id": "a16z_entity",
                        "name": "a16z",
                        "labels": ["venture capital"],
                    }
                ]
            return []

        with patch.object(client, "search_entity", new=mock_search):
            result = await client.get_smart_money_wallets()

            assert result is not None
            assert len(result) >= 1
            # Check that Jump Trading was found
            names = [e.get("name", "") for e in result]
            assert any("Jump" in n for n in names)

    @pytest.mark.asyncio
    async def test_get_smart_money_wallets_no_key(self):
        """test_get_smart_money_wallets_no_key — returns None without API key."""
        client = ArkhamClient()
        result = await client.get_smart_money_wallets()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_smart_money_wallets_empty(self):
        """test_get_smart_money_wallets_empty — returns None when nothing found."""
        client = ArkhamClient(api_key="test_key")

        async def mock_search(query):
            return []

        with patch.object(client, "search_entity", new=mock_search):
            result = await client.get_smart_money_wallets()
            assert result is None


class TestArkhamEnrichAlert:
    """Test enrich_alert_with_entity method."""

    @pytest.mark.asyncio
    async def test_enrich_alert_with_entity_success(self):
        """test_enrich_alert_with_entity_success — returns enriched data."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "entityId": "jump_entity",
            "entityName": "Jump Trading",
            "labels": ["market maker", "institutional"],
        }

        with patch.object(client, "get_address_intelligence", new_callable=AsyncMock) as mock_intel:
            mock_intel.return_value = mock_response
            result = await client.enrich_alert_with_entity("0x123...")

            assert result is not None
            assert result["entity_name"] == "Jump Trading"
            assert result["is_smart_money"] is True
            assert "market maker" in result["labels"]

    @pytest.mark.asyncio
    async def test_enrich_alert_with_entity_no_intelligence(self):
        """test_enrich_alert_with_entity_no_intelligence — returns None."""
        client = ArkhamClient(api_key="test_key")

        with patch.object(client, "get_address_intelligence", new_callable=AsyncMock) as mock_intel:
            mock_intel.return_value = None
            result = await client.enrich_alert_with_entity("0x123...")
            assert result is None

    @pytest.mark.asyncio
    async def test_enrich_alert_with_entity_not_smart_money(self):
        """test_enrich_alert_with_entity_not_smart_money — is_smart_money False."""
        client = ArkhamClient(api_key="test_key")
        mock_response = {
            "entityId": "unknown_entity",
            "entityName": "Random Wallet",
            "labels": ["retail"],
        }

        with patch.object(client, "get_address_intelligence", new_callable=AsyncMock) as mock_intel:
            mock_intel.return_value = mock_response
            result = await client.enrich_alert_with_entity("0x123...")

            assert result is not None
            assert result["is_smart_money"] is False


# ============================================================================
# WhaleTracker Arkham Integration Tests
# ============================================================================


class TestWhaleTrackerArkhamIntegration:
    """Test WhaleTracker integration with Arkham."""

    def test_whale_tracker_with_arkham_key(self):
        """test_whale_tracker_with_arkham_key — initializes ArkhamClient."""
        tracker = WhaleTracker(
            tracked_wallets={"0xabc...": "Test Whale"},
            arkham_api_key="test_arkham_key",
        )
        assert tracker.arkham_client is not None
        assert tracker.arkham_client._api_key == "test_arkham_key"

    def test_whale_tracker_without_arkham_key(self):
        """test_whale_tracker_without_arkham_key — arkham_client is None."""
        tracker = WhaleTracker(tracked_wallets={"0xabc...": "Test Whale"})
        assert tracker.arkham_client is None

    @pytest.mark.asyncio
    async def test_enrich_alert_with_arkham_no_client(self):
        """test_enrich_alert_with_arkham_no_client — returns original alert."""
        tracker = WhaleTracker(tracked_wallets={"0xabc...": "Test Whale"})
        alert = WhaleAlert(
            wallet="0xabc...",
            chain="ethereum",
            action="swap",
            token_in="ETH",
            token_out="USDC",
            amount_usd=100000.0,
            timestamp=1234567890.0,
            tx_hash="0xtxhash",
            context="Swapped ETH for USDC",
        )

        enriched = await tracker.enrich_alert_with_arkham(alert)
        assert enriched.context == "Swapped ETH for USDC"

    @pytest.mark.asyncio
    async def test_enrich_alert_with_arkham_smart_money(self):
        """test_enrich_alert_with_arkham_smart_money — integration test for enrichment."""
        tracker = WhaleTracker(
            tracked_wallets={"0xabcd1234efgh5678ijkl9012mnop3456qrst": "Test Whale"},
            arkham_api_key="test_key",
        )

        alert = WhaleAlert(
            wallet="0xabcd1234efgh5678ijkl9012mnop3456qrst",
            chain="ethereum",
            action="swap",
            token_in="ETH",
            token_out="USDC",
            amount_usd=100000.0,
            timestamp=1234567890.0,
            tx_hash="0xtxhash",
            context="Swapped ETH for USDC",
            signal_strength=0.5,
        )

        # Create a mock client with proper async behavior
        mock_arkham = MagicMock()
        mock_arkham.enrich_alert_with_entity = AsyncMock(
            return_value={
                "entity_id": "jump_entity",
                "entity_name": "Jump Trading",
                "labels": ["market maker"],
                "is_smart_money": True,
            }
        )
        tracker.arkham_client = mock_arkham

        enriched = await tracker.enrich_alert_with_arkham(alert)
        assert "Entity: Jump Trading" in enriched.context
        assert enriched.signal_strength > 0.5

    @pytest.mark.asyncio
    async def test_enrich_alert_skips_truncated_address(self):
        """test_enrich_alert_skips_truncated_address — doesn't enrich 6...4 style."""
        tracker = WhaleTracker(
            tracked_wallets={"0xabc...": "Test Whale"},
            arkham_api_key="test_key",
        )

        alert = WhaleAlert(
            wallet="0x1234...abcd",  # Truncated address
            chain="ethereum",
            action="swap",
            token_in="ETH",
            token_out="USDC",
            amount_usd=100000.0,
            timestamp=1234567890.0,
            tx_hash="0xtxhash",
            context="Swapped ETH for USDC",
        )

        enriched = await tracker.enrich_alert_with_arkham(alert)
        # Should be unchanged since we can't use truncated address
        assert enriched.context == "Swapped ETH for USDC"

    @pytest.mark.asyncio
    async def test_get_smart_money_wallets_no_client(self):
        """test_get_smart_money_wallets_no_client — returns None."""
        tracker = WhaleTracker(tracked_wallets={"0xabc...": "Test Whale"})
        result = await tracker.get_smart_money_wallets()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_smart_money_wallets_with_client(self):
        """test_get_smart_money_wallets_with_client — returns cached results."""
        tracker = WhaleTracker(
            tracked_wallets={"0xabc...": "Test Whale"},
            arkham_api_key="test_key",
        )

        mock_entities = [{"id": "1", "name": "Jump Trading"}]
        tracker.arkham_client.get_smart_money_wallets = AsyncMock(
            return_value=mock_entities
        )

        result = await tracker.get_smart_money_wallets()
        assert result == mock_entities

        # Second call should use cache
        result2 = await tracker.get_smart_money_wallets()
        assert tracker.arkham_client.get_smart_money_wallets.call_count == 1

    @pytest.mark.asyncio
    async def test_discover_new_whales_no_client(self):
        """test_discover_new_whales_no_client — returns empty list."""
        tracker = WhaleTracker(tracked_wallets={"0xabc...": "Test Whale"})
        result = await tracker.discover_new_whales()
        assert result == []

    @pytest.mark.asyncio
    async def test_discover_new_whales_with_smart_money(self):
        """test_discover_new_whales_with_smart_money — finds smart money in tracked."""
        tracker = WhaleTracker(
            tracked_wallets={"0xabc123def456...": "Test Whale"},
            arkham_api_key="test_key",
        )

        tracker.arkham_client.enrich_alert_with_entity = AsyncMock(
            return_value={
                "entity_id": "jump_entity",
                "entity_name": "Jump Trading",
                "labels": ["market maker"],
                "is_smart_money": True,
            }
        )

        discoveries = await tracker.discover_new_whales()
        assert len(discoveries) >= 1
        assert discoveries[0]["entity_name"] == "Jump Trading"


# ============================================================================
# Known Smart Money Labels Test
# ============================================================================


def test_known_smart_money_labels_exist():
    """test_known_smart_money_labels_exist — verifies list is populated."""
    assert len(KNOWN_SMART_MONEY_LABELS) > 0
    assert "Jump Trading" in KNOWN_SMART_MONEY_LABELS
    assert "a16z" in KNOWN_SMART_MONEY_LABELS
    assert "Paradigm" in KNOWN_SMART_MONEY_LABELS


# ============================================================================
# Safe Float Tests
# ============================================================================


def test_arkham_safe_float():
    """test_arkham_safe_float — safely converts values."""
    client = ArkhamClient()

    assert client._safe_float(None) == 0.0
    assert client._safe_float(100) == 100.0
    assert client._safe_float("100.5") == 100.5
    assert client._safe_float("invalid") == 0.0
    assert client._safe_float(0) == 0.0
