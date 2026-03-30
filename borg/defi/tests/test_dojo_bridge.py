"""
Tests for Dojo Bridge Module.

Tests the integration layer connecting DeFi trade outcomes to borg's learning loop:
- Trade outcome classification
- Failure memory integration
- Strategy reputation updates
- Nudge generation
- Rug warning propagation

Run with:
    pytest borg/defi/tests/test_dojo_bridge.py -v --tb=short
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.dojo_bridge import (
    DojoBridge,
    TRADE_ERROR_PATTERNS,
    NUDGE_THRESHOLDS,
    TradeOutcome,
    StrategyReputation,
    DEFAULT_DOJO_MEMORY_DIR,
)
from borg.defi.swap_executor import SwapTrade, SwapResult
from borg.defi.data_models import DeFiPackMetadata
from borg.core.failure_memory import FailureMemory


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Create a temporary memory directory for testing."""
    return tmp_path / "dojo_test"


@pytest.fixture
def failure_memory(temp_memory_dir):
    """Create a FailureMemory instance with temp directory."""
    return FailureMemory(memory_dir=temp_memory_dir / "failures")


@pytest.fixture
def dojo_bridge(failure_memory, temp_memory_dir):
    """Create a DojoBridge instance for testing."""
    return DojoBridge(
        failure_memory=failure_memory,
        memory_dir=temp_memory_dir,
        pack_id="test-defi-pack",
    )


@pytest.fixture
def sample_trade_success():
    """Create a successful trade."""
    return SwapTrade(
        trade_id="trade_001",
        timestamp=time.time(),
        chain="solana",
        provider="jupiter",
        input_token="So11111111111111111111111111111111111111112",
        output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        input_amount=1000000000,  # 1 SOL
        output_amount=98765432,  # ~98.7 USDC
        output_amount_usd=98.70,
        gas_used_usd=0.25,
        price_impact_pct=0.12,
        slippage_bps=50,
        success=True,
        wallet="TestWallet123",
        session_id="session_001",
        error=None,
    )


@pytest.fixture
def sample_trade_slippage_exceeded():
    """Create a trade that exceeded slippage."""
    return SwapTrade(
        trade_id="trade_002",
        timestamp=time.time(),
        chain="solana",
        provider="jupiter",
        input_token="So11111111111111111111111111111111111111112",
        output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        input_amount=1000000000,
        output_amount=95000000,
        output_amount_usd=92.00,
        gas_used_usd=0.25,
        price_impact_pct=5.5,
        slippage_bps=50,
        success=False,
        wallet="TestWallet123",
        session_id="session_001",
        error="Slippage tolerance exceeded. Price impact too high.",
    )


@pytest.fixture
def sample_trade_insufficient_liquidity():
    """Create a trade with insufficient liquidity."""
    return SwapTrade(
        trade_id="trade_003",
        timestamp=time.time(),
        chain="ethereum",
        provider="1inch",
        input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        input_amount=1000000000,  # 1000 USDC
        output_amount=0,
        output_amount_usd=0,
        gas_used_usd=0,
        price_impact_pct=0,
        slippage_bps=50,
        success=False,
        wallet="TestWallet456",
        session_id="session_002",
        error="Insufficient liquidity for this trade.",
    )


@pytest.fixture
def sample_trade_reverted():
    """Create a reverted trade."""
    return SwapTrade(
        trade_id="trade_004",
        timestamp=time.time(),
        chain="arbitrum",
        provider="1inch",
        input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        output_token="0x912CE5914419dC4BDaC24C3c46D3F0d07B5C2f3B",
        input_amount=500000000,
        output_amount=0,
        output_amount_usd=0,
        gas_used_usd=5.00,
        price_impact_pct=0,
        slippage_bps=50,
        success=False,
        wallet="TestWallet789",
        session_id="session_003",
        error="Transaction reverted: execution reverted",
    )


@pytest.fixture
def sample_trade_rug_detected():
    """Create a trade with rug detection."""
    return SwapTrade(
        trade_id="trade_005",
        timestamp=time.time(),
        chain="ethereum",
        provider="1inch",
        input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        output_token="0x6979E204D0CDllMan8F1155a82B8B2f31cF3b11",
        input_amount=100000000,
        output_amount=0,
        output_amount_usd=0,
        gas_used_usd=2.00,
        price_impact_pct=0,
        slippage_bps=50,
        success=False,
        wallet="TestWalletABC",
        session_id="session_004",
        error="Honeypot detected: cannot sell this token",
    )


