"""Strategy backtester module for Borg DeFi.

Provides historical testing capabilities for yield strategies, whale trade
replay, LP position simulation, and performance metrics calculation.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

from borg.defi.data_models import Position, OHLCV, WhaleAlert, YieldOpportunity

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    """Represents a single trade in a backtest.
    
    Attributes:
        timestamp: Unix timestamp of trade
        token_in: Input token symbol
        token_out: Output token symbol
        amount_in: Amount of input token
        amount_out: Amount of output token
        price_in: Price of input token at execution
        price_out: Price of output token at execution
        value_usd: USD value of trade
        pnl_usd: P&L from this trade
        pnl_pct: P&L percentage from this trade
        protocol: Protocol used for trade
        chain: Chain where trade occurred
        fee_usd: Fee paid in USD
    """
    timestamp: float
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    price_in: float
    price_out: float
    value_usd: float
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    protocol: str = ""
    chain: str = ""
    fee_usd: float = 0.0


@dataclass
class BacktestResult:
    """Result of a backtest run.
    
    Attributes:
        trades: List of trades executed
        total_pnl_usd: Total P&L in USD
        total_pnl_pct: Total P&L percentage
        sharpe_ratio: Sharpe ratio
        sortino_ratio: Sortino ratio
        max_drawdown_pct: Maximum drawdown percentage
        max_drawdown_duration: Duration of max drawdown
        win_rate: Percentage of winning trades
        avg_return_per_trade: Average return per trade
        volatility: Portfolio volatility
        timestamp: Unix timestamp of backtest completion
    """
    trades: List[BacktestTrade]
    total_pnl_usd: float
    total_pnl_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration: float
    win_rate: float
    avg_return_per_trade: float
    volatility: float
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class WhaleReplayResult:
    """Result of replaying whale trades.
    
    Attributes:
        whale_address: Whale wallet address
        trades_replayed: Number of trades successfully replayed
        trades_failed: Number of trades that failed
        total_profit_usd: Total profit from replayed trades
        followed_direction: Whether following whale direction was profitable
        best_trade: Best individual trade result
        worst_trade: Worst individual trade result
    """
    whale_address: str
    trades_replayed: int
    trades_failed: int
    total_profit_usd: float
    followed_direction: bool
    best_trade: Optional[BacktestTrade] = None
    worst_trade: Optional[BacktestTrade] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class LPSimulationResult:
    """Result of LP position simulation.
    
    Attributes:
        token0: First token in LP pair
        token1: Second token in LP pair
        initial_value_usd: Initial position value in USD
        final_value_usd: Final position value in USD
        impermanent_loss_usd: IL in USD
        impermanent_loss_pct: IL as percentage of hodl value
        fees_earned_usd: Trading fees earned
        net_value: Final value minus IL plus fees
        price_change_token0: Price change for token0
        price_change_token1: Price change for token1
        duration_days: Duration of position in days
    """
    token0: str
    token1: str
    initial_value_usd: float
    final_value_usd: float
    impermanent_loss_usd: float
    impermanent_loss_pct: float
    fees_earned_usd: float
    net_value: float
    price_change_token0: float
    price_change_token1: float
    duration_days: float


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a strategy.
    
    Attributes:
        sharpe_ratio: Risk-adjusted return (annualized)
        sortino_ratio: Downside risk-adjusted return
        max_drawdown_pct: Maximum drawdown observed
        max_drawdown_duration: Duration of worst drawdown
        win_rate: Percentage of profitable periods
        profit_factor: Ratio of gross profit to gross loss
        avg_return: Average return per period
        volatility: Standard deviation of returns
        calmar_ratio: Return / max drawdown
        tail_ratio: 95th percentile / 5th percentile of returns
    """
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration: float
    win_rate: float
    profit_factor: float
    avg_return: float
    volatility: float
    calmar_ratio: float
    tail_ratio: float


