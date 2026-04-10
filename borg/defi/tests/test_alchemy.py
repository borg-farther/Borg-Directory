"""
Tests for Alchemy EVM RPC API client.

Run with:
    pytest borg/defi/tests/test_alchemy.py -v --tb=short
    BORG_DEFI_INTEGRATION=true pytest borg/defi/tests/test_alchemy.py -v -k integration
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.api_clients.alchemy import AlchemyClient


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name, "r") as f:
        return json.load(f)


@pytest.fixture
def alchemy_token_balances_fixture():
    """Load Alchemy token balances fixture."""
    return load_fixture("alchemy_token_balances.json")


@pytest.fixture
def alchemy_transfers_fixture():
    """Load Alchemy asset transfers fixture."""
    return load_fixture("alchemy_transfers.json")


@pytest.fixture
def alchemy_token_metadata_fixture():
    """Load Alchemy token metadata fixture."""
    return load_fixture("alchemy_token_metadata.json")


@pytest.fixture
def alchemy_receipt_fixture():
    """Load Alchemy transaction receipt fixture."""
    return load_fixture("alchemy_receipt.json")


# ---------------------------------------------------------------------
# Alchemy Client Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alchemy_init_with_key():
    """Test Alchemy client initialization with API key."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key_123"}):
        client = AlchemyClient()

        assert client._api_key == "test_key_123"
        assert "eth-mainnet" in client._base_url
        assert "test_key_123" in client._base_url

        print(f"✓ Alchemy init with key test passed")


@pytest.mark.asyncio
async def test_alchemy_init_explicit_key():
    """Test Alchemy client initialization with explicit key."""
    client = AlchemyClient(api_key="explicit_key_456")

    assert client._api_key == "explicit_key_456"
    assert "explicit_key_456" in client._base_url

    print(f"✓ Alchemy init explicit key test passed")


@pytest.mark.asyncio
async def test_alchemy_init_network_selection():
    """Test Alchemy client network selection."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient(network="polygon-mainnet")
        assert "polygon-mainnet.g.alchemy.com" in client._base_url

        client2 = AlchemyClient(network="arb-mainnet")
        assert "arb-mainnet.g.alchemy.com" in client2._base_url

        client3 = AlchemyClient(network="base-mainnet")
        assert "base-mainnet.g.alchemy.com" in client3._base_url

        print(f"✓ Alchemy network selection test passed")


@pytest.mark.asyncio
async def test_alchemy_get_token_balances(alchemy_token_balances_fixture):
    """Test Alchemy get token balances."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "_rpc_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = alchemy_token_balances_fixture

            balances = await client.get_token_balances(
                "0x1234567890123456789012345678901234567890"
            )

            assert balances is not None
            assert isinstance(balances, list)
            assert len(balances) > 0

            print(f"✓ Alchemy token balances test passed: {len(balances)} tokens")


@pytest.mark.asyncio
async def test_alchemy_get_asset_transfers(alchemy_transfers_fixture):
    """Test Alchemy get asset transfers."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"result": alchemy_transfers_fixture}

            transfers = await client.get_asset_transfers(
                "0x1234567890123456789012345678901234567890",
                category="erc20",
            )

            assert transfers is not None
            assert isinstance(transfers, list)

            print(f"✓ Alchemy asset transfers test passed: {len(transfers)} transfers")


@pytest.mark.asyncio
async def test_alchemy_get_token_metadata(alchemy_token_metadata_fixture):
    """Test Alchemy get token metadata."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "_rpc_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = alchemy_token_metadata_fixture

            metadata = await client.get_token_metadata(
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
            )

            assert metadata is not None
            assert "decimals" in metadata
            assert "symbol" in metadata

            print(f"✓ Alchemy token metadata test passed: {metadata.get('symbol')}")


@pytest.mark.asyncio
async def test_alchemy_get_transaction_receipts(alchemy_receipt_fixture):
    """Test Alchemy get transaction receipts."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        tx_hashes = [
            "0xabc123def456abc123def456abc123def456abc123def456abc123def456abc1",
            "0x0987654321098765432109876543210987654321098765432109876543210987",
        ]

        with patch.object(client, "_rpc_call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [alchemy_receipt_fixture, alchemy_receipt_fixture]

            receipts = await client.get_transaction_receipts(tx_hashes)

            assert receipts is not None
            assert isinstance(receipts, list)
            assert len(receipts) == 2

            print(f"✓ Alchemy transaction receipts test passed: {len(receipts)} receipts")


@pytest.mark.asyncio
async def test_alchemy_get_block_number():
    """Test Alchemy get block number."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "_rpc_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "0x10d4f20"

            block = await client.get_block_number()

            assert block == "0x10d4f20"

            print(f"✓ Alchemy get block number test passed")