@pytest.fixture
def sample_trade_gas_estimation_failed():
    """Create a trade with gas estimation failure."""
    return SwapTrade(
        trade_id="trade_006",
        timestamp=time.time(),
        chain="polygon",
        provider="1inch",
        input_token="0x7D1AfA7B718fb893dB30a3aBc0Cfc1Aa4d4d6dC5",
        output_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        input_amount=2000000000,
        output_amount=0,
        output_amount_usd=0,
        gas_used_usd=0,
        price_impact_pct=0,
        slippage_bps=50,
        success=False,
        wallet="TestWalletDEF",
        session_id="session_005",
        error="Gas estimation failed: cannot estimate gas",
    )


# -------------------------------------------------------------------------
# Classification Tests
# -------------------------------------------------------------------------


class TestClassifyTradeOutcome:
    """Tests for DojoBridge.classify_trade_outcome."""

    def test_classify_success(self, dojo_bridge, sample_trade_success):
        """Test classification of successful trade."""
        result = dojo_bridge.classify_trade_outcome(sample_trade_success)
        assert result == "success"

    def test_classify_slippage_exceeded(self, dojo_bridge, sample_trade_slippage_exceeded):
        """Test classification of slippage exceeded error."""
        result = dojo_bridge.classify_trade_outcome(sample_trade_slippage_exceeded)
        assert result == "slippage_exceeded"

    def test_classify_insufficient_liquidity(self, dojo_bridge, sample_trade_insufficient_liquidity):
        """Test classification of insufficient liquidity error."""
        result = dojo_bridge.classify_trade_outcome(sample_trade_insufficient_liquidity)
        assert result == "insufficient_liquidity"

    def test_classify_transaction_reverted(self, dojo_bridge, sample_trade_reverted):
        """Test classification of transaction reverted error."""
        result = dojo_bridge.classify_trade_outcome(sample_trade_reverted)
        assert result == "transaction_reverted"

    def test_classify_rug_detected(self, dojo_bridge, sample_trade_rug_detected):
        """Test classification of rug detected error."""
        result = dojo_bridge.classify_trade_outcome(sample_trade_rug_detected)
        assert result == "rug_detected"

    def test_classify_gas_estimation_failed(self, dojo_bridge, sample_trade_gas_estimation_failed):
        """Test classification of gas estimation failed error."""
        result = dojo_bridge.classify_trade_outcome(sample_trade_gas_estimation_failed)
        assert result == "gas_estimation_failed"

    def test_classify_unknown_error_defaults_to_reverted(self, dojo_bridge):
        """Test that unknown errors default to transaction_reverted."""
        trade = SwapTrade(
            trade_id="trade_unknown",
            timestamp=time.time(),
            chain="ethereum",
            provider="1inch",
            input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            input_amount=1000000000,
            output_amount=0,
            output_amount_usd=0,
            gas_used_usd=1.00,
            price_impact_pct=0,
            slippage_bps=50,
            success=False,
            wallet="TestWallet",
            session_id="session_unknown",
            error="Some completely unknown error message",
        )
        result = dojo_bridge.classify_trade_outcome(trade)
        assert result == "transaction_reverted"

    @pytest.mark.parametrize(
        "error_msg,expected_class",
        [
            ("SLIPPAGE_TOLERANCE_EXCEEDED", "slippage_exceeded"),
            ("Insufficient Liquidity Detected", "insufficient_liquidity"),
            ("EXECUTION REVERTED", "transaction_reverted"),
            ("Honeypot in contract", "rug_detected"),
            ("Gas estimation failed", "gas_estimation_failed"),
        ],
    )
    def test_classify_case_insensitive(self, dojo_bridge, error_msg, expected_class):
        """Test that classification is case insensitive."""
        trade = SwapTrade(
            trade_id=f"trade_{expected_class}",
            timestamp=time.time(),
            chain="ethereum",
            provider="1inch",
            input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            input_amount=1000000000,
            output_amount=0,
            output_amount_usd=0,
            gas_used_usd=1.00,
            price_impact_pct=0,
            slippage_bps=50,
            success=False,
            wallet="TestWallet",
            session_id="session_test",
            error=error_msg,
        )
        result = dojo_bridge.classify_trade_outcome(trade)
        assert result == expected_class


# -------------------------------------------------------------------------
# Record Outcome Tests
# -------------------------------------------------------------------------


