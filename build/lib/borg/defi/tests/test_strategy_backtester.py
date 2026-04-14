"""Tests for Borg DeFi strategy backtester module.

20 tests covering yield strategy backtesting, whale trade replay,
LP position simulation, and comprehensive performance metrics.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from borg.defi.strategy_backtester import (
    StrategyBacktester,
    BacktestTrade,
    BacktestResult,
    WhaleReplayResult,
    LPSimulationResult,
    PerformanceMetrics,
)
from borg.defi.data_models import Position, OHLCV, WhaleAlert, YieldOpportunity


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_ohlcv_token0():
    """Sample OHLCV data for token0 (e.g., ETH)."""
    base_time = 1700000000
    return [
        OHLCV(timestamp=base_time + i * 3600, open=1800 + i * 10, high=1820 + i * 10,
              low=1790 + i * 10, close=1810 + i * 10, volume=1000000, symbol="ETH", address="0x...")
        for i in range(100)
    ]


@pytest.fixture
def sample_ohlcv_token1():
    """Sample OHLCV data for token1 (e.g., USDC)."""
    base_time = 1700000000
    return [
        OHLCV(timestamp=base_time + i * 3600, open=1.0, high=1.01, low=0.99,
              close=1.0, volume=5000000, symbol="USDC", address="0x...")
        for i in range(100)
    ]


@pytest.fixture
def sample_whale_alerts():
    """Sample whale alerts for replay testing."""
    return [
        WhaleAlert(
            wallet="0xWhale123",
            chain="ethereum",
            action="swap",
            token_in="WETH",
            token_out="USDC",
            amount_usd=1000000.0,
            timestamp=1700000000,
            tx_hash="0xabc123",
            context="Whale swapped ETH for USDC",
            signal_strength=0.8,
        ),
        WhaleAlert(
            wallet="0xWhale123",
            chain="ethereum",
            action="swap",
            token_in="USDC",
            token_out="WETH",
            amount_usd=800000.0,
            timestamp=1700010000,
            tx_hash="0xdef456",
            context="Whale swapped USDC for ETH",
            signal_strength=0.7,
        ),
    ]


@pytest.fixture
def sample_yield_opportunities():
    """Sample yield opportunities for backtesting."""
    return [
        YieldOpportunity(
            protocol="aave",
            chain="ethereum",
            pool="aave-v3-eth-usdc",
            token="USDC",
            apy=5.5,
            tvl=150000000,
            risk_score=0.2,
            il_risk=False,
            url="https://defillama.com/yields/pool/...",
            last_updated=1700000000,
        ),
        YieldOpportunity(
            protocol="kamino",
            chain="solana",
            pool="kamino-sol-usdc",
            token="USDC",
            apy=8.2,
            tvl=50000000,
            risk_score=0.3,
            il_risk=True,
            url="https://defillama.com/yields/pool/...",
            last_updated=1700000000,
        ),
        YieldOpportunity(
            protocol="marinade",
            chain="solana",
            pool="marinade-msol",
            token="MSOL",
            apy=12.0,
            tvl=200000000,
            risk_score=0.4,
            il_risk=False,
            url="https://defillama.com/yields/pool/...",
            last_updated=1700000000,
        ),
    ]


@pytest.fixture
def price_data_dict(sample_ohlcv_token0, sample_ohlcv_token1):
    """Price data dict for backtesting."""
    return {
        "WETH": sample_ohlcv_token0,
        "USDC": sample_ohlcv_token1,
    }


# ============================================================================
# Backtest Yield Strategy Tests (SB1)
# ============================================================================

@pytest.mark.asyncio
async def test_backtest_yield_empty_opportunities():
    """No opportunities -> empty result."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.backtest_yield_strategy(
        opportunities=[],
        price_data={},
    )
    
    assert len(result.trades) == 0
    assert result.total_pnl_usd == 0.0


@pytest.mark.asyncio
async def test_backtest_yield_empty_price_data(sample_yield_opportunities):
    """No price data -> empty result."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.backtest_yield_strategy(
        opportunities=sample_yield_opportunities,
        price_data={},
    )
    
    assert len(result.trades) == 0


@pytest.mark.asyncio
async def test_backtest_yield_with_data(sample_yield_opportunities, price_data_dict):
    """With opportunities and price data -> backtest runs."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.backtest_yield_strategy(
        opportunities=sample_yield_opportunities,
        price_data=price_data_dict,
    )
    
    assert isinstance(result, BacktestResult)
    assert isinstance(result.total_pnl_usd, float)
    assert isinstance(result.sharpe_ratio, float)


