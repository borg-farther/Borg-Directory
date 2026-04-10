"""
Strategy Selector and Dojo Feedback Loop for Borg DeFi.

This module provides the StrategySelector class that:
- Reads strategy metadata from dojo YAML files
- Scores and ranks strategies based on performance metrics
- Determines if a strategy should be avoided
- Manages strategy nudges for the feedback loop
- Integrates with SwapExecutor for routing decisions
- Integrates with YieldScanner for reputation-based boosts

Score Formula:
    score = win_rate * 0.4 + normalized_sharpe * 0.3 + recency * 0.2 + collective * 0.1

Storage:
- Strategy metadata: ~/.hermes/borg/dojo/strategies/<name>.yaml
- Collective warnings: ~/.hermes/borg/dojo/collective_warnings/
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from borg.defi.data_models import DeFiPackMetadata

logger = logging.getLogger(__name__)

# Default dojo directories
DEFAULT_DOJO_DIR = Path.home() / ".hermes" / "borg" / "dojo"
DEFAULT_STRATEGIES_DIR = DEFAULT_DOJO_DIR / "strategies"
DEFAULT_WARNINGS_DIR = DEFAULT_DOJO_DIR / "collective_warnings"

# Score weights
WEIGHT_WIN_RATE = 0.4
WEIGHT_SHARPE = 0.3
WEIGHT_RECENCY = 0.2
WEIGHT_COLLECTIVE = 0.1

# Avoidance thresholds
AVOID_WIN_RATE_THRESHOLD = 0.30  # <30% win rate
AVOID_CONSECUTIVE_LOSSES_THRESHOLD = 3  # >=3 consecutive losses

# Recency normalization (7 days = 1.0, older = lower)
RECENCY_HALF_LIFE_SECONDS = 7 * 24 * 60 * 60


@dataclass
class StrategyScore:
    """Represents a scored strategy with breakdown."""
    name: str
    score: float
    win_rate: float
    normalized_sharpe: float
    recency: float
    collective_score: float
    metadata: Optional[DeFiPackMetadata] = None


@dataclass
class Nudge:
    """Represents a strategy nudge."""
    nudge_id: str
    strategy_name: str
    message: str
    created_at: float
    applied: bool = False


class StrategySelector:
    """Selects best strategies based on dojo feedback loop.
    
    The StrategySelector reads strategy metadata from YAML files in the
    dojo directory and scores them based on multiple factors:
    - win_rate (40% weight): Historical win rate
    - normalized_sharpe (30% weight): Risk-adjusted returns, normalized 0-1
    - recency (20% weight): More recent trades score higher
    - collective (10% weight): Based on collective warnings (1.0 if no warnings)
    
    Usage:
        selector = StrategySelector()
        
        # Get best strategy for a context
        best = selector.get_best_strategy("swap")
        
        # Check if strategy should be avoided
        should_avoid, reason = selector.should_avoid("momentum-v1")
        
        # Get active nudges
        nudges = selector.get_active_nudges()
        
        # Apply a nudge
        selector.apply_nudge("momentum-v1", "nudge_001")
        
        # Get full ranking
        ranking = selector.get_strategy_ranking()
        
        # Register a trade outcome
        selector.register_outcome("momentum-v1", won=True, pnl=50.0)
    """
    
    def __init__(
        self,
        strategies_dir: Optional[Path] = None,
        warnings_dir: Optional[Path] = None,
        dojo_bridge=None,
    ):
        """Initialize StrategySelector.
        
        Args:
            strategies_dir: Directory containing strategy YAML files.
                          Defaults to ~/.hermes/borg/dojo/strategies/
            warnings_dir: Directory containing collective warning YAML files.
                         Defaults to ~/.hermes/borg/dojo/collective_warnings/
            dojo_bridge: Optional DojoBridge instance for register_outcome.
        """
        self.strategies_dir = strategies_dir or DEFAULT_STRATEGIES_DIR
        self.warnings_dir = warnings_dir or DEFAULT_WARNINGS_DIR
        self.dojo_bridge = dojo_bridge
        
        # Cache of loaded strategy metadata
        self._strategy_cache: Dict[str, Dict[str, Any]] = {}
        
        # Cache of active warnings keyed by strategy name
        self._warnings_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # Load existing metadata on init
        self._load_all_strategies()
        self._load_all_warnings()
    
    def _load_all_strategies(self) -> None:
        """Load all strategy YAML files from the strategies directory."""
        if not self.strategies_dir.exists():
            logger.debug(f"Strategies directory does not exist: {self.strategies_dir}")
            return
        
        for yaml_file in self.strategies_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if data:
                    strategy_name = yaml_file.stem
                    self._strategy_cache[strategy_name] = data
                    logger.debug(f"Loaded strategy: {strategy_name}")
            except Exception as e:
                logger.warning(f"Failed to load strategy file {yaml_file}: {e}")
    
    def _load_all_warnings(self) -> None:
        """Load all collective warning YAML files."""
        if not self.warnings_dir.exists():
            logger.debug(f"Warnings directory does not exist: {self.warnings_dir}")
            return
        
        for yaml_file in self.warnings_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if data:
                    # Extract affected strategies from warning
                    affected = data.get("affected_strategies", [])
                    warning_type = data.get("type", "unknown")
                    for strategy in affected:
                        if strategy not in self._warnings_cache:
                            self._warnings_cache[strategy] = []
                        self._warnings_cache[strategy].append({
                            "type": warning_type,
                            "reason": data.get("reason", ""),
                            "severity": data.get("severity", "medium"),
                            "token": data.get("token", ""),
                            "timestamp": data.get("timestamp", ""),
                            "source_file": str(yaml_file),
                        })
                    logger.debug(f"Loaded warning file: {yaml_file.name}")
            except Exception as e:
                logger.warning(f"Failed to load warning file {yaml_file}: {e}")
    
    def _load_strategy_metadata(self, strategy_name: str) -> Optional[DeFiPackMetadata]:
        """Load metadata for a single strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            DeFiPackMetadata if found, None otherwise
        """
        # Check cache first
        if strategy_name in self._strategy_cache:
            data = self._strategy_cache[strategy_name]
            meta_dict = data.get("metadata", {})
            return self._dict_to_metadata(meta_dict)
        
        # Try to load from disk
        strategy_path = self.strategies_dir / f"{strategy_name}.yaml"
        if not strategy_path.exists():
            return None
        
        try:
            data = yaml.safe_load(strategy_path.read_text(encoding="utf-8"))
            if data:
                self._strategy_cache[strategy_name] = data
                meta_dict = data.get("metadata", {})
                return self._dict_to_metadata(meta_dict)
        except Exception as e:
            logger.warning(f"Failed to load strategy {strategy_name}: {e}")
        
        return None
    
    @staticmethod
    def _dict_to_metadata(data: Dict[str, Any]) -> DeFiPackMetadata:
        """Convert dict to DeFiPackMetadata."""
        return DeFiPackMetadata(
            total_trades=data.get("total_trades", 0),
            winning_trades=data.get("winning_trades", 0),
            total_pnl_usd=data.get("total_pnl_usd", 0.0),
            max_drawdown_pct=data.get("max_drawdown_pct", 0.0),
            sharpe_ratio=data.get("sharpe_ratio", 0.0),
            win_rate=data.get("win_rate", 0.0),
            avg_return_per_trade=data.get("avg_return_per_trade", 0.0),
            last_trade_timestamp=data.get("last_trade_timestamp", 0.0),
            chains=data.get("chains", []),
            protocols=data.get("protocols", []),
        )
    
    def _calculate_recency(self, last_trade_timestamp: float) -> float:
        """Calculate recency score (0-1) based on last trade time.
        
        More recent trades score higher. Uses exponential decay with
        7-day half-life.
        
        Args:
            last_trade_timestamp: Unix timestamp of last trade
            
        Returns:
            Recency score between 0 and 1
        """
        if last_trade_timestamp <= 0:
            return 0.0
        
        age_seconds = time.time() - last_trade_timestamp
        recency = 1.0 / (2 ** (age_seconds / RECENCY_HALF_LIFE_SECONDS))
        return max(0.0, min(1.0, recency))
    
    def _normalize_sharpe(self, sharpe_ratio: float) -> float:
        """Normalize Sharpe ratio to 0-1 range.
        
        Assumes Sharpe ratio typically ranges from -2 to 4.
        Values outside this range are clamped.
        
        Args:
            sharpe_ratio: Raw Sharpe ratio
            
        Returns:
            Normalized score between 0 and 1
        """
        # Typical range: -2 to 4
        min_sharpe = -2.0
        max_sharpe = 4.0
        normalized = (sharpe_ratio - min_sharpe) / (max_sharpe - min_sharpe)
        return max(0.0, min(1.0, normalized))
    
    def _calculate_collective_score(self, strategy_name: str) -> float:
        """Calculate collective score based on warnings.
        
        Returns 1.0 if no warnings, lower scores for strategies with warnings.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Collective score between 0 and 1
        """
        warnings = self._warnings_cache.get(strategy_name, [])
        if not warnings:
            return 1.0
        
        # Reduce score based on warning severity
        severity_penalty = {
            "low": 0.1,
            "medium": 0.25,
            "high": 0.5,
            "critical": 0.75,
        }
        
        total_penalty = 0.0
        for warning in warnings:
            severity = warning.get("severity", "medium")
            penalty = severity_penalty.get(severity, 0.25)
            total_penalty = max(total_penalty, penalty)
        
        return max(0.1, 1.0 - total_penalty)
    
    def _score_strategy(self, strategy_name: str) -> Optional[StrategyScore]:
        """Calculate composite score for a strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            StrategyScore if strategy exists, None otherwise
        """
        metadata = self._load_strategy_metadata(strategy_name)
        if not metadata:
            return None
        
        win_rate = metadata.win_rate if metadata.total_trades > 0 else 0.0
        normalized_sharpe = self._normalize_sharpe(metadata.sharpe_ratio)
        recency = self._calculate_recency(metadata.last_trade_timestamp)
        collective = self._calculate_collective_score(strategy_name)
        
        score = (
            win_rate * WEIGHT_WIN_RATE +
            normalized_sharpe * WEIGHT_SHARPE +
            recency * WEIGHT_RECENCY +
            collective * WEIGHT_COLLECTIVE
        )
        
        return StrategyScore(
            name=strategy_name,
            score=score,
            win_rate=win_rate,
            normalized_sharpe=normalized_sharpe,
            recency=recency,
            collective_score=collective,
            metadata=metadata,
        )
    
    def _get_consecutive_losses(self, strategy_name: str) -> int:
        """Get consecutive losses count for a strategy.
        
        Reads from the YAML metadata file directly since consecutive_losses
        may not always be in the cached data.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Number of consecutive losses (0 if unknown/not found)
        """
        metadata = self._load_strategy_metadata(strategy_name)
        if metadata is None:
            return 0
        
        # consecutive_losses might be stored at top level of the strategy file
        # Check the cached data
        if strategy_name in self._strategy_cache:
            data = self._strategy_cache[strategy_name]
            return data.get("consecutive_losses", 0)
        
        # Try loading from file directly
        strategy_path = self.strategies_dir / f"{strategy_name}.yaml"
        if strategy_path.exists():
            try:
                data = yaml.safe_load(strategy_path.read_text(encoding="utf-8"))
                if data:
                    self._strategy_cache[strategy_name] = data
                    return data.get("consecutive_losses", 0)
            except Exception:
                pass
        
        return 0
    
    def get_best_strategy(self, context: str) -> Optional[str]:
        """Get the highest-scoring strategy for a context.
        
        Context can be 'yield', 'swap', or 'lp'. For now, all contexts
        use the same scoring as the strategy metadata doesn't distinguish
        by context. This could be extended to have context-specific scores.
        
        Args:
            context: Trading context ('yield', 'swap', 'lp')
            
        Returns:
            Strategy name with highest score, or None if no strategies exist
        """
        # Filter strategies that should be avoided
        candidates = []
        for strategy_name in self._strategy_cache.keys():
            avoid, _ = self.should_avoid(strategy_name)
            if not avoid:
                score = self._score_strategy(strategy_name)
                if score:
                    candidates.append((strategy_name, score.score))
        
        if not candidates:
            return None
        
        # Return highest scoring
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    def should_avoid(self, strategy: str) -> Tuple[bool, Optional[str]]:
        """Check if a strategy should be avoided.
        
        A strategy should be avoided if:
        - Win rate is below 30%
        - Has 3 or more consecutive losses
        - Has an active warning
        
        Args:
            strategy: Strategy name
            
        Returns:
            Tuple of (should_avoid: bool, reason: Optional[str])
        """
        metadata = self._load_strategy_metadata(strategy)
        
        # Check win rate
        if metadata and metadata.total_trades >= 5:  # Only enforce after min trades
            if metadata.win_rate < AVOID_WIN_RATE_THRESHOLD:
                return True, f"Low win rate: {metadata.win_rate:.1%} (below {AVOID_WIN_RATE_THRESHOLD:.0%})"
        
        # Check consecutive losses
        consecutive_losses = self._get_consecutive_losses(strategy)
        if consecutive_losses >= AVOID_CONSECUTIVE_LOSSES_THRESHOLD:
            return True, f"Consecutive losses: {consecutive_losses} (>= {AVOID_CONSECUTIVE_LOSSES_THRESHOLD})"
        
        # Check active warnings
        warnings = self._warnings_cache.get(strategy, [])
        if warnings:
            high_severity = [w for w in warnings if w.get("severity") in ("high", "critical")]
            if high_severity:
                return True, f"Active warning: {high_severity[0].get('reason', 'See collective warnings')}"
        
        return False, None
    
    def get_active_nudges(self) -> List[Dict[str, Any]]:
        """Get all active (pending) nudges from strategy YAML files.
        
        Nudges are stored in the pending_nudges field of each strategy YAML.
        
        Returns:
            List of nudge dicts with keys: nudge_id, strategy_name, message, created_at, applied
        """
        nudges = []
        
        for strategy_name, data in self._strategy_cache.items():
            pending = data.get("pending_nudges", [])
            for nudge in pending:
                if isinstance(nudge, dict) and not nudge.get("applied", False):
                    nudges.append({
                        "nudge_id": nudge.get("nudge_id", ""),
                        "strategy_name": strategy_name,
                        "message": nudge.get("message", ""),
                        "created_at": nudge.get("created_at", 0.0),
                        "applied": False,
                    })
        
        return nudges
    
    def apply_nudge(self, strategy: str, nudge_id: str) -> bool:
        """Mark a nudge as applied in the strategy YAML file.
        
        Args:
            strategy: Strategy name
            nudge_id: ID of the nudge to mark as applied
            
        Returns:
            True if nudge was found and applied, False otherwise
        """
        strategy_path = self.strategies_dir / f"{strategy}.yaml"
        if not strategy_path.exists():
            logger.warning(f"Strategy file not found: {strategy_path}")
            return False
        
        try:
            data = yaml.safe_load(strategy_path.read_text(encoding="utf-8"))
            if not data:
                data = {"strategy_name": strategy}
            
            pending = data.get("pending_nudges", [])
            applied = False
            
            for nudge in pending:
                if isinstance(nudge, dict) and nudge.get("nudge_id") == nudge_id:
                    nudge["applied"] = True
                    nudge["applied_at"] = datetime.now(timezone.utc).isoformat()
                    applied = True
            
            if applied:
                data["pending_nudges"] = pending
                strategy_path.write_text(
                    yaml.safe_dump(data, default_flow_style=False, sort_keys=False),
                    encoding="utf-8",
                )
                # Update cache
                self._strategy_cache[strategy] = data
                logger.info(f"Applied nudge {nudge_id} for strategy {strategy}")
            
            return applied
        except Exception as e:
            logger.error(f"Failed to apply nudge {nudge_id} for {strategy}: {e}")
            return False
    
    def get_strategy_ranking(self) -> List[Tuple[str, float]]:
        """Get all strategies sorted by composite score.
        
        Returns:
            List of (strategy_name, score) tuples, sorted highest first
        """
        scored_strategies = []
        
        for strategy_name in self._strategy_cache.keys():
            score = self._score_strategy(strategy_name)
            if score:
                scored_strategies.append((strategy_name, score.score))
        
        scored_strategies.sort(key=lambda x: x[1], reverse=True)
        return scored_strategies
    
    def register_outcome(self, strategy: str, won: bool, pnl: float) -> bool:
        """Convenience method to register a trade outcome.
        
        This delegates to the dojo_bridge if available. Creates a synthetic
        SwapTrade to pass to the bridge.
        
        Args:
            strategy: Strategy name
            won: Whether the trade was a win
            pnl: PnL in USD
            
        Returns:
            True if registered successfully, False otherwise
        """
        if not self.dojo_bridge:
            logger.warning("No dojo_bridge configured, cannot register outcome")
            return False
        
        try:
            # Create a synthetic trade for the dojo bridge
            from borg.defi.swap_executor import SwapTrade
            trade = SwapTrade(
                trade_id=f"selector_{strategy}_{int(time.time())}",
                timestamp=time.time(),
                chain="unknown",
                provider="selector",
                input_token="unknown",
                output_token="unknown",
                input_amount=0,
                output_amount=0,
                output_amount_usd=pnl if won else 0,
                gas_used_usd=abs(pnl) if not won else 0,
                price_impact_pct=0,
                slippage_bps=0,
                success=won,
                wallet="selector",
                session_id="selector",
            )
            
            # Let dojo bridge classify and record
            classification = self.dojo_bridge.classify_trade_outcome(trade)
            self.dojo_bridge.record_outcome(trade, classification, strategy)
            self.dojo_bridge.update_strategy_reputation(strategy, trade)
            
            # Reload strategy cache after update
            self._load_all_strategies()
            
            return True
        except Exception as e:
            logger.error(f"Failed to register outcome for {strategy}: {e}")
            return False
    
    def get_strategy_details(self, strategy: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a strategy.
        
        Args:
            strategy: Strategy name
            
        Returns:
            Dict with strategy details or None if not found
        """
        metadata = self._load_strategy_metadata(strategy)
        if not metadata:
            return None
        
        score = self._score_strategy(strategy)
        avoid, reason = self.should_avoid(strategy)
        
        return {
            "name": strategy,
            "metadata": metadata.to_dict(),
            "score": score.score if score else 0.0,
            "score_breakdown": {
                "win_rate": score.win_rate if score else 0.0,
                "normalized_sharpe": score.normalized_sharpe if score else 0.0,
                "recency": score.recency if score else 0.0,
                "collective": score.collective_score if score else 1.0,
            },
            "should_avoid": avoid,
            "avoid_reason": reason,
            "consecutive_losses": self._get_consecutive_losses(strategy),
            "warnings": self._warnings_cache.get(strategy, []),
        }
    
    def refresh(self) -> None:
        """Refresh cached data from disk."""
        self._strategy_cache.clear()
        self._warnings_cache.clear()
        self._load_all_strategies()
        self._load_all_warnings()
    
    def strategies_for_context(self, context: str) -> List[str]:
        """Get list of strategies suitable for a context.
        
        Args:
            context: Context type ('yield', 'swap', 'lp')
            
        Returns:
            List of strategy names that are suitable (not avoided)
        """
        suitable = []
        for strategy_name in self._strategy_cache.keys():
            avoid, _ = self.should_avoid(strategy_name)
            if not avoid:
                suitable.append(strategy_name)
        return suitable