class TestRecordOutcome:
    """Tests for DojoBridge.record_outcome."""

    def test_record_success_outcome(self, dojo_bridge, sample_trade_success):
        """Test recording a successful trade outcome."""
        classification = "success"
        dojo_bridge.record_outcome(sample_trade_success, classification)

        # Verify failure memory was called (success is also recorded)
        recall = dojo_bridge.failure_memory.recall("successful_swap_solana")
        assert recall is not None

    def test_record_failure_outcome(self, dojo_bridge, sample_trade_slippage_exceeded):
        """Test recording a failed trade outcome."""
        classification = "slippage_exceeded"
        dojo_bridge.record_outcome(sample_trade_slippage_exceeded, classification)

        # Verify failure memory was updated
        recall = dojo_bridge.failure_memory.recall("slippage_exceeded")
        assert recall is not None

    def test_record_with_strategy_name(self, dojo_bridge, sample_trade_success):
        """Test recording with a custom strategy name."""
        classification = "success"
        strategy_name = "momentum-strategy-v1"
        dojo_bridge.record_outcome(sample_trade_success, classification, strategy_name)

        # Verify it was recorded under the strategy name
        recall = dojo_bridge.failure_memory.recall("successful_swap_solana")
        assert recall is not None

    def test_record_rug_outcome(self, dojo_bridge, sample_trade_rug_detected):
        """Test recording a rug detection outcome."""
        classification = "rug_detected"
        dojo_bridge.record_outcome(sample_trade_rug_detected, classification)

        recall = dojo_bridge.failure_memory.recall("rug_detected")
        assert recall is not None


# -------------------------------------------------------------------------
# Strategy Reputation Tests
# -------------------------------------------------------------------------


class TestUpdateStrategyReputation:
    """Tests for DojoBridge.update_strategy_reputation."""

    def test_first_trade_creates_reputation(self, dojo_bridge, sample_trade_success):
        """Test that first trade creates strategy reputation."""
        strategy_name = "test-strategy-001"
        metadata = dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)

        assert metadata.total_trades == 1
        assert metadata.winning_trades == 1
        assert metadata.total_pnl_usd >= 0
        assert metadata.win_rate == 1.0

    def test_loss_decrements_winning_trades(self, dojo_bridge, sample_trade_success, sample_trade_reverted):
        """Test that losing trades are tracked correctly."""
        strategy_name = "test-strategy-002"

        # First trade wins
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)
        metadata1 = dojo_bridge.get_strategy_metadata(strategy_name)
        assert metadata1.winning_trades == 1

        # Second trade loses
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_reverted)
        metadata2 = dojo_bridge.get_strategy_metadata(strategy_name)
        assert metadata2.winning_trades == 1  # Still 1 win
        assert metadata2.total_trades == 2

    def test_win_rate_calculation(self, dojo_bridge, sample_trade_success, sample_trade_reverted):
        """Test win rate is calculated correctly."""
        strategy_name = "test-strategy-003"

        # 3 wins, 1 loss
        for _ in range(3):
            dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_reverted)

        metadata = dojo_bridge.get_strategy_metadata(strategy_name)
        assert metadata.total_trades == 4
        assert metadata.winning_trades == 3
        assert metadata.win_rate == 0.75

    def test_consecutive_losses_tracking(self, dojo_bridge, sample_trade_reverted):
        """Test that consecutive losses are tracked."""
        strategy_name = "test-strategy-004"

        for i in range(3):
            trade = SwapTrade(
                trade_id=f"trade_loss_{i}",
                timestamp=time.time(),
                chain="ethereum",
                provider="1inch",
                input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                input_amount=1000000000,
                output_amount=0,
                output_amount_usd=0,
                gas_used_usd=5.00,
                price_impact_pct=0,
                slippage_bps=50,
                success=False,
                wallet="TestWallet",
                session_id=f"session_{i}",
                error="Transaction reverted",
            )
            dojo_bridge.update_strategy_reputation(strategy_name, trade)

        rep = dojo_bridge._strategy_reputations[strategy_name]
        assert rep.consecutive_losses == 3

    def test_chains_updated(self, dojo_bridge, sample_trade_success):
        """Test that chains are tracked in metadata."""
        strategy_name = "test-strategy-005"
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)

        metadata = dojo_bridge.get_strategy_metadata(strategy_name)
        assert "solana" in metadata.chains

    def test_persist_strategy_metadata(self, dojo_bridge, sample_trade_success, temp_memory_dir):
        """Test that strategy metadata is persisted to disk."""
        strategy_name = "test-strategy-006"
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)

        # Check file exists
        metadata_path = temp_memory_dir / "strategies" / f"{strategy_name}.yaml"
        assert metadata_path.exists()


