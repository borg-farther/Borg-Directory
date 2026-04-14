"""Tests for StrategySelector and dojo feedback loop."""

import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from borg.defi.data_models import DeFiPackMetadata
from borg.defi.strategy_selector import (
    StrategySelector,
    StrategyScore,
    WEIGHT_WIN_RATE,
    WEIGHT_SHARPE,
    WEIGHT_RECENCY,
    WEIGHT_COLLECTIVE,
    AVOID_WIN_RATE_THRESHOLD,
    AVOID_CONSECUTIVE_LOSSES_THRESHOLD,
)


class TestScoringFormula:
    """Tests for the scoring formula."""

    def test_score_formula_weights_sum_to_one(self):
        """Verify that score weights sum to 1.0."""
        total = WEIGHT_WIN_RATE + WEIGHT_SHARPE + WEIGHT_RECENCY + WEIGHT_COLLECTIVE
        assert abs(total - 1.0) < 0.001

    def test_score_with_perfect_strategy(self):
        """Test score calculation for a theoretically perfect strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create a strategy with perfect metrics
            metadata = DeFiPackMetadata(
                total_trades=100,
                winning_trades=95,
                total_pnl_usd=5000.0,
                max_drawdown_pct=2.0,
                sharpe_ratio=4.0,  # Maximum Sharpe
                win_rate=0.95,
                avg_return_per_trade=50.0,
                last_trade_timestamp=time.time(),  # Recent = 1.0 recency
                chains=["solana"],
                protocols=["jupiter"],
            )
            
            strategy_data = {
                "strategy_name": "perfect-strategy",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 0,
                "pending_nudges": [],
            }
            
            (strategies_dir / "perfect-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            # Get score breakdown
            score = selector._score_strategy("perfect-strategy")
            
            assert score is not None
            assert score.win_rate == 0.95
            assert score.normalized_sharpe == 1.0  # Max Sharpe = 4.0
            assert abs(score.recency - 1.0) < 0.01  # Recent trade (within 1% of 1.0)
            assert score.collective_score == 1.0  # No warnings
            
            # Expected: 0.95*0.4 + 1.0*0.3 + 1.0*0.2 + 1.0*0.1 = 0.38 + 0.3 + 0.2 + 0.1 = 0.98
            expected = 0.95 * WEIGHT_WIN_RATE + 1.0 * WEIGHT_SHARPE + 1.0 * WEIGHT_RECENCY + 1.0 * WEIGHT_COLLECTIVE
            assert abs(score.score - expected) < 0.01

    def test_score_with_poor_strategy(self):
        """Test score calculation for a poor strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create a strategy with poor metrics
            metadata = DeFiPackMetadata(
                total_trades=50,
                winning_trades=10,
                total_pnl_usd=-500.0,
                max_drawdown_pct=30.0,
                sharpe_ratio=-2.0,  # Minimum Sharpe
                win_rate=0.20,
                avg_return_per_trade=-10.0,
                last_trade_timestamp=time.time() - (30 * 24 * 60 * 60),  # 30 days old
                chains=["ethereum"],
                protocols=["uniswap"],
            )
            
            strategy_data = {
                "strategy_name": "poor-strategy",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 0,
                "pending_nudges": [],
            }
            
            (strategies_dir / "poor-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            score = selector._score_strategy("poor-strategy")
            
            assert score is not None
            assert score.win_rate == 0.20
            assert score.normalized_sharpe == 0.0  # Min Sharpe = -2.0
            # Recency for 30 days old: half-life is 7 days, so 30/7 ~ 4.3 half-lives
            # 1 / 2^4.3 ~= 0.05
            assert score.recency < 0.1
            assert score.collective_score == 1.0
            # Overall score should be low
            assert score.score < 0.3

    def test_normalize_sharpe(self):
        """Test Sharpe ratio normalization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            selector = StrategySelector(strategies_dir=Path(tmpdir))
            
            # Min Sharpe (-2.0) should normalize to 0
            assert selector._normalize_sharpe(-2.0) == 0.0
            
            # Max Sharpe (4.0) should normalize to 1
            assert selector._normalize_sharpe(4.0) == 1.0
            
            # Midpoint Sharpe (1.0) should normalize to 0.5
            assert abs(selector._normalize_sharpe(1.0) - 0.5) < 0.01
            
            # Values outside range should be clamped
            assert selector._normalize_sharpe(-5.0) == 0.0
            assert selector._normalize_sharpe(10.0) == 1.0

    def test_recency_calculation(self):
        """Test recency score calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            selector = StrategySelector(strategies_dir=Path(tmpdir))
            
            now = time.time()
            
            # Very recent (now) should give 1.0
            assert abs(selector._calculate_recency(now) - 1.0) < 0.01
            
            # 7 days ago (one half-life) should give ~0.5
            week_ago = now - (7 * 24 * 60 * 60)
            assert abs(selector._calculate_recency(week_ago) - 0.5) < 0.01
            
            # Old timestamp (0) should give 0
            assert selector._calculate_recency(0) == 0.0


class TestAvoidanceLogic:
    """Tests for the should_avoid method."""

    def test_avoid_low_win_rate(self):
        """Test that strategies with <30% win rate are avoided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Strategy with 25% win rate
            metadata = DeFiPackMetadata(
                total_trades=20,
                winning_trades=5,
                win_rate=0.25,
                sharpe_ratio=0.0,
            )
            
            strategy_data = {
                "strategy_name": "low-win-rate",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 0,
            }
            
            (strategies_dir / "low-win-rate.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            avoid, reason = selector.should_avoid("low-win-rate")
            
            assert avoid is True
            assert "win rate" in reason.lower()
            assert "25" in reason

    def test_avoid_consecutive_losses(self):
        """Test that strategies with >=3 consecutive losses are avoided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            metadata = DeFiPackMetadata(
                total_trades=10,
                winning_trades=5,
                win_rate=0.50,
            )
            
            strategy_data = {
                "strategy_name": "loss-streak",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 3,  # Exactly the threshold
            }
            
            (strategies_dir / "loss-streak.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            avoid, reason = selector.should_avoid("loss-streak")
            
            assert avoid is True
            assert "consecutive losses" in reason.lower()

    def test_avoid_high_severity_warning(self):
        """Test that strategies with high severity warnings are avoided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            warnings_dir = Path(tmpdir) / "warnings"
            strategies_dir.mkdir()
            warnings_dir.mkdir()
            
            metadata = DeFiPackMetadata(
                total_trades=10,
                winning_trades=6,
                win_rate=0.60,
            )
            
            strategy_data = {
                "strategy_name": "warned-strategy",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 0,
            }
            
            warning_data = {
                "type": "rug_exploit_warning",
                "token": "SOME_TOKEN",
                "reason": "honeypot detected",
                "severity": "high",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "affected_strategies": ["warned-strategy"],
            }
            
            (strategies_dir / "warned-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            (warnings_dir / "warning_honeypot.yaml").write_text(
                yaml.safe_dump(warning_data), encoding="utf-8"
            )
            
            selector = StrategySelector(
                strategies_dir=strategies_dir,
                warnings_dir=warnings_dir,
            )
            avoid, reason = selector.should_avoid("warned-strategy")
            
            assert avoid is True
            assert "warning" in reason.lower()

    def test_no_avoid_good_strategy(self):
        """Test that good strategies are not marked for avoidance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            metadata = DeFiPackMetadata(
                total_trades=50,
                winning_trades=35,
                win_rate=0.70,
                sharpe_ratio=1.5,
            )
            
            strategy_data = {
                "strategy_name": "good-strategy",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 1,
            }
            
            (strategies_dir / "good-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            avoid, reason = selector.should_avoid("good-strategy")
            
            assert avoid is False
            assert reason is None


class TestYAMLRoundTrip:
    """Tests for YAML read/write operations."""

    def test_load_existing_strategies(self):
        """Test loading strategies from YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create multiple strategy files
            for i in range(3):
                metadata = DeFiPackMetadata(
                    total_trades=10 * (i + 1),
                    winning_trades=6 * (i + 1),
                    win_rate=0.60,
                    sharpe_ratio=float(i) * 0.5,
                )
                
                strategy_data = {
                    "strategy_name": f"strategy-{i}",
                    "metadata": metadata.to_dict(),
                    "consecutive_losses": 0,
                }
                
                (strategies_dir / f"strategy-{i}.yaml").write_text(
                    yaml.safe_dump(strategy_data), encoding="utf-8"
                )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            # Should have loaded all 3 strategies
            assert len(selector._strategy_cache) == 3
            assert "strategy-0" in selector._strategy_cache
            assert "strategy-1" in selector._strategy_cache
            assert "strategy-2" in selector._strategy_cache

    def test_metadata_persistence(self):
        """Test that metadata is correctly persisted and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            original_metadata = DeFiPackMetadata(
                total_trades=100,
                winning_trades=75,
                total_pnl_usd=2500.0,
                max_drawdown_pct=5.5,
                sharpe_ratio=2.1,
                win_rate=0.75,
                avg_return_per_trade=25.0,
                last_trade_timestamp=1234567890.0,
                chains=["solana", "ethereum"],
                protocols=["jupiter", "uniswap"],
            )
            
            strategy_data = {
                "strategy_name": "persist-test",
                "metadata": original_metadata.to_dict(),
                "consecutive_losses": 2,
            }
            
            path = strategies_dir / "persist-test.yaml"
            path.write_text(yaml.safe_dump(strategy_data), encoding="utf-8")
            
            # Load and verify
            selector = StrategySelector(strategies_dir=strategies_dir)
            loaded = selector._load_strategy_metadata("persist-test")
            
            assert loaded is not None
            assert loaded.total_trades == original_metadata.total_trades
            assert loaded.winning_trades == original_metadata.winning_trades
            assert loaded.total_pnl_usd == original_metadata.total_pnl_usd
            assert loaded.max_drawdown_pct == original_metadata.max_drawdown_pct
            assert loaded.sharpe_ratio == original_metadata.sharpe_ratio
            assert loaded.win_rate == original_metadata.win_rate
            assert loaded.avg_return_per_trade == original_metadata.avg_return_per_trade
            assert loaded.last_trade_timestamp == original_metadata.last_trade_timestamp
            assert loaded.chains == original_metadata.chains
            assert loaded.protocols == original_metadata.protocols

    def test_refresh_reloads_from_disk(self):
        """Test that refresh() clears cache and reloads from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create initial strategy
            metadata = DeFiPackMetadata(total_trades=10, winning_trades=6)
            strategy_data = {
                "strategy_name": "refresh-test",
                "metadata": metadata.to_dict(),
            }
            (strategies_dir / "refresh-test.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            assert len(selector._strategy_cache) == 1
            
            # Add another strategy directly to disk
            metadata2 = DeFiPackMetadata(total_trades=20, winning_trades=12)
            strategy_data2 = {
                "strategy_name": "refresh-test-2",
                "metadata": metadata2.to_dict(),
            }
            (strategies_dir / "refresh-test-2.yaml").write_text(
                yaml.safe_dump(strategy_data2), encoding="utf-8"
            )
            
            # Before refresh, cache only has 1
            assert len(selector._strategy_cache) == 1
            
            # After refresh, should have 2
            selector.refresh()
            assert len(selector._strategy_cache) == 2


class TestNudgeLifecycle:
    """Tests for nudge creation, reading, and applying."""

    def test_get_active_nudges(self):
        """Test reading pending nudges from strategy files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            nudges = [
                {
                    "nudge_id": "nudge-001",
                    "message": "Consider reducing position size",
                    "created_at": time.time(),
                    "applied": False,
                },
                {
                    "nudge_id": "nudge-002",
                    "message": "Review entry timing",
                    "created_at": time.time(),
                    "applied": False,
                },
            ]
            
            strategy_data = {
                "strategy_name": "nudge-test",
                "metadata": {"total_trades": 10},
                "pending_nudges": nudges,
            }
            
            (strategies_dir / "nudge-test.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            active = selector.get_active_nudges()
            
            assert len(active) == 2
            # Should not include applied nudges
            assert all(n["applied"] is False for n in active)

    def test_apply_nudge(self):
        """Test marking a nudge as applied."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            nudges = [
                {
                    "nudge_id": "nudge-to-apply",
                    "message": "Test nudge",
                    "created_at": time.time(),
                    "applied": False,
                },
                {
                    "nudge_id": "nudge-to-keep",
                    "message": "Keep this one",
                    "created_at": time.time(),
                    "applied": False,
                },
            ]
            
            strategy_data = {
                "strategy_name": "apply-test",
                "metadata": {"total_trades": 10},
                "pending_nudges": nudges,
            }
            
            path = strategies_dir / "apply-test.yaml"
            path.write_text(yaml.safe_dump(strategy_data), encoding="utf-8")
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            result = selector.apply_nudge("apply-test", "nudge-to-apply")
            
            assert result is True
            
            # Verify the nudge was marked as applied
            selector.refresh()
            active = selector.get_active_nudges()
            
            # Should only have one active nudge now
            assert len(active) == 1
            assert active[0]["nudge_id"] == "nudge-to-keep"

    def test_apply_nudge_not_found(self):
        """Test applying a non-existent nudge returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            strategy_data = {
                "strategy_name": "nonexistent",
                "metadata": {"total_trades": 10},
                "pending_nudges": [],
            }
            
            (strategies_dir / "nonexistent.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            result = selector.apply_nudge("nonexistent", "fake-nudge")
            
            assert result is False

    def test_nudge_not_found_for_nonexistent_strategy(self):
        """Test applying nudge to non-existent strategy returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            result = selector.apply_nudge("totally-fake", "nudge-id")
            
            assert result is False


class TestRanking:
    """Tests for strategy ranking."""

    def test_ranking_sorted_by_score(self):
        """Test that ranking returns strategies sorted by score."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create strategies with different performance
            best_metadata = DeFiPackMetadata(
                total_trades=100, winning_trades=80, win_rate=0.80,
                sharpe_ratio=3.0, last_trade_timestamp=time.time(),
            )
            mid_metadata = DeFiPackMetadata(
                total_trades=100, winning_trades=55, win_rate=0.55,
                sharpe_ratio=1.0, last_trade_timestamp=time.time(),
            )
            worst_metadata = DeFiPackMetadata(
                total_trades=100, winning_trades=30, win_rate=0.30,
                sharpe_ratio=-1.0, last_trade_timestamp=time.time() - 86400 * 30,
            )
            
            for name, metadata in [("best", best_metadata), ("mid", mid_metadata), ("worst", worst_metadata)]:
                strategy_data = {
                    "strategy_name": name,
                    "metadata": metadata.to_dict(),
                    "consecutive_losses": 0,
                }
                (strategies_dir / f"{name}.yaml").write_text(
                    yaml.safe_dump(strategy_data), encoding="utf-8"
                )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            ranking = selector.get_strategy_ranking()
            
            assert len(ranking) == 3
            # Should be sorted highest to lowest
            assert ranking[0][0] == "best"
            assert ranking[1][0] == "mid"
            assert ranking[2][0] == "worst"
            # Scores should be descending
            assert ranking[0][1] >= ranking[1][1] >= ranking[2][1]

    def test_get_best_strategy(self):
        """Test getting the best strategy for a context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create strategies
            good_metadata = DeFiPackMetadata(
                total_trades=50, winning_trades=40, win_rate=0.80,
                sharpe_ratio=2.0, last_trade_timestamp=time.time(),
            )
            bad_metadata = DeFiPackMetadata(
                total_trades=50, winning_trades=15, win_rate=0.30,
                sharpe_ratio=-0.5, last_trade_timestamp=time.time(),
            )
            
            for name, metadata in [("good-strat", good_metadata), ("bad-strat", bad_metadata)]:
                strategy_data = {
                    "strategy_name": name,
                    "metadata": metadata.to_dict(),
                    "consecutive_losses": 0,
                }
                (strategies_dir / f"{name}.yaml").write_text(
                    yaml.safe_dump(strategy_data), encoding="utf-8"
                )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            best = selector.get_best_strategy("swap")
            
            assert best == "good-strat"


class TestEmptyState:
    """Tests for empty state handling."""

    def test_no_strategies_returns_none(self):
        """Test that get_best_strategy returns None when no strategies exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()  # Empty directory
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            assert selector.get_best_strategy("swap") is None
            assert selector.get_best_strategy("yield") is None
            assert selector.get_best_strategy("lp") is None

    def test_no_strategies_returns_empty_ranking(self):
        """Test that get_strategy_ranking returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            assert selector.get_strategy_ranking() == []

    def test_no_strategy_returns_no_avoid(self):
        """Test that should_avoid returns False for unknown strategies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            avoid, reason = selector.should_avoid("totally-unknown")
            assert avoid is False
            assert reason is None

    def test_no_nudges_returns_empty(self):
        """Test that get_active_nudges returns empty list when no nudges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            assert selector.get_active_nudges() == []


class TestFullRoundTrip:
    """Full round-trip tests for the feedback loop."""

    def test_bad_outcomes_then_good_outcomes(self):
        """Test full cycle: bad outcomes -> avoid -> good outcomes -> recommend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            warnings_dir = Path(tmpdir) / "warnings"
            strategies_dir.mkdir()
            warnings_dir.mkdir()
            
            # Create a strategy file
            metadata = DeFiPackMetadata(
                total_trades=10,
                winning_trades=5,
                win_rate=0.50,
                sharpe_ratio=0.0,
            )
            
            strategy_data = {
                "strategy_name": "roundtrip-strategy",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 0,
                "pending_nudges": [],
            }
            
            (strategies_dir / "roundtrip-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(
                strategies_dir=strategies_dir,
                warnings_dir=warnings_dir,
            )
            
            # Initially should not be avoided
            avoid, _ = selector.should_avoid("roundtrip-strategy")
            assert avoid is False
            
            # Simulate bad outcomes by updating the file with consecutive losses
            bad_metadata = DeFiPackMetadata(
                total_trades=15,
                winning_trades=3,
                win_rate=0.20,  # Below threshold
                sharpe_ratio=-1.0,
            )
            
            bad_strategy_data = {
                "strategy_name": "roundtrip-strategy",
                "metadata": bad_metadata.to_dict(),
                "consecutive_losses": 4,  # Above threshold
                "pending_nudges": [],
            }
            
            (strategies_dir / "roundtrip-strategy.yaml").write_text(
                yaml.safe_dump(bad_strategy_data), encoding="utf-8"
            )
            
            # Refresh and check
            selector.refresh()
            
            avoid, reason = selector.should_avoid("roundtrip-strategy")
            assert avoid is True
            assert "win rate" in reason.lower() or "consecutive losses" in reason.lower()
            
            # Should not be recommended
            best = selector.get_best_strategy("swap")
            assert best != "roundtrip-strategy"
            
            # Simulate recovery: good outcomes
            good_metadata = DeFiPackMetadata(
                total_trades=50,
                winning_trades=35,
                win_rate=0.70,
                sharpe_ratio=1.5,
            )
            
            good_strategy_data = {
                "strategy_name": "roundtrip-strategy",
                "metadata": good_metadata.to_dict(),
                "consecutive_losses": 0,
                "pending_nudges": [],
            }
            
            (strategies_dir / "roundtrip-strategy.yaml").write_text(
                yaml.safe_dump(good_strategy_data), encoding="utf-8"
            )
            
            # Refresh and verify recovery
            selector.refresh()
            
            avoid, reason = selector.should_avoid("roundtrip-strategy")
            assert avoid is False
            
            best = selector.get_best_strategy("swap")
            assert best == "roundtrip-strategy"

    def test_warning_creates_avoid(self):
        """Test that adding a warning causes a strategy to be avoided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            warnings_dir = Path(tmpdir) / "warnings"
            strategies_dir.mkdir()
            warnings_dir.mkdir()
            
            # Good strategy initially
            metadata = DeFiPackMetadata(
                total_trades=50,
                winning_trades=35,
                win_rate=0.70,
            )
            
            strategy_data = {
                "strategy_name": "warned-recovery",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 0,
            }
            
            (strategies_dir / "warned-recovery.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(
                strategies_dir=strategies_dir,
                warnings_dir=warnings_dir,
            )
            
            # Should not be avoided initially
            avoid, _ = selector.should_avoid("warned-recovery")
            assert avoid is False
            
            # Add a critical warning
            warning_data = {
                "type": "rug_exploit_warning",
                "token": "PROBLEMATIC_TOKEN",
                "reason": "Potential rug detected",
                "severity": "critical",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "affected_strategies": ["warned-recovery"],
            }
            
            (warnings_dir / "warning_critical.yaml").write_text(
                yaml.safe_dump(warning_data), encoding="utf-8"
            )
            
            # Refresh and check
            selector.refresh()
            
            avoid, reason = selector.should_avoid("warned-recovery")
            assert avoid is True
            assert "warning" in reason.lower()


class TestContextFilter:
    """Tests for context-based strategy filtering."""

    def test_strategies_for_context(self):
        """Test filtering strategies by context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create multiple strategies
            for i in range(5):
                metadata = DeFiPackMetadata(
                    total_trades=10,
                    winning_trades=5 + i,  # Varying win rates
                    win_rate=(0.5 + i * 0.1),
                )
                
                strategy_data = {
                    "strategy_name": f"context-strat-{i}",
                    "metadata": metadata.to_dict(),
                    "consecutive_losses": 0,
                }
                
                (strategies_dir / f"context-strat-{i}.yaml").write_text(
                    yaml.safe_dump(strategy_data), encoding="utf-8"
                )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            # All should be suitable since none are avoided
            suitable = selector.strategies_for_context("swap")
            assert len(suitable) == 5

    def test_avoided_strategies_not_in_context(self):
        """Test that avoided strategies are filtered from context."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            # Create good and bad strategies
            good_metadata = DeFiPackMetadata(
                total_trades=50,
                winning_trades=35,
                win_rate=0.70,
            )
            
            bad_metadata = DeFiPackMetadata(
                total_trades=50,
                winning_trades=10,
                win_rate=0.20,
            )
            
            for name, metadata in [("good", good_metadata), ("bad", bad_metadata)]:
                strategy_data = {
                    "strategy_name": name,
                    "metadata": metadata.to_dict(),
                    "consecutive_losses": 0,
                }
                (strategies_dir / f"{name}.yaml").write_text(
                    yaml.safe_dump(strategy_data), encoding="utf-8"
                )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            
            suitable = selector.strategies_for_context("swap")
            assert "good" in suitable
            assert "bad" not in suitable


class TestStrategyDetails:
    """Tests for get_strategy_details method."""

    def test_get_details_for_existing_strategy(self):
        """Test getting details for an existing strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            metadata = DeFiPackMetadata(
                total_trades=100,
                winning_trades=75,
                total_pnl_usd=2500.0,
                max_drawdown_pct=5.0,
                sharpe_ratio=2.0,
                win_rate=0.75,
            )
            
            strategy_data = {
                "strategy_name": "detailed-strategy",
                "metadata": metadata.to_dict(),
                "consecutive_losses": 1,
            }
            
            (strategies_dir / "detailed-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            details = selector.get_strategy_details("detailed-strategy")
            
            assert details is not None
            assert details["name"] == "detailed-strategy"
            assert details["metadata"]["total_trades"] == 100
            assert details["consecutive_losses"] == 1
            assert details["should_avoid"] is False
            assert "score_breakdown" in details

    def test_get_details_for_nonexistent_strategy(self):
        """Test that get_details returns None for unknown strategy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            strategies_dir.mkdir()
            
            selector = StrategySelector(strategies_dir=strategies_dir)
            details = selector.get_strategy_details("unknown")
            
            assert details is None


class TestCollectiveWarnings:
    """Tests for collective warning loading and processing."""

    def test_load_warnings_from_files(self):
        """Test that warnings are loaded from YAML files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            warnings_dir = Path(tmpdir) / "warnings"
            strategies_dir.mkdir()
            warnings_dir.mkdir()
            
            # Create strategy
            metadata = DeFiPackMetadata(total_trades=10, winning_trades=6)
            strategy_data = {
                "strategy_name": "warned-strategy",
                "metadata": metadata.to_dict(),
            }
            (strategies_dir / "warned-strategy.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            # Create warning
            warning_data = {
                "type": "rug_exploit_warning",
                "token": "RISKY_TOKEN",
                "reason": "Suspicious contract",
                "severity": "high",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "affected_strategies": ["warned-strategy"],
            }
            
            (warnings_dir / "warning_risky.yaml").write_text(
                yaml.safe_dump(warning_data), encoding="utf-8"
            )
            
            selector = StrategySelector(
                strategies_dir=strategies_dir,
                warnings_dir=warnings_dir,
            )
            
            # Strategy should have warning in cache
            assert "warned-strategy" in selector._warnings_cache
            assert len(selector._warnings_cache["warned-strategy"]) == 1

    def test_collective_score_with_multiple_warnings(self):
        """Test collective score calculation with multiple warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            strategies_dir = Path(tmpdir) / "strategies"
            warnings_dir = Path(tmpdir) / "warnings"
            strategies_dir.mkdir()
            warnings_dir.mkdir()
            
            metadata = DeFiPackMetadata(total_trades=10, winning_trades=6)
            strategy_data = {
                "strategy_name": "multi-warned",
                "metadata": metadata.to_dict(),
            }
            (strategies_dir / "multi-warned.yaml").write_text(
                yaml.safe_dump(strategy_data), encoding="utf-8"
            )
            
            # Create multiple warnings
            for i, severity in enumerate(["low", "medium", "high", "critical"]):
                warning_data = {
                    "type": "rug_exploit_warning",
                    "token": f"TOKEN_{i}",
                    "reason": f"Warning {i}",
                    "severity": severity,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "affected_strategies": ["multi-warned"],
                }
                (warnings_dir / f"warning_{i}.yaml").write_text(
                    yaml.safe_dump(warning_data), encoding="utf-8"
                )
            
            selector = StrategySelector(
                strategies_dir=strategies_dir,
                warnings_dir=warnings_dir,
            )
            
            # Collective score should be reduced by the highest severity warning
            score = selector._calculate_collective_score("multi-warned")
            assert score < 1.0
            # Critical penalty is 0.75, so score should be at least 0.25
            assert score >= 0.25