class ReputationBoostedYieldScanner:
    """YieldScanner wrapper that applies strategy reputation boosts/penalties.
    
    This class wraps a YieldScanner and adjusts opportunity scores
    based on strategy reputation from the dojo feedback loop.
    """
    
    def __init__(
        self,
        yield_scanner: YieldScanner,
        strategy_selector: Optional[StrategySelector] = None,
        boost_factor: float = 0.2,
        penalty_factor: float = 0.3,
    ):
        """Initialize with a YieldScanner and optional StrategySelector.
        
        Args:
            yield_scanner: The YieldScanner to wrap
            strategy_selector: Optional StrategySelector for reputation data
            boost_factor: How much to boost good strategies (0.2 = 20%)
            penalty_factor: How much to penalize bad strategies (0.3 = 30%)
        """
        self.scanner = yield_scanner
        self.selector = strategy_selector
        self.boost_factor = boost_factor
        self.penalty_factor = penalty_factor
    
    def rank_opportunities(
        self,
        opps: List[Any],
        min_tvl: Optional[float] = None,
        max_risk: Optional[float] = None,
        strategy_name: Optional[str] = None,
    ) -> List[Any]:
        """Rank opportunities with strategy reputation boost/penalty.
        
        Args:
            opps: List of YieldOpportunity to rank
            min_tvl: Optional override for min TVL filter
            max_risk: Optional override for max risk filter
            strategy_name: Optional strategy name to get reputation boost from
            
        Returns:
            Sorted list of YieldOpportunity with reputation adjustments applied
        """
        # First, get base ranking
        ranked = self.scanner.rank_opportunities(opps, min_tvl, max_risk)
        
        if not self.selector or not strategy_name:
            return ranked
        
        # Check if strategy should be avoided - apply penalty
        avoid, reason = self.selector.should_avoid(strategy_name)
        if avoid:
            # Apply penalty to all opportunities
            for opp in ranked:
                opp.apy = opp.apy * (1 - self.penalty_factor)
            return ranked
        
        # Get strategy score for potential boost
        score_data = self.selector.get_strategy_details(strategy_name)
        if not score_data:
            return ranked
        
        score_breakdown = score_data.get("score_breakdown", {})
        
        # Boost if strategy has good metrics
        win_rate = score_breakdown.get("win_rate", 0)
        collective = score_breakdown.get("collective", 1.0)
        
        # Only boost if win rate > 50% and no warnings
        if win_rate > 0.5 and collective >= 0.9:
            boost = 1 + (self.boost_factor * (win_rate - 0.5) * 2)  # Scale boost
            for opp in ranked:
                opp.apy = opp.apy * boost
        
        return ranked
    
    def __getattr__(self, name: str):
        """Proxy all other attribute access to the wrapped scanner."""
        return getattr(self.scanner, name)
