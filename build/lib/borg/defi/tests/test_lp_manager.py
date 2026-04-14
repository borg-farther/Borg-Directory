"""
Tests for lp_manager — concentrated liquidity position management.

Tests:
    LPPosition dataclass
    UniswapV3Position → LPPosition conversion
    OrcaWhirlpoolPosition → LPPosition conversion
    monitor_positions() — price checking and status updates
    calculate_il() — IL estimation
    suggest_rebalance() — rebalance suggestions
    track_fees() — fee accumulation
    format_lp_report() — daily report generation
    format_lp_report_text() — text formatting

Run with:
    pytest borg/defi/tests/test_lp_manager.py -v --tb=short
    BORG_DEFI_INTEGRATION=true pytest borg/defi/tests/test_lp_manager.py -v -k integration
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.defi.lp_manager import (
    LPPosition,
    UniswapV3Position,
    OrcaWhirlpoolPosition,
    RebalanceSuggestion,
    FeeUpdate,
    LPReport,
    Protocol,
    Chain,
    PositionStatus,
    calculate_il,
    _price_to_status,
    _tick_to_status,
    monitor_positions,
    suggest_rebalance,
    _suggest_uniswap_rebalance,
    _suggest_orca_rebalance,
    track_fees,
    format_lp_report,
    format_lp_report_text,
    get_current_price,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_dex_client():
    """Mock DexScreenerClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def sample_uni_position():
    """Sample Uniswap V3 LP position."""
    return LPPosition(
        protocol=Protocol.UNISWAP_V3.value,
        chain=Chain.ETHEREUM.value,
        pair_address="0x1234...uniswap-v3-pool",
        token0="WETH",
        token1="USDC",
        token0_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        token1_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        lower_price=1800.0,   # $1800 USDC per ETH
        upper_price=2200.0,   # $2200 USDC per ETH
        liquidity=1_000_000.0,
        amount0=1.0,          # 1 WETH
        amount1=2000.0,       # 2000 USDC
        value_usd=3000.0,
        position_id="12345",
        opened_at=datetime.now().timestamp() - 86400 * 7,  # 7 days ago
        status=PositionStatus.IN_RANGE.value,
    )


@pytest.fixture
def sample_orca_position():
    """Sample Orca Whirlpool LP position."""
    return LPPosition(
        protocol=Protocol.ORCA_WHIRLPOOLS.value,
        chain=Chain.SOLANA.value,
        pair_address="orca_whirlpool_abc123",
        token0="SOL",
        token1="USDC",
        token0_address="So11111111111111111111111111111111111111112",
        token1_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        lower_price=80.0,     # $80 USDC per SOL
        upper_price=120.0,    # $120 USDC per SOL
        liquidity=5_000_000.0,
        amount0=10.0,         # 10 SOL
        amount1=1000.0,       # 1000 USDC
        value_usd=2000.0,
        position_id="orca_position_mint_xyz",
        opened_at=datetime.now().timestamp() - 86400 * 3,
        status=PositionStatus.IN_RANGE.value,
    )


# ---------------------------------------------------------------------------
# LPPosition Dataclass Tests
# ---------------------------------------------------------------------------

class TestLPPosition:
    def test_lp_position_creation(self):
        """Test basic LPPosition creation and defaults."""
        pos = LPPosition(
            protocol=Protocol.UNISWAP_V3.value,
            chain=Chain.ETHEREUM.value,
            pair_address="0xpool",
            token0="WETH",
            token1="USDC",
        )
        assert pos.protocol == "uniswap_v3"
        assert pos.chain == "ethereum"
        assert pos.token0 == "WETH"
        assert pos.token1 == "USDC"
        assert pos.status == PositionStatus.NOT_INITIALIZED.value
        assert pos.fees_earned_usd == 0.0
        assert pos.il_estimate_usd == 0.0
        assert pos.opened_at > 0
        assert pos.last_monitored > 0

    def test_lp_position_to_dict(self):
        """Test to_dict serialization."""
        pos = LPPosition(
            protocol=Protocol.ORCA_WHIRLPOOLS.value,
            chain=Chain.SOLANA.value,
            pair_address="orca_pool",
            token0="SOL",
            token1="USDC",
            value_usd=5000.0,
            fees_earned_usd=25.50,
            lower_price=80.0,
            upper_price=120.0,
        )
        d = pos.to_dict()
        assert d["protocol"] == "orca_whirlpools"
        assert d["chain"] == "solana"
        assert d["value_usd"] == 5000.0
        assert d["fees_earned_usd"] == 25.50
        assert "lower_price" in d
        assert "upper_price" in d