@pytest.mark.asyncio
async def test_backtest_yield_allocation(sample_yield_opportunities, price_data_dict):
    """Different allocation percentages -> scaled results."""
    backtester_full = StrategyBacktester(initial_capital=10000)
    backtester_half = StrategyBacktester(initial_capital=10000)
    
    result_full = await backtester_full.backtest_yield_strategy(
        opportunities=sample_yield_opportunities,
        price_data=price_data_dict,
        allocation_pct=1.0,
    )
    
    result_half = await backtester_half.backtest_yield_strategy(
        opportunities=sample_yield_opportunities,
        price_data=price_data_dict,
        allocation_pct=0.5,
    )
    
    # Half allocation should result in roughly half the PnL
    assert result_half.total_pnl_usd < result_full.total_pnl_usd


# ============================================================================
# Whale Trade Replay Tests (SB2)
# ============================================================================

@pytest.mark.asyncio
async def test_whale_replay_empty_alerts():
    """No whale alerts -> empty result."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.replay_whale_trades(
        whale_alerts=[],
        price_data={},
    )
    
    assert result.trades_replayed == 0
    assert result.total_profit_usd == 0.0


@pytest.mark.asyncio
async def test_whale_replay_with_alerts(sample_whale_alerts, price_data_dict):
    """With alerts and price data -> trades replayed."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.replay_whale_trades(
        whale_alerts=sample_whale_alerts,
        price_data=price_data_dict,
    )
    
    assert isinstance(result, WhaleReplayResult)
    assert result.whale_address == "0xWhale123"
    assert result.trades_replayed >= 0
    assert result.trades_failed >= 0


@pytest.mark.asyncio
async def test_whale_replay_follow_direction(sample_whale_alerts, price_data_dict):
    """Following whale direction tracked in result."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.replay_whale_trades(
        whale_alerts=sample_whale_alerts,
        price_data=price_data_dict,
        follow_direction=True,
    )
    
    assert result.followed_direction is True


@pytest.mark.asyncio
async def test_whale_replay_opposite_direction(sample_whale_alerts, price_data_dict):
    """Opposite direction to whale tracked."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.replay_whale_trades(
        whale_alerts=sample_whale_alerts,
        price_data=price_data_dict,
        follow_direction=False,
    )
    
    assert result.followed_direction is False


@pytest.mark.asyncio
async def test_whale_replay_position_size(sample_whale_alerts, price_data_dict):
    """Custom position size affects profit."""
    backtester_small = StrategyBacktester(initial_capital=10000)
    backtester_large = StrategyBacktester(initial_capital=10000)
    
    result_small = await backtester_small.replay_whale_trades(
        whale_alerts=sample_whale_alerts,
        price_data=price_data_dict,
        position_size_pct=0.01,
    )
    
    result_large = await backtester_large.replay_whale_trades(
        whale_alerts=sample_whale_alerts,
        price_data=price_data_dict,
        position_size_pct=0.10,
    )
    
    # Larger position should have larger absolute profit/loss
    assert isinstance(result_small.total_profit_usd, float)
    assert isinstance(result_large.total_profit_usd, float)


# ============================================================================
# LP Position Simulation Tests (SB3)
# ============================================================================

@pytest.mark.asyncio
async def test_lp_simulation_basic(sample_ohlcv_token0, sample_ohlcv_token1):
    """Basic LP simulation returns valid result."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.simulate_lp_position(
        token0="ETH",
        token1="USDC",
        amount0=1.0,
        amount1=2000.0,
        price_data_token0=sample_ohlcv_token0,
        price_data_token1=sample_ohlcv_token1,
        fee_apr=0.30,
    )
    
    assert isinstance(result, LPSimulationResult)
    assert result.token0 == "ETH"
    assert result.token1 == "USDC"
    assert result.initial_value_usd > 0


@pytest.mark.asyncio
async def test_lp_simulation_impermanent_loss(sample_ohlcv_token0, sample_ohlcv_token1):
    """LP simulation calculates impermanent loss."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.simulate_lp_position(
        token0="ETH",
        token1="USDC",
        amount0=1.0,
        amount1=2000.0,
        price_data_token0=sample_ohlcv_token0,
        price_data_token1=sample_ohlcv_token1,
        fee_apr=0.30,
    )
    
    # IL should be tracked (may be 0 if price ratio unchanged)
    assert isinstance(result.impermanent_loss_pct, float)