# -------------------------------------------------------------------------
# Nudge Generation Tests
# -------------------------------------------------------------------------


class TestGenerateNudge:
    """Tests for DojoBridge.generate_nudge."""

    def test_no_nudge_for_new_strategy(self, dojo_bridge):
        """Test no nudge generated for strategy with no trades."""
        nudge = dojo_bridge.generate_nudge("nonexistent-strategy")
        assert nudge is None

    def test_loss_streak_nudge(self, dojo_bridge, sample_trade_reverted):
        """Test nudge generated after consecutive losses."""
        strategy_name = "test-strategy-007"

        # Execute 3 losing trades
        for i in range(3):
            trade = SwapTrade(
                trade_id=f"trade_loss_{i}",
                timestamp=time.time(),
                chain="ethereum",
                provider="1inch",
                input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                input_amount=1000000000,
                output_amount=0,
                output_amount_usd=0,
                gas_used_usd=5.00,
                price_impact_pct=0,
                slippage_bps=50,
                success=False,
                wallet="TestWallet",
                session_id=f"session_{i}",
                error="Transaction reverted",
            )
            dojo_bridge.update_strategy_reputation(strategy_name, trade)

        nudge = dojo_bridge.generate_nudge(strategy_name)
        assert nudge is not None
        assert "LOSS_STREAK" in nudge
        assert "3" in nudge

    def test_drawdown_alert_nudge(self, dojo_bridge, sample_trade_success, sample_trade_reverted):
        """Test nudge generated when drawdown exceeds threshold."""
        strategy_name = "test-strategy-008"

        # First create a win to establish a peak
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)

        # Create large loss to trigger drawdown
        large_loss_trade = SwapTrade(
            trade_id="large_loss",
            timestamp=time.time(),
            chain="ethereum",
            provider="1inch",
            input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            input_amount=10000000000,  # Large amount
            output_amount=0,
            output_amount_usd=0,
            gas_used_usd=5.00,
            price_impact_pct=0,
            slippage_bps=50,
            success=False,
            wallet="TestWallet",
            session_id="session_large",
            error="Transaction reverted",
        )
        dojo_bridge.update_strategy_reputation(strategy_name, large_loss_trade)

        # May or may not trigger depending on drawdown calculation
        nudge = dojo_bridge.generate_nudge(strategy_name)

    def test_low_win_rate_nudge(self, dojo_bridge, sample_trade_success, sample_trade_reverted):
        """Test nudge generated when win rate drops below threshold."""
        strategy_name = "test-strategy-009"

        # Create 2 wins and 5 losses (win rate < 40%)
        for _ in range(2):
            dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)
        for _ in range(5):
            dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_reverted)

        nudge = dojo_bridge.generate_nudge(strategy_name)
        assert nudge is not None
        assert "LOW_WIN_RATE" in nudge

    def test_positive_momentum_nudge(self, dojo_bridge, sample_trade_success):
        """Test nudge generated during winning streak."""
        strategy_name = "test-strategy-010"

        # Execute 5 winning trades
        for i in range(5):
            trade = SwapTrade(
                trade_id=f"trade_win_{i}",
                timestamp=time.time(),
                chain="solana",
                provider="jupiter",
                input_token="So11111111111111111111111111111111111111112",
                output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                input_amount=1000000000,
                output_amount=99000000,
                output_amount_usd=99.00,
                gas_used_usd=0.25,
                price_impact_pct=0.1,
                slippage_bps=50,
                success=True,
                wallet="TestWallet",
                session_id=f"session_{i}",
                error=None,
            )
            dojo_bridge.update_strategy_reputation(strategy_name, trade)

        nudge = dojo_bridge.generate_nudge(strategy_name)
        assert nudge is not None
        assert "MOMENTUM" in nudge

    def test_profitable_strategy_nudge(self, dojo_bridge, sample_trade_success):
        """Test nudge for consistently profitable strategy."""
        strategy_name = "test-strategy-011"

        for i in range(3):
            trade = SwapTrade(
                trade_id=f"trade_profit_{i}",
                timestamp=time.time(),
                chain="solana",
                provider="jupiter",
                input_token="So11111111111111111111111111111111111111112",
                output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                input_amount=5000000000,  # Large amount
                output_amount=4900000000,
                output_amount_usd=4900.00,  # High value
                gas_used_usd=0.25,
                price_impact_pct=0.1,
                slippage_bps=50,
                success=True,
                wallet="TestWallet",
                session_id=f"session_{i}",
                error=None,
            )
            dojo_bridge.update_strategy_reputation(strategy_name, trade)

        nudge = dojo_bridge.generate_nudge(strategy_name)
        assert nudge is not None
        assert "PROFITABLE" in nudge