# ---------------------------------------------------------------------------
# Uniswap V3 Position Tests
# ---------------------------------------------------------------------------

class TestUniswapV3Position:
    def test_uni_position_to_lp_position(self):
        """Test UniswapV3Position → LPPosition conversion."""
        uni_pos = UniswapV3Position(
            token_id=12345,
            owner="0xOwnerWallet",
            tick_lower=-100000,   # ~0.0000... very low
            tick_upper=100000,    # ~2200
            liquidity=1_000_000,
            tokens_owed0=0,
            tokens_owed1=0,
        )
        pair_data = {
            "chain": "ethereum",
            "pair_address": "0xPoolAddress",
            "token0": "WETH",
            "token1": "USDC",
            "token0_address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "token1_address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "current_tick": 50000,  # mid range
        }
        lp = uni_pos.to_lp_position(pair_data)
        assert lp.protocol == "uniswap_v3"
        assert lp.position_id == "12345"
        assert lp.lower_price > 0
        assert lp.upper_price > 0
        assert lp.status in [PositionStatus.IN_RANGE.value,
                              PositionStatus.OUT_OF_RANGE_ABOVE.value,
                              PositionStatus.OUT_OF_RANGE_BELOW.value]


# ---------------------------------------------------------------------------
# Orca Whirlpool Position Tests
# ---------------------------------------------------------------------------

class TestOrcaWhirlpoolPosition:
    def test_orca_position_to_lp_position(self):
        """Test OrcaWhirlpoolPosition → LPPosition conversion."""
        orca_pos = OrcaWhirlpoolPosition(
            position_mint="position_mint_abc",
            whirlpool="whirlpool_def",
            tick_lower_index=10,   # multiplied by tick_spacing
            tick_upper_index=20,
            liquidity=5_000_000,
        )
        pair_data = {
            "chain": "solana",
            "token0": "SOL",
            "token1": "USDC",
            "token0_address": "So11111111111111111111111111111111111111112",
            "token1_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "tick_spacing": 64,
            "current_tick": 15,
        }
        lp = orca_pos.to_lp_position(pair_data)
        assert lp.protocol == "orca_whirlpools"
        assert lp.chain == "solana"
        assert lp.position_id == "position_mint_abc"
        assert lp.lower_price > 0
        assert lp.upper_price > lp.lower_price


# ---------------------------------------------------------------------------
# Status Helpers Tests
# ---------------------------------------------------------------------------

class TestStatusHelpers:
    def test_price_in_range(self):
        """Price within bounds → IN_RANGE."""
        status = _price_to_status(current_price=2000.0, lower_price=1800.0, upper_price=2200.0)
        assert status == PositionStatus.IN_RANGE.value

    def test_price_below_lower(self):
        """Price below lower bound → OUT_OF_RANGE_BELOW."""
        status = _price_to_status(current_price=1500.0, lower_price=1800.0, upper_price=2200.0)
        assert status == PositionStatus.OUT_OF_RANGE_BELOW.value

    def test_price_above_upper(self):
        """Price above upper bound → OUT_OF_RANGE_ABOVE."""
        status = _price_to_status(current_price=2500.0, lower_price=1800.0, upper_price=2200.0)
        assert status == PositionStatus.OUT_OF_RANGE_ABOVE.value

    def test_price_at_exact_bounds(self):
        """Price at exact bounds → IN_RANGE."""
        status = _price_to_status(current_price=1800.0, lower_price=1800.0, upper_price=2200.0)
        assert status == PositionStatus.IN_RANGE.value
        status = _price_to_status(current_price=2200.0, lower_price=1800.0, upper_price=2200.0)
        assert status == PositionStatus.IN_RANGE.value

    def test_invalid_prices(self):
        """Zero or negative prices → NOT_INITIALIZED."""
        assert _price_to_status(0.0, 1800.0, 2200.0) == PositionStatus.NOT_INITIALIZED.value
        assert _price_to_status(-100.0, 1800.0, 2200.0) == PositionStatus.NOT_INITIALIZED.value

    def test_tick_to_status_in_range(self):
        """Tick in range → IN_RANGE."""
        assert _tick_to_status(50000, 40000, 60000) == PositionStatus.IN_RANGE.value

    def test_tick_to_status_below(self):
        """Tick below lower → OUT_OF_RANGE_BELOW."""
        assert _tick_to_status(30000, 40000, 60000) == PositionStatus.OUT_OF_RANGE_BELOW.value

    def test_tick_to_status_above(self):
        """Tick above upper → OUT_OF_RANGE_ABOVE."""
        assert _tick_to_status(70000, 40000, 60000) == PositionStatus.OUT_OF_RANGE_ABOVE.value


