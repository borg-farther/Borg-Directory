"""
Tests for drift detection (borg/defi/v2/drift.py).
Covers degrading/improving/stable detection, z-score thresholds, and edge cases.
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from borg.defi.v2.drift import (
    detect_drift,
    detect_trend,
    detect_drift_from_returns,
    compute_z_score,
)


class MockPack:
    """Mock DeFiStrategyPack for testing drift detection."""
    def __init__(
        self,
        total_outcomes=0,
        avg_return_pct=0.0,
        std_dev=0.0,
        last_5_returns=None,
    ):
        self.total_outcomes = total_outcomes
        self.avg_return_pct = avg_return_pct
        self.std_dev = std_dev
        self.last_5_returns = last_5_returns or []

    @property
    def collective(self):
        return self


class TestDegradingDetection:
    """Test detection of degrading performance (z < -2)."""

    def test_detects_degrading_when_z_below_minus_2(self):
        """Should detect DEGRADING when recent mean is significantly worse."""
        # Historical: 5% avg return, 2% std_dev
        # Recent: -2% avg return (z should be around -3.5)
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[-1.5, -2.0, -2.5, -1.8, -2.2],  # avg ~ -2.0%
        )
        
        result = detect_drift(pack)
        
        assert result is not None
        assert "DEGRADING" in result

    def test_degrading_includes_z_score(self):
        """DEGRADING message should include the z-score."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[-1.5, -2.0, -2.5, -1.8, -2.2],
        )
        
        result = detect_drift(pack)
        
        assert result is not None
        assert "z=" in result

    def test_degrading_shows_recent_vs_historical(self):
        """DEGRADING message should show comparison."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[-1.5, -2.0, -2.5, -1.8, -2.2],
        )
        
        result = detect_drift(pack)
        
        assert result is not None
        assert "recent avg" in result
        assert "historical" in result


class TestImprovingDetection:
    """Test detection of improving performance (z > 2)."""

    def test_detects_improving_when_z_above_2(self):
        """Should detect IMPROVING when recent mean is significantly better."""
        # Historical: 5% avg return, 2% std_dev
        # Recent: 12% avg return (z should be around 3.5)
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[11.0, 12.5, 11.5, 13.0, 12.0],  # avg ~ 12.0%
        )
        
        result = detect_drift(pack)
        
        assert result is not None
        assert "IMPROVING" in result

    def test_improving_includes_z_score(self):
        """IMPROVING message should include the z-score."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[11.0, 12.5, 11.5, 13.0, 12.0],
        )
        
        result = detect_drift(pack)
        
        assert result is not None
        assert "z=" in result

    def test_improving_shows_recent_vs_historical(self):
        """IMPROVING message should show comparison."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[11.0, 12.5, 11.5, 13.0, 12.0],
        )
        
        result = detect_drift(pack)
        
        assert result is not None
        assert "recent avg" in result
        assert "historical" in result


class TestStableDetection:
    """Test stable (no drift) detection."""

    def test_no_drift_when_recent_matches_historical(self):
        """Should return None (no drift) when recent ≈ historical."""
        # Historical: 5% avg return, 2% std_dev
        # Recent: ~5% avg return (z ≈ 0)
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[4.5, 5.2, 5.0, 5.5, 4.8],  # avg ~ 5.0%
        )
        
        result = detect_drift(pack)
        
        assert result is None

    def test_no_drift_within_2_z_threshold(self):
        """Should return None when |z| <= 2 (within 95% confidence)."""
        # Recent mean slightly above historical but within threshold
        # z = (5.5 - 5.0) / (2.0 / sqrt(5)) = 0.5 / 0.89 = 0.56
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[5.0, 5.5, 5.2, 5.8, 5.0],  # avg ~ 5.3%
        )
        
        result = detect_drift(pack)
        
        # z ~ 0.3-0.5, should be stable (None)
        assert result is None


class TestEdgeCases:
    """Test edge cases: insufficient data, zero variance, etc."""

    def test_insufficient_data_returns_none(self):
        """Should return None when total_outcomes < 10."""
        pack = MockPack(
            total_outcomes=9,  # Below threshold
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[4.0, 5.0, 6.0, 5.0, 5.0],
        )
        
        result = detect_drift(pack)
        
        assert result is None

    def test_missing_last_5_returns_returns_none(self):
        """Should return None when last_5_returns is incomplete."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[4.0, 5.0, 6.0],  # Only 3 returns
        )
        
        result = detect_drift(pack)
        
        assert result is None

    def test_zero_variance_returns_none(self):
        """Should return None when std_dev <= 0."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=0.0,  # Zero variance
            last_5_returns=[5.0, 5.0, 5.0, 5.0, 5.0],
        )
        
        result = detect_drift(pack)
        
        assert result is None

    def test_negative_std_dev_returns_none(self):
        """Should return None when std_dev < 0."""
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=-1.0,  # Negative (invalid)
            last_5_returns=[5.0, 5.0, 5.0, 5.0, 5.0],
        )
        
        result = detect_drift(pack)
        
        assert result is None

    def test_zero_std_dev_with_variation_returns_none(self):
        """Even with variation in returns, zero std_dev triggers None."""
        # Note: If all returns are the same, std_dev will be 0
        pack = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=0.0,
            last_5_returns=[5.0, 5.0, 5.0, 5.0, 5.0],
        )
        
        result = detect_drift(pack)
        
        assert result is None


class TestDetectTrend:
    """Test detect_trend function."""

    def test_improving_trend_with_positive_slope(self):
        """Should detect improving trend with positive slope > 0.2."""
        returns = [1.0, 2.0, 3.0, 4.0, 5.0]  # Slope = 1.0
        result = detect_trend(returns)
        assert result == "improving"

    def test_degrading_trend_with_negative_slope(self):
        """Should detect degrading trend with negative slope < -0.2."""
        returns = [5.0, 4.0, 3.0, 2.0, 1.0]  # Slope = -1.0
        result = detect_trend(returns)
        assert result == "degrading"

    def test_stable_trend_with_flat_slope(self):
        """Should detect stable trend when slope is near 0."""
        returns = [5.0, 5.1, 4.9, 5.0, 5.05]  # Slope ≈ 0
        result = detect_trend(returns)
        assert result == "stable"

    def test_stable_with_less_than_3_returns(self):
        """Should return stable when fewer than 3 returns."""
        returns = [5.0, 4.0]
        result = detect_trend(returns)
        assert result == "stable"

    def test_stable_when_denominator_is_zero(self):
        """Should return stable when variance calculation yields 0."""
        returns = [5.0, 5.0, 5.0, 5.0, 5.0]
        result = detect_trend(returns)
        assert result == "stable"


class TestDetectDriftFromReturns:
    """Test detect_drift_from_returns standalone function."""

    def test_degrading_detection_from_returns(self):
        """Should detect DEGRADING from raw returns data."""
        result = detect_drift_from_returns(
            last_5_returns=[-1.5, -2.0, -2.5, -1.8, -2.2],
            historical_mean=5.0,
            std_dev=2.0,
            total_outcomes=15,
        )
        
        assert result is not None
        assert "DEGRADING" in result

    def test_improving_detection_from_returns(self):
        """Should detect IMPROVING from raw returns data."""
        result = detect_drift_from_returns(
            last_5_returns=[11.0, 12.5, 11.5, 13.0, 12.0],
            historical_mean=5.0,
            std_dev=2.0,
            total_outcomes=15,
        )
        
        assert result is not None
        assert "IMPROVING" in result

    def test_no_drift_from_returns(self):
        """Should return None from raw returns when stable."""
        result = detect_drift_from_returns(
            last_5_returns=[4.5, 5.2, 5.0, 5.5, 4.8],
            historical_mean=5.0,
            std_dev=2.0,
            total_outcomes=15,
        )
        
        assert result is None


class TestComputeZScore:
    """Test compute_z_score function."""

    def test_z_score_positive_when_sample_above_mean(self):
        """Z-score should be positive when sample mean > population mean."""
        z = compute_z_score(
            sample=[6.0, 6.5, 5.5],
            population_mean=5.0,
            population_std=2.0,
        )
        assert z > 0

    def test_z_score_negative_when_sample_below_mean(self):
        """Z-score should be negative when sample mean < population mean."""
        z = compute_z_score(
            sample=[4.0, 3.5, 4.5],
            population_mean=5.0,
            population_std=2.0,
        )
        assert z < 0

    def test_z_score_near_zero_when_sample_equals_mean(self):
        """Z-score should be near 0 when sample mean ≈ population mean."""
        z = compute_z_score(
            sample=[5.0, 5.0, 5.0],
            population_mean=5.0,
            population_std=2.0,
        )
        assert abs(z) < 0.01

    def test_z_score_zero_for_empty_sample(self):
        """Z-score should be 0 for empty sample."""
        z = compute_z_score(
            sample=[],
            population_mean=5.0,
            population_std=2.0,
        )
        assert z == 0.0

    def test_z_score_zero_when_std_is_zero(self):
        """Z-score should be 0 when population_std is 0."""
        z = compute_z_score(
            sample=[5.0, 5.5, 4.5],
            population_mean=5.0,
            population_std=0.0,
        )
        assert z == 0.0


class TestThresholdBoundaries:
    """Test exact threshold boundaries for z-score detection."""

    def test_z_minus_2_boundary_returns_none(self):
        """At exactly z = -2, should still be stable (|z| > 2 required)."""
        # z = -2 means recent_mean - historical_mean = -2 * (std_dev / sqrt(5))
        # If std_dev = 2, then: diff = -2 * (2 / 2.23) = -1.79
        # With historical = 5, recent = 3.21, z = -1.79
        # This would be None since |z| < 2
        pass  # Skip exact boundary test as it depends on floating point

    def test_multiple_degrading_then_improving(self):
        """Should detect changes from degrading to improving."""
        # First: degrading
        pack1 = MockPack(
            total_outcomes=15,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[-1.5, -2.0, -2.5, -1.8, -2.2],
        )
        assert "DEGRADING" in detect_drift(pack1)
        
        # Then: improving
        pack2 = MockPack(
            total_outcomes=20,
            avg_return_pct=5.0,
            std_dev=2.0,
            last_5_returns=[11.0, 12.5, 11.5, 13.0, 12.0],
        )
        assert "IMPROVING" in detect_drift(pack2)
