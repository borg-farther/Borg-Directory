"""
Tests for MEV Protection Module.

Covers:
- JitoClient for Solana MEV protection
- FlashbotsClient for EVM MEV protection
- MEV integration in SwapExecutor

Run with:
    pytest borg/defi/tests/test_mev.py -v --tb=short
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.mev.jito import JitoClient
from borg.defi.mev.flashbots import FlashbotsClient
from borg.defi.swap_executor import SwapExecutor, SwapQuote

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def jito_client():
    """Create a Jito client for testing."""
    return JitoClient()


@pytest.fixture
def flashbots_client():
    """Create a Flashbots client for testing."""
    return FlashbotsClient(signing_key="0x" + "ab" * 32)


@pytest.fixture
def mock_swap_quote_solana():
    """Create a mock Solana swap quote."""
    return SwapQuote(
        chain="solana",
        input_token="So11111111111111111111111111111111111111112",
        output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        input_amount=1000000000,  # 1 SOL
        output_amount=98765432,
        output_amount_min=98265432,
        slippage_bps=50,
        price_impact_pct=0.125,
        route={},
        provider="jupiter",
        expires_at=time.time() + 60,
        raw_quote={},
    )


@pytest.fixture
def mock_swap_quote_evm():
    """Create a mock EVM swap quote."""
    return SwapQuote(
        chain="ethereum",
        input_token="0x0000000000000000000000000000000000000000",
        output_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        input_amount=1000000000000000000,  # 1 ETH
        output_amount=3245000000,
        output_amount_min=3226775000,
        slippage_bps=50,
        price_impact_pct=0.05,
        route={"routerAddress": "0x1111111254EEB25477B68fb85Ed929f73A960582"},
        provider="1inch",
        expires_at=time.time() + 300,
        raw_quote={},
    )


# ---------------------------------------------------------------------------
# JitoClient Tests
# ---------------------------------------------------------------------------

class TestJitoClient:
    """Tests for JitoClient (Solana MEV protection)."""

    def test_initialization(self, jito_client):
        """Test JitoClient initialization."""
        assert jito_client is not None
        assert jito_client._base_url == JitoClient.BASE_URL
        assert "mainnet.block-engine.jito.wtf" in jito_client._base_url

    def test_base_url_override(self):
        """Test JitoClient with custom base URL."""
        custom_url = "https://test.block-engine.jito.wtf/api/v1"
        client = JitoClient(base_url=custom_url)
        assert client._base_url == custom_url

    @pytest.mark.asyncio
    async def test_send_bundle_success(self, jito_client):
        """Test successful bundle send to Jito."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "bundle_id_123456789abcdef"
        }

        with patch.object(jito_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await jito_client.send_bundle(
                transactions=["base64_tx_1", "base64_tx_2"]
            )

        assert result == "bundle_id_123456789abcdef"

    @pytest.mark.asyncio
    async def test_send_bundle_failure(self, jito_client):
        """Test bundle send failure."""
        with patch.object(jito_client, 'post', new=AsyncMock(return_value=None)):
            result = await jito_client.send_bundle(transactions=["tx1"])

        assert result == ""

    @pytest.mark.asyncio
    async def test_send_bundle_empty_response(self, jito_client):
        """Test bundle send with empty result."""
        with patch.object(jito_client, 'post', new=AsyncMock(return_value={"result": None})):
            result = await jito_client.send_bundle(transactions=["tx1"])

        assert result == ""

    @pytest.mark.asyncio
    async def test_get_bundle_status_landed(self, jito_client):
        """Test bundle status check for landed bundle."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [
                {
                    "bundle_id": "bundle_123",
                    "status": {
                        "type": "landed",
                        "slot": 123456789
                    },
                    "confirmation_status": "confirmed"
                }
            ]
        }

        with patch.object(jito_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await jito_client.get_bundle_status("bundle_123")

        assert result["bundle_id"] == "bundle_123"
        assert result["status"] == "landed"
        assert result["slot"] == 123456789

    @pytest.mark.asyncio
    async def test_get_bundle_status_pending(self, jito_client):
        """Test bundle status check for pending bundle."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [
                {
                    "bundle_id": "bundle_456",
                    "status": {
                        "type": "pending"
                    }
                }
            ]
        }

        with patch.object(jito_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await jito_client.get_bundle_status("bundle_456")

        assert result["bundle_id"] == "bundle_456"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_bundle_status_error(self, jito_client):
        """Test bundle status check with error."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [
                {
                    "bundle_id": "bundle_789",
                    "status": {
                        "type": "failed"
                    },
                    "err": "Simulation failed"
                }
            ]
        }

        with patch.object(jito_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await jito_client.get_bundle_status("bundle_789")

        assert result["status"] == "failed"
        assert result["error"] == "Simulation failed"

    @pytest.mark.asyncio
    async def test_get_bundle_status_empty_result(self, jito_client):
        """Test bundle status with empty result."""
        with patch.object(jito_client, 'post', new=AsyncMock(return_value=None)):
            result = await jito_client.get_bundle_status("bundle_xyz")

        assert result["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_get_tip_accounts_success(self, jito_client):
        """Test getting tip accounts."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": [
                "Cw8ysy5qK8eGCvU7xqgVPzqD5v3YjnqgFQS3mYJNUStR",
                "4uvnsG27sn9Gq7L9mCfoMcfFXXLCa6i8y8KfsR5U6wL8",
            ]
        }

        with patch.object(jito_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await jito_client.get_tip_accounts()

        assert len(result) == 2
        assert "Cw8ysy5qK8eGCvU7xqgVPzqD5v3YjnqgFQS3mYJNUStR" in result

    @pytest.mark.asyncio
    async def test_get_tip_accounts_fallback(self, jito_client):
        """Test tip accounts fallback on failure."""
        with patch.object(jito_client, 'post', new=AsyncMock(return_value=None)):
            result = await jito_client.get_tip_accounts()

        assert len(result) > 0
        assert isinstance(result[0], str)

    @pytest.mark.asyncio
    async def test_estimate_tip_low(self, jito_client):
        """Test tip estimation for low priority."""
        result = await jito_client.estimate_tip("low")
        assert result == 1000

    @pytest.mark.asyncio
    async def test_estimate_tip_medium(self, jito_client):
        """Test tip estimation for medium priority."""
        result = await jito_client.estimate_tip("medium")
        assert result == 10000

    @pytest.mark.asyncio
    async def test_estimate_tip_high(self, jito_client):
        """Test tip estimation for high priority."""
        result = await jito_client.estimate_tip("high")
        assert result == 100000

    @pytest.mark.asyncio
    async def test_estimate_tip_unknown_defaults_medium(self, jito_client):
        """Test tip estimation defaults to medium for unknown priority."""
        result = await jito_client.estimate_tip("invalid_priority")
        assert result == 10000  # medium


# ---------------------------------------------------------------------------
# FlashbotsClient Tests
# ---------------------------------------------------------------------------

class TestFlashbotsClient:
    """Tests for FlashbotsClient (EVM MEV protection)."""

    def test_initialization(self, flashbots_client):
        """Test FlashbotsClient initialization."""
        assert flashbots_client is not None
        assert flashbots_client._base_url == FlashbotsClient.BASE_URL
        assert flashbots_client._signing_key is not None

    def test_base_url_override(self):
        """Test FlashbotsClient with custom base URL."""
        custom_url = "https://test.relay.flashbots.net"
        client = FlashbotsClient(base_url=custom_url)
        assert client._base_url == custom_url

    def test_headers_generation(self, flashbots_client):
        """Test X-Flashbots-Signature header generation."""
        body_hash = "0xabc123"
        headers = flashbots_client._get_headers(body_hash)

        assert "Content-Type" in headers
        assert "X-Flashbots-Signature" in headers
        assert headers["X-Flashbots-Signature"] == f"{flashbots_client._signing_key}:{body_hash}"

    def test_headers_no_key(self):
        """Test headers with no signing key."""
        client = FlashbotsClient(signing_key=None)
        headers = client._get_headers("0xabc")

        assert headers["X-Flashbots-Signature"] == ""

    @pytest.mark.asyncio
    async def test_send_bundle_success(self, flashbots_client):
        """Test successful bundle send to Flashbots."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0xbundle_hash_123456789"
        }

        with patch.object(flashbots_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await flashbots_client.send_bundle(
                signed_txs=["0x_signed_tx1", "0x_signed_tx2"],
                target_block=18000000
            )

        assert result == "0xbundle_hash_123456789"

    @pytest.mark.asyncio
    async def test_send_bundle_failure(self, flashbots_client):
        """Test bundle send failure."""
        with patch.object(flashbots_client, 'post', new=AsyncMock(return_value=None)):
            result = await flashbots_client.send_bundle(
                signed_txs=["0x_tx"],
                target_block=18000000
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_send_bundle_custom_block_range(self, flashbots_client):
        """Test bundle send with custom block range."""
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": "0xbundle"}

        with patch.object(flashbots_client, 'post', new=AsyncMock(return_value=mock_response)) as mock_post:
            await flashbots_client.send_bundle(
                signed_txs=["0x_tx"],
                target_block=18000000,
                min_block_number=18000001,
                max_block_number=18000010
            )

            # Verify the payload was constructed correctly
            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["params"][0]["blockNumber"] == hex(18000000)
            assert payload["method"] == "eth_sendBundle"

    @pytest.mark.asyncio
    async def test_get_bundle_stats_success(self, flashbots_client):
        """Test getting bundle statistics."""
        mock_response = {
            "isHighPriority": True,
            "Simulated": {"gasUsed": 150000},
            "Sealed": True,
            "恭敬": {"blockNumber": 18000001}
        }

        with patch.object(flashbots_client, 'get', new=AsyncMock(return_value=mock_response)):
            result = await flashbots_client.get_bundle_stats("0xbundle_hash")

        assert result["is_high_priority"] is True
        assert result["sealed"] is True
        assert result["simulated"]["gasUsed"] == 150000

    @pytest.mark.asyncio
    async def test_get_bundle_stats_failure(self, flashbots_client):
        """Test getting bundle stats with failure."""
        with patch.object(flashbots_client, 'get', new=AsyncMock(return_value=None)):
            result = await flashbots_client.get_bundle_stats("0xbundle_hash")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, flashbots_client):
        """Test getting user reputation stats."""
        mock_response = {
            "address": "0x123abc",
            "totalEscrowed": "1000000000000000000",
            "pendingEscrowed": "500000000000000000",
            "reputation": 100,
            "blocksBuilt": 50,
            "bundlesSubmitted": 200
        }

        with patch.object(flashbots_client, 'get', new=AsyncMock(return_value=mock_response)):
            result = await flashbots_client.get_user_stats("0x123abc")

        assert result["reputation"] == 100
        assert result["blocks_built"] == 50
        assert result["total_escrowed"] == "1000000000000000000"

    @pytest.mark.asyncio
    async def test_get_user_stats_failure(self, flashbots_client):
        """Test getting user stats with failure."""
        with patch.object(flashbots_client, 'get', new=AsyncMock(return_value=None)):
            result = await flashbots_client.get_user_stats("0x123abc")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_simulate_bundle_success(self, flashbots_client):
        """Test successful bundle simulation."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "success": True,
                "stateDiff": {},
                "gasUsed": 145000,
                "logs": []
            }
        }

        with patch.object(flashbots_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await flashbots_client.simulate_bundle(
                signed_txs=["0x_signed_tx"],
                block_number=18000000
            )

        assert result["success"] is True
        assert result["gas_used"] == 145000

    @pytest.mark.asyncio
    async def test_simulate_bundle_with_error(self, flashbots_client):
        """Test bundle simulation with error."""
        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "error": "Execution reverted"
            }
        }

        with patch.object(flashbots_client, 'post', new=AsyncMock(return_value=mock_response)):
            result = await flashbots_client.simulate_bundle(
                signed_txs=["0x_signed_tx"],
                block_number=18000000
            )

        assert result["success"] is False
        assert "Execution reverted" in result["error"]

    @pytest.mark.asyncio
    async def test_simulate_bundle_failure(self, flashbots_client):
        """Test bundle simulation failure."""
        with patch.object(flashbots_client, 'post', new=AsyncMock(return_value=None)):
            result = await flashbots_client.simulate_bundle(
                signed_txs=["0x_tx"],
                block_number=18000000
            )

        assert result["success"] is False