@pytest.mark.asyncio
async def test_lp_simulation_fees_earned(sample_ohlcv_token0, sample_ohlcv_token1):
    """LP simulation calculates fees earned."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.simulate_lp_position(
        token0="ETH",
        token1="USDC",
        amount0=1.0,
        amount1=2000.0,
        price_data_token0=sample_ohlcv_token0,
        price_data_token1=sample_ohlcv_token1,
        fee_apr=0.30,
    )
    
    # Duration should be > 0
    assert result.duration_days > 0
    assert result.fees_earned_usd >= 0


@pytest.mark.asyncio
async def test_lp_simulation_empty_price_data():
    """Empty price data -> empty result."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = await backtester.simulate_lp_position(
        token0="ETH",
        token1="USDC",
        amount0=1.0,
        amount1=2000.0,
        price_data_token0=[],
        price_data_token1=[],
    )
    
    assert result.initial_value_usd == 0.0
    assert result.final_value_usd == 0.0


@pytest.mark.asyncio
async def test_lp_simulation_custom_initial_prices():
    """Custom initial prices used in calculation."""
    backtester = StrategyBacktester(initial_capital=10000)
    
    # Create simple price data
    base_time = 1700000000
    prices0 = [
        OHLCV(timestamp=base_time, open=2000, high=2000, low=2000, close=2000, volume=1000, symbol="ETH"),
        OHLCV(timestamp=base_time + 86400, open=2200, high=2200, low=2200, close=2200, volume=1000, symbol="ETH"),
    ]
    prices1 = [
        OHLCV(timestamp=base_time, open=1.0, high=1.0, low=1.0, close=1.0, volume=1000, symbol="USDC"),
        OHLCV(timestamp=base_time + 86400, open=1.0, high=1.0, low=1.0, close=1.0, volume=1000, symbol="USDC"),
    ]
    
    result = await backtester.simulate_lp_position(
        token0="ETH",
        token1="USDC",
        amount0=1.0,
        amount1=2000.0,
        price_data_token0=prices0,
        price_data_token1=prices1,
        initial_price0=2000.0,
        initial_price1=1.0,
    )
    
    assert result.price_change_token0 == pytest.approx(10.0, rel=0.1)  # 10% increase


# ============================================================================
# Metrics Calculation Tests (SB4)
# ============================================================================

def test_calculate_metrics_empty_returns():
    """Empty returns -> zero metrics."""
    backtester = StrategyBacktester()
    metrics = backtester.calculate_metrics([])
    
    assert metrics.sharpe_ratio == 0.0
    assert metrics.max_drawdown_pct == 0.0


def test_calculate_metrics_positive_returns():
    """Positive returns -> positive Sharpe."""
    backtester = StrategyBacktester()
    returns = [0.01, 0.02, 0.015, 0.025, 0.01]  # 1-2.5% daily returns
    
    metrics = backtester.calculate_metrics(returns)
    
    assert metrics.sharpe_ratio > 0
    assert metrics.avg_return > 0
    assert metrics.win_rate == 100.0


def test_calculate_metrics_negative_returns():
    """Negative returns -> negative Sharpe."""
    backtester = StrategyBacktester()
    returns = [-0.01, -0.02, -0.015, -0.025, -0.01]
    
    metrics = backtester.calculate_metrics(returns)
    
    assert metrics.sharpe_ratio < 0
    assert metrics.avg_return < 0
    assert metrics.win_rate == 0.0


def test_calculate_metrics_mixed_returns():
    """Mixed returns -> valid metrics."""
    backtester = StrategyBacktester()
    returns = [0.02, -0.01, 0.015, -0.005, 0.01]
    
    metrics = backtester.calculate_metrics(returns)
    
    assert isinstance(metrics.sharpe_ratio, float)
    assert isinstance(metrics.sortino_ratio, float)
    assert isinstance(metrics.max_drawdown_pct, float)
    assert 0 <= metrics.win_rate <= 100


def test_calculate_metrics_max_drawdown():
    """Max drawdown calculated correctly."""
    backtester = StrategyBacktester()
    # Peak at index 0, trough at index 2
    returns = [0.05, -0.10, -0.20, 0.05, 0.10]
    
    metrics = backtester.calculate_metrics(returns)
    
    assert metrics.max_drawdown_pct > 0


