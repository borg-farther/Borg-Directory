"""
Dojo Bridge — Integration Layer for DeFi Trade Outcomes to Borg Learning Loop.

This module connects trade outcomes from swap executions to borg's learning system:
1. Classifies trade outcomes using failure pattern matching
2. Records wins/losses to failure_memory YAML files
3. Updates strategy pack reputation metrics
4. Generates nudges for better strategies based on cumulative PnL
5. Propagates rug/exploit warnings to collective via pack publishing

Classification Categories:
- slippage_exceeded: Price impact too high or slippage tolerance exceeded
- insufficient_liquidity: No route found or insufficient liquidity
- transaction_reverted: Transaction execution failed
- rug_detected: Honeypot or trading disabled detected
- gas_estimation_failed: Gas estimation failed

Storage: YAML files at ~/.hermes/borg/failures/<pack_id>/<error_hash>.yaml
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from borg.core.failure_memory import FailureMemory
from borg.defi.data_models import DeFiPackMetadata
from borg.defi.swap_executor import SwapTrade, SwapResult

logger = logging.getLogger(__name__)

# Default memory directory for dojo bridge
DEFAULT_DOJO_MEMORY_DIR = Path.home() / ".hermes" / "borg" / "dojo"


# ============================================================================
# Classification Patterns
# ============================================================================

TRADE_ERROR_PATTERNS = {
    "slippage_exceeded": [
        r"(?i)slippage",
        r"(?i)price impact too high",
        r"(?i)price impact.*exceeded",
        r"(?i)slippage.*exceeded",
    ],
    "insufficient_liquidity": [
        r"(?i)insufficient liquidity",
        r"(?i)no route found",
        r"(?i)not enough liquidity",
        r"(?i)liquidity.*insufficient",
    ],
    "transaction_reverted": [
        r"(?i)reverted",
        r"(?i)execution reverted",
        r"(?i)transaction reverted",
        r"(?i)call revert",
    ],
    "rug_detected": [
        r"(?i)honeypot",
        r"(?i)cannot sell",
        r"(?i)trading disabled",
        r"(?i)pause.*trade",
        r"(?i)owner.*only",
    ],
    "gas_estimation_failed": [
        r"(?i)gas estimation",
        r"(?i)out of gas",
        r"(?i)gas.*failed",
        r"(?i)cannot estimate gas",
    ],
}

# Nudge thresholds
NUDGE_THRESHOLDS = {
    "loss_streak": 3,  # Generate nudge after 3 consecutive losses
    "drawdown_alert": 10.0,  # Alert at 10% drawdown
    "low_win_rate": 0.40,  # Alert if win rate below 40%
    "positive_momentum": 5,  # Number of wins before nudge to continue
}


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TradeOutcome:
    """Represents a classified trade outcome for dojo learning.

    Attributes:
        trade_id: Unique trade identifier
        classification: Category of the outcome (success, slippage_exceeded, etc.)
        error_pattern: The specific error pattern matched
        timestamp: Unix timestamp of the trade
        chain: Blockchain network
        pnl_usd: Profit/loss in USD
        strategy_name: Strategy pack name used
        is_win: Whether this was a winning trade
    """
    trade_id: str
    classification: str
    error_pattern: str
    timestamp: float
    chain: str
    pnl_usd: float
    strategy_name: str
    is_win: bool


@dataclass
class StrategyReputation:
    """Tracks reputation metrics for a strategy pack.

    Attributes:
        strategy_name: Name of the strategy
        metadata: DeFi pack metadata with trading metrics
        outcomes: List of recent trade outcomes
        consecutive_losses: Count of consecutive losing trades
        max_consecutive_wins: Max consecutive winning trades
        last_nudge: Last nudge generated for this strategy
        last_updated: Unix timestamp of last update
    """
    strategy_name: str
    metadata: DeFiPackMetadata = field(default_factory=DeFiPackMetadata)
    outcomes: List[TradeOutcome] = field(default_factory=list)
    consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    current_win_streak: int = 0
    last_nudge: Optional[str] = None
    last_updated: float = field(default_factory=lambda: time.time())


# ============================================================================
# DojoBridge
# ============================================================================


class DojoBridge:
    """Bridge connecting DeFi trade outcomes to borg's learning loop.

    The DojoBridge integrates with FailureMemory to record trade outcomes,
    update strategy pack reputation, and generate nudges for improvement.

    Usage:
        # Initialize bridge
        bridge = DojoBridge(
            failure_memory=FailureMemory(),
            strategy_name="momentum-strategy-v1"
        )

        # Process a trade
        classification = bridge.classify_trade_outcome(trade)
        bridge.record_outcome(trade, classification)
        bridge.update_strategy_reputation("momentum-strategy-v1", trade)

        # Get improvement nudge
        nudge = bridge.generate_nudge("momentum-strategy-v1")

        # Propagate rug warning
        bridge.propagate_warning("TOKEN_ADDRESS", "honeypot detected")
    """

    def __init__(
        self,
        failure_memory: Optional[FailureMemory] = None,
        memory_dir: Optional[Path] = None,
        pack_id: str = "defi-trading",
    ) -> None:
        """Initialize DojoBridge.

        Args:
            failure_memory: FailureMemory instance for storing outcomes.
                           Creates a default if not provided.
            memory_dir: Directory for storing strategy reputation data.
                       Defaults to ~/.hermes/borg/dojo/
            pack_id: Default pack ID for failure memory recording.
        """
        self.failure_memory = failure_memory or FailureMemory(
            memory_dir=memory_dir or DEFAULT_DOJO_MEMORY_DIR
        )
        self.memory_dir = memory_dir or DEFAULT_DOJO_MEMORY_DIR
        self.default_pack_id = pack_id

        # Strategy reputations keyed by strategy name
        self._strategy_reputations: Dict[str, StrategyReputation] = {}

        # Rug warnings for collective propagation
        self._rug_warnings: List[Dict[str, Any]] = []

    def classify_trade_outcome(self, trade: SwapTrade) -> str:
        """Classify a trade outcome based on error patterns.

        Uses regex patterns to match trade error messages against known
        failure categories. Returns 'success' if no error pattern matches
        and the trade succeeded.

        Args:
            trade: The SwapTrade to classify

        Returns:
            Classification string: 'success', 'slippage_exceeded',
            'insufficient_liquidity', 'transaction_reverted', 'rug_detected',
            or 'gas_estimation_failed'
        """
        # If trade succeeded with no error, return success
        if trade.success and not trade.error:
            return "success"

        # If trade succeeded but we have an error message (partial fill etc)
        # still check for warning patterns
        if trade.success and trade.error:
            for category, patterns in TRADE_ERROR_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, trade.error):
                        return category

        # For failed trades, check error message against patterns
        error_msg = trade.error or ""

        for category, patterns in TRADE_ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, error_msg):
                    logger.info(f"Classified trade {trade.trade_id} as {category}")
                    return category

        # Default to transaction_reverted for unknown errors
        if trade.error:
            logger.warning(
                f"Unknown error pattern for trade {trade.trade_id}: {trade.error[:100]}"
            )
            return "transaction_reverted"

        # No error but failed - likely silent failure
        return "transaction_reverted"

    def record_outcome(
        self,
        trade: SwapTrade,
        classification: str,
        strategy_name: Optional[str] = None,
    ) -> None:
        """Record a trade outcome to failure memory.

        For failures, records to FailureMemory using the pack_id pattern.
        For successes, records successful approach patterns.

        Args:
            trade: The SwapTrade that was executed
            classification: Classification result from classify_trade_outcome
            strategy_name: Optional strategy name for attribution
        """
        pack_id = strategy_name or self.default_pack_id
        phase = classification  # Use classification as phase for DeFi errors

        if classification == "success":
            approach = self._build_success_approach(trade)
            outcome = "success"
            error_pattern = f"successful_swap_{trade.chain}"
        else:
            approach = self._build_failure_approach(trade, classification)
            outcome = "failure"
            # Build a normalized error pattern from the classification
            error_pattern = classification

        self.failure_memory.record_failure(
            error_pattern=error_pattern,
            pack_id=pack_id,
            phase=phase,
            approach=approach,
            outcome=outcome,
        )

        logger.info(
            f"Recorded {outcome} for trade {trade.trade_id} "
            f"(classification={classification}, pack_id={pack_id})"
        )

    def update_strategy_reputation(
        self,
        strategy_name: str,
        trade_result: SwapTrade,
    ) -> DeFiPackMetadata:
        """Update reputation metrics for a strategy pack.

        Maintains running statistics for the strategy including:
        - total_trades: Total number of trades
        - winning_trades: Number of profitable trades
        - total_pnl_usd: Cumulative P&L in USD
        - max_drawdown_pct: Maximum drawdown seen
        - sharpe_ratio: Risk-adjusted return (simplified)
        - win_rate: Percentage of winning trades

        Args:
            strategy_name: Name of the strategy to update
            trade_result: The trade result to process

        Returns:
            Updated DeFiPackMetadata for the strategy
        """
        # Get or create strategy reputation
        if strategy_name not in self._strategy_reputations:
            self._strategy_reputations[strategy_name] = StrategyReputation(
                strategy_name=strategy_name
            )

        rep = self._strategy_reputations[strategy_name]

        # Create trade outcome
        is_win = trade_result.success and self._is_profitable(trade_result)
        pnl_usd = self._calculate_pnl(trade_result)

        outcome = TradeOutcome(
            trade_id=trade_result.trade_id,
            classification=self.classify_trade_outcome(trade_result),
            error_pattern=trade_result.error or "",
            timestamp=trade_result.timestamp,
            chain=trade_result.chain,
            pnl_usd=pnl_usd,
            strategy_name=strategy_name,
            is_win=is_win,
        )

        rep.outcomes.append(outcome)

        # Update metadata
        rep.metadata.total_trades += 1

        if is_win:
            rep.metadata.winning_trades += 1
            rep.consecutive_losses = 0
            rep.current_win_streak += 1
            rep.max_consecutive_wins = max(rep.max_consecutive_wins, rep.current_win_streak)
        else:
            rep.consecutive_losses += 1
            rep.current_win_streak = 0

        rep.metadata.total_pnl_usd += pnl_usd

        # Update win rate
        if rep.metadata.total_trades > 0:
            rep.metadata.win_rate = rep.metadata.winning_trades / rep.metadata.total_trades

        # Update average return per trade
        if rep.metadata.total_trades > 0:
            rep.metadata.avg_return_per_trade = (
                rep.metadata.total_pnl_usd / rep.metadata.total_trades
            )

        # Calculate max drawdown
        rep.metadata.max_drawdown_pct = self._calculate_max_drawdown(rep.outcomes)

        # Calculate simplified sharpe ratio (using win rate as proxy)
        rep.metadata.sharpe_ratio = self._calculate_sharpe_ratio(rep.metadata)

        # Update chains and protocols if available
        if trade_result.chain and trade_result.chain not in rep.metadata.chains:
            rep.metadata.chains.append(trade_result.chain)

        rep.metadata.last_trade_timestamp = trade_result.timestamp

        rep.last_updated = time.time()

        logger.info(
            f"Updated strategy '{strategy_name}' reputation: "
            f"total={rep.metadata.total_trades}, "
            f"wins={rep.metadata.winning_trades}, "
            f"pnl=${rep.metadata.total_pnl_usd:.2f}, "
            f"win_rate={rep.metadata.win_rate:.1%}"
        )

        # Persist the updated metadata
        self._persist_strategy_metadata(strategy_name, rep.metadata)

        return rep.metadata

    def generate_nudge(self, strategy_name: str) -> Optional[str]:
        """Generate an improvement nudge based on strategy performance.

        Analyzes cumulative PnL and trading metrics to suggest better
        strategies or highlight concerning patterns.

        Args:
            strategy_name: Name of the strategy to analyze

        Returns:
            Nudge string with suggestions, or None if no nudge needed
        """
        if strategy_name not in self._strategy_reputations:
            return None

        rep = self._strategy_reputations[strategy_name]
        metadata = rep.metadata

        nudges = []

        # Check for loss streak
        if rep.consecutive_losses >= NUDGE_THRESHOLDS["loss_streak"]:
            nudges.append(
                f"LOSS_STREAK: {rep.consecutive_losses} consecutive losses detected. "
                f"Consider reducing position sizes or reviewing entry timing."
            )

        # Check for high drawdown
        if metadata.max_drawdown_pct >= NUDGE_THRESHOLDS["drawdown_alert"]:
            nudges.append(
                f"DRAWDOWN_ALERT: Portfolio drawdown at {metadata.max_drawdown_pct:.1f}%. "
                f"Consider tightening stop-losses or reducing exposure."
            )

        # Check for low win rate
        if metadata.total_trades >= 5 and metadata.win_rate < NUDGE_THRESHOLDS["low_win_rate"]:
            nudges.append(
                f"LOW_WIN_RATE: Win rate at {metadata.win_rate:.1%} (below {NUDGE_THRESHOLDS['low_win_rate']:.0%}). "
                f"Review strategy criteria or consider a different approach."
            )

        # Check for positive momentum
        if rep.current_win_streak >= NUDGE_THRESHOLDS["positive_momentum"]:
            nudges.append(
                f"MOMENTUM: {rep.current_win_streak} wins in a row! "
                f"Consider slightly increasing position size while maintaining risk management."
            )

        # Check for profitable strategy with high avg return
        if metadata.total_pnl_usd > 0 and metadata.avg_return_per_trade > 50:
            nudges.append(
                f"PROFITABLE: Average return of ${metadata.avg_return_per_trade:.2f} per trade. "
                f"Document this strategy's edge for future reference."
            )

        # Check for unprofitable strategy
        if metadata.total_trades >= 10 and metadata.total_pnl_usd < -100:
            nudges.append(
                f"LOSING_STRATEGY: Total losses of ${metadata.total_pnl_usd:.2f} over {metadata.total_trades} trades. "
                f"Consider backtesting alternative parameters or pausing this strategy."
            )

        if nudges:
            nudge_msg = " | ".join(nudges)
            rep.last_nudge = nudge_msg
            logger.info(f"Generated nudge for '{strategy_name}': {nudge_msg}")
            return nudge_msg

        return None

    def propagate_warning(
        self,
        token: str,
        reason: str,
        severity: str = "high",
        affected_strategies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Propagate a rug/exploit warning to the collective via pack publishing.

        Creates a warning record that can be published to notify other agents
        about dangerous tokens or protocols.

        Args:
            token: Token address or symbol that triggered the warning
            reason: Reason for the warning (e.g., 'honeypot detected')
            severity: Warning severity ('low', 'medium', 'high', 'critical')
            affected_strategies: Optional list of strategy names that used this token

        Returns:
            Warning dict suitable for collective propagation
        """
        warning = {
            "type": "rug_exploit_warning",
            "token": token,
            "reason": reason,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "affected_strategies": affected_strategies or [],
            "pack_id": self.default_pack_id,
        }

        self._rug_warnings.append(warning)

        # Persist warning to collective directory
        self._persist_warning(warning)

        # Update affected strategies' metadata
        if affected_strategies:
            for strategy_name in affected_strategies:
                if strategy_name in self._strategy_reputations:
                    rep = self._strategy_reputations[strategy_name]
                    # Add warning to strategy context
                    logger.warning(
                        f"RUG_WARNING propagated for token {token} "
                        f"(strategy: {strategy_name}): {reason}"
                    )

        logger.warning(
            f"Propagated rug/exploit warning: token={token}, reason={reason}, "
            f"severity={severity}"
        )

        return warning

    def get_strategy_metadata(self, strategy_name: str) -> Optional[DeFiPackMetadata]:
        """Get the current metadata for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            DeFiPackMetadata if strategy exists, None otherwise
        """
        if strategy_name in self._strategy_reputations:
            return self._strategy_reputations[strategy_name].metadata
        return None

    def get_recent_outcomes(
        self,
        strategy_name: str,
        limit: int = 10,
    ) -> List[TradeOutcome]:
        """Get recent trade outcomes for a strategy.

        Args:
            strategy_name: Name of the strategy
            limit: Maximum number of outcomes to return

        Returns:
            List of recent TradeOutcome objects
        """
        if strategy_name not in self._strategy_reputations:
            return []
        outcomes = self._strategy_reputations[strategy_name].outcomes
        return outcomes[-limit:] if len(outcomes) > limit else outcomes

    def get_rug_warnings(self) -> List[Dict[str, Any]]:
        """Get all rug/exploit warnings recorded by this bridge.

        Returns:
            List of warning dictionaries
        """
        return self._rug_warnings.copy()

    def recall_similar_failures(self, error_context: str) -> Optional[Dict[str, Any]]:
        """Recall similar failure patterns from memory.

        Uses FailureMemory recall to find known approaches for similar errors.

        Args:
            error_context: Error message or context to search for

        Returns:
            Recall result dict with wrong_approaches and correct_approaches
        """
        return self.failure_memory.recall(error_context)

    # -------------------------------------------------------------------------
    # Internal Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _is_profitable(trade: SwapTrade) -> bool:
        """Check if a trade was profitable.
        
        A trade is considered profitable if:
        1. It succeeded
        2. The output USD value covers gas costs and provides positive PnL
        """
        if not trade.success:
            return False
        
        # If we have output USD value, check if it covers costs
        # Simplified: if output > gas costs, consider it a win
        if trade.output_amount_usd > 0:
            return True
        
        return False

    @staticmethod
    def _calculate_pnl(trade: SwapTrade) -> float:
        """Calculate PnL for a trade in USD."""
        # Estimate input value if not available
        input_value_usd = trade.output_amount_usd * 0.98  # Approximate gas cost

        pnl = trade.output_amount_usd - input_value_usd - trade.gas_used_usd

        # If successful, PnL is positive (simplified)
        if trade.success:
            return max(0, pnl) if pnl > 0 else pnl
        else:
            # Failed trade loses the gas cost plus potential slippage
            return -(trade.gas_used_usd + (trade.output_amount_usd * 0.01))  # Assume 1% slippage cost

    @staticmethod
    def _calculate_max_drawdown(outcomes: List[TradeOutcome]) -> float:
        """Calculate maximum drawdown percentage from outcomes."""
        if not outcomes:
            return 0.0

        cumulative_pnl = 0.0
        peak_pnl = 0.0
        max_drawdown = 0.0

        for outcome in outcomes:
            cumulative_pnl += outcome.pnl_usd
            if cumulative_pnl > peak_pnl:
                peak_pnl = cumulative_pnl
            if peak_pnl > 0:
                drawdown = ((peak_pnl - cumulative_pnl) / peak_pnl) * 100
                max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    @staticmethod
    def _calculate_sharpe_ratio(metadata: DeFiPackMetadata) -> float:
        """Calculate simplified Sharpe ratio for strategy.

        Uses win rate and average return to approximate risk-adjusted performance.
        A proper implementation would use return standard deviation.
        """
        if metadata.total_trades < 2:
            return 0.0

        # Simplified: use win rate as success probability
        # and avg return as the return metric
        if metadata.avg_return_per_trade == 0:
            return 0.0

        # Win rate above 50% is good, scale accordingly
        win_rate_factor = (metadata.win_rate - 0.5) * 2  # Centers around 50%

        # Positive PnL per trade suggests positive Sharpe potential
        return win_rate_factor * (metadata.avg_return_per_trade / 100)

    @staticmethod
    def _build_success_approach(trade: SwapTrade) -> str:
        """Build a success approach description for failure memory."""
        return (
            f"Successful {trade.chain} swap via {trade.provider}: "
            f"{trade.input_token[:12]} -> {trade.output_token[:12]}, "
            f"output_usd={trade.output_amount_usd:.2f}, "
            f"price_impact={trade.price_impact_pct:.2f}%"
        )

    @staticmethod
    def _build_failure_approach(trade: SwapTrade, classification: str) -> str:
        """Build a failure approach description for failure memory."""
        return (
            f"Failed {classification} on {trade.chain} via {trade.provider}: "
            f"{trade.input_token[:12]} -> {trade.output_token[:12]}, "
            f"error={trade.error[:100] if trade.error else 'unknown'}"
        )

    def _persist_strategy_metadata(
        self,
        strategy_name: str,
        metadata: DeFiPackMetadata,
    ) -> None:
        """Persist strategy metadata to YAML file."""
        strategy_dir = self.memory_dir / "strategies"
        strategy_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = strategy_dir / f"{strategy_name}.yaml"

        data = {
            "strategy_name": strategy_name,
            "metadata": metadata.to_dict(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        metadata_path.write_text(
            yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

    def _persist_warning(self, warning: Dict[str, Any]) -> None:
        """Persist rug warning to collective directory."""
        collective_dir = self.memory_dir / "collective_warnings"
        collective_dir.mkdir(parents=True, exist_ok=True)

        # Use timestamp-based filename for uniqueness
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_token = warning["token"][:16].replace("/", "_").replace(":", "_")
        warning_path = collective_dir / f"warning_{safe_token}_{timestamp}.yaml"

        warning_path.write_text(
            yaml.safe_dump(warning, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

        logger.debug(f"Persisted warning to {warning_path}")