# ---------------------------------------------------------------------------
# SwapExecutor MEV Integration Tests
# ---------------------------------------------------------------------------

class TestSwapExecutorMEVIntegration:
    """Tests for MEV integration in SwapExecutor."""

    @pytest.fixture
    def mock_jito_client(self):
        """Create a mock Jito client."""
        client = MagicMock(spec=JitoClient)
        client.send_bundle = AsyncMock(return_value="jito_bundle_123")
        client.get_bundle_status = AsyncMock(return_value={"status": "pending"})
        client.get_tip_accounts = AsyncMock(return_value=["tip_account_1", "tip_account_2"])
        client.estimate_tip = AsyncMock(return_value=10000)
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def mock_flashbots_client(self):
        """Create a mock Flashbots client."""
        client = MagicMock(spec=FlashbotsClient)
        client.send_bundle = AsyncMock(return_value="flashbots_bundle_456")
        client.get_bundle_stats = AsyncMock(return_value={"is_high_priority": True})
        client.simulate_bundle = AsyncMock(return_value={"success": True})
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def swap_executor_with_mev(self, mock_jito_client, mock_flashbots_client):
        """Create a SwapExecutor with MEV clients."""
        return SwapExecutor(
            jito_client=mock_jito_client,
            flashbots_client=mock_flashbots_client
        )

    def test_swap_executor_initialization_with_mev(
        self, mock_jito_client, mock_flashbots_client
    ):
        """Test SwapExecutor initialization with MEV clients."""
        executor = SwapExecutor(
            jito_client=mock_jito_client,
            flashbots_client=mock_flashbots_client
        )

        assert executor.jito is mock_jito_client
        assert executor.flashbots is mock_flashbots_client

    def test_swap_executor_initialization_without_mev(self):
        """Test SwapExecutor works without MEV clients."""
        executor = SwapExecutor()
        assert executor.jito is None
        assert executor.flashbots is None

    @pytest.mark.asyncio
    async def test_close_closes_mev_clients(self, swap_executor_with_mev, mock_jito_client, mock_flashbots_client):
        """Test that close() also closes MEV clients."""
        await swap_executor_with_mev.close()

        mock_jito_client.close.assert_called_once()
        mock_flashbots_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_swap_solana_with_mev_protection(
        self,
        swap_executor_with_mev,
        mock_jito_client,
        mock_swap_quote_solana
    ):
        """Test Solana swap with MEV protection enabled."""
        mock_keypair = MagicMock()
        mock_keypair.pubkey.return_value = "TestWallet123"

        # Mock the Jupiter swap transaction response
        swap_tx_data = {
            "transactions": ["base64_tx_1", "base64_tx_2"],
            "lastValidBlockHeight": 123456789
        }

        with patch.object(
            swap_executor_with_mev.jupiter,
            'get_swap_transaction',
            new=AsyncMock(return_value=swap_tx_data)
        ):
            result = await swap_executor_with_mev.execute_swap_solana(
                quote=mock_swap_quote_solana,
                wallet_keypair=mock_keypair,
                simulate_only=True,
                use_mev_protection=True
            )

        # Verify Jito was called
        mock_jito_client.send_bundle.assert_called_once_with(
            ["base64_tx_1", "base64_tx_2"]
        )

        assert result.success is True
        assert result.provider == "jupiter"

    @pytest.mark.asyncio
    async def test_execute_swap_solana_without_mev_protection(
        self,
        swap_executor_with_mev,
        mock_jito_client,
        mock_swap_quote_solana
    ):
        """Test Solana swap without MEV protection."""
        mock_keypair = MagicMock()
        mock_keypair.pubkey.return_value = "TestWallet123"

        swap_tx_data = {"transactions": ["base64_tx_1"]}

        with patch.object(
            swap_executor_with_mev.jupiter,
            'get_swap_transaction',
            new=AsyncMock(return_value=swap_tx_data)
        ):
            result = await swap_executor_with_mev.execute_swap_solana(
                quote=mock_swap_quote_solana,
                wallet_keypair=mock_keypair,
                simulate_only=True,
                use_mev_protection=False
            )

        # Jito should not be called
        mock_jito_client.send_bundle.assert_not_called()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_swap_solana_mev_without_jito_client(
        self,
        swap_executor_with_mev,
        mock_swap_quote_solana
    ):
        """Test Solana swap with MEV requested but no Jito client configured."""
        # Remove jito client
        swap_executor_with_mev.jito = None

        mock_keypair = MagicMock()
        mock_keypair.pubkey.return_value = "TestWallet123"

        swap_tx_data = {"transactions": ["base64_tx_1"]}

        with patch.object(
            swap_executor_with_mev.jupiter,
            'get_swap_transaction',
            new=AsyncMock(return_value=swap_tx_data)
        ):
            result = await swap_executor_with_mev.execute_swap_solana(
                quote=mock_swap_quote_solana,
                wallet_keypair=mock_keypair,
                simulate_only=True,
                use_mev_protection=True
            )

        # Should still succeed, just without MEV protection
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_swap_evm_with_mev_protection(
        self,
        swap_executor_with_mev,
        mock_flashbots_client,
        mock_swap_quote_evm
    ):
        """Test EVM swap with MEV protection enabled."""
        # Mock the oneinch client since it's None by default
        mock_oneinch = MagicMock()
        mock_oneinch.get_swap = AsyncMock(return_value={
            "tx": {"data": "0x_signed_calldata"},
            "routerAddress": "0x1111111254EEB25477B68fb85Ed929f73A960582"
        })
        swap_executor_with_mev.oneinch = mock_oneinch

        result = await swap_executor_with_mev.execute_swap_evm(
            quote=mock_swap_quote_evm,
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f5fCAb",
            simulate_only=False,
            use_mev_protection=True
        )

        # Verify Flashbots was attempted
        mock_flashbots_client.send_bundle.assert_called_once()

        assert result.success is True
        assert result.provider == "1inch"

    @pytest.mark.asyncio
    async def test_execute_swap_evm_without_mev_protection(
        self,
        swap_executor_with_mev,
        mock_flashbots_client,
        mock_swap_quote_evm
    ):
        """Test EVM swap without MEV protection."""
        # Mock the oneinch client since it's None by default
        mock_oneinch = MagicMock()
        mock_oneinch.get_swap = AsyncMock(return_value={
            "tx": {"data": "0x_signed_calldata"},
            "routerAddress": "0x1111111254EEB25477B68fb85Ed929f73A960582"
        })
        swap_executor_with_mev.oneinch = mock_oneinch

        result = await swap_executor_with_mev.execute_swap_evm(
            quote=mock_swap_quote_evm,
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f5fCAb",
            simulate_only=False,
            use_mev_protection=False
        )

        # Flashbots should not be called
        mock_flashbots_client.send_bundle.assert_not_called()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_swap_evm_mev_without_flashbots_client(
        self,
        swap_executor_with_mev,
        mock_swap_quote_evm
    ):
        """Test EVM swap with MEV requested but no Flashbots client."""
        # Remove flashbots client
        swap_executor_with_mev.flashbots = None

        # Mock the oneinch client since it's None by default
        mock_oneinch = MagicMock()
        mock_oneinch.get_swap = AsyncMock(return_value={
            "tx": {"data": "0x_signed_calldata"},
            "routerAddress": "0x1111111254EEB25477B68fb85Ed929f73A960582"
        })
        swap_executor_with_mev.oneinch = mock_oneinch

        result = await swap_executor_with_mev.execute_swap_evm(
            quote=mock_swap_quote_evm,
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f5fCAb",
            simulate_only=False,
            use_mev_protection=True
        )

        # Should still succeed, just without MEV protection
        assert result.success is True


# ---------------------------------------------------------------------------
# MEV Module Import Tests
# ---------------------------------------------------------------------------

class TestMEVModuleImports:
    """Test that MEV module imports work correctly."""

    def test_jito_client_import(self):
        """Test JitoClient can be imported."""
        from borg.defi.mev import JitoClient
        assert JitoClient is not None

    def test_flashbots_client_import(self):
        """Test FlashbotsClient can be imported."""
        from borg.defi.mev import FlashbotsClient
        assert FlashbotsClient is not None

    def test_mev_module_exports(self):
        """Test MEV module exports are correct."""
        from borg.defi.mev import JitoClient, FlashbotsClient
        from borg.defi.mev import __all__

        assert "JitoClient" in __all__
        assert "FlashbotsClient" in __all__
        assert len(__all__) == 2
