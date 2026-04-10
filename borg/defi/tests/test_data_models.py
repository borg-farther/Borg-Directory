"""
Tests for DeFi data models.

Covers all dataclasses in borg/defi/data_models.py:
- WhaleAlert
- YieldOpportunity
- Position
- DeFiPackMetadata
- TokenPrice
- OHLCV
- Transaction
- DexPair

Run with:
    pytest borg/defi/tests/test_data_models.py -v --tb=short
"""

import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import get_origin, get_args
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.data_models import (
    WhaleAlert,
    YieldOpportunity,
    Position,
    DeFiPackMetadata,
    TokenPrice,
    OHLCV,
    Transaction,
    DexPair,
    RiskAlert,
    SpendingLimit,
    WhitelistedContract,
    YieldChange,
    PortfolioSummary,
    RiskLevel,
)


# ---------------------------------------------------------------------------
# WhaleAlert Tests
# ---------------------------------------------------------------------------


class TestWhaleAlert:
    """Tests for WhaleAlert dataclass."""

    def test_whale_alert_minimal_init(self):
        """Test WhaleAlert with only required fields."""
        alert = WhaleAlert(
            wallet="TestWallet",
            chain="solana",
            action="swap",
            token_in="SOL",
            token_out="USDC",
            amount_usd=1000000.0,
            timestamp=1234567890.0,
            tx_hash="abc123",
            context="Large swap",
        )
        assert alert.wallet == "TestWallet"
        assert alert.chain == "solana"
        assert alert.action == "swap"
        assert alert.amount_usd == 1000000.0
        assert alert.signal_strength == 0.5  # default

    def test_whale_alert_with_signal_strength(self):
        """Test WhaleAlert with custom signal_strength."""
        alert = WhaleAlert(
            wallet="WhaleWallet",
            chain="ethereum",
            action="transfer",
            token_in="ETH",
            token_out="USDT",
            amount_usd=5000000.0,
            timestamp=1234567890.0,
            tx_hash="def456",
            context="Large transfer",
            signal_strength=0.9,
        )
        assert alert.signal_strength == 0.9

    def test_whale_alert_to_dict(self):
        """Test WhaleAlert serialization to dict."""
        alert = WhaleAlert(
            wallet="TestWallet",
            chain="solana",
            action="swap",
            token_in="SOL",
            token_out="USDC",
            amount_usd=1000000.0,
            timestamp=1234567890.0,
            tx_hash="abc123",
            context="Large swap",
            signal_strength=0.7,
        )
        result = alert.to_dict()
        assert isinstance(result, dict)
        assert result["wallet"] == "TestWallet"
        assert result["signal_strength"] == 0.7
        assert len(result) == 10  # 9 required fields + signal_strength

    def test_whale_alert_edge_case_zero_amount(self):
        """Test WhaleAlert with zero amount."""
        alert = WhaleAlert(
            wallet="TestWallet",
            chain="solana",
            action="transfer",
            token_in="SOL",
            token_out="SOL",
            amount_usd=0.0,
            timestamp=1234567890.0,
            tx_hash="zero123",
            context="Zero amount transfer",
        )
        assert alert.amount_usd == 0.0

    def test_whale_alert_unicode_symbols(self):
        """Test WhaleAlert with Unicode in strings."""
        alert = WhaleAlert(
            wallet="钱包地址",
            chain="solana",
            action="swap",
            token_in="SOL🔺",
            token_out="USDC€",
            amount_usd=100.0,
            timestamp=1234567890.0,
            tx_hash="unicode123",
            context="Unicode 测试",
        )
        assert "钱包" in alert.wallet

    def test_whale_alert_max_float(self):
        """Test WhaleAlert with max float values."""
        alert = WhaleAlert(
            wallet="MaxWallet",
            chain="ethereum",
            action="swap",
            token_in="ETH",
            token_out="USDC",
            amount_usd=sys.float_info.max,
            timestamp=1e308,
            tx_hash="max123",
            context="Max values",
        )
        assert alert.amount_usd == sys.float_info.max


# ---------------------------------------------------------------------------
# YieldOpportunity Tests
# ---------------------------------------------------------------------------


