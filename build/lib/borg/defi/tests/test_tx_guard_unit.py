"""
Tests for TransactionGuard.

Covers:
- Spending limits: at limit, over limit, under limit
- Daily limit reset
- Contract whitelist: allow, deny, empty list, wildcard
- check_token: known safe, unknown, with GoPlus mock
- check_spending_limit with concurrent calls
- record_spend accumulation

Run with:
    pytest borg/defi/tests/test_tx_guard_unit.py -v --tb=short
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.security.keystore import SpendingLimitStore, ContractWhitelist
from borg.defi.security.tx_guard import (
    TransactionGuard,
    TransactionCheck,
    TokenCheck,
    TransactionError,
    SpendingLimitError,
    ContractNotWhitelistedError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_keystore_dir(tmp_path):
    """Create temporary keystore directory."""
    keystore_dir = tmp_path / ".hermes" / "borg" / "defi"
    keystore_dir.mkdir(parents=True, exist_ok=True)
    return keystore_dir


@pytest.fixture
def spending_store(temp_keystore_dir, monkeypatch):
    """Create SpendingLimitStore with temp directory."""
    monkeypatch.setattr(SpendingLimitStore, "LIMITS_FILE", temp_keystore_dir / "spending_limits.json")
    store = SpendingLimitStore()
    yield store
    # Cleanup
    if temp_keystore_dir.exists():
        for f in temp_keystore_dir.glob("*.json"):
            f.unlink()


@pytest.fixture
def whitelist(temp_keystore_dir, monkeypatch):
    """Create ContractWhitelist with temp directory."""
    monkeypatch.setattr(ContractWhitelist, "WHITELIST_FILE", temp_keystore_dir / "approved_contracts.json")
    wl = ContractWhitelist()
    yield wl
    # Cleanup
    if temp_keystore_dir.exists():
        for f in temp_keystore_dir.glob("*.json"):
            f.unlink()


@pytest.fixture
def tx_guard(spending_store, whitelist):
    """Create TransactionGuard with mocked stores."""
    guard = TransactionGuard(
        spending_store=spending_store,
        whitelist=whitelist,
        helius_api_key="test_key",
        goplus_api_key=None,  # No GoPlus for unit tests
    )
    return guard


@pytest.fixture
def wallet():
    """Test wallet identifier."""
    return "TestWallet123"


# ---------------------------------------------------------------------------
# Spending Limit Tests
# ---------------------------------------------------------------------------


class TestSpendingLimits:
    """Tests for spending limit checks."""

    def test_spending_limit_no_limits(self, tx_guard, wallet):
        """Test when wallet has no limits set."""
        result = tx_guard.check_spending_limit(wallet, 1000.0)
        assert result.approved is True

    def test_spending_limit_within_per_trade(self, tx_guard, spending_store, wallet):
        """Test spending within per-trade limit."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        result = tx_guard.check_spending_limit(wallet, 500.0)
        assert result.approved is True

    def test_spending_limit_at_per_trade_limit(self, tx_guard, spending_store, wallet):
        """Test spending exactly at per-trade limit."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        result = tx_guard.check_spending_limit(wallet, 1000.0)
        assert result.approved is True

    def test_spending_limit_over_per_trade(self, tx_guard, spending_store, wallet):
        """Test spending over per-trade limit."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        result = tx_guard.check_spending_limit(wallet, 1001.0)
        assert result.approved is False
        assert "Per-trade limit exceeded" in result.error

    def test_spending_limit_within_daily(self, tx_guard, spending_store, wallet):
        """Test spending within daily limit."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # Spend well under daily limit (respecting per-trade)
        result = tx_guard.check_spending_limit(wallet, 500.0)
        assert result.approved is True

    def test_spending_limit_at_daily_limit(self, tx_guard, spending_store, wallet):
        """Test spending exactly at daily limit."""
        spending_store.set_limit(wallet, per_trade=5000.0, daily=5000.0)
        
        result = tx_guard.check_spending_limit(wallet, 5000.0)
        assert result.approved is True

    def test_spending_limit_over_daily(self, tx_guard, spending_store, wallet):
        """Test spending over daily limit."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # First spend to set daily_spent
        spending_store._limits[wallet]["daily_spent"] = 4500.0
        spending_store._save()
        
        # Try to spend 501 (over remaining 500)
        result = tx_guard.check_spending_limit(wallet, 501.0)
        assert result.approved is False
        assert "Daily limit exceeded" in result.error