class StrategyBacktester:
    """Backtesting engine for DeFi strategies.
    
    Provides methods for:
    - Backtesting yield strategies against historical data
    - Replaying whale wallet trades
    - Simulating LP positions with IL calculation
    - Calculating comprehensive performance metrics
    """
    
    RISK_FREE_RATE = 0.05  # 5% annual risk-free rate (USD stablecoin yield)
    TRADING_DAYS_PER_YEAR = 365
    
    def __init__(self, initial_capital: float = 10_000.0):
        """Initialize strategy backtester.
        
        Args:
            initial_capital: Starting capital in USD for backtests
        """
        self.initial_capital = initial_capital
    
    async def backtest_yield_strategy(
        self,
        opportunities: List[YieldOpportunity],
        price_data: Dict[str, List[OHLCV]],
        allocation_pct: float = 1.0,
        rebalance_threshold: float = 0.10,
    ) -> BacktestResult:
        """Backtest a yield strategy using historical DeFiLlama data.
        
        Args:
            opportunities: List of yield opportunities to test
            price_data: Historical price data by token
            allocation_pct: Percentage of capital to allocate (0.0-1.0)
            rebalance_threshold: Threshold to trigger rebalancing
            
        Returns:
            BacktestResult with trades and metrics
        """
        if not opportunities or not price_data:
            return self._empty_backtest_result()
        
        trades: List[BacktestTrade] = []
        capital = self.initial_capital * allocation_pct
        current_positions: Dict[str, float] = {}  # token -> amount
        
        # Build APY history from opportunities
        apy_history = self._build_apy_history(opportunities)
        
        # Process each time period
        timestamps = self._get_common_timestamps(price_data)
        
        for i, ts in enumerate(timestamps):
            # Calculate current yield
            current_apy = self._get_current_apy(opportunities, ts, apy_history)
            
            # Simulate yield accrual
            period_return = current_apy / 100 / self.TRADING_DAYS_PER_YEAR
            yield_earned = capital * period_return
            
            # Track positions and value
            total_value = capital + yield_earned
            
            # Check for rebalancing need
            if current_positions and self._should_rebalance(current_positions, total_value, rebalance_threshold):
                current_positions, trades = self._rebalance_positions(
                    current_positions, total_value, opportunities, ts, trades
                )
            
            capital = total_value
        
        # Calculate final metrics
        total_pnl = capital - (self.initial_capital * allocation_pct)
        total_pnl_pct = (total_pnl / (self.initial_capital * allocation_pct)) * 100 if self.initial_capital > 0 else 0
        
        return self._build_backtest_result(
            trades=trades,
            final_value=capital,
            initial_value=self.initial_capital * allocation_pct,
        )
    
    async def replay_whale_trades(
        self,
        whale_alerts: List[WhaleAlert],
        price_data: Dict[str, List[OHLCV]],
        follow_direction: bool = True,
        position_size_pct: float = 0.01,
    ) -> WhaleReplayResult:
        """Replay whale wallet trades with hypothetical positions.
        
        Args:
            whale_alerts: List of whale alerts to replay
            price_data: Historical price data by token
            follow_direction: If True, trade in same direction as whale
            position_size_pct: Position size as % of capital
            
        Returns:
            WhaleReplayResult with replay statistics
        """
        if not whale_alerts:
            return WhaleReplayResult(
                whale_address="",
                trades_replayed=0,
                trades_failed=0,
                total_profit_usd=0.0,
                followed_direction=False,
            )
        
        whale_address = whale_alerts[0].wallet if whale_alerts else "unknown"
        trades_replayed = 0
        trades_failed = 0
        total_profit = 0.0
        all_trades: List[BacktestTrade] = []
        
        for alert in whale_alerts:
            try:
                # Get price data for tokens
                token_in_prices = price_data.get(alert.token_in, [])
                token_out_prices = price_data.get(alert.token_out, [])
                
                # Find price at alert timestamp
                price_in = self._get_price_at_timestamp(token_in_prices, alert.timestamp)
                price_out = self._get_price_at_timestamp(token_out_prices, alert.timestamp)
                
                if price_in == 0 or price_out == 0:
                    trades_failed += 1
                    continue
                
                # Calculate position size
                position_value = self.initial_capital * position_size_pct
                
                # Calculate trade amounts
                if follow_direction:
                    amount_in = position_value / price_in
                    amount_out = amount_in * (price_in / price_out)  # Simplified
                else:
                    # Opposite direction
                    amount_in = position_value / price_out
                    amount_out = amount_in * (price_out / price_in)
                
                # Calculate P&L (simplified - exit at next price point)
                exit_ts = alert.timestamp + 3600  # Exit 1 hour later
                exit_price_in = self._get_price_at_timestamp(token_in_prices, exit_ts)
                exit_price_out = self._get_price_at_timestamp(token_out_prices, exit_ts)
                
                if exit_price_in > 0 and exit_price_out > 0:
                    if follow_direction:
                        pnl = (exit_price_out - price_out) * amount_out
                    else:
                        pnl = (price_in - exit_price_in) * amount_in
                    
                    total_profit += pnl
                    trades_replayed += 1
                    
                    trade = BacktestTrade(
                        timestamp=alert.timestamp,
                        token_in=alert.token_in,
                        token_out=alert.token_out,
                        amount_in=amount_in,
                        amount_out=amount_out,
                        price_in=price_in,
                        price_out=price_out,
                        value_usd=position_value,
                        pnl_usd=pnl,
                        pnl_pct=(pnl / position_value) * 100 if position_value > 0 else 0,
                        protocol="whale_replay",
                        chain=alert.chain,
                    )
                    all_trades.append(trade)
                else:
                    trades_failed += 1
                    
            except Exception as e:
                logger.debug(f"Failed to replay whale trade: {e}")
                trades_failed += 1
        
        # Find best and worst trades
        best_trade = max(all_trades, key=lambda t: t.pnl_usd) if all_trades else None
        worst_trade = min(all_trades, key=lambda t: t.pnl_usd) if all_trades else None
        
        return WhaleReplayResult(
            whale_address=whale_address,
            trades_replayed=trades_replayed,
            trades_failed=trades_failed,
            total_profit_usd=total_profit,
            followed_direction=follow_direction,
            best_trade=best_trade,
            worst_trade=worst_trade,
        )
    
    async def simulate_lp_position(
        self,
        token0: str,
        token1: str,
        amount0: float,
        amount1: float,
        price_data_token0: List[OHLCV],
        price_data_token1: List[OHLCV],
        fee_apr: float = 0.30,
        initial_price0: Optional[float] = None,
        initial_price1: Optional[float] = None,
    ) -> LPSimulationResult:
        """Simulate an LP position with historical price data.
        
        Args:
            token0: First token symbol
            token1: Second token symbol
            amount0: Initial amount of token0
            amount1: Initial amount of token1
            price_data_token0: Historical OHLCV data for token0
            price_data_token1: Historical OHLCV data for token1
            fee_apr: Fee APR from LP rewards
            initial_price0: Optional override for initial price of token0
            initial_price1: Optional override for initial price of token1
            
        Returns:
            LPSimulationResult with IL and performance metrics
        """
        if not price_data_token0 or not price_data_token1:
            return self._empty_lp_result(token0, token1)
        
        # Get initial prices
        if initial_price0 is None:
            initial_price0 = price_data_token0[0].close
        if initial_price1 is None:
            initial_price1 = price_data_token1[0].close
        
        # Calculate initial value (using token0 as base)
        initial_value_usd = (amount0 * initial_price0) + (amount1 * initial_price1)
        
        # Calculate initial ratio
        initial_ratio = amount1 / amount0 if amount0 > 0 else 0
        initial_price_ratio = initial_price1 / initial_price0 if initial_price0 > 0 else 0
        
        # Get final prices
        final_price0 = price_data_token0[-1].close
        final_price1 = price_data_token1[-1].close
        final_ratio = price_data_token1[-1].close / price_data_token0[-1].close if price_data_token0[-1].close > 0 else 0
        
        # Calculate duration
        duration_seconds = price_data_token0[-1].timestamp - price_data_token0[0].timestamp
        duration_days = duration_seconds / 86400
        
        # Calculate impermanent loss
        # IL = 2 * sqrt(price_ratio / initial_ratio) / (1 + price_ratio) - 1
        if initial_ratio > 0 and final_ratio > 0:
            hodl_value = (amount0 * final_price0) + (amount1 * final_price1)
            
            # LP value calculation: need to find current token amounts
            # At initialization: value = 2 * sqrt(amount0 * amount1 * initial_price0 * initial_price1)
            # But simplified: IL = 2 * sqrt(r) / (1 + r) - 1 where r = price_ratio / initial_ratio
            price_change_ratio = final_ratio / initial_ratio if initial_ratio > 0 else 0
            sqrt_ratio = math.sqrt(price_change_ratio) if price_change_ratio > 0 else 0
            
            il_factor = (2 * sqrt_ratio / (1 + price_change_ratio)) if (1 + price_change_ratio) > 0 else 0
            impermanent_loss_pct = (il_factor - 1) * -100  # Negative because IL is a loss
            
            # Calculate IL in USD
            # Simplified: IL = hodl_value * (il_factor - 1) * -1
            impermanent_loss_usd = abs(hodl_value * (il_factor - 1)) if il_factor < 1 else 0
        else:
            impermanent_loss_pct = 0.0
            impermanent_loss_usd = 0.0
        
        # Calculate fees earned
        # Fee APR -> daily -> based on duration
        daily_fee_rate = fee_apr / 365
        fees_earned_usd = initial_value_usd * daily_fee_rate * duration_days
        
        # Calculate final value (HODL value - IL + fees)
        hodl_value = (amount0 * final_price0) + (amount1 * final_price1)
        final_value_usd = hodl_value - impermanent_loss_usd + fees_earned_usd
        
        # Net value (what you end up with vs initial)
        net_value = final_value_usd - initial_value_usd
        
        # Price changes
        price_change_token0 = ((final_price0 / initial_price0) - 1) * 100 if initial_price0 > 0 else 0
        price_change_token1 = ((final_price1 / initial_price1) - 1) * 100 if initial_price1 > 0 else 0
        
        return LPSimulationResult(
            token0=token0,
            token1=token1,
            initial_value_usd=initial_value_usd,
            final_value_usd=final_value_usd,
            impermanent_loss_usd=impermanent_loss_usd,
            impermanent_loss_pct=impermanent_loss_pct,
            fees_earned_usd=fees_earned_usd,
            net_value=net_value,
            price_change_token0=price_change_token0,
            price_change_token1=price_change_token1,
            duration_days=duration_days,
        )
    
    def calculate_metrics(
        self,
        returns: List[float],
        periods_per_year: int = 365,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics from returns series.
        
        Args:
            returns: List of period returns (e.g., daily returns)
            periods_per_year: Number of periods in a year (365 for daily)
            
        Returns:
            PerformanceMetrics with all calculated metrics
        """
        if not returns:
            return self._empty_performance_metrics()
        
        n = len(returns)
        
        # Basic statistics
        avg_return = sum(returns) / n if n > 0 else 0.0
        variance = sum((r - avg_return) ** 2 for r in returns) / n if n > 1 else 0.0
        volatility = math.sqrt(variance * periods_per_year)  # Annualized
        
        # Risk-free rate per period
        rf_per_period = self.RISK_FREE_RATE / periods_per_year
        
        # Sharpe ratio
        excess_returns = [r - rf_per_period for r in returns]
        excess_mean = sum(excess_returns) / n if n > 0 else 0.0
        excess_std = math.sqrt(sum((r - excess_mean) ** 2 for r in excess_returns) / n) if n > 1 else 0.0
        
        if excess_std > 0:
            sharpe_ratio = (excess_mean / excess_std) * math.sqrt(periods_per_year)
        else:
            sharpe_ratio = 0.0
        
        # Sortino ratio (downside deviation)
        downside_returns = [r for r in returns if r < 0]
        downside_variance = sum(r ** 2 for r in downside_returns) / n if downside_returns else 0.0
        downside_std = math.sqrt(downside_variance * periods_per_year)
        
        if downside_std > 0:
            sortino_ratio = (excess_mean / downside_std) * math.sqrt(periods_per_year)
        else:
            sortino_ratio = 0.0 if excess_mean <= 0 else float('inf')
        
        # Max drawdown
        max_dd, max_dd_duration = self._calculate_max_drawdown(returns)
        
        # Win rate
        winning_periods = sum(1 for r in returns if r > 0)
        win_rate = (winning_periods / n) * 100 if n > 0 else 0.0
        
        # Profit factor
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
        
        # Calmar ratio
        annualized_return = avg_return * periods_per_year
        calmar_ratio = annualized_return / max_dd if max_dd > 0 else 0.0
        
        # Tail ratio
        sorted_returns = sorted(returns)
        p95_idx = min(int(n * 0.95), n - 1)
        p5_idx = min(int(n * 0.05), n - 1)
        p95 = sorted_returns[p95_idx] if p95_idx < n else 0
        p5 = sorted_returns[p5_idx] if p5_idx < n else 0
        tail_ratio = abs(p95 / p5) if p5 != 0 else 0.0
        
        return PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown_pct=max_dd * 100,
            max_drawdown_duration=max_dd_duration,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_return=avg_return,
            volatility=volatility,
            calmar_ratio=calmar_ratio,
            tail_ratio=tail_ratio,
        )
    
    def calculate_metrics_from_trades(
        self,
        trades: List[BacktestTrade],
        initial_capital: float,
    ) -> PerformanceMetrics:
        """Calculate performance metrics from a list of trades.
        
        Args:
            trades: List of backtest trades
            initial_capital: Starting capital in USD
            
        Returns:
            PerformanceMetrics calculated from trades
        """
        if not trades:
            return self._empty_performance_metrics()
        
        # Convert trades to returns series
        returns = []
        running_capital = initial_capital
        
        for trade in trades:
            if running_capital > 0:
                period_return = trade.pnl_pct / 100
                returns.append(period_return)
                running_capital *= (1 + period_return)
        
        return self.calculate_metrics(returns)
    
    # ========================================================================
    # Helper methods
    # ========================================================================
    
    def _empty_backtest_result(self) -> BacktestResult:
        """Return an empty backtest result."""
        return BacktestResult(
            trades=[],
            total_pnl_usd=0.0,
            total_pnl_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_duration=0.0,
            win_rate=0.0,
            avg_return_per_trade=0.0,
            volatility=0.0,
        )
    
    def _empty_lp_result(self, token0: str, token1: str) -> LPSimulationResult:
        """Return an empty LP simulation result."""
        return LPSimulationResult(
            token0=token0,
            token1=token1,
            initial_value_usd=0.0,
            final_value_usd=0.0,
            impermanent_loss_usd=0.0,
            impermanent_loss_pct=0.0,
            fees_earned_usd=0.0,
            net_value=0.0,
            price_change_token0=0.0,
            price_change_token1=0.0,
            duration_days=0.0,
        )
    
    def _empty_performance_metrics(self) -> PerformanceMetrics:
        """Return empty performance metrics."""
        return PerformanceMetrics(
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_duration=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            avg_return=0.0,
            volatility=0.0,
            calmar_ratio=0.0,
            tail_ratio=0.0,
        )
    
    def _build_apy_history(
        self,
        opportunities: List[YieldOpportunity],
    ) -> Dict[str, List[Tuple[float, float]]]:
        """Build APY history from opportunities.
        
        Returns:
            Dict of protocol -> [(timestamp, apy), ...]
        """
        history: Dict[str, List[Tuple[float, float]]] = {}
        
        for opp in opportunities:
            if opp.protocol not in history:
                history[opp.protocol] = []
            history[opp.protocol].append((opp.last_updated, opp.apy))
        
        # Sort each protocol's history by timestamp
        for protocol in history:
            history[protocol].sort(key=lambda x: x[0])
        
        return history
    
    def _get_common_timestamps(
        self,
        price_data: Dict[str, List[OHLCV]],
    ) -> List[float]:
        """Get common timestamps across all price data."""
        if not price_data:
            return []
        
        # Get all timestamps from first token
        all_timestamps = set()
        for token, candles in price_data.items():
            for c in candles:
                all_timestamps.add(c.timestamp)
        
        return sorted(all_timestamps)
    
    def _get_current_apy(
        self,
        opportunities: List[YieldOpportunity],
        timestamp: float,
        apy_history: Dict[str, List[Tuple[float, float]]],
    ) -> float:
        """Get APY at a specific timestamp."""
        # Find most recent APY before timestamp
        current_apy = 0.0
        
        for opp in opportunities:
            if opp.last_updated <= timestamp:
                if opp.protocol in apy_history:
                    for ts, apy in reversed(apy_history[opp.protocol]):
                        if ts <= timestamp:
                            current_apy = max(current_apy, apy)
                            break
        
        return current_apy
    
    def _should_rebalance(
        self,
        positions: Dict[str, float],
        total_value: float,
        threshold: float,
    ) -> bool:
        """Check if portfolio should be rebalanced."""
        if not positions or total_value <= 0:
            return False
        
        # Simple threshold check - if any position drifted > threshold
        target_pct = 1.0 / len(positions) if positions else 0
        
        for token, amount in positions.items():
            # Simplified check
            if abs(amount / total_value - target_pct) > threshold:
                return True
        
        return False
    
    def _rebalance_positions(
        self,
        positions: Dict[str, float],
        total_value: float,
        opportunities: List[YieldOpportunity],
        timestamp: float,
        existing_trades: List[BacktestTrade],
    ) -> Tuple[Dict[str, float], List[BacktestTrade]]:
        """Rebalance positions and record trades."""
        # Simplified rebalancing
        new_positions = {}
        
        if opportunities:
            # Equal weight among opportunities
            per_position = total_value / len(opportunities)
            
            for opp in opportunities:
                new_positions[opp.token] = per_position / opp.apy  # Simplified
        else:
            new_positions = positions
        
        return new_positions, existing_trades
    
    def _get_price_at_timestamp(
        self,
        candles: List[OHLCV],
        timestamp: float,
    ) -> float:
        """Get closing price at or just before timestamp."""
        for c in candles:
            if c.timestamp >= timestamp:
                return c.close
        
        # Return last price if timestamp is after all data
        return candles[-1].close if candles else 0.0
    
    def _calculate_max_drawdown(
        self,
        returns: List[float],
    ) -> Tuple[float, float]:
        """Calculate max drawdown and its duration from returns series.
        
        Returns:
            Tuple of (max_drawdown_pct, duration_in_periods)
        """
        if not returns:
            return 0.0, 0.0
        
        cumulative = 1.0
        peak = 1.0
        max_dd = 0.0
        max_dd_duration = 0
        
        current_dd_duration = 0
        in_drawdown = False
        
        for r in returns:
            cumulative *= (1 + r)
            
            if cumulative > peak:
                peak = cumulative
                in_drawdown = False
                current_dd_duration = 0
            else:
                in_drawdown = True
                current_dd_duration += 1
                dd = (peak - cumulative) / peak
                
                if dd > max_dd:
                    max_dd = dd
                    max_dd_duration = current_dd_duration
        
        return max_dd, max_dd_duration
    
    def _build_backtest_result(
        self,
        trades: List[BacktestTrade],
        final_value: float,
        initial_value: float,
    ) -> BacktestResult:
        """Build BacktestResult from trades and final values."""
        total_pnl = final_value - initial_value
        total_pnl_pct = (total_pnl / initial_value) * 100 if initial_value > 0 else 0
        
        # Calculate returns from trades
        returns = [t.pnl_pct / 100 for t in trades]
        
        # Calculate metrics
        metrics = self.calculate_metrics(returns)
        
        # Win rate from trades
        winning_trades = sum(1 for t in trades if t.pnl_usd > 0)
        win_rate = (winning_trades / len(trades)) * 100 if trades else 0.0
        
        avg_return = total_pnl_pct / len(trades) if trades else 0.0
        
        return BacktestResult(
            trades=trades,
            total_pnl_usd=total_pnl,
            total_pnl_pct=total_pnl_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            sortino_ratio=metrics.sortino_ratio,
            max_drawdown_pct=metrics.max_drawdown_pct,
            max_drawdown_duration=metrics.max_drawdown_duration,
            win_rate=win_rate,
            avg_return_per_trade=avg_return,
            volatility=metrics.volatility,
        )