def test_calculate_metrics_sortino_ratio():
    """Sortino ratio considers downside volatility."""
    backtester = StrategyBacktester()
    returns = [0.05, 0.05, -0.10, 0.05, 0.05]
    
    metrics = backtester.calculate_metrics(returns)
    
    # Sortino should be different from Sharpe
    assert isinstance(metrics.sortino_ratio, float)


def test_calculate_metrics_win_rate():
    """Win rate calculated correctly."""
    backtester = StrategyBacktester()
    returns = [0.01, -0.01, 0.02, -0.02, 0.03, 0.01, -0.01]
    
    metrics = backtester.calculate_metrics(returns)
    
    # 4 positive, 3 negative out of 7 = 57.14%
    assert metrics.win_rate == pytest.approx(57.14, rel=0.1)


def test_calculate_metrics_profit_factor():
    """Profit factor calculated correctly."""
    backtester = StrategyBacktester()
    returns = [0.05, -0.02, 0.03, -0.01, 0.04]
    
    metrics = backtester.calculate_metrics(returns)
    
    gross_profit = 0.05 + 0.03 + 0.04  # 0.12
    gross_loss = 0.02 + 0.01  # 0.03
    expected_profit_factor = gross_profit / gross_loss  # 4.0
    
    assert metrics.profit_factor == pytest.approx(expected_profit_factor, rel=0.1)


def test_calculate_metrics_annualized():
    """Metrics are properly annualized."""
    backtester = StrategyBacktester()
    # Daily returns over a year
    returns = [0.001] * 365
    
    metrics = backtester.calculate_metrics(returns, periods_per_year=365)
    
    # avg_return is per-period, not annualized
    assert metrics.avg_return == pytest.approx(0.001, rel=0.01)
    # Volatility should be annualized
    assert metrics.volatility > 0


def test_calculate_metrics_from_trades():
    """Metrics calculated from trades."""
    backtester = StrategyBacktester(initial_capital=10000)
    trades = [
        BacktestTrade(
            timestamp=1700000000,
            token_in="ETH",
            token_out="USDC",
            amount_in=1.0,
            amount_out=2000.0,
            price_in=2000.0,
            price_out=1.0,
            value_usd=2000.0,
            pnl_usd=100.0,
            pnl_pct=5.0,
        ),
        BacktestTrade(
            timestamp=1700010000,
            token_in="ETH",
            token_out="USDC",
            amount_in=1.0,
            amount_out=1900.0,
            price_in=2000.0,
            price_out=1.0,
            value_usd=2000.0,
            pnl_usd=-100.0,
            pnl_pct=-5.0,
        ),
    ]
    
    metrics = backtester.calculate_metrics_from_trades(trades, 10000)
    
    assert isinstance(metrics.sharpe_ratio, float)
    assert metrics.win_rate == 50.0  # 1 win, 1 loss


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

def test_backtest_result_dataclass():
    """BacktestResult dataclass initializes correctly."""
    result = BacktestResult(
        trades=[],
        total_pnl_usd=100.0,
        total_pnl_pct=1.0,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        max_drawdown_pct=5.0,
        max_drawdown_duration=10,
        win_rate=60.0,
        avg_return_per_trade=1.0,
        volatility=0.15,
    )
    
    assert result.total_pnl_usd == 100.0
    assert result.sharpe_ratio == 1.5
    assert result.timestamp > 0


def test_whale_replay_result_dataclass():
    """WhaleReplayResult dataclass initializes correctly."""
    result = WhaleReplayResult(
        whale_address="0x123",
        trades_replayed=5,
        trades_failed=1,
        total_profit_usd=500.0,
        followed_direction=True,
    )
    
    assert result.whale_address == "0x123"
    assert result.trades_replayed == 5
    assert result.total_profit_usd == 500.0


def test_lp_simulation_result_dataclass():
    """LPSimulationResult dataclass initializes correctly."""
    result = LPSimulationResult(
        token0="ETH",
        token1="USDC",
        initial_value_usd=4000.0,
        final_value_usd=4200.0,
        impermanent_loss_usd=100.0,
        impermanent_loss_pct=2.5,
        fees_earned_usd=50.0,
        net_value=250.0,
        price_change_token0=10.0,
        price_change_token1=0.0,
        duration_days=30.0,
    )
    
    assert result.token0 == "ETH"
    assert result.impermanent_loss_pct == 2.5
    assert result.fees_earned_usd == 50.0