@pytest.mark.asyncio
async def test_alchemy_get_balance():
    """Test Alchemy get native balance."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "_rpc_call", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "0xde0b6b3a7640000"  # 1 ETH in hex

            balance = await client.get_balance("0x1234567890123456789012345678901234567890")

            assert balance == "0xde0b6b3a7640000"

            print(f"✓ Alchemy get balance test passed")


# ---------------------------------------------------------------------
# Helper Method Tests
# ---------------------------------------------------------------------


def test_hex_to_int():
    """Test hex to int conversion."""
    assert AlchemyClient.hex_to_int("0x0") == 0
    assert AlchemyClient.hex_to_int("0x1") == 1
    assert AlchemyClient.hex_to_int("0xde0b6b3a7640000") == 1000000000000000000
    assert AlchemyClient.hex_to_int("0x") == 0
    assert AlchemyClient.hex_to_int(None) == 0


def test_wei_to_eth():
    """Test wei to ETH conversion."""
    assert abs(AlchemyClient.wei_to_eth("0xde0b6b3a7640000") - 1.0) < 0.001
    assert AlchemyClient.wei_to_eth("0x0") == 0.0
    assert AlchemyClient.wei_to_eth(None) == 0.0


# ---------------------------------------------------------------------
# ERC20 Transfer Helper Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_erc20_transfers():
    """Test get_erc20_transfers helper."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "get_asset_transfers", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [{"hash": "0xabc"}, {"hash": "0xdef"}]

            transfers = await client.get_erc20_transfers("0x1234567890123456789012345678901234567890")

            mock_get.assert_called_once()
            args = mock_get.call_args
            assert args[0][0] == "0x1234567890123456789012345678901234567890"
            assert args[0][1] == "erc20"

            print(f"✓ Alchemy get_erc20_transfers test passed")


@pytest.mark.asyncio
async def test_get_native_transfers():
    """Test get_native_transfers helper."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "get_asset_transfers", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            transfers = await client.get_native_transfers("0x1234567890123456789012345678901234567890")

            mock_get.assert_called_once()
            args = mock_get.call_args
            assert args[0][1] == "native"

            print(f"✓ Alchemy get_native_transfers test passed")


@pytest.mark.asyncio
async def test_get_nft_transfers():
    """Test get_nft_transfers helper."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "get_asset_transfers", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []

            transfers = await client.get_nft_transfers("0x1234567890123456789012345678901234567890")

            mock_get.assert_called_once()
            args = mock_get.call_args
            assert args[0][1] == "erc721"

            print(f"✓ Alchemy get_nft_transfers test passed")


# ---------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alchemy_no_api_key():
    """Test Alchemy handles missing API key gracefully."""
    # Clear env var
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": ""}, clear=True):
        client = AlchemyClient()

        # Should still initialize with warning (empty string, not None)
        assert client._api_key == "" or client._api_key is None

        # RPC calls should fail gracefully
        result = await client._rpc_call("eth_blockNumber", [])
        assert result is None

        print(f"✓ Alchemy no API key test passed")


@pytest.mark.asyncio
async def test_alchemy_rpc_call_error():
    """Test Alchemy handles RPC errors gracefully."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = await client._rpc_call("eth_blockNumber", [])

            assert result is None

            print(f"✓ Alchemy RPC error handling test passed")


@pytest.mark.asyncio
async def test_alchemy_get_token_balances_error():
    """Test Alchemy get_token_balances handles errors gracefully."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        client = AlchemyClient()

        with patch.object(client, "_rpc_call", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("RPC error")

            balances = await client.get_token_balances("0x1234567890123456789012345678901234567890")

            assert balances == []

            print(f"✓ Alchemy get_token_balances error handling test passed")


# ---------------------------------------------------------------------
# Network URL Tests
# ---------------------------------------------------------------------


def test_alchemy_network_urls():
    """Test Alchemy constructs correct URLs for different networks."""
    with patch.dict(os.environ, {"ALCHEMY_API_KEY": "test_key"}):
        networks = [
            ("eth-mainnet", "eth-mainnet.g.alchemy.com"),
            ("ethereum-mainnet", "eth-mainnet.g.alchemy.com"),
            ("polygon-mainnet", "polygon-mainnet.g.alchemy.com"),
            ("arb-mainnet", "arb-mainnet.g.alchemy.com"),
            ("arbitrum-mainnet", "arb-mainnet.g.alchemy.com"),
            ("opt-mainnet", "opt-mainnet.g.alchemy.com"),
            ("optimism-mainnet", "opt-mainnet.g.alchemy.com"),
            ("base-mainnet", "base-mainnet.g.alchemy.com"),
        ]

        for network, expected_host in networks:
            client = AlchemyClient(network=network)
            assert expected_host in client._base_url, f"Network {network} should use {expected_host}"

        print(f"✓ Alchemy network URLs test passed")


# ---------------------------------------------------------------------
# Integration Tests (require network and real API key)
# ---------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_alchemy_get_block_number_real():
    """Integration test: Alchemy real API call to get block number."""
    api_key = os.environ.get("ALCHEMY_API_KEY")
    if not api_key:
        pytest.skip("ALCHEMY_API_KEY not set")

    async with AlchemyClient(network="eth-mainnet") as client:
        block = await client.get_block_number()

        assert block is not None
        assert block.startswith("0x")

        block_num = int(block, 16)
        assert block_num > 15000000  # Ethereum mainnet block should be high

        print(f"✓ Alchemy real API test passed: block {block_num}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_alchemy_get_balance_real():
    """Integration test: Alchemy real API call to get ETH balance."""
    api_key = os.environ.get("ALCHEMY_API_KEY")
    if not api_key:
        pytest.skip("ALCHEMY_API_KEY not set")

    async with AlchemyClient(network="eth-mainnet") as client:
        # Vitalik Buterin's address
        balance = await client.get_balance("0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B")

        assert balance is not None
        assert balance.startswith("0x")

        eth_balance = AlchemyClient.wei_to_eth(balance)
        assert eth_balance > 0

        print(f"✓ Alchemy real balance test passed: {eth_balance:.4f} ETH")