class TestYieldOpportunity:
    """Tests for YieldOpportunity dataclass."""

    def test_yield_opportunity_required_fields(self):
        """Test YieldOpportunity with required fields only."""
        opp = YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aUSDC",
            token="USDC",
            apy=5.5,
            tvl=100000000.0,
            risk_score=0.2,
            il_risk=False,
            url="https://aave.com",
            last_updated=1234567890.0,
        )
        assert opp.protocol == "aave"
        assert opp.apy == 5.5
        assert opp.project_name is None  # optional

    def test_yield_opportunity_with_optional_fields(self):
        """Test YieldOpportunity with all optional fields."""
        opp = YieldOpportunity(
            protocol="kamino",
            chain="solana",
            pool="Kamino Lend",
            token="SOL",
            apy=12.5,
            tvl=50000000.0,
            risk_score=0.4,
            il_risk=True,
            url="https://kamino.finance",
            last_updated=1234567890.0,
            project_name="Kamino Finance",
            symbol="kSOL",
            pool_id="kamino_pool_1",
        )
        assert opp.project_name == "Kamino Finance"
        assert opp.symbol == "kSOL"
        assert opp.pool_id == "kamino_pool_1"

    def test_yield_opportunity_post_init_risk_clamping(self):
        """Test YieldOpportunity __post_init__ clamps risk_score to 0-1."""
        # risk_score > 1 should be clamped to 1
        opp_high = YieldOpportunity(
            protocol="test",
            chain="solana",
            pool="test",
            token="TEST",
            apy=10.0,
            tvl=1000.0,
            risk_score=1.5,
            il_risk=False,
            url="https://test.com",
            last_updated=0.0,
        )
        assert opp_high.risk_score == 1.0

        # risk_score < 0 should be clamped to 0
        opp_low = YieldOpportunity(
            protocol="test",
            chain="solana",
            pool="test",
            token="TEST",
            apy=10.0,
            tvl=1000.0,
            risk_score=-0.5,
            il_risk=False,
            url="https://test.com",
            last_updated=0.0,
        )
        assert opp_low.risk_score == 0.0

    def test_yield_opportunity_post_init_apy_clamping(self):
        """Test YieldOpportunity __post_init__ clamps negative APY to 0."""
        opp = YieldOpportunity(
            protocol="test",
            chain="solana",
            pool="test",
            token="TEST",
            apy=-5.0,
            tvl=1000.0,
            risk_score=0.5,
            il_risk=False,
            url="https://test.com",
            last_updated=0.0,
        )
        assert opp.apy == 0.0

    def test_yield_opportunity_post_init_tvl_clamping(self):
        """Test YieldOpportunity __post_init__ clamps negative TVL to 0."""
        opp = YieldOpportunity(
            protocol="test",
            chain="solana",
            pool="test",
            token="TEST",
            apy=10.0,
            tvl=-1000.0,
            risk_score=0.5,
            il_risk=False,
            url="https://test.com",
            last_updated=0.0,
        )
        assert opp.tvl == 0.0


# ---------------------------------------------------------------------------
# Position Tests
# ---------------------------------------------------------------------------


