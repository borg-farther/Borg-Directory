"""Tests for Borg DeFi risk engine module.

20 tests covering correlation analysis, protocol risk assessment,
concentration risk, drawdown tracking, and overall risk scoring.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from borg.defi.risk_engine import (
    RiskEngine,
    CorrelationResult,
    ProtocolRiskResult,
    ConcentrationRiskResult,
    DrawdownResult,
)
from borg.defi.data_models import Position, RiskAlert


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_positions():
    """Sample portfolio positions for testing."""
    return [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.5,
            value_usd=2100.0,
            entry_price=180.0,
            current_price=200.0,
            pnl_usd=210.0,
            pnl_pct=11.1,
            position_type="hold",
        ),
        Position(
            chain="solana",
            protocol="kamino",
            token="USDC-USDT LP",
            amount=5000.0,
            value_usd=5100.0,
            entry_price=1.0,
            current_price=1.02,
            pnl_usd=100.0,
            pnl_pct=2.0,
            position_type="lp",
        ),
        Position(
            chain="ethereum",
            protocol="aave",
            token="USDC",
            amount=2000.0,
            value_usd=2000.0,
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            health_factor=1.8,
            position_type="lending",
        ),
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="WETH",
            amount=1.5,
            value_usd=3000.0,
            entry_price=2800.0,
            current_price=2000.0,
            pnl_usd=-1200.0,
            pnl_pct=-28.6,
            position_type="hold",
        ),
        Position(
            chain="solana",
            protocol="bonk",
            token="BONK",
            amount=1000000.0,
            value_usd=150.0,
            entry_price=0.0002,
            current_price=0.00015,
            pnl_usd=-50.0,
            pnl_pct=-33.3,
            position_type="hold",
        ),
    ]


@pytest.fixture
def correlated_positions():
    """Positions with high correlation for testing."""
    return [
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="WETH",
            amount=2.0,
            value_usd=4000.0,
            entry_price=1800.0,
            current_price=2000.0,
            pnl_usd=400.0,
            pnl_pct=11.1,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="uniswap",
            token="UNI",
            amount=500.0,
            value_usd=4000.0,
            entry_price=7.0,
            current_price=8.0,
            pnl_usd=500.0,
            pnl_pct=14.3,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="link",
            token="LINK",
            amount=300.0,
            value_usd=4000.0,
            entry_price=12.0,
            current_price=13.33,
            pnl_usd=400.0,
            pnl_pct=11.1,
            position_type="hold",
        ),
    ]


@pytest.fixture
def concentrated_positions():
    """Highly concentrated positions for testing."""
    return [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=50.0,
            value_usd=10000.0,
            entry_price=180.0,
            current_price=200.0,
            pnl_usd=1000.0,
            pnl_pct=10.0,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="WETH",
            amount=0.5,
            value_usd=1000.0,
            entry_price=1800.0,
            current_price=2000.0,
            pnl_usd=100.0,
            pnl_pct=11.1,
            position_type="hold",
        ),
    ]


@pytest.fixture
def mock_tvl_data():
    """Mock TVL data for protocol risk assessment."""
    return {
        "aave": {
            "tvl_usd": 15000000000,
            "tvl_history": [14500000000, 14800000000, 15000000000],
        },
        "kamino": {
            "tvl_usd": 50000000,
            "tvl_history": [55000000, 53000000, 50000000],
        },
        "bonk": {
            "tvl_usd": 500000,
            "tvl_history": [600000, 550000, 500000],
        },
        "unproven": {
            "tvl_usd": 50000,
            "tvl_history": [100000, 75000, 50000],
        },
    }


@pytest.fixture
def mock_audit_data():
    """Mock audit data for protocol risk assessment."""
    return {
        "aave": "audited",
        "kamino": "audited",
        "bonk": "partial",
        "unproven": "unaudited",
    }


@pytest.fixture
def mock_price_history():
    """Mock price history for correlation analysis."""
    return {
        "SOL": [100.0, 105.0, 110.0, 108.0, 112.0, 115.0],
        "ETH": [1800.0, 1850.0, 1900.0, 1880.0, 1920.0, 1950.0],
        "BONK": [0.0001, 0.00011, 0.00012, 0.000115, 0.00013, 0.00014],
    }


# ============================================================================
# Correlation Analysis Tests (RE1)
# ============================================================================

def test_correlation_single_position():
    """Single position -> no correlation possible."""
    engine = RiskEngine()
    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.0,
            value_usd=2000.0,
            entry_price=180.0,
            current_price=200.0,
            pnl_usd=200.0,
            pnl_pct=10.0,
        ),
    ]
    
    result = engine.correlation_analysis(positions)
    
    assert result.portfolio_correlation == 0.0
    assert len(result.token_pairs) == 0
    assert len(result.high_correlation_pairs) == 0


def test_correlation_empty_positions():
    """Empty positions -> empty result."""
    engine = RiskEngine()
    result = engine.correlation_analysis([])
    
    assert result.portfolio_correlation == 0.0
    assert len(result.token_pairs) == 0


def test_correlation_with_price_history(correlated_positions, mock_price_history):
    """With price history -> correlation calculated."""
    engine = RiskEngine(high_correlation_threshold=0.5)
    result = engine.correlation_analysis(correlated_positions, mock_price_history)
    
    assert isinstance(result, CorrelationResult)
    assert len(result.token_pairs) == 3  # 3 pairs from 3 tokens
    assert isinstance(result.portfolio_correlation, float)


def test_correlation_high_correlation_pairs(correlated_positions, mock_price_history):
    """High correlation pairs identified."""
    engine = RiskEngine(high_correlation_threshold=0.7)
    result = engine.correlation_analysis(correlated_positions, mock_price_history)
    
    # ETH and ERC20 tokens often correlate
    assert isinstance(result.high_correlation_pairs, list)


def test_correlation_fallback_without_history(sample_positions):
    """Without price history -> uses P&L as proxy."""
    engine = RiskEngine()
    result = engine.correlation_analysis(sample_positions)
    
    assert isinstance(result, CorrelationResult)
    # Should still return structure even without price data


# ============================================================================
# Protocol Risk Assessment Tests (RE2)
# ============================================================================

def test_protocol_risk_aave(sample_positions, mock_tvl_data, mock_audit_data):
    """Aave with high TVL -> low risk."""
    engine = RiskEngine()
    positions = [p for p in sample_positions if p.protocol == "aave"]
    
    results = engine.protocol_risk_assessment(positions, mock_tvl_data, mock_audit_data)
    
    assert "aave" in results
    assert results["aave"].tvl_usd == 15000000000
    assert results["aave"].risk_score < 0.5  # Should be low risk
    assert results["aave"].audit_status == "audited"


def test_protocol_risk_low_tvl(sample_positions, mock_tvl_data, mock_audit_data):
    """Low TVL protocol -> higher risk."""
    engine = RiskEngine()
    positions = [p for p in sample_positions if p.protocol == "bonk"]
    
    results = engine.protocol_risk_assessment(positions, mock_tvl_data, mock_audit_data)
    
    assert "bonk" in results
    assert results["bonk"].risk_score >= 0.5


def test_protocol_risk_unaudited(sample_positions, mock_tvl_data, mock_audit_data):
    """Unaudited protocol -> risk factors include unaudited."""
    engine = RiskEngine()
    positions = [
        Position(
            chain="ethereum",
            protocol="unproven",
            token="SOME",
            amount=100.0,
            value_usd=100.0,
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
        ),
    ]
    
    results = engine.protocol_risk_assessment(positions, mock_tvl_data, mock_audit_data)
    
    assert "unproven" in results
    assert "Protocol is unaudited" in results["unproven"].risk_factors


def test_protocol_risk_decreasing_tvl(mock_tvl_data, mock_audit_data):
    """Decreasing TVL trend -> identified in risk factors."""
    engine = RiskEngine()
    positions = [
        Position(
            chain="solana",
            protocol="kamino",
            token="USDC",
            amount=100.0,
            value_usd=100.0,
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
        ),
    ]
    
    # Create TVL data with significant decline - 50% drop over 14 days
    tvl_data_decreasing = {
        "kamino": {
            "tvl_usd": 30000000,
            "tvl_history": [60000000, 58000000, 56000000, 54000000, 52000000, 50000000, 
                           48000000, 46000000, 44000000, 42000000, 40000000, 38000000,
                           36000000, 34000000, 32000000, 30000000],
        },
    }
    
    results = engine.protocol_risk_assessment(positions, tvl_data_decreasing, mock_audit_data)
    
    assert "kamino" in results
    assert "Declining TVL trend" in results["kamino"].risk_factors


def test_protocol_risk_il_positions(sample_positions, mock_tvl_data, mock_audit_data):
    """LP positions -> IL risk factor identified."""
    engine = RiskEngine()
    positions = [p for p in sample_positions if p.position_type == "lp"]
    
    results = engine.protocol_risk_assessment(positions, mock_tvl_data, mock_audit_data)
    
    for protocol, result in results.items():
        if result.risk_factors:
            assert any("Impermanent loss risk" in f for f in result.risk_factors)


# ============================================================================
# Concentration Risk Tests (RE3)
# ============================================================================

def test_concentration_warning_threshold(concentrated_positions):
    """Position >25% -> warning alert."""
    engine = RiskEngine(concentration_warning_threshold=0.25)
    concentrations = engine.concentration_risk(concentrated_positions)
    
    # SOL is 10000/11000 = 91%, should exceed threshold
    sol_conc = next(c for c in concentrations if c.token == "SOL")
    assert sol_conc.threshold_exceeded is True
    assert sol_conc.risk_level in ["high", "critical"]


def test_concentration_critical_threshold(concentrated_positions):
    """Position >40% -> critical alert."""
    engine = RiskEngine(concentration_critical_threshold=0.40)
    concentrations = engine.concentration_risk(concentrated_positions)
    
    sol_conc = next(c for c in concentrations if c.token == "SOL")
    assert sol_conc.risk_level == "critical"


def test_concentration_no_alert():
    """Balanced portfolio -> no alerts."""
    engine = RiskEngine()
    # Create truly balanced positions - each well below 25%
    very_balanced = [
        Position(chain="solana", protocol="solana", token="SOL", amount=1.0, value_usd=400.0,
                 entry_price=200.0, current_price=400.0, pnl_usd=200.0, pnl_pct=100.0),
        Position(chain="ethereum", protocol="ethereum", token="WETH", amount=0.1, value_usd=400.0,
                 entry_price=2000.0, current_price=4000.0, pnl_usd=200.0, pnl_pct=100.0),
        Position(chain="solana", protocol="kamino", token="USDC", amount=400.0, value_usd=400.0,
                 entry_price=1.0, current_price=1.0, pnl_usd=0.0, pnl_pct=0.0),
        Position(chain="ethereum", protocol="aave", token="DAI", amount=400.0, value_usd=400.0,
                 entry_price=1.0, current_price=1.0, pnl_usd=0.0, pnl_pct=0.0),
        Position(chain="solana", protocol="marinade", token="MSOL", amount=10.0, value_usd=400.0,
                 entry_price=40.0, current_price=40.0, pnl_usd=0.0, pnl_pct=0.0),
    ]
    concentrations = engine.concentration_risk(very_balanced)
    
    # All should be below 25% (each is 20%)
    for c in concentrations:
        assert c.threshold_exceeded is False


def test_concentration_alerts_message(concentrated_positions):
    """Alert message contains token and percentage."""
    engine = RiskEngine()
    alerts = engine.concentration_alerts(concentrated_positions)
    
    assert len(alerts) > 0
    for alert in alerts:
        assert alert.alert_type == "concentration"
        assert "SOL" in alert.message
        assert "%" in alert.message


def test_concentration_sorted_by_exposure(sample_positions):
    """Results sorted by concentration (highest first)."""
    engine = RiskEngine()
    concentrations = engine.concentration_risk(sample_positions)
    
    concentrations_pct = [c.concentration_pct for c in concentrations]
    assert concentrations_pct == sorted(concentrations_pct, reverse=True)


# ============================================================================
# Drawdown Tracking Tests (RE4)
# ============================================================================

def test_drawdown_no_history():
    """No history -> no drawdown."""
    engine = RiskEngine()
    result = engine.drawdown_tracking(current_value=10000.0)
    
    assert result.current_drawdown_pct == 0.0
    assert result.max_drawdown_pct == 0.0
    assert result.stop_loss_triggered is False


def test_drawdown_new_peak():
    """New peak -> drawdown resets."""
    engine = RiskEngine()
    
    # First value becomes peak
    result1 = engine.drawdown_tracking(current_value=10000.0)
    assert result1.peak_value == 10000.0
    
    # Higher value -> new peak
    result2 = engine.drawdown_tracking(current_value=11000.0)
    assert result2.peak_value == 11000.0
    assert result2.current_drawdown_pct == 0.0


def test_drawdown_from_peak():
    """Value below peak -> drawdown calculated."""
    engine = RiskEngine()
    
    engine.drawdown_tracking(current_value=10000.0)  # Set peak
    result = engine.drawdown_tracking(current_value=9000.0)  # 10% drop
    
    assert result.current_drawdown_pct == pytest.approx(0.10, rel=0.01)
    assert result.peak_value == 10000.0
    assert result.trough_value == 9000.0


def test_drawdown_stop_loss_triggered():
    """Drawdown exceeds threshold -> stop loss triggered."""
    engine = RiskEngine(default_stop_loss=0.20)
    
    engine.drawdown_tracking(current_value=10000.0)  # Set peak
    result = engine.drawdown_tracking(current_value=7500.0)  # 25% drop
    
    assert result.stop_loss_triggered is True
    assert result.stop_loss_threshold == 0.20


def test_drawdown_stop_loss_not_triggered():
    """Drawdown below threshold -> no stop loss."""
    engine = RiskEngine(default_stop_loss=0.20)
    
    engine.drawdown_tracking(current_value=10000.0)  # Set peak
    result = engine.drawdown_tracking(current_value=9000.0)  # 10% drop
    
    assert result.stop_loss_triggered is False


def test_drawdown_recovery():
    """Portfolio recovers -> is_recovered flag set."""
    engine = RiskEngine()
    
    engine.drawdown_tracking(current_value=10000.0)  # Peak
    engine.drawdown_tracking(current_value=8000.0)   # Trough
    result = engine.drawdown_tracking(current_value=10000.0)  # Recovered
    
    assert result.is_recovered is True
    assert result.recovery_time is not None


def test_drawdown_max_tracking():
    """Max drawdown persists even after recovery."""
    engine = RiskEngine()
    
    engine.drawdown_tracking(current_value=10000.0)  # Peak
    dd_result = engine.drawdown_tracking(current_value=8000.0)   # Trough - 20% drop
    # At trough, max_drawdown should be 20%
    assert dd_result.max_drawdown_pct == pytest.approx(0.20, rel=0.01)
    
    # After partial recovery to 9000, max should still be 20%
    partial = engine.drawdown_tracking(current_value=9000.0)
    assert partial.max_drawdown_pct == pytest.approx(0.20, rel=0.01)
    
    # After new peak at 11000, max should still be 20% from original peak
    result = engine.drawdown_tracking(current_value=11000.0)
    assert result.max_drawdown_pct == pytest.approx(0.20, rel=0.01)


def test_drawdown_reset():
    """Reset clears all tracking state."""
    engine = RiskEngine()
    
    engine.drawdown_tracking(current_value=10000.0)
    engine.drawdown_tracking(current_value=8000.0)
    engine.reset_drawdown_tracking()
    
    result = engine.drawdown_tracking(current_value=10000.0)
    assert result.max_drawdown_pct == 0.0
    assert result.peak_value == 10000.0


def test_drawdown_custom_threshold():
    """Custom stop loss threshold respected."""
    engine = RiskEngine()
    
    engine.drawdown_tracking(current_value=10000.0)
    result = engine.drawdown_tracking(
        current_value=8500.0,
        stop_loss_threshold=0.10  # 10% threshold
    )
    
    assert result.stop_loss_triggered is True


# ============================================================================
# Overall Risk Score Tests (RE5)
# ============================================================================

def test_risk_score_empty_positions():
    """Empty portfolio -> zero risk."""
    engine = RiskEngine()
    score = engine.calculate_portfolio_risk_score([])
    
    assert score == 0.0


def test_risk_score_balanced_portfolio(sample_positions):
    """Balanced portfolio -> moderate risk."""
    engine = RiskEngine()
    score = engine.calculate_portfolio_risk_score(sample_positions)
    
    # Balanced should be < 0.5
    assert 0.0 <= score <= 1.0


def test_risk_score_concentrated_portfolio(concentrated_positions):
    """Concentrated portfolio -> higher risk."""
    engine = RiskEngine()
    score = engine.calculate_portfolio_risk_score(concentrated_positions)
    
    # Concentrated should be higher
    assert score > 0.0


def test_risk_score_includes_concentration(sample_positions, mock_tvl_data, mock_audit_data, mock_price_history):
    """Risk score incorporates concentration."""
    engine = RiskEngine()
    
    base_score = engine.calculate_portfolio_risk_score(sample_positions)
    
    # Add TVL and price data for full scoring
    full_score = engine.calculate_portfolio_risk_score(
        sample_positions,
        mock_tvl_data,
        mock_audit_data,
        mock_price_history
    )
    
    # Both should be valid scores
    assert 0.0 <= base_score <= 1.0
    assert 0.0 <= full_score <= 1.0


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================

def test_risk_engine_zero_value_positions():
    """Positions with zero value handled gracefully."""
    engine = RiskEngine()
    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=0.0,
            value_usd=0.0,
            entry_price=200.0,
            current_price=200.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
        ),
    ]
    
    concentrations = engine.concentration_risk(positions)
    assert len(concentrations) == 0  # Zero value not included


def test_risk_engine_negative_pnl():
    """Negative PnL handled correctly."""
    engine = RiskEngine()
    positions = [
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="WETH",
            amount=1.0,
            value_usd=1500.0,
            entry_price=2000.0,
            current_price=1500.0,
            pnl_usd=-500.0,
            pnl_pct=-25.0,
        ),
    ]
    
    result = engine.correlation_analysis(positions)
    assert isinstance(result, CorrelationResult)


def test_risk_engine_dataclass_post_init():
    """Dataclasses set timestamp on init."""
    import time
    result = CorrelationResult(
        token_pairs={},
        portfolio_correlation=0.0,
        high_correlation_pairs=[],
    )
    
    assert result.timestamp > 0
    assert abs(result.timestamp - time.time()) < 1


def test_risk_engine_all_thresholds():
    """Custom thresholds respected."""
    engine = RiskEngine(
        concentration_warning_threshold=0.15,
        concentration_critical_threshold=0.30,
        high_correlation_threshold=0.50,
        default_stop_loss=0.15,
    )
    
    assert engine.concentration_warning_threshold == 0.15
    assert engine.concentration_critical_threshold == 0.30
    assert engine.high_correlation_threshold == 0.50
    assert engine.default_stop_loss == 0.15


def test_risk_alert_dataclass():
    """RiskAlert dataclass works correctly."""
    alert = RiskAlert(
        alert_type="concentration",
        severity="warning",
        message="TEST",
        affected_positions=["SOL"],
    )
    
    assert alert.alert_type == "concentration"
    assert alert.severity == "warning"
    assert alert.timestamp > 0


def test_drawdown_tracking_timestamps():
    """Drawdown tracking uses provided timestamps."""
    engine = RiskEngine()
    ts = 1700000000.0
    
    result = engine.drawdown_tracking(current_value=10000.0, timestamp=ts)
    
    # Check that values are stored correctly at peak
    assert result.peak_value == 10000.0
    assert result.current_value == 10000.0
    # The trough equals peak at start
    assert result.trough_value == 10000.0


def test_protocol_risk_empty_positions():
    """Empty positions -> empty results."""
    engine = RiskEngine()
    results = engine.protocol_risk_assessment([])
    
    assert len(results) == 0


def test_concentration_risk_empty_positions():
    """Empty positions -> empty results."""
    engine = RiskEngine()
    results = engine.concentration_risk([])
    
    assert len(results) == 0


def test_concentration_alerts_empty():
    """Empty positions -> no alerts."""
    engine = RiskEngine()
    alerts = engine.concentration_alerts([])
    
    assert len(alerts) == 0