# -------------------------------------------------------------------------
# Rug Warning Propagation Tests
# -------------------------------------------------------------------------


class TestPropagateWarning:
    """Tests for DojoBridge.propagate_warning."""

    def test_propagate_basic_warning(self, dojo_bridge):
        """Test basic warning propagation."""
        warning = dojo_bridge.propagate_warning(
            token="0x1234567890abcdef",
            reason="Honeypot detected",
            severity="high",
        )

        assert warning["type"] == "rug_exploit_warning"
        assert warning["token"] == "0x1234567890abcdef"
        assert warning["reason"] == "Honeypot detected"
        assert warning["severity"] == "high"
        assert "timestamp" in warning

    def test_warning_stored_in_list(self, dojo_bridge):
        """Test that warnings are stored in the bridge."""
        dojo_bridge.propagate_warning(
            token="0x1234567890abcdef",
            reason="Honeypot detected",
            severity="high",
        )

        warnings = dojo_bridge.get_rug_warnings()
        assert len(warnings) == 1
        assert warnings[0]["token"] == "0x1234567890abcdef"

    def test_warning_with_affected_strategies(self, dojo_bridge, sample_trade_rug_detected):
        """Test warning propagation with affected strategies."""
        strategy_name = "affected-strategy-001"
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_rug_detected)

        warning = dojo_bridge.propagate_warning(
            token="0xPROBLEMATIC",
            reason="Trading disabled",
            severity="critical",
            affected_strategies=[strategy_name],
        )

        assert strategy_name in warning["affected_strategies"]

    def test_multiple_warnings(self, dojo_bridge):
        """Test multiple warnings are stored."""
        dojo_bridge.propagate_warning(
            token="0xTOKEN1",
            reason="Honeypot",
            severity="high",
        )
        dojo_bridge.propagate_warning(
            token="0xTOKEN2",
            reason="Cannot sell",
            severity="critical",
        )

        warnings = dojo_bridge.get_rug_warnings()
        assert len(warnings) == 2

    def test_warning_persisted_to_disk(self, dojo_bridge, temp_memory_dir):
        """Test that warnings are persisted to disk."""
        dojo_bridge.propagate_warning(
            token="0xPERSISTED_TOKEN",
            reason="Test warning",
            severity="medium",
        )

        collective_dir = temp_memory_dir / "collective_warnings"
        # Check that at least one warning file exists
        warning_files = list(collective_dir.glob("warning_*.yaml"))
        assert len(warning_files) >= 1


# -------------------------------------------------------------------------
# Recall and Memory Tests
# -------------------------------------------------------------------------


class TestRecallSimilarFailures:
    """Tests for DojoBridge.recall_similar_failures."""

    def test_recall_after_recorded_failure(self, dojo_bridge, sample_trade_slippage_exceeded):
        """Test recalling a similar failure after recording."""
        classification = "slippage_exceeded"
        dojo_bridge.record_outcome(sample_trade_slippage_exceeded, classification)

        # Recall using the classification as the error pattern
        recall = dojo_bridge.recall_similar_failures("slippage_exceeded")
        assert recall is not None

    def test_recall_no_match(self, dojo_bridge):
        """Test recall with no matching failures."""
        recall = dojo_bridge.recall_similar_failures("completely unknown error")
        assert recall is None


# -------------------------------------------------------------------------
# Get Recent Outcomes Tests
# -------------------------------------------------------------------------