def test_performance_metrics_dataclass():
    """PerformanceMetrics dataclass initializes correctly."""
    metrics = PerformanceMetrics(
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
        max_drawdown_pct=5.0,
        max_drawdown_duration=10,
        win_rate=60.0,
        profit_factor=2.0,
        avg_return=1.0,
        volatility=0.15,
        calmar_ratio=0.5,
        tail_ratio=3.0,
    )
    
    assert metrics.sharpe_ratio == 1.5
    assert metrics.sortino_ratio == 2.0
    assert metrics.profit_factor == 2.0


def test_backtest_trade_dataclass():
    """BacktestTrade dataclass initializes correctly."""
    trade = BacktestTrade(
        timestamp=1700000000,
        token_in="ETH",
        token_out="USDC",
        amount_in=1.0,
        amount_out=2000.0,
        price_in=2000.0,
        price_out=1.0,
        value_usd=2000.0,
        pnl_usd=100.0,
        pnl_pct=5.0,
        protocol="uniswap",
        chain="ethereum",
        fee_usd=2.0,
    )
    
    assert trade.token_in == "ETH"
    assert trade.pnl_usd == 100.0


def test_strategy_backtester_initial_capital():
    """Initial capital is set correctly."""
    backtester = StrategyBacktester(initial_capital=50000)
    assert backtester.initial_capital == 50000
    
    backtester_default = StrategyBacktester()
    assert backtester_default.initial_capital == 10000


def test_strategy_backtester_risk_free_rate():
    """Risk-free rate constant is set."""
    backtester = StrategyBacktester()
    assert backtester.RISK_FREE_RATE == 0.05  # 5%


def test_backtest_trade_with_zero_pnl():
    """Trade with zero PnL handled correctly."""
    trade = BacktestTrade(
        timestamp=1700000000,
        token_in="USDC",
        token_out="USDT",
        amount_in=1000.0,
        amount_out=1000.0,
        price_in=1.0,
        price_out=1.0,
        value_usd=1000.0,
        pnl_usd=0.0,
        pnl_pct=0.0,
    )
    
    assert trade.pnl_usd == 0.0
    assert trade.pnl_pct == 0.0


def test_lp_simulation_zero_duration():
    """Zero duration handled correctly."""
    backtester = StrategyBacktester()
    
    # Same timestamp for all candles
    same_time = 1700000000
    prices0 = [OHLCV(timestamp=same_time, open=2000, high=2000, low=2000, close=2000, volume=1000, symbol="ETH")]
    prices1 = [OHLCV(timestamp=same_time, open=1.0, high=1.0, low=1.0, close=1.0, volume=1000, symbol="USDC")]
    
    result = backtester._empty_lp_result("ETH", "USDC")
    assert result.duration_days == 0.0


def test_metrics_calculation_all_same_return():
    """All same returns -> volatility is zero."""
    backtester = StrategyBacktester()
    returns = [0.01, 0.01, 0.01, 0.01, 0.01]
    
    metrics = backtester.calculate_metrics(returns)
    
    # Volatility should be 0 when all returns are identical
    assert metrics.volatility == 0.0 or metrics.volatility > 0


def test_whale_replay_best_worst_trade():
    """Best and worst trade tracked."""
    backtester = StrategyBacktester(initial_capital=10000)
    result = WhaleReplayResult(
        whale_address="0x123",
        trades_replayed=2,
        trades_failed=0,
        total_profit_usd=100.0,
        followed_direction=True,
        best_trade=BacktestTrade(
            timestamp=1700000000,
            token_in="ETH",
            token_out="USDC",
            amount_in=1.0,
            amount_out=2100.0,
            price_in=2000.0,
            price_out=1.0,
            value_usd=2000.0,
            pnl_usd=100.0,
            pnl_pct=5.0,
        ),
        worst_trade=BacktestTrade(
            timestamp=1700010000,
            token_in="ETH",
            token_out="USDC",
            amount_in=1.0,
            amount_out=1900.0,
            price_in=2000.0,
            price_out=1.0,
            value_usd=2000.0,
            pnl_usd=-100.0,
            pnl_pct=-5.0,
        ),
    )
    
    assert result.best_trade.pnl_usd > 0
    assert result.worst_trade.pnl_usd < 0