class TestPosition:
    """Tests for Position dataclass."""

    def test_position_required_fields(self):
        """Test Position with required fields only."""
        pos = Position(
            chain="solana",
            protocol="kamino",
            token="SOL",
            amount=100.0,
            value_usd=5000.0,
            entry_price=50.0,
            current_price=50.0,
        )
        assert pos.chain == "solana"
        assert pos.pnl_usd == 0.0  # default
        assert pos.health_factor is None  # optional

    def test_position_with_pnl_calculation(self):
        """Test Position __post_init__ calculates PnL correctly."""
        pos = Position(
            chain="solana",
            protocol="kamino",
            token="SOL",
            amount=10.0,
            value_usd=500.0,
            entry_price=50.0,
            current_price=60.0,
        )
        assert pos.pnl_usd == 100.0  # (60-50) * 10
        assert pos.pnl_pct == pytest.approx(20.0, rel=1e-9)  # (60/50 - 1) * 100

    def test_position_with_explicit_pnl(self):
        """Test Position allows explicit PnL values."""
        pos = Position(
            chain="ethereum",
            protocol="aave",
            token="ETH",
            amount=5.0,
            value_usd=10000.0,
            entry_price=1800.0,
            current_price=2000.0,
            pnl_usd=1000.0,
            pnl_pct=11.11,
        )
        assert pos.pnl_usd == 1000.0
        assert pos.pnl_pct == 11.11

    def test_position_health_factor(self):
        """Test Position with health_factor."""
        pos = Position(
            chain="ethereum",
            protocol="aave",
            token="ETH",
            amount=10.0,
            value_usd=20000.0,
            entry_price=1800.0,
            current_price=2000.0,
            health_factor=1.5,
        )
        assert pos.health_factor == 1.5

    def test_position_edge_case_zero_entry_price(self):
        """Test Position with zero entry price skips PnL calculation."""
        pos = Position(
            chain="solana",
            protocol="kamino",
            token="SOL",
            amount=10.0,
            value_usd=500.0,
            entry_price=0.0,
            current_price=50.0,
        )
        assert pos.pnl_usd == 0.0


# ---------------------------------------------------------------------------
# DeFiPackMetadata Tests
# ---------------------------------------------------------------------------


class TestDeFiPackMetadata:
    """Tests for DeFiPackMetadata dataclass."""

    def test_defi_pack_metadata_defaults(self):
        """Test DeFiPackMetadata with all defaults."""
        meta = DeFiPackMetadata()
        assert meta.total_trades == 0
        assert meta.winning_trades == 0
        assert meta.chains == []
        assert meta.protocols == []

    def test_defi_pack_metadata_full_init(self):
        """Test DeFiPackMetadata with all fields."""
        meta = DeFiPackMetadata(
            total_trades=100,
            winning_trades=65,
            total_pnl_usd=5000.0,
            max_drawdown_pct=15.0,
            sharpe_ratio=1.5,
            win_rate=65.0,
            avg_return_per_trade=50.0,
            last_trade_timestamp=1234567890.0,
            chains=["solana", "ethereum"],
            protocols=["kamino", "aave"],
        )
        assert meta.total_trades == 100
        assert meta.win_rate == 65.0
        assert len(meta.chains) == 2

    def test_defi_pack_metadata_to_dict(self):
        """Test DeFiPackMetadata serialization."""
        meta = DeFiPackMetadata(
            total_trades=50,
            winning_trades=30,
            chains=["solana"],
            protocols=["kamino"],
        )
        result = meta.to_dict()
        assert isinstance(result, dict)
        assert result["total_trades"] == 50
        assert result["chains"] == ["solana"]

    def test_defi_pack_metadata_empty_lists(self):
        """Test DeFiPackMetadata with empty chain/protocol lists."""
        meta = DeFiPackMetadata(
            chains=[],
            protocols=[],
        )
        assert meta.chains == []
        assert meta.protocols == []


# ---------------------------------------------------------------------------
# TokenPrice Tests
# ---------------------------------------------------------------------------


class TestTokenPrice:
    """Tests for TokenPrice dataclass."""

    def test_token_price_required_fields(self):
        """Test TokenPrice with only required fields."""
        tp = TokenPrice(
            symbol="SOL",
            address="So11111111111111111111111111111111111111112",
        )
        assert tp.symbol == "SOL"
        assert tp.price == 0.0  # default
        assert tp.timestamp == 0.0  # default

    def test_token_price_full_init(self):
        """Test TokenPrice with all fields."""
        tp = TokenPrice(
            symbol="SOL",
            address="So11111111111111111111111111111111111111112",
            price=100.50,
            price_native=1.0,
            timestamp=1234567890.0,
            volume_24h=1000000000.0,
        )
        assert tp.price == 100.50
        assert tp.volume_24h == 1e9

    def test_token_price_to_dict(self):
        """Test TokenPrice serialization."""
        tp = TokenPrice(
            symbol="BTC",
            address="0x1234",
            price=50000.0,
        )
        result = tp.to_dict()
        assert result["symbol"] == "BTC"
        assert result["price"] == 50000.0

    def test_token_price_edge_case_max_float(self):
        """Test TokenPrice with max float price."""
        tp = TokenPrice(
            symbol="SHIT",
            address="0x9999",
            price=sys.float_info.max,
        )
        assert tp.price == sys.float_info.max