# ---------------------------------------------------------------------------
# calculate_il() Tests
# ---------------------------------------------------------------------------

class TestCalculateIL:
    def test_il_in_range_zero(self):
        """IL should be 0 when price is in range."""
        il_usd, il_pct = calculate_il(
            current_price=2000.0,
            lower_price=1800.0,
            upper_price=2200.0,
            value_usd=3000.0,
        )
        assert il_usd == 0.0
        assert il_pct == 0.0

    def test_il_below_range(self):
        """IL when price drops below range."""
        il_usd, il_pct = calculate_il(
            current_price=1500.0,  # 25% below range center
            lower_price=1800.0,
            upper_price=2200.0,
            value_usd=3000.0,
        )
        assert il_usd > 0
        assert il_pct > 0

    def test_il_above_range(self):
        """IL when price rises above range."""
        il_usd, il_pct = calculate_il(
            current_price=3000.0,  # above range
            lower_price=1800.0,
            upper_price=2200.0,
            value_usd=3000.0,
        )
        assert il_usd > 0
        assert il_pct > 0
        assert il_pct <= 50.0  # IL should be capped at 50%

    def test_il_invalid_prices(self):
        """Invalid prices → 0 IL."""
        assert calculate_il(0.0, 1800.0, 2200.0, 3000.0) == (0.0, 0.0)
        assert calculate_il(-100.0, 1800.0, 2200.0, 3000.0) == (0.0, 0.0)
        assert calculate_il(2000.0, 0.0, 2200.0, 3000.0) == (0.0, 0.0)

    def test_il_proportional_to_value(self):
        """IL should scale with position value."""
        il_usd_1, _ = calculate_il(1500.0, 1800.0, 2200.0, 3000.0)
        il_usd_2, _ = calculate_il(1500.0, 1800.0, 2200.0, 6000.0)
        assert il_usd_2 == pytest.approx(il_usd_1 * 2, rel=0.01)


# ---------------------------------------------------------------------------
# track_fees() Tests
# ---------------------------------------------------------------------------

class TestTrackFees:
    def test_track_fees_basic(self, sample_uni_position):
        """Test basic fee tracking."""
        sample_uni_position.fees_earned_token0 = 0.01  # 0.01 WETH
        sample_uni_position.fees_earned_token1 = 20.0  # 20 USDC
        sample_uni_position.last_fee_update = datetime.now().timestamp() - 3600

        update = track_fees(
            sample_uni_position,
            token0_price_usd=2000.0,  # ETH at $2000
            token1_price_usd=1.0,     # USDC at $1
        )

        assert update.fees_token0 == 0.01
        assert update.fees_token1 == 20.0
        assert update.fees_usd == pytest.approx(40.0, rel=0.01)  # 0.01*2000 + 20*1
        assert update.elapsed_seconds == pytest.approx(3600, rel=0.1)

    def test_track_fees_updates_position(self, sample_orca_position):
        """Test that track_fees updates the position."""
        sample_orca_position.fees_earned_token0 = 0.5  # 0.5 SOL
        sample_orca_position.fees_earned_token1 = 5.0  # 5 USDC
        sample_orca_position.last_fee_update = 0

        update = track_fees(
            sample_orca_position,
            token0_price_usd=100.0,
            token1_price_usd=1.0,
        )

        assert sample_orca_position.fees_earned_usd == 55.0  # 0.5*100 + 5*1
        assert sample_orca_position.last_fee_update > 0

    def test_track_fees_zero_fees(self, sample_uni_position):
        """Test tracking with zero accumulated fees."""
        update = track_fees(sample_uni_position, 2000.0, 1.0)
        assert update.fees_usd == 0.0


# ---------------------------------------------------------------------------
# monitor_positions() Tests
# ---------------------------------------------------------------------------

