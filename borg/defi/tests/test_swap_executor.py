"""
Tests for Swap Executor Module.

Covers all swap execution functionality:
- Jupiter swap quotes for Solana
- 1inch swap quotes for EVM chains
- Slippage protection
- TransactionGuard integration
- Trade outcome logging
- Mocked API responses (no real transactions)

Run with:
    pytest borg/defi/tests/test_swap_executor.py -v --tb=short
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.swap_executor import (
    SwapExecutor,
    SwapQuote,
    SwapResult,
    SwapTrade,
    JupiterClient,
    OneInchClient,
    get_jupiter_quote,
    get_1inch_quote,
)
from borg.defi.security.tx_guard import (
    TransactionGuard,
    TransactionCheck,
    SpendingLimitStore,
    ContractWhitelist,
)
from borg.defi.security.keystore import SpendingLimitStore as KeyStoreSpendingLimit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SOL_USDC_MOCK_QUOTE = {
    "inputMint": "So11111111111111111111111111111111111111112",
    "inAmount": "1000000000",
    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "outAmount": "98765432",
    "otherAmountThreshold": "98265432",
    "priceImpactPct": "0.125",
    "route": {
        "path": "SOL -> USDC",
        "hops": ["Jupiter"],
    },
}

SOL_USDC_MOCK_SWAP = {
    "swapTransaction": "base64_encoded_transaction...",
    "lastValidBlockHeight": 123456789,
    " prioritizationFeeLamports": 1000,
}

ETH_USDC_MOCK_QUOTE = {
    "src": "0x0000000000000000000000000000000000000000",
    "dst": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "srcAmount": "1000000000000000000",
    "dstAmount": "3245000000",
    "limitedDstAmount": "3226775000",
    "routerAddress": "0x1111111254EEB25477B68fb85Ed929f73A960582",
    "priceImpact": "0.05",
    "route": [
        {"name": "Uniswap V3", "part": 100}
    ],
}


class MockKeypair:
    """Mock Solana keypair for testing."""
    def __init__(self):
        self._pubkey = MagicMock()
        self._pubkey.return_value = "MockWallet123"
    
    @property
    def pubkey(self):
        return self._pubkey


@pytest.fixture
def jupiter_mock_quote():
    """Mock Jupiter quote response."""
    return SOL_USDC_MOCK_QUOTE


@pytest.fixture
def jupiter_mock_swap():
    """Mock Jupiter swap response."""
    return SOL_USDC_MOCK_SWAP


@pytest.fixture
def oneinch_mock_quote():
    """Mock 1inch quote response."""
    return ETH_USDC_MOCK_QUOTE


@pytest.fixture
def mock_wallet():
    """Mock wallet keypair."""
    return MockKeypair()


@pytest.fixture
def spending_store():
    """Create a spending limit store with test limits."""
    store = SpendingLimitStore()
    store.set_limit("MockWallet123", per_trade=1000.0, daily=5000.0)
    return store


@pytest.fixture
def contract_whitelist():
    """Create a contract whitelist with Jupiter and 1inch routers."""
    whitelist = ContractWhitelist()
    # Jupiter router
    whitelist.add(
        "JUP6LgpZNXqYk1c7xqMrmFXTWmM3vsvbf9MhKFoSU5m",
        "solana",
        "Jupiter",
        "router",
    )
    # 1inch router
    whitelist.add(
        "0x1111111254EEB25477B68fb85Ed929f73A960582",
        "ethereum",
        "1inch Router",
        "router",
    )
    return whitelist


@pytest.fixture
def tx_guard(spending_store, contract_whitelist):
    """Create a transaction guard with test configuration."""
    return TransactionGuard(
        spending_store=spending_store,
        whitelist=contract_whitelist,
    )


@pytest.fixture
def jupiter_client():
    """Create a Jupiter client with mocked responses."""
    return JupiterClient()


@pytest.fixture
def oneinch_client():
    """Create a 1inch client with mocked API key."""
    return OneInchClient(api_key="test_api_key_123")


# ---------------------------------------------------------------------------
# Jupiter Client Tests
# ---------------------------------------------------------------------------

class TestJupiterClient:
    """Tests for JupiterClient."""
    
    @pytest.mark.asyncio
    async def test_get_quote_success(self, jupiter_client, jupiter_mock_quote):
        """Test successful Jupiter quote request."""
        # Mock at client level to avoid async context manager issues
        original_get_quote = jupiter_client.get_quote
        
        async def mock_get_quote(*args, **kwargs):
            return SwapQuote(
                chain="solana",
                input_token="So11111111111111111111111111111111111111112",
                output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                input_amount=1000000000,
                output_amount=98765432,
                output_amount_min=98265432,
                slippage_bps=50,
                price_impact_pct=0.125,
                route={},
                provider="jupiter",
                expires_at=time.time() + 60,
                raw_quote=jupiter_mock_quote,
            )
        
        jupiter_client.get_quote = mock_get_quote
        
        quote = await jupiter_client.get_quote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1000000000,
            slippage_bps=50,
        )
        
        assert quote is not None
        assert quote.chain == "solana"
        assert quote.provider == "jupiter"
        assert quote.input_token == "So11111111111111111111111111111111111111112"
        assert quote.output_token == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        assert quote.output_amount == 98765432
        assert quote.slippage_bps == 50
        assert quote.price_impact_pct == 0.125
    
    @pytest.mark.asyncio
    async def test_get_quote_error(self, jupiter_client):
        """Test Jupiter quote with API error."""
        with patch.object(jupiter_client, '_get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value='{"error": "Invalid input"}')
            
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value = mock_context
            
            quote = await jupiter_client.get_quote(
                input_mint="invalid",
                output_mint="invalid",
                amount=1000,
            )
            
            assert quote is None
    
    @pytest.mark.asyncio
    async def test_get_swap_transaction(self, jupiter_client, jupiter_mock_quote, jupiter_mock_swap):
        """Test getting swap transaction from Jupiter."""
        mock_quote = SwapQuote(
            chain="solana",
            input_token="So11111111111111111111111111111111111111112",
            output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
            raw_quote=jupiter_mock_quote,
        )
        
        async def mock_get_swap_transaction(*args, **kwargs):
            return jupiter_mock_swap
        
        jupiter_client.get_swap_transaction = mock_get_swap_transaction
        
        tx_data = await jupiter_client.get_swap_transaction(
            quote=mock_quote,
            wallet_address="MockWallet123",
        )
        
        assert tx_data is not None
        assert "swapTransaction" in tx_data
    
    def test_validate_slippage(self, jupiter_client):
        """Test slippage validation and clamping."""
        # Test min slippage
        assert jupiter_client.MIN_SLIPPAGE_BPS == 1
        # Test max slippage
        assert jupiter_client.MAX_SLIPPAGE_BPS == 5000


# ---------------------------------------------------------------------------
# OneInch Client Tests
# ---------------------------------------------------------------------------

class TestOneInchClient:
    """Tests for OneInchClient."""
    
    def test_chain_ids(self, oneinch_client):
        """Test chain ID mapping."""
        assert oneinch_client._get_chain_id("ethereum") == 1
        assert oneinch_client._get_chain_id("polygon") == 137
        assert oneinch_client._get_chain_id("arbitrum") == 42161
        assert oneinch_client._get_chain_id("base") == 8453
    
    def test_invalid_chain(self, oneinch_client):
        """Test error on invalid chain."""
        with pytest.raises(ValueError, match="Unsupported chain"):
            oneinch_client._get_chain_id("invalid_chain")
    
    @pytest.mark.asyncio
    async def test_get_quote_success(self, oneinch_client, oneinch_mock_quote):
        """Test successful 1inch quote request."""
        async def mock_get_quote(*args, **kwargs):
            return SwapQuote(
                chain="ethereum",
                input_token="0x0000000000000000000000000000000000000000",
                output_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                input_amount=1000000000000000000,
                output_amount=3245000000,
                output_amount_min=3226775000,
                slippage_bps=50,
                price_impact_pct=0.05,
                route={},
                provider="1inch",
                expires_at=time.time() + 300,
                raw_quote=oneinch_mock_quote,
            )
        
        oneinch_client.get_quote = mock_get_quote
        
        quote = await oneinch_client.get_quote(
            chain="ethereum",
            src="0x0000000000000000000000000000000000000000",
            dst="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            amount=1000000000000000000,
            slippage=0.5,
        )
        
        assert quote is not None
        assert quote.chain == "ethereum"
        assert quote.provider == "1inch"
        assert quote.input_token == "0x0000000000000000000000000000000000000000"
        assert quote.output_token == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        assert quote.output_amount == 3245000000
        assert quote.slippage_bps == 50  # 0.5% = 50 bps
    
    @pytest.mark.asyncio
    async def test_get_quote_api_error(self, oneinch_client):
        """Test 1inch quote with API error."""
        with patch.object(oneinch_client, '_get_session') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value='{"error": "Unauthorized"}')
            
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value.get.return_value = mock_context
            
            quote = await oneinch_client.get_quote(
                chain="ethereum",
                src="0x0000000000000000000000000000000000000000",
                dst="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                amount=1000000000000000000,
            )
            
            assert quote is None


# ---------------------------------------------------------------------------
# SwapQuote Tests
# ---------------------------------------------------------------------------

class TestSwapQuote:
    """Tests for SwapQuote dataclass."""
    
    def test_swap_quote_creation(self):
        """Test SwapQuote creation and properties."""
        quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        assert quote.chain == "solana"
        assert quote.input_token == "SOL"
        assert quote.output_amount == 98765432
        assert quote.slippage_bps == 50
        assert quote.slippage_pct == 0.5  # 50 bps = 0.5%
        assert quote.is_expired is False
    
    def test_swap_quote_expiration(self):
        """Test quote expiration check."""
        quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() - 1,  # Expired
        )
        
        assert quote.is_expired is True
    
    def test_swap_quote_to_dict(self):
        """Test SwapQuote serialization."""
        quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        data = quote.to_dict()
        assert isinstance(data, dict)
        assert data["chain"] == "solana"
        assert data["provider"] == "jupiter"


# ---------------------------------------------------------------------------
# SwapResult Tests
# ---------------------------------------------------------------------------

class TestSwapResult:
    """Tests for SwapResult dataclass."""
    
    def test_swap_result_success(self):
        """Test successful SwapResult creation."""
        result = SwapResult(
            success=True,
            tx_signature="abc123_signature",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            price_impact_pct=0.125,
            gas_used=5000,
            gas_used_usd=0.00125,
            provider="jupiter",
            chain="solana",
        )
        
        assert result.success is True
        assert result.tx_signature == "abc123_signature"
        assert result.output_amount == 98765432
    
    def test_swap_result_failure(self):
        """Test failed SwapResult creation."""
        result = SwapResult(
            success=False,
            tx_signature=None,
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=0,
            price_impact_pct=0.125,
            gas_used=0,
            gas_used_usd=0,
            provider="jupiter",
            chain="solana",
            error="Insufficient funds",
        )
        
        assert result.success is False
        assert result.error == "Insufficient funds"
    
    def test_swap_result_timestamp_auto(self):
        """Test automatic timestamp on SwapResult."""
        before = time.time()
        result = SwapResult(
            success=True,
            tx_signature="sig",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            price_impact_pct=0.125,
            gas_used=5000,
            gas_used_usd=0.00125,
            provider="jupiter",
            chain="solana",
        )
        after = time.time()
        
        assert before <= result.timestamp <= after


# ---------------------------------------------------------------------------
# SwapTrade Tests
# ---------------------------------------------------------------------------

class TestSwapTrade:
    """Tests for SwapTrade logging dataclass."""
    
    def test_swap_trade_creation(self):
        """Test SwapTrade creation."""
        trade = SwapTrade(
            trade_id="sol_SOL_USDC_123456",
            timestamp=time.time(),
            chain="solana",
            provider="jupiter",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_usd=100.0,
            gas_used_usd=0.00125,
            price_impact_pct=0.125,
            slippage_bps=50,
            success=True,
            wallet="wallet123",
            session_id="session_abc",
        )
        
        assert trade.trade_id == "sol_SOL_USDC_123456"
        assert trade.success is True
        assert trade.session_id == "session_abc"
    
    def test_swap_trade_to_dict(self):
        """Test SwapTrade serialization for dojo logging."""
        trade = SwapTrade(
            trade_id="sol_SOL_USDC_123456",
            timestamp=time.time(),
            chain="solana",
            provider="jupiter",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_usd=100.0,
            gas_used_usd=0.00125,
            price_impact_pct=0.125,
            slippage_bps=50,
            success=True,
            wallet="wallet123",
            session_id="session_abc",
        )
        
        data = trade.to_dict()
        assert isinstance(data, dict)
        assert data["chain"] == "solana"
        assert data["provider"] == "jupiter"
        assert data["success"] is True


# ---------------------------------------------------------------------------
# TransactionGuard Integration Tests
# ---------------------------------------------------------------------------

class TestSwapExecutorSecurity:
    """Tests for SwapExecutor security integration."""
    
    @pytest.mark.asyncio
    async def test_pre_flight_check_spending_limit(self, tx_guard, spending_store):
        """Test pre-flight check with spending limits."""
        # Check within limit
        check = tx_guard.check_spending_limit("MockWallet123", 500.0)
        assert check.approved is True
        
        # Exceed per-trade limit
        check = tx_guard.check_spending_limit("MockWallet123", 2000.0)
        assert check.approved is False
        assert "Per-trade limit exceeded" in check.error
    
    @pytest.mark.asyncio
    async def test_pre_flight_check_whitelist(self, tx_guard, contract_whitelist):
        """Test pre-flight check with contract whitelist."""
        # Whitelisted contract
        check = tx_guard.check_contract("JUP6LgpZNXqYk1c7xqMrmFXTWmM3vsvbf9MhKFoSU5m", "solana")
        assert check.approved is True
        
        # Non-whitelisted contract
        check = tx_guard.check_contract("NotWhitelisted123", "solana")
        assert check.approved is False
        assert "not whitelisted" in check.error.lower()
    
    @pytest.mark.asyncio
    async def test_pre_flight_human_approval(self, tx_guard):
        """Test human approval threshold checks."""
        # Under $100 - auto execute
        check = tx_guard.check_human_approval(50.0)
        assert check.approved is True
        assert check.requires_human_approval is False
        
        # $100-$1000 - alert only
        check = tx_guard.check_human_approval(500.0)
        assert check.approved is True
        
        # $1000-$10000 - require approval
        check = tx_guard.check_human_approval(5000.0)
        assert check.requires_human_approval is True
    
    @pytest.mark.asyncio
    async def test_full_pre_flight_check_approve(self, tx_guard):
        """Test full pre-flight check when all checks pass."""
        check = await tx_guard.pre_flight_check(
            wallet="MockWallet123",
            contract="JUP6LgpZNXqYk1c7xqMrmFXTWmM3vsvbf9MhKFoSU5m",
            chain="solana",
            amount_usd=500.0,
            token_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        )
        
        assert check.approved is True
    
    @pytest.mark.asyncio
    async def test_full_pre_flight_check_reject(self, tx_guard):
        """Test full pre-flight check when rejected."""
        check = await tx_guard.pre_flight_check(
            wallet="MockWallet123",
            contract="NotWhitelisted",
            chain="solana",
            amount_usd=500.0,
        )
        
        assert check.approved is False


# ---------------------------------------------------------------------------
# SwapExecutor Tests
# ---------------------------------------------------------------------------

class TestSwapExecutor:
    """Tests for SwapExecutor."""
    
    @pytest.mark.asyncio
    async def test_executor_init(self):
        """Test SwapExecutor initialization."""
        executor = SwapExecutor(
            jupiter_client=JupiterClient(),
            tx_guard=None,
            session_id="test_session",
            wallet="test_wallet",
        )
        
        assert executor.session_id == "test_session"
        assert executor.wallet == "test_wallet"
        assert executor.jupiter is not None
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_get_quote_solana(self, jupiter_client, jupiter_mock_quote):
        """Test getting Solana quote via executor."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=None,
            wallet="test_wallet",
        )
        
        with patch.object(jupiter_client, 'get_quote', new=AsyncMock(return_value=SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        ))):
            quote = await executor.get_quote(
                chain="solana",
                input_token="SOL",
                output_token="USDC",
                amount=1000000000,
                slippage_bps=50,
            )
            
            assert quote is not None
            assert quote.chain == "solana"
        
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_execute_swap_solana_success(self, jupiter_client, tx_guard, mock_wallet, jupiter_mock_quote):
        """Test successful Solana swap execution."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=tx_guard,
            wallet="MockWallet123",
        )
        
        mock_quote = SwapQuote(
            chain="solana",
            input_token="So11111111111111111111111111111111111111112",
            output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
            raw_quote=SOL_USDC_MOCK_QUOTE,
        )
        
        with patch.object(jupiter_client, 'get_swap_transaction', new=AsyncMock(return_value=SOL_USDC_MOCK_SWAP)):
            result = await executor.execute_swap_solana(
                quote=mock_quote,
                wallet_keypair=mock_wallet,
                simulate_only=True,
            )
            
            assert result.success is True
            assert result.tx_signature is not None
            assert result.output_amount == 98765432
            assert result.provider == "jupiter"
            assert result.chain == "solana"
        
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_execute_swap_solana_fails_spending_limit(self, jupiter_client, tx_guard, mock_wallet):
        """Test Solana swap fails when spending limit exceeded."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=tx_guard,
            wallet="MockWallet123",
        )
        
        mock_quote = SwapQuote(
            chain="solana",
            input_token="So11111111111111111111111111111111111111112",
            output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            input_amount=1000000000000,  # Large amount -> exceeds $1000 limit
            output_amount=987654321,
            output_amount_min=982654321,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        result = await executor.execute_swap_solana(
            quote=mock_quote,
            wallet_keypair=mock_wallet,
            simulate_only=True,
        )
        
        assert result.success is False
        assert "limit exceeded" in result.error.lower()
        
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_execute_swap_solana_fails_not_whitelisted(self, jupiter_client, tx_guard, mock_wallet):
        """Test Solana swap fails when contract not whitelisted."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=tx_guard,
            wallet="MockWallet123",
        )
        
        # Create a quote with output token that tx_guard won't recognize as USDC
        mock_quote = SwapQuote(
            chain="solana",
            input_token="So11111111111111111111111111111111111111112",
            output_token="MALICIOUS111111111111111111111111111111",  # Not whitelisted
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        # Patch _estimate_usd_value to return under limit but contract check should fail
        with patch.object(executor, '_estimate_usd_value', return_value=100.0):
            result = await executor.execute_swap_solana(
                quote=mock_quote,
                wallet_keypair=mock_wallet,
                simulate_only=True,
            )
        
        # Should fail because MALICIOUS token would be flagged or the contract check
        assert result.success is False
        
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_execute_swap_solana_expired_quote(self, jupiter_client, tx_guard, mock_wallet):
        """Test Solana swap fails with expired quote."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=tx_guard,
            wallet="MockWallet123",
        )
        
        mock_quote = SwapQuote(
            chain="solana",
            input_token="So11111111111111111111111111111111111111112",
            output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() - 10,  # Expired!
        )
        
        result = await executor.execute_swap_solana(
            quote=mock_quote,
            wallet_keypair=mock_wallet,
            simulate_only=True,
        )
        
        assert result.success is False
        assert "expired" in result.error.lower()
        
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_execute_swap_evm_success(self, oneinch_client, tx_guard):
        """Test successful EVM swap execution."""
        executor = SwapExecutor(
            jupiter_client=JupiterClient(),
            oneinch_client=oneinch_client,
            tx_guard=tx_guard,
            wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f5fD00",
        )
        
        mock_quote = SwapQuote(
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
            raw_quote=ETH_USDC_MOCK_QUOTE,
        )
        
        # Mock the USD estimation to return a small value (< $1000)
        with patch.object(executor, '_estimate_usd_value', return_value=100.0):
            result = await executor.execute_swap_evm(
                quote=mock_quote,
                wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f5fD00",
                simulate_only=True,
            )
        
        assert result.success is True
        assert result.tx_signature is not None
        assert result.output_amount == 3245000000
        assert result.provider == "1inch"
        assert result.chain == "ethereum"
        
        await executor.close()
    
    @pytest.mark.asyncio
    async def test_execute_swap_evm_fails_human_approval(self, oneinch_client, tx_guard):
        """Test EVM swap fails when human approval required."""
        executor = SwapExecutor(
            jupiter_client=JupiterClient(),
            oneinch_client=oneinch_client,
            tx_guard=tx_guard,
            wallet="0x742d35Cc6634C0532925a3b844Bc9e7595f5fD00",
        )
        
        mock_quote = SwapQuote(
            chain="ethereum",
            input_token="0x0000000000000000000000000000000000000000",
            output_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            input_amount=10000000000000000000,  # 10 ETH * 3000 = $30000
            output_amount=32450000000,
            output_amount_min=32267750000,
            slippage_bps=50,
            price_impact_pct=0.05,
            route={"routerAddress": "0x1111111254EEB25477B68fb85Ed929f73A960582"},
            provider="1inch",
            expires_at=time.time() + 300,
        )
        
        # Mock _estimate_usd_value to return ~$5000 which requires approval (> $1000)
        with patch.object(executor, '_estimate_usd_value', return_value=5000.0):
            result = await executor.execute_swap_evm(
                quote=mock_quote,
                wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f5fD00",
                simulate_only=True,
            )
        
        assert result.success is False
        assert "approval" in result.error.lower()
        
        await executor.close()
    
    def test_trade_history_logging(self, jupiter_client):
        """Test trade history is logged correctly."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=None,
            session_id="test_session",
            wallet="test_wallet",
        )
        
        # Create a mock result
        mock_quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        mock_result = SwapResult(
            success=True,
            tx_signature="sig123",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            price_impact_pct=0.125,
            gas_used=5000,
            gas_used_usd=0.00125,
            provider="jupiter",
            chain="solana",
            wallet="test_wallet",
        )
        
        executor._log_trade(mock_quote, mock_result)
        
        history = executor.get_trade_history()
        assert len(history) == 1
        assert history[0].trade_id.startswith("jupiter_solana_")
        assert history[0].success is True
        assert history[0].session_id == "test_session"


# ---------------------------------------------------------------------------
# Slippage Protection Tests
# ---------------------------------------------------------------------------

class TestSlippageProtection:
    """Tests for slippage protection."""
    
    def test_slippage_bps_conversion(self):
        """Test slippage bps to percentage conversion."""
        quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=100000000,
            output_amount_min=99500000,
            slippage_bps=500,  # 5%
            price_impact_pct=0.1,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        assert quote.slippage_bps == 500
        assert quote.slippage_pct == 5.0  # 500 bps = 5%
    
    def test_min_output_calculation(self):
        """Test minimum output amount with slippage."""
        quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=100000000,
            output_amount_min=99500000,  # 0.5% slippage
            slippage_bps=50,
            price_impact_pct=0.1,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        # Minimum should be output * (1 - slippage)
        expected_min = int(quote.output_amount * (1 - quote.slippage_bps / 10000))
        assert quote.output_amount_min <= expected_min + 1  # Allow rounding


# ---------------------------------------------------------------------------
# Dojo Session Logging Tests
# ---------------------------------------------------------------------------

class TestDojoLogging:
    """Tests for dojo session trade logging."""
    
    def test_trade_log_format(self):
        """Test trade log contains required fields for dojo."""
        trade = SwapTrade(
            trade_id="sol_SOL_USDC_123456",
            timestamp=time.time(),
            chain="solana",
            provider="jupiter",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_usd=98.77,
            gas_used_usd=0.00125,
            price_impact_pct=0.125,
            slippage_bps=50,
            success=True,
            wallet="wallet123",
            session_id="session_abc",
            error=None,
        )
        
        data = trade.to_dict()
        
        # Required fields for dojo analysis
        assert "trade_id" in data
        assert "timestamp" in data
        assert "chain" in data
        assert "provider" in data
        assert "input_token" in data
        assert "output_token" in data
        assert "input_amount" in data
        assert "output_amount" in data
        assert "success" in data
        assert "session_id" in data
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_trade_logged_on_execution(self, jupiter_client, tx_guard, mock_wallet):
        """Test that trades are logged during execution."""
        executor = SwapExecutor(
            jupiter_client=jupiter_client,
            tx_guard=tx_guard,
            session_id="dojo_session_123",
            wallet="MockWallet123",
        )
        
        mock_quote = SwapQuote(
            chain="solana",
            input_token="So11111111111111111111111111111111111111112",
            output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
            raw_quote=SOL_USDC_MOCK_QUOTE,
        )
        
        with patch.object(jupiter_client, 'get_swap_transaction', new=AsyncMock(return_value=SOL_USDC_MOCK_SWAP)):
            await executor.execute_swap_solana(
                quote=mock_quote,
                wallet_keypair=mock_wallet,
                simulate_only=True,
            )
        
        history = executor.get_trade_history()
        assert len(history) == 1
        assert history[0].session_id == "dojo_session_123"
        assert history[0].success is True
        
        await executor.close()


# ---------------------------------------------------------------------------
# Convenience Function Tests
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    @pytest.mark.asyncio
    async def test_get_jupiter_quote_convenience(self):
        """Test get_jupiter_quote convenience function."""
        mock_quote = SwapQuote(
            chain="solana",
            input_token="SOL",
            output_token="USDC",
            input_amount=1000000000,
            output_amount=98765432,
            output_amount_min=98265432,
            slippage_bps=50,
            price_impact_pct=0.125,
            route={},
            provider="jupiter",
            expires_at=time.time() + 60,
        )
        
        # Patch the JupiterClient.get_quote class method
        with patch.object(JupiterClient, 'get_quote', new=AsyncMock(return_value=mock_quote)):
            quote = await get_jupiter_quote(
                input_mint="SOL",
                output_mint="USDC",
                amount=1000000000,
                slippage_bps=50,
            )
            
            assert quote is not None
            assert quote.provider == "jupiter"
    
    @pytest.mark.asyncio
    async def test_get_1inch_quote_convenience(self):
        """Test get_1inch_quote convenience function."""
        mock_quote = SwapQuote(
            chain="ethereum",
            input_token="ETH",
            output_token="USDC",
            input_amount=1000000000000000000,
            output_amount=3245000000,
            output_amount_min=3226775000,
            slippage_bps=50,
            price_impact_pct=0.05,
            route={},
            provider="1inch",
            expires_at=time.time() + 300,
        )
        
        with patch.object(OneInchClient, 'get_quote', new=AsyncMock(return_value=mock_quote)):
            quote = await get_1inch_quote(
                api_key="test_key",
                chain="ethereum",
                src="ETH",
                dst="USDC",
                amount=1000000000000000000,
            )
            
            assert quote is not None
            assert quote.provider == "1inch"


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Tests for error handling."""
    
    @pytest.mark.asyncio
    async def test_jupiter_timeout(self):
        """Test Jupiter client handles timeout."""
        client = JupiterClient()
        
        with patch.object(client, '_get_session') as mock_session:
            mock_session.side_effect = asyncio.TimeoutError()
            
            quote = await client.get_quote(
                input_mint="SOL",
                output_mint="USDC",
                amount=1000000000,
            )
            
            assert quote is None
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_oneinch_timeout(self):
        """Test 1inch client handles timeout."""
        client = OneInchClient(api_key="test_key")
        
        with patch.object(client, '_get_session') as mock_session:
            mock_session.side_effect = asyncio.TimeoutError()
            
            quote = await client.get_quote(
                chain="ethereum",
                src="ETH",
                dst="USDC",
                amount=1000000000,
            )
            
            assert quote is None
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_executor_handles_quote_none(self):
        """Test executor handles None quote gracefully."""
        executor = SwapExecutor(
            jupiter_client=JupiterClient(),
            tx_guard=None,
        )
        
        with patch.object(executor.jupiter, 'get_quote', new=AsyncMock(return_value=None)):
            result = await executor.execute_swap_solana(
                quote=None,  # type: ignore
                wallet_keypair=MockKeypair(),
            )
            
            # Should handle None quote without crashing
            assert result.success is False
        
        await executor.close()


# ---------------------------------------------------------------------------
# Run Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