# ---------------------------------------------------------------------------
# OHLCV Tests
# ---------------------------------------------------------------------------


class TestOHLCV:
    """Tests for OHLCV dataclass."""

    def test_ohlcv_required_fields(self):
        """Test OHLCV with only required fields."""
        ohlcv = OHLCV(
            timestamp=1234567890.0,
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000.0,
        )
        assert ohlcv.open == 100.0
        assert ohlcv.symbol == ""  # default

    def test_ohlcv_full_init(self):
        """Test OHLCV with all fields."""
        ohlcv = OHLCV(
            timestamp=1234567890.0,
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000.0,
            symbol="SOL",
            address="So11111111111111111111111111111111111111112",
        )
        assert ohlcv.symbol == "SOL"
        assert ohlcv.address == "So11111111111111111111111111111111111111112"

    def test_ohlcv_to_dict(self):
        """Test OHLCV serialization."""
        ohlcv = OHLCV(
            timestamp=1234567890.0,
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000.0,
        )
        result = ohlcv.to_dict()
        assert len(result) == 8  # timestamp, open, high, low, close, volume, symbol, address
        assert result["close"] == 103.0

    def test_ohlcv_unicode_symbol(self):
        """Test OHLCV with Unicode symbol."""
        ohlcv = OHLCV(
            timestamp=1234567890.0,
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000.0,
            symbol="测试",
        )
        assert "测试" in ohlcv.symbol


# ---------------------------------------------------------------------------
# Transaction Tests
# ---------------------------------------------------------------------------


class TestTransaction:
    """Tests for Transaction dataclass."""

    def test_transaction_required_fields(self):
        """Test Transaction with only required fields."""
        tx = Transaction(
            signature="sig123",
            slot=100,
            timestamp=1234567890.0,
            fee=5000,
            status="success",
            type="swap",
        )
        assert tx.accounts == []  # default
        assert tx.token_balances == {}  # default
        assert tx.error is None  # optional

    def test_transaction_full_init(self):
        """Test Transaction with all fields."""
        tx = Transaction(
            signature="sig456",
            slot=200,
            timestamp=1234567890.0,
            fee=10000,
            status="failed",
            type="swap",
            accounts=["acc1", "acc2"],
            token_balances={
                "SOL": {"before": 100.0, "after": 90.0},
            },
            error="Insufficient funds",
        )
        assert len(tx.accounts) == 2
        assert tx.error == "Insufficient funds"

    def test_transaction_to_dict(self):
        """Test Transaction serialization."""
        tx = Transaction(
            signature="sig789",
            slot=300,
            timestamp=1234567890.0,
            fee=5000,
            status="success",
            type="transfer",
        )
        result = tx.to_dict()
        assert result["signature"] == "sig789"
        assert result["status"] == "success"

    def test_transaction_with_token_balances(self):
        """Test Transaction with complex token balances."""
        tx = Transaction(
            signature="sig_complex",
            slot=400,
            timestamp=1234567890.0,
            fee=5000,
            status="success",
            type="swap",
            token_balances={
                "SOL": {"before": 100.0, "after": 90.0},
                "USDC": {"before": 5000.0, "after": 5100.0},
            },
        )
        assert "SOL" in tx.token_balances
        assert tx.token_balances["USDC"]["after"] == 5100.0


# ---------------------------------------------------------------------------
# DexPair Tests
# ---------------------------------------------------------------------------