class TestMonitorPositions:
    @pytest.mark.asyncio
    async def test_monitor_in_range(self, sample_uni_position, mock_dex_client):
        """Test monitoring a position that's in range."""
        # Mock DexScreener returning a pair
        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair.price_usd = 2000.0
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        positions = [sample_uni_position]
        updated = await monitor_positions(positions, mock_dex_client)

        assert len(updated) == 1
        assert updated[0].status == PositionStatus.IN_RANGE.value
        assert updated[0].last_monitored > 0

    @pytest.mark.asyncio
    async def test_monitor_out_of_range_below(self, sample_uni_position, mock_dex_client):
        """Test monitoring when price drops below range."""
        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair.price_usd = 1500.0  # Below 1800 lower bound
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        updated = await monitor_positions([sample_uni_position], mock_dex_client)

        assert updated[0].status == PositionStatus.OUT_OF_RANGE_BELOW.value
        assert updated[0].il_estimate_usd > 0

    @pytest.mark.asyncio
    async def test_monitor_out_of_range_above(self, sample_uni_position, mock_dex_client):
        """Test monitoring when price rises above range."""
        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair.price_usd = 2500.0  # Above 2200 upper bound
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        updated = await monitor_positions([sample_uni_position], mock_dex_client)

        assert updated[0].status == PositionStatus.OUT_OF_RANGE_ABOVE.value

    @pytest.mark.asyncio
    async def test_monitor_no_price_found(self, sample_uni_position, mock_dex_client):
        """Test monitoring when no price can be fetched."""
        mock_dex_client.search_pairs = AsyncMock(return_value=None)
        updated = await monitor_positions([sample_uni_position], mock_dex_client)
        assert updated[0].status == PositionStatus.NOT_INITIALIZED.value

    @pytest.mark.asyncio
    async def test_monitor_multiple_positions(self, sample_uni_position, sample_orca_position, mock_dex_client):
        """Test monitoring multiple positions at once."""
        # Uniswap position price
        mock_pair1 = MagicMock()
        mock_pair1.chain = "ethereum"
        mock_pair1.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair1.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair1.price_usd = 2000.0

        # Orca position price
        mock_pair2 = MagicMock()
        mock_pair2.chain = "solana"
        mock_pair2.base_token_address = sample_orca_position.token0_address.lower()
        mock_pair2.quote_token_address = sample_orca_position.token1_address.lower()
        mock_pair2.price_usd = 100.0

        mock_dex_client.search_pairs = AsyncMock(side_effect=[[mock_pair1], [mock_pair2]])

        updated = await monitor_positions([sample_uni_position, sample_orca_position], mock_dex_client)
        assert len(updated) == 2
        assert updated[0].status == PositionStatus.IN_RANGE.value
        assert updated[1].status == PositionStatus.IN_RANGE.value


# ---------------------------------------------------------------------------
# suggest_rebalance() Tests
# ---------------------------------------------------------------------------