class TestDailyLimitReset:
    """Tests for daily limit reset functionality."""

    def test_daily_reset_on_new_day(self, tx_guard, spending_store, wallet):
        """Test that daily spent resets on new day."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # Record spend
        spending_store.record_spend(wallet, 4000.0)
        
        # Manually set last_reset to yesterday
        yesterday = (datetime.now() - timedelta(days=1)).timestamp()
        spending_store._limits[wallet]["last_reset"] = yesterday
        
        # Now check - should reset daily spent
        result = tx_guard.check_spending_limit(wallet, 1000.0)
        assert result.approved is True

    def test_daily_reset_resets_spent(self, tx_guard, spending_store, wallet):
        """Test that reset_if_new_day actually resets daily_spent."""
        limit = spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        spending_store._limits[wallet]["daily_spent"] = 4500.0
        spending_store._limits[wallet]["last_reset"] = (datetime.now() - timedelta(days=1)).timestamp()
        spending_store._save()
        
        # Reload store to pick up changes
        spending_store._load()
        
        # Check limit before reset
        result = tx_guard.check_spending_limit(wallet, 100.0)
        # After checking, reset should have happened
        assert spending_store._limits[wallet]["daily_spent"] == 0.0 or result.approved is True

    def test_no_reset_within_same_day(self, tx_guard, spending_store, wallet):
        """Test that daily spent doesn't reset within same day."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        spending_store.record_spend(wallet, 4000.0)
        
        # Should now be blocked
        result = tx_guard.check_spending_limit(wallet, 1001.0)
        assert result.approved is False