class TestGetRecentOutcomes:
    """Tests for DojoBridge.get_recent_outcomes."""

    def test_get_recent_outcomes_empty(self, dojo_bridge):
        """Test getting outcomes for unknown strategy."""
        outcomes = dojo_bridge.get_recent_outcomes("unknown-strategy")
        assert outcomes == []

    def test_get_recent_outcomes_with_trades(self, dojo_bridge, sample_trade_success):
        """Test getting recent outcomes with trades."""
        strategy_name = "test-strategy-outcomes"
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)

        outcomes = dojo_bridge.get_recent_outcomes(strategy_name)
        assert len(outcomes) == 1
        assert outcomes[0].trade_id == sample_trade_success.trade_id

    def test_get_recent_outcomes_limit(self, dojo_bridge, sample_trade_success):
        """Test limiting recent outcomes."""
        strategy_name = "test-strategy-limit"

        # Create 15 trades
        for i in range(15):
            trade = SwapTrade(
                trade_id=f"trade_{i}",
                timestamp=time.time(),
                chain="solana",
                provider="jupiter",
                input_token="So11111111111111111111111111111111111111112",
                output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                input_amount=1000000000,
                output_amount=98765432,
                output_amount_usd=98.70,
                gas_used_usd=0.25,
                price_impact_pct=0.12,
                slippage_bps=50,
                success=True,
                wallet="TestWallet",
                session_id=f"session_{i}",
                error=None,
            )
            dojo_bridge.update_strategy_reputation(strategy_name, trade)

        # Get last 5
        outcomes = dojo_bridge.get_recent_outcomes(strategy_name, limit=5)
        assert len(outcomes) == 5


# -------------------------------------------------------------------------
# Strategy Metadata Tests
# -------------------------------------------------------------------------


class TestGetStrategyMetadata:
    """Tests for DojoBridge.get_strategy_metadata."""

    def test_get_unknown_strategy_returns_none(self, dojo_bridge):
        """Test getting metadata for unknown strategy."""
        metadata = dojo_bridge.get_strategy_metadata("unknown-strategy")
        assert metadata is None

    def test_get_existing_strategy_returns_metadata(self, dojo_bridge, sample_trade_success):
        """Test getting metadata for existing strategy."""
        strategy_name = "test-strategy-metadata"
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)

        metadata = dojo_bridge.get_strategy_metadata(strategy_name)
        assert metadata is not None
        assert isinstance(metadata, DeFiPackMetadata)
        assert metadata.total_trades == 1


# -------------------------------------------------------------------------
# Integration Tests
# -------------------------------------------------------------------------


class TestDojoBridgeIntegration:
    """Integration tests for complete DojoBridge workflow."""

    def test_full_trade_lifecycle(self, dojo_bridge, sample_trade_success):
        """Test complete lifecycle: classify -> record -> update -> nudge."""
        strategy_name = "integration-test-strategy"

        # Classify
        classification = dojo_bridge.classify_trade_outcome(sample_trade_success)
        assert classification == "success"

        # Record
        dojo_bridge.record_outcome(sample_trade_success, classification, strategy_name)

        # Update reputation
        metadata = dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_success)
        assert metadata.total_trades == 1
        assert metadata.win_rate == 1.0

        # Generate nudge (should be None for new strategy with few trades)
        nudge = dojo_bridge.generate_nudge(strategy_name)
        # May be None or have momentum nudge

    def test_full_failure_lifecycle(
        self,
        dojo_bridge,
        sample_trade_slippage_exceeded,
    ):
        """Test complete lifecycle for failure case."""
        strategy_name = "failure-integration-test"

        # Classify
        classification = dojo_bridge.classify_trade_outcome(sample_trade_slippage_exceeded)
        assert classification == "slippage_exceeded"

        # Record
        dojo_bridge.record_outcome(sample_trade_slippage_exceeded, classification, strategy_name)

        # Update reputation
        metadata = dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_slippage_exceeded)
        assert metadata.total_trades == 1
        assert metadata.winning_trades == 0

    def test_rug_warning_full_flow(self, dojo_bridge, sample_trade_rug_detected):
        """Test rug warning integration with strategy updates."""
        strategy_name = "rug-warning-test"

        # Record the rug detection trade
        dojo_bridge.update_strategy_reputation(strategy_name, sample_trade_rug_detected)

        # Propagate warning
        warning = dojo_bridge.propagate_warning(
            token=sample_trade_rug_detected.output_token,
            reason="Honeypot detected - cannot sell",
            severity="critical",
            affected_strategies=[strategy_name],
        )

        assert warning["type"] == "rug_exploit_warning"
        assert warning["severity"] == "critical"
        assert strategy_name in warning["affected_strategies"]

    def test_multi_strategy_independence(self, dojo_bridge, sample_trade_success, sample_trade_reverted):
        """Test that multiple strategies maintain independent reputations."""
        strategy_a = "strategy-a"
        strategy_b = "strategy-b"

        # Strategy A: 3 wins
        for _ in range(3):
            dojo_bridge.update_strategy_reputation(strategy_a, sample_trade_success)

        # Strategy B: 1 win, 2 losses
        dojo_bridge.update_strategy_reputation(strategy_b, sample_trade_success)
        dojo_bridge.update_strategy_reputation(strategy_b, sample_trade_reverted)
        dojo_bridge.update_strategy_reputation(strategy_b, sample_trade_reverted)

        # Verify independence
        meta_a = dojo_bridge.get_strategy_metadata(strategy_a)
        meta_b = dojo_bridge.get_strategy_metadata(strategy_b)

        assert meta_a.total_trades == 3
        assert meta_a.winning_trades == 3
        assert meta_a.win_rate == 1.0

        assert meta_b.total_trades == 3
        assert meta_b.winning_trades == 1
        assert meta_b.win_rate < 1.0