class TestSuggestRebalance:
    @pytest.mark.asyncio
    async def test_suggest_rebalance_out_of_range_below(self, sample_uni_position, mock_dex_client):
        """Test rebalance suggestion when price is below range."""
        sample_uni_position.status = PositionStatus.OUT_OF_RANGE_BELOW.value
        sample_uni_position.fees_earned_usd = 25.0
        sample_uni_position.il_estimate_usd = 50.0
        sample_uni_position.il_pct = 1.67

        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair.price_usd = 1500.0
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        suggestion = await suggest_rebalance(sample_uni_position, mock_dex_client)

        assert suggestion is not None
        assert suggestion.severity in ["warning", "critical"]
        assert "below" in suggestion.message.lower() or "fallen" in suggestion.message.lower()
        assert suggestion.estimated_cost_usd > 0

    @pytest.mark.asyncio
    async def test_suggest_rebalance_out_of_range_above(self, sample_uni_position, mock_dex_client):
        """Test rebalance suggestion when price is above range."""
        sample_uni_position.status = PositionStatus.OUT_OF_RANGE_ABOVE.value
        sample_uni_position.fees_earned_usd = 50.0
        sample_uni_position.il_estimate_usd = 75.0
        sample_uni_position.il_pct = 2.5

        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair.price_usd = 2500.0
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        suggestion = await suggest_rebalance(sample_uni_position, mock_dex_client)

        assert suggestion is not None
        assert suggestion.current_status == PositionStatus.OUT_OF_RANGE_ABOVE.value
        assert "rebalance" in suggestion.suggested_action.lower()

    @pytest.mark.asyncio
    async def test_suggest_rebalance_in_range(self, sample_uni_position, mock_dex_client):
        """No suggestion when price is in range."""
        sample_uni_position.status = PositionStatus.IN_RANGE.value
        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = sample_uni_position.token0_address.lower()
        mock_pair.quote_token_address = sample_uni_position.token1_address.lower()
        mock_pair.price_usd = 2000.0
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        suggestion = await suggest_rebalance(sample_uni_position, mock_dex_client)
        assert suggestion is None

    @pytest.mark.asyncio
    async def test_suggest_orca_rebalance(self, sample_orca_position, mock_dex_client):
        """Test Orca rebalance suggestion with Solana gas costs."""
        sample_orca_position.status = PositionStatus.OUT_OF_RANGE_BELOW.value
        sample_orca_position.fees_earned_usd = 10.0
        sample_orca_position.il_estimate_usd = 30.0
        sample_orca_position.il_pct = 1.5

        mock_pair = MagicMock()
        mock_pair.chain = "solana"
        mock_pair.base_token_address = sample_orca_position.token0_address.lower()
        mock_pair.quote_token_address = sample_orca_position.token1_address.lower()
        mock_pair.price_usd = 60.0  # Below 80 lower bound
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        suggestion = await suggest_rebalance(sample_orca_position, mock_dex_client)

        assert suggestion is not None
        # Solana gas cost is ~$0.25
        assert suggestion.estimated_cost_usd < 1.0

    def test_rebalance_suggestion_to_dict(self):
        """Test RebalanceSuggestion serialization."""
        s = RebalanceSuggestion(
            position_id="pos123",
            pair="ETH/USDC",
            current_price=1500.0,
            lower_price=1800.0,
            upper_price=2200.0,
            current_status="out_of_range_below",
            severity="critical",
            message="Price below range",
            suggested_action="rebalance",
            estimated_cost_usd=5.0,
        )
        d = s.to_dict()
        assert d["position_id"] == "pos123"
        assert d["pair"] == "ETH/USDC"
        assert d["severity"] == "critical"
        assert d["estimated_cost_usd"] == 5.0


# ---------------------------------------------------------------------------
# format_lp_report() Tests
# ---------------------------------------------------------------------------

class TestFormatLPReport:
    def test_format_lp_report_basic(self, sample_uni_position, sample_orca_position):
        """Test basic report generation."""
        sample_uni_position.value_usd = 3000.0
        sample_uni_position.fees_earned_usd = 25.0
        sample_uni_position.il_estimate_usd = 50.0
        sample_uni_position.status = PositionStatus.IN_RANGE.value

        sample_orca_position.value_usd = 2000.0
        sample_orca_position.fees_earned_usd = 10.0
        sample_orca_position.il_estimate_usd = 30.0
        sample_orca_position.status = PositionStatus.OUT_OF_RANGE_BELOW.value

        report = format_lp_report([sample_uni_position, sample_orca_position])

        assert report.positions_count == 2
        assert report.total_value_usd == 5000.0
        assert report.total_fees_earned_usd == 35.0
        assert report.total_il_usd == 80.0
        assert report.in_range_count == 1
        assert report.out_of_range_count == 1

    def test_format_lp_report_with_suggestions(self, sample_uni_position):
        """Test report with rebalance suggestions."""
        sample_uni_position.value_usd = 3000.0
        sample_uni_position.status = PositionStatus.OUT_OF_RANGE_ABOVE.value

        suggestion = RebalanceSuggestion(
            position_id="12345",
            pair="ETH/USDC",
            current_price=2500.0,
            lower_price=1800.0,
            upper_price=2200.0,
            current_status="out_of_range_above",
            severity="warning",
            message="Price above range",
            suggested_action="rebalance",
            estimated_cost_usd=5.0,
        )

        report = format_lp_report([sample_uni_position], rebalance_suggestions=[suggestion])

        assert len(report.rebalance_suggestions) == 1
        assert report.rebalance_suggestions[0]["pair"] == "ETH/USDC"

    def test_format_lp_report_empty(self):
        """Test report with no positions."""
        report = format_lp_report([])
        assert report.positions_count == 0
        assert report.total_value_usd == 0.0
        assert report.in_range_count == 0

    def test_lp_report_to_dict(self, sample_uni_position):
        """Test LPReport serialization."""
        sample_uni_position.value_usd = 3000.0
        report = format_lp_report([sample_uni_position])
        d = report.to_dict()
        assert "generated_at_str" in d
        assert d["positions_count"] == 1
        assert d["total_value_usd"] == 3000.0

    def test_format_lp_report_text(self, sample_uni_position, sample_orca_position):
        """Test text report formatting."""
        sample_uni_position.value_usd = 3000.0
        sample_uni_position.fees_earned_usd = 25.0
        sample_uni_position.il_estimate_usd = 50.0
        sample_uni_position.status = PositionStatus.IN_RANGE.value

        sample_orca_position.value_usd = 2000.0
        sample_orca_position.fees_earned_usd = 10.0
        sample_orca_position.il_estimate_usd = 30.0
        sample_orca_position.status = PositionStatus.OUT_OF_RANGE_BELOW.value

        report = format_lp_report([sample_uni_position, sample_orca_position])
        text = format_lp_report_text(report)

        assert "DAILY LP PERFORMANCE REPORT" in text
        assert "Total Positions:" in text
        assert "$5,000.00" in text  # total value
        assert "35.00" in text  # total fees
        assert "In Range:" in text
        assert "Out of Range:" in text

    def test_format_lp_report_text_with_suggestions(self, sample_uni_position):
        """Test text report with rebalance alerts."""
        sample_uni_position.value_usd = 3000.0
        sample_uni_position.status = PositionStatus.OUT_OF_RANGE_BELOW.value
        sample_uni_position.fees_earned_usd = 25.0
        sample_uni_position.il_estimate_usd = 50.0

        suggestion = RebalanceSuggestion(
            position_id="12345",
            pair="ETH/USDC",
            current_price=1500.0,
            lower_price=1800.0,
            upper_price=2200.0,
            current_status="out_of_range_below",
            severity="critical",
            message="Price below range, position at risk",
            suggested_action="rebalance",
            estimated_cost_usd=5.0,
        )

        report = format_lp_report([sample_uni_position], rebalance_suggestions=[suggestion])
        text = format_lp_report_text(report)

        assert "REBALANCE ALERTS" in text
        assert "critical" in text.lower()
        assert "ETH/USDC" in text