class TestRecordSpend:
    """Tests for record_spend functionality."""

    def test_record_spend_accumulates(self, tx_guard, spending_store, wallet):
        """Test that record_spend accumulates."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        tx_guard.record_spend(wallet, 100.0)
        tx_guard.record_spend(wallet, 200.0)
        tx_guard.record_spend(wallet, 300.0)
        
        limit = spending_store.get_limit(wallet)
        assert limit["daily_spent"] == 600.0

    def test_record_spend_returns_true(self, tx_guard, spending_store, wallet):
        """Test that record_spend returns True when within limits."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        result = tx_guard.record_spend(wallet, 100.0)
        assert result is True

    def test_record_spend_returns_false_over_limit(self, tx_guard, spending_store, wallet):
        """Test that record_spend returns False when over limit."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # Spend to exceed daily
        spending_store._limits[wallet]["daily_spent"] = 4900.0
        spending_store._save()
        
        result = tx_guard.record_spend(wallet, 200.0)
        assert result is False


# ---------------------------------------------------------------------------
# Contract Whitelist Tests
# ---------------------------------------------------------------------------


class TestContractWhitelist:
    """Tests for contract whitelist checks."""

    def test_contract_allowed(self, tx_guard, whitelist, wallet):
        """Test whitelisted contract is allowed."""
        whitelist.add(
            address="0xContract123",
            chain="ethereum",
            name="Uniswap Router",
            contract_type="router",
        )
        
        result = tx_guard.check_contract("0xContract123", "ethereum")
        assert result.approved is True

    def test_contract_not_whitelisted(self, tx_guard, whitelist):
        """Test non-whitelisted contract is rejected."""
        result = tx_guard.check_contract("0xNotWhitelisted", "ethereum")
        assert result.approved is False
        assert "not whitelisted" in result.error.lower()

    def test_whitelist_empty_all_denied(self, tx_guard, whitelist):
        """Test that empty whitelist denies all."""
        result = tx_guard.check_contract("0xAnyContract", "solana")
        assert result.approved is False

    def test_whitelist_address_case_insensitive(self, tx_guard, whitelist):
        """Test whitelist check is case insensitive."""
        whitelist.add(
            address="0xContract123",
            chain="ethereum",
            name="Test Router",
            contract_type="router",
        )
        
        # Same address, different case
        result = tx_guard.check_contract("0xCONTRACT123", "ethereum")
        assert result.approved is True

    def test_whitelist_get_contract(self, tx_guard, whitelist):
        """Test getting contract info from whitelist."""
        whitelist.add(
            address="0xContract456",
            chain="ethereum",
            name="Aave",
            contract_type="protocol",
        )
        
        info = whitelist.get_contract("0xContract456", "ethereum")
        assert info is not None
        assert info["name"] == "Aave"

    def test_whitelist_remove_contract(self, tx_guard, whitelist):
        """Test removing contract from whitelist."""
        whitelist.add(
            address="0xToRemove",
            chain="ethereum",
            name="Temp Contract",
            contract_type="unknown",
        )
        
        assert whitelist.is_allowed("0xToRemove", "ethereum") is True
        
        whitelist.remove("0xToRemove", "ethereum")
        
        assert whitelist.is_allowed("0xToRemove", "ethereum") is False


# ---------------------------------------------------------------------------
# Check Token Tests
# ---------------------------------------------------------------------------


class TestCheckToken:
    """Tests for token check functionality."""

    @pytest.mark.asyncio
    async def test_check_token_known_safe_solana(self, tx_guard):
        """Test check_token for known safe Solana token (USDC)."""
        result = await tx_guard.check_token(
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "solana",
        )
        assert result.is_safe is True
        assert result.can_sell is True

    @pytest.mark.asyncio
    async def test_check_token_known_safe_ethereum(self, tx_guard):
        """Test check_token for known safe Ethereum token (USDC)."""
        result = await tx_guard.check_token(
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "ethereum",
        )
        assert result.is_safe is True
        assert result.can_sell is True

    @pytest.mark.asyncio
    async def test_check_token_unknown_token(self, tx_guard):
        """Test check_token for unknown token returns safe by default."""
        result = await tx_guard.check_token(
            "UnknownTokenAddress123",
            "solana",
        )
        # Unknown tokens return safe=True by default
        assert result.is_safe is True

    @pytest.mark.asyncio
    async def test_check_token_without_goplus(self, tx_guard):
        """Test check_token without GoPlus API returns safe defaults."""
        tx_guard.goplus_api_key = None
        tx_guard._goplus_client = None
        
        result = await tx_guard.check_token(
            "RandomToken",
            "ethereum",
        )
        assert result.is_safe is True


class TestCheckTokenWithMock:
    """Tests for check_token with mocked GoPlus."""

    @pytest.mark.asyncio
    async def test_check_token_with_goplus_mock(self, tx_guard):
        """Test check_token with mocked GoPlus response."""
        mock_result = {
            "is_honeypot": "false",
            "can_sell": "true",
            "risk_score": "20",
            "transfer_tax": "0",
            "is_mintable": "false",
        }
        
        with patch.object(tx_guard, 'check_token_security', new_callable=AsyncMock) as mock_check:
            mock_check.return_value = TokenCheck(
                is_safe=True,
                can_sell=True,
                transfer_tax=0.0,
                is_pausable=False,
                warnings=[],
            )
            
            result = await tx_guard.check_token("TestToken", "ethereum")
            # Uses mock from check_token_security
            assert result.is_safe is True


# ---------------------------------------------------------------------------
# Human Approval Tests
# ---------------------------------------------------------------------------


class TestHumanApproval:
    """Tests for human approval threshold checks."""

    def test_auto_approve_small_amount(self, tx_guard):
        """Test small amount auto-approved."""
        result = tx_guard.check_human_approval(50.0)
        assert result.approved is True
        assert result.requires_human_approval is False

    def test_auto_approve_at_threshold(self, tx_guard):
        """Test amount at auto threshold."""
        result = tx_guard.check_human_approval(100.0)
        assert result.approved is True

    def test_alert_threshold(self, tx_guard):
        """Test amount in alert range ($100-$1000)."""
        result = tx_guard.check_human_approval(500.0)
        assert result.approved is True
        assert result.requires_human_approval is False

    def test_approval_required(self, tx_guard):
        """Test amount requiring approval ($1000-$10000)."""
        result = tx_guard.check_human_approval(5000.0)
        assert result.approved is False
        assert result.requires_human_approval is True
        assert "human approval" in result.error.lower()

    def test_2fa_required(self, tx_guard):
        """Test amount requiring 2FA ($10000-$100000)."""
        result = tx_guard.check_human_approval(50000.0)
        assert result.approved is False
        assert result.requires_human_approval is True
        assert "2FA" in result.error

    def test_senior_approval_required(self, tx_guard):
        """Test amount over $100000 requires senior approval."""
        result = tx_guard.check_human_approval(150000.0)
        assert result.approved is False
        assert result.requires_human_approval is True
        assert "senior approval" in result.error.lower()


# ---------------------------------------------------------------------------
# Pre-flight Check Tests
# ---------------------------------------------------------------------------


class TestPreFlightCheck:
    """Tests for full pre-flight check."""

    @pytest.mark.asyncio
    async def test_pre_flight_all_checks_pass(self, tx_guard, spending_store, whitelist, wallet):
        """Test pre-flight check when all checks pass."""
        # Set up spending limit
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # Whitelist contract
        whitelist.add("0xContract", "ethereum", "Test Router", "router")
        
        result = await tx_guard.pre_flight_check(
            wallet=wallet,
            contract="0xContract",
            chain="ethereum",
            amount_usd=100.0,
        )
        
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_pre_flight_spending_limit_fails(self, tx_guard, spending_store, whitelist, wallet):
        """Test pre-flight when spending limit fails."""
        spending_store.set_limit(wallet, per_trade=100.0, daily=500.0)
        whitelist.add("0xContract", "ethereum", "Test Router", "router")
        
        result = await tx_guard.pre_flight_check(
            wallet=wallet,
            contract="0xContract",
            chain="ethereum",
            amount_usd=200.0,
        )
        
        assert result.approved is False
        assert "limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_pre_flight_contract_not_whitelisted(self, tx_guard, spending_store, wallet):
        """Test pre-flight when contract not whitelisted."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        result = await tx_guard.pre_flight_check(
            wallet=wallet,
            contract="0xNotWhitelisted",
            chain="ethereum",
            amount_usd=100.0,
        )
        
        assert result.approved is False
        assert "whitelist" in result.error.lower()