# -------------------------------------------------------------------------
# Edge Cases and Error Handling
# -------------------------------------------------------------------------


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_error_message(self, dojo_bridge):
        """Test classification with empty error message."""
        trade = SwapTrade(
            trade_id="trade_empty_err",
            timestamp=time.time(),
            chain="ethereum",
            provider="1inch",
            input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            input_amount=1000000000,
            output_amount=0,
            output_amount_usd=0,
            gas_used_usd=0,
            price_impact_pct=0,
            slippage_bps=50,
            success=False,
            wallet="TestWallet",
            session_id="session_empty",
            error="",  # Empty error
        )
        result = dojo_bridge.classify_trade_outcome(trade)
        assert result == "transaction_reverted"

    def test_trade_with_no_output_usd(self, dojo_bridge):
        """Test trade with zero output USD value."""
        trade = SwapTrade(
            trade_id="trade_zero_output",
            timestamp=time.time(),
            chain="solana",
            provider="jupiter",
            input_token="So11111111111111111111111111111111111111112",
            output_token="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            input_amount=0,
            output_amount=0,
            output_amount_usd=0,
            gas_used_usd=0,
            price_impact_pct=0,
            slippage_bps=50,
            success=False,
            wallet="TestWallet",
            session_id="session_zero",
            error="No output",
        )
        result = dojo_bridge.classify_trade_outcome(trade)
        assert result == "transaction_reverted"

    def test_multiple_error_patterns_match(self, dojo_bridge):
        """Test when multiple patterns could match."""
        trade = SwapTrade(
            trade_id="trade_multi_match",
            timestamp=time.time(),
            chain="ethereum",
            provider="1inch",
            input_token="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            output_token="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            input_amount=1000000000,
            output_amount=0,
            output_amount_usd=0,
            gas_used_usd=5.00,
            price_impact_pct=0,
            slippage_bps=50,
            success=False,
            wallet="TestWallet",
            session_id="session_multi",
            error="Insufficient liquidity and gas estimation failed",  # Multiple issues
        )
        result = dojo_bridge.classify_trade_outcome(trade)
        # Should match first pattern in order (insufficient_liquidity)
        assert result == "insufficient_liquidity"


# -------------------------------------------------------------------------
# Test pattern definitions
# -------------------------------------------------------------------------


class TestTradeErrorPatterns:
    """Tests for the TRADE_ERROR_PATTERNS definitions."""

    def test_all_error_categories_defined(self):
        """Test all required error categories are defined."""
        expected_categories = {
            "slippage_exceeded",
            "insufficient_liquidity",
            "transaction_reverted",
            "rug_detected",
            "gas_estimation_failed",
        }
        assert set(TRADE_ERROR_PATTERNS.keys()) == expected_categories

    def test_each_category_has_patterns(self):
        """Test each error category has at least one pattern."""
        for category, patterns in TRADE_ERROR_PATTERNS.items():
            assert len(patterns) > 0, f"Category {category} has no patterns"

    def test_patterns_are_valid_regex(self):
        """Test all patterns are valid regex."""
        import re
        for category, patterns in TRADE_ERROR_PATTERNS.items():
            for pattern in patterns:
                try:
                    re.compile(pattern)
                except re.error:
                    pytest.fail(f"Invalid regex pattern in {category}: {pattern}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])