# ---------------------------------------------------------------------------
# get_current_price() Tests
# ---------------------------------------------------------------------------

class TestGetCurrentPrice:
    @pytest.mark.asyncio
    async def test_get_price_finds_matching_pair(self, mock_dex_client):
        """Test finding price for a specific token pair."""
        mock_pair = MagicMock()
        mock_pair.chain = "ethereum"
        mock_pair.base_token_address = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
        mock_pair.quote_token_address = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
        mock_pair.price_usd = 2000.0
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        price = await get_current_price(
            token0_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            token1_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain="ethereum",
            dex_client=mock_dex_client,
        )
        # DexScreener returns USD price directly
        assert price == 2000.0

    @pytest.mark.asyncio
    async def test_get_price_no_pair_found(self, mock_dex_client):
        """Test when no pair is found."""
        mock_dex_client.search_pairs = AsyncMock(return_value=None)
        price = await get_current_price(
            token0_address="0xinvalid",
            token1_address="0xinvalid2",
            chain="ethereum",
            dex_client=mock_dex_client,
        )
        assert price is None

    @pytest.mark.asyncio
    async def test_get_price_no_matching_chain(self, mock_dex_client):
        """Test when chain doesn't match."""
        mock_pair = MagicMock()
        mock_pair.chain = "solana"  # Different chain
        mock_pair.base_token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        mock_pair.quote_token_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        mock_pair.price_usd = 2000.0
        mock_dex_client.search_pairs = AsyncMock(return_value=[mock_pair])

        price = await get_current_price(
            token0_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            token1_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            chain="ethereum",
            dex_client=mock_dex_client,
        )
        assert price is None


# ---------------------------------------------------------------------------
# Integration Tests (real API calls)
# ---------------------------------------------------------------------------

class TestIntegration:
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not __import__("os").getenv("BORG_DEFI_INTEGRATION"),
        reason="Set BORG_DEFI_INTEGRATION=true to run integration tests"
    )
    async def test_dexscreener_real_eth_usdc(self):
        """Test real DexScreener API call for ETH/USDC."""
        from borg.defi.api_clients.dexscreener import DexScreenerClient
        client = DexScreenerClient()
        # Search for USDC (common stablecoin pair)
        pairs = await client.search_pairs("WETH")
        eth_pairs = [p for p in pairs if p.chain == "ethereum"] if pairs else []
        assert len(eth_pairs) > 0, "Should find ETH pairs on Ethereum"
        print(f"Found {len(eth_pairs)} ETH pairs on Ethereum")