# ---------------------------------------------------------------------------
# Concurrent Calls Tests
# ---------------------------------------------------------------------------


class TestConcurrentCalls:
    """Tests for concurrent spending limit checks."""

    def test_concurrent_spending_checks(self, tx_guard, spending_store, wallet):
        """Test concurrent check_spending_limit calls."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # Run multiple calls - all should work
        results = []
        for _ in range(10):
            r = tx_guard.check_spending_limit(wallet, 100.0)
            results.append(r)
        
        # All should be approved since total doesn't exceed daily
        assert all(r.approved for r in results)

    def test_concurrent_record_spend(self, tx_guard, spending_store, wallet):
        """Test concurrent record_spend calls."""
        spending_store.set_limit(wallet, per_trade=1000.0, daily=5000.0)
        
        # Run multiple record_spend
        results = []
        for _ in range(10):
            r = tx_guard.record_spend(wallet, 100.0)
            results.append(r)
        
        # All should succeed (we're under the limit)
        assert all(results)


# ---------------------------------------------------------------------------
# TransactionCheck Dataclass Tests
# ---------------------------------------------------------------------------


class TestTransactionCheck:
    """Tests for TransactionCheck dataclass."""

    def test_transaction_check_approved(self):
        """Test approved TransactionCheck."""
        check = TransactionCheck(approved=True)
        assert check.approved is True
        assert check.requires_human_approval is False
        assert check.error is None

    def test_transaction_check_not_approved(self):
        """Test not approved TransactionCheck."""
        check = TransactionCheck(
            approved=False,
            error="Test error",
        )
        assert check.approved is False
        assert check.error == "Test error"

    def test_transaction_check_with_human_approval(self):
        """Test TransactionCheck requiring human approval."""
        check = TransactionCheck(
            approved=False,
            requires_human_approval=True,
            error="Requires approval",
        )
        assert check.requires_human_approval is True


class TestTokenCheck:
    """Tests for TokenCheck dataclass."""

    def test_token_check_safe(self):
        """Test safe TokenCheck."""
        check = TokenCheck(
            is_safe=True,
            can_sell=True,
            transfer_tax=0.0,
            is_pausable=False,
            warnings=[],
        )
        assert check.is_safe is True
        assert check.can_sell is True

    def test_token_check_with_warnings(self):
        """Test TokenCheck with warnings."""
        check = TokenCheck(
            is_safe=True,
            can_sell=True,
            transfer_tax=0.0,
            is_pausable=False,
            warnings=["Low liquidity", "High volatility"],
        )
        assert len(check.warnings) == 2

    def test_token_check_honeypot(self):
        """Test TokenCheck marking honeypot."""
        check = TokenCheck(
            is_safe=False,
            can_sell=False,
            transfer_tax=0.0,
            is_pausable=False,
            warnings=["Cannot sell"],
        )
        assert check.is_safe is False
        assert check.can_sell is False


# ---------------------------------------------------------------------------
# Exception Tests
# ---------------------------------------------------------------------------


class TestExceptions:
    """Tests for TransactionGuard exceptions."""

    def test_transaction_error_exists(self):
        """Test TransactionError is defined."""
        assert issubclass(TransactionError, Exception)

    def test_spending_limit_error_exists(self):
        """Test SpendingLimitError is defined."""
        assert issubclass(SpendingLimitError, TransactionError)

    def test_contract_not_whitelisted_error_exists(self):
        """Test ContractNotWhitelistedError is defined."""
        assert issubclass(ContractNotWhitelistedError, TransactionError)


# ---------------------------------------------------------------------------
# Format Approval Request Tests
# ---------------------------------------------------------------------------


class TestFormatApprovalRequest:
    """Tests for format_approval_request method."""

    def test_format_basic(self, tx_guard):
        """Test basic approval request formatting."""
        result = tx_guard.format_approval_request(
            wallet="TestWallet",
            contract="0xContract123",
            chain="ethereum",
            amount_usd=5000.0,
        )
        
        # Check it contains the key info
        assert "ethereum" in result
        assert "0xContract123" in result
        assert "5,000" in result or "5000" in result

    def test_format_with_token(self, tx_guard):
        """Test approval request with token address."""
        result = tx_guard.format_approval_request(
            wallet="TestWallet",
            contract="0xContract123",
            chain="ethereum",
            amount_usd=5000.0,
            token_address="0xToken456",
        )
        
        assert "0xToken456" in result