class TestDexPair:
    """Tests for DexPair dataclass."""

    def test_dex_pair_required_fields(self):
        """Test DexPair with only required fields."""
        pair = DexPair(
            pair_address="Pair123",
            base_token="SOL",
            base_token_address="So11111111111111111111111111111111111111112",
            quote_token="USDC",
            quote_token_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        )
        assert pair.price_usd == 0.0  # default
        assert pair.chain == ""  # default

    def test_dex_pair_full_init(self):
        """Test DexPair with all fields."""
        pair = DexPair(
            pair_address="Pair456",
            base_token="SOL",
            base_token_address="So11111111111111111111111111111111111111112",
            quote_token="USDC",
            quote_token_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            price_usd=100.50,
            volume_24h=50000000.0,
            liquidity_usd=100000000.0,
            tx_count_24h=10000,
            price_change_24h=5.5,
            chain="solana",
            dex="raydium",
            timestamp=1234567890.0,
        )
        assert pair.price_usd == 100.50
        assert pair.tx_count_24h == 10000
        assert pair.dex == "raydium"

    def test_dex_pair_to_dict(self):
        """Test DexPair serialization."""
        pair = DexPair(
            pair_address="Pair789",
            base_token="BTC",
            base_token_address="0xbtc",
            quote_token="ETH",
            quote_token_address="0xeth",
            price_usd=50000.0,
        )
        result = pair.to_dict()
        assert result["pair_address"] == "Pair789"
        assert result["price_usd"] == 50000.0
        assert len(result) == 13  # All 13 fields

    def test_dex_pair_edge_case_negative_price_change(self):
        """Test DexPair with negative price change."""
        pair = DexPair(
            pair_address="PairNeg",
            base_token="DOGE",
            base_token_address="0xdoge",
            quote_token="SOL",
            quote_token_address="0xsol",
            price_change_24h=-15.5,
        )
        assert pair.price_change_24h == -15.5

    def test_dex_pair_extremely_long_strings(self):
        """Test DexPair with extremely long string fields."""
        long_string = "x" * 10000
        pair = DexPair(
            pair_address=long_string,
            base_token=long_string,
            base_token_address=long_string,
            quote_token=long_string,
            quote_token_address=long_string,
        )
        assert len(pair.base_token) == 10000
        assert len(pair.pair_address) == 10000


# ---------------------------------------------------------------------------
# Other Dataclass Tests (brief coverage for completeness)
# ---------------------------------------------------------------------------


class TestOtherDataclasses:
    """Tests for other dataclasses."""

    def test_risk_alert_defaults(self):
        """Test RiskAlert with defaults."""
        alert = RiskAlert(
            alert_type="concentration",
            severity="warning",
            message="High concentration in SOL",
        )
        assert alert.affected_positions == []
        assert alert.timestamp > 0  # auto-set

    def test_spending_limit_can_spend(self):
        """Test SpendingLimit.can_spend()."""
        limit = SpendingLimit(
            per_trade_limit=1000.0,
            daily_limit=5000.0,
            daily_spent=1000.0,
        )
        assert limit.can_spend(500.0) is True
        assert limit.can_spend(1001.0) is False  # per-trade limit

    def test_spending_limit_add_spend(self):
        """Test SpendingLimit.add_spend()."""
        limit = SpendingLimit(
            per_trade_limit=1000.0,
            daily_limit=5000.0,
        )
        limit.add_spend(100.0)
        assert limit.daily_spent == 100.0

    def test_whitelisted_contract_defaults(self):
        """Test WhitelistedContract with defaults."""
        wc = WhitelistedContract(
            address="0x123",
            chain="ethereum",
            name="Test Contract",
            contract_type="router",
        )
        assert wc.added_at > 0  # auto-set

    def test_yield_change(self):
        """Test YieldChange."""
        yc = YieldChange(
            pool_id="pool1",
            protocol="aave",
            chain="ethereum",
            previous_apy=5.0,
            current_apy=10.0,
            change_pct=100.0,
            is_spike=True,
        )
        assert yc.is_spike is True
        assert yc.change_pct == 100.0

    def test_portfolio_summary(self):
        """Test PortfolioSummary."""
        ps = PortfolioSummary(
            total_value_usd=100000.0,
            total_pnl_usd=5000.0,
            total_pnl_pct=5.0,
            daily_change_usd=1000.0,
            daily_change_pct=1.0,
            positions=[],
            risk_alerts=[],
            allocations={"SOL": 50.0, "ETH": 50.0},
        )
        assert ps.total_value_usd == 100000.0
        assert len(ps.allocations) == 2

    def test_risk_level_enum(self):
        """Test RiskLevel enum values."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.CRITICAL.value == "critical"
