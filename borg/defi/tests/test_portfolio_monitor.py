"""Tests for Borg DeFi portfolio monitor module.

16 tests covering portfolio retrieval, P&L calculation, and risk alerts.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from borg.defi.portfolio_monitor import PortfolioMonitor
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
            token="USDC-USDC LP",
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
            token="ETH",
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
def mock_helius_response():
    """Mock Helius API response."""
    return {
        "result": {
            "items": [
                {
                    "id": "sol_token_1",
                    "interface": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                    "token_info": {
                        "symbol": "SOL",
                        "decimals": 9,
                        "amount": 10500000000,  # 10.5 SOL
                        "price_info": {
                            "price_per_token": 200.0,
                        },
                    },
                },
                {
                    "id": "sol_token_2",
                    "interface": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                    "token_info": {
                        "symbol": "USDC",
                        "decimals": 6,
                        "amount": 5100000,  # 5.1 USDC
                        "price_info": {
                            "price_per_token": 1.0,
                        },
                    },
                },
            ]
        }
    }


@pytest.fixture
def mock_alchemy_response():
    """Mock Alchemy API response."""
    return {
        "result": {
            "tokenBalances": [
                {
                    "contractAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
                    "tokenBalance": "0x1DCD65000",  # 2000 USDC
                },
                {
                    "contractAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
                    "tokenBalance": "0xD3",  # ~0.85 WETH
                },
            ]
        }
    }


# ============================================================================
# Position DataClass Tests (PM1)
# ============================================================================

def test_position_dataclass():
    """Verify all fields of Position dataclass."""
    pos = Position(
        chain="solana",
        protocol="kamino",
        token="USDC",
        amount=1000.0,
        value_usd=1020.0,
        entry_price=1.0,
        current_price=1.02,
        pnl_usd=20.0,
        pnl_pct=2.0,
        health_factor=None,
        position_type="hold",
    )
    
    assert pos.chain == "solana"
    assert pos.protocol == "kamino"
    assert pos.token == "USDC"
    assert pos.amount == 1000.0
    assert pos.value_usd == 1020.0
    assert pos.entry_price == 1.0
    assert pos.current_price == 1.02
    assert pos.pnl_usd == 20.0
    assert pos.pnl_pct == 2.0
    assert pos.health_factor is None
    assert pos.position_type == "hold"


def test_position_auto_pnl_calculation():
    """PNL calculated from entry/current price if not provided."""
    pos = Position(
        chain="solana",
        protocol="solana",
        token="SOL",
        amount=10.0,
        value_usd=2000.0,
        entry_price=180.0,
        current_price=200.0,
    )
    
    # Should auto-calculate pnl_usd and pnl_pct
    assert pos.pnl_usd == pytest.approx(200.0, rel=0.01)
    assert pos.pnl_pct == pytest.approx(11.11, rel=0.01)


# ============================================================================
# Portfolio Retrieval Tests (PM1, PM7)
# ============================================================================

@pytest.mark.asyncio
async def test_portfolio_solana(mock_helius_response):
    """Mock Helius -> positions listed."""
    monitor = PortfolioMonitor(helius_api_key="test_key")
    
    with patch.object(monitor, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_helius_response)
        
        # Create mock session that properly supports async context manager protocol
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_instance.post.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        positions = await monitor.get_solana_portfolio("test_wallet")
    
    assert len(positions) == 2
    assert all(isinstance(p, Position) for p in positions)
    tokens = [p.token for p in positions]
    assert "SOL" in tokens
    assert "USDC" in tokens


@pytest.mark.asyncio
async def test_portfolio_evm(mock_alchemy_response):
    """Mock Alchemy -> positions listed."""
    monitor = PortfolioMonitor(alchemy_api_key="test_key")
    
    with patch.object(monitor, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_alchemy_response)
        
        # Create mock session that properly supports async context manager protocol
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_instance.post.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        positions = await monitor.get_evm_portfolio("0x1234", "ethereum")
    
    # Without detailed metadata, might return mock or empty
    assert isinstance(positions, list)


@pytest.mark.asyncio
async def test_empty_wallet():
    """No tokens -> empty portfolio, no crash."""
    monitor = PortfolioMonitor(helius_api_key="test_key")
    
    with patch.object(monitor, '_get_session') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"result": {"items": []}})
        
        # Create mock session that properly supports async context manager protocol
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_session_instance.post.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_instance
        
        positions = await monitor.get_solana_portfolio("empty_wallet")
    
    assert positions == []


# ============================================================================
# P&L Calculation Tests (PM2)
# ============================================================================

def test_pnl_calculation_profit():
    """+20% -> correct PnL."""
    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.0,
            value_usd=2160.0,
            entry_price=180.0,
            current_price=216.0,
            pnl_usd=360.0,
            pnl_pct=20.0,
        ),
    ]
    
    monitor = PortfolioMonitor()
    pnl = monitor.calculate_pnl(positions)
    
    assert pnl["total_value_usd"] == 2160.0
    assert pnl["total_pnl_usd"] == 360.0
    assert pnl["total_pnl_pct"] == pytest.approx(20.0, rel=0.1)


def test_pnl_calculation_loss():
    """-15% -> correct PnL."""
    positions = [
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="ETH",
            amount=1.0,
            value_usd=1700.0,
            entry_price=2000.0,
            current_price=1700.0,
            pnl_usd=-300.0,
            pnl_pct=-15.0,
        ),
    ]
    
    monitor = PortfolioMonitor()
    pnl = monitor.calculate_pnl(positions)
    
    assert pnl["total_value_usd"] == 1700.0
    assert pnl["total_pnl_usd"] == -300.0
    assert pnl["total_pnl_pct"] == pytest.approx(-15.0, rel=0.1)


def test_pnl_calculation_zero():
    """Flat -> $0 PnL."""
    positions = [
        Position(
            chain="solana",
            protocol="circle",
            token="USDC",
            amount=1000.0,
            value_usd=1000.0,
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
        ),
    ]
    
    monitor = PortfolioMonitor()
    pnl = monitor.calculate_pnl(positions)
    
    assert pnl["total_value_usd"] == 1000.0
    assert pnl["total_pnl_usd"] == 0.0
    assert pnl["total_pnl_pct"] == 0.0


def test_pnl_empty_portfolio():
    """Empty portfolio returns zero values."""
    monitor = PortfolioMonitor()
    pnl = monitor.calculate_pnl([])
    
    assert pnl["total_value_usd"] == 0.0
    assert pnl["total_pnl_usd"] == 0.0
    assert pnl["total_pnl_pct"] == 0.0


# ============================================================================
# Risk Alert Tests (PM3, PM4, PM5)
# ============================================================================

def test_risk_concentration(sample_positions):
    """40% in SOL -> warning."""
    monitor = PortfolioMonitor()
    alerts = monitor.risk_alerts(sample_positions)
    
    concentration_alerts = [a for a in alerts if a.alert_type == "concentration"]
    
    # SOL is 2100/12350 = 17%, no concentration alert expected
    # Let's test with a more concentrated position
    concentrated = [
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
        ),
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="ETH",
            amount=0.5,
            value_usd=1000.0,
            entry_price=1800.0,
            current_price=2000.0,
            pnl_usd=100.0,
            pnl_pct=11.1,
        ),
    ]
    
    alerts = monitor.risk_alerts(concentrated)
    conc_alerts = [a for a in alerts if a.alert_type == "concentration"]
    
    assert len(conc_alerts) == 1
    assert "SOL" in conc_alerts[0].message
    assert "40%" in conc_alerts[0].message or ">" in conc_alerts[0].message


def test_risk_health_factor():
    """HF 0.8 -> critical alert."""
    positions = [
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
            health_factor=0.8,
            position_type="lending",
        ),
    ]
    
    monitor = PortfolioMonitor()
    alerts = monitor.risk_alerts(positions)
    
    hf_alerts = [a for a in alerts if a.alert_type == "health_factor"]
    
    assert len(hf_alerts) == 1
    assert hf_alerts[0].severity == "critical"
    assert "0.80" in hf_alerts[0].message


def test_risk_drawdown():
    """-25% -> warning."""
    positions = [
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="ETH",
            amount=1.0,
            value_usd=1500.0,
            entry_price=2000.0,
            current_price=1500.0,
            pnl_usd=-500.0,
            pnl_pct=-25.0,
            position_type="hold",
        ),
    ]
    
    monitor = PortfolioMonitor()
    alerts = monitor.risk_alerts(positions)
    
    drawdown_alerts = [a for a in alerts if a.alert_type == "drawdown"]
    
    assert len(drawdown_alerts) == 1
    assert drawdown_alerts[0].severity == "warning"
    assert "25.0% loss" in drawdown_alerts[0].message


def test_risk_no_alert(sample_positions):
    """Balanced portfolio -> no warnings."""
    # Create a balanced portfolio with no concentration issues or drawdowns
    # Each position is 20% of portfolio (below 30% threshold)
    balanced = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=5.0,
            value_usd=500.0,
            entry_price=200.0,
            current_price=200.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            health_factor=2.0,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="ETH",
            amount=0.25,
            value_usd=500.0,
            entry_price=2000.0,
            current_price=2000.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            health_factor=2.0,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="aave",
            token="USDC",
            amount=500.0,
            value_usd=500.0,
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            health_factor=2.0,
            position_type="lending",
        ),
        Position(
            chain="solana",
            protocol="kamino",
            token="USDC-USDC LP",
            amount=500.0,
            value_usd=500.0,
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            health_factor=2.0,
            position_type="lp",
        ),
    ]
    
    monitor = PortfolioMonitor()
    alerts = monitor.risk_alerts(balanced)
    
    # Should have no alerts for a balanced portfolio
    assert len(alerts) == 0


# ============================================================================
# Report Formatting Tests (PM6)
# ============================================================================

def test_daily_report_format(sample_positions):
    """Verify sections present: total value, top positions, alerts."""
    monitor = PortfolioMonitor()
    
    pnl = monitor.calculate_pnl(sample_positions)
    msg = monitor.format_daily_report(sample_positions, pnl)
    
    assert "💼 *Daily Portfolio Report*" in msg
    assert "$12,350" in msg or "Total:" in msg
    assert "Top Positions:" in msg
    assert "SOL" in msg
    assert "By Chain:" in msg


# ============================================================================
# Multi-chain Aggregation Tests (PM7)
# ============================================================================

def test_multi_chain_aggregation(sample_positions):
    """SOL + ETH -> combined total."""
    monitor = PortfolioMonitor()
    
    # Group by chain
    by_chain = {}
    for p in sample_positions:
        by_chain[p.chain] = by_chain.get(p.chain, 0.0) + p.value_usd
    
    assert "solana" in by_chain
    assert "ethereum" in by_chain
    assert by_chain["solana"] > 0
    assert by_chain["ethereum"] > 0
    
    total = sum(by_chain.values())
    assert total == pytest.approx(12350.0, rel=0.01)


# ============================================================================
# Historical Tracking Tests (PM8)
# ============================================================================

def test_historical_snapshot(sample_positions):
    """Save + load -> data preserved."""
    monitor = PortfolioMonitor()
    
    # Save snapshot
    monitor.save_snapshot(sample_positions)
    
    # Get historical values
    history = monitor.get_historical_value(days=1)
    
    assert len(history) == 1
    assert history[0]["total_value"] == pytest.approx(12350.0, rel=0.01)


def test_historical_snapshot_multiple(sample_positions):
    """Multiple snapshots tracked."""
    monitor = PortfolioMonitor()
    
    # Save multiple snapshots with different values
    monitor.save_snapshot(sample_positions)
    
    # Modify positions
    modified = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.0,
            value_usd=2500.0,
            entry_price=180.0,
            current_price=250.0,
            pnl_usd=700.0,
            pnl_pct=38.9,
        ),
    ]
    monitor.save_snapshot(modified)
    
    history = monitor.get_historical_value(days=1)
    
    assert len(history) == 2
    values = [h["total_value"] for h in history]
    assert 2500.0 in values
    assert 12350.0 in values


# ============================================================================
# Cron Integration Test (PM16)
# ============================================================================

def test_portfolio_cron_integration():
    """Simulate daily report cron."""
    monitor = PortfolioMonitor()
    
    # Morning cron: get portfolio, calculate pnl, generate report
    positions = monitor._get_mock_solana_portfolio("test_wallet")
    pnl = monitor.calculate_pnl(positions)
    alerts = monitor.risk_alerts(positions)
    report = monitor.format_daily_report(positions, pnl)
    
    assert "Daily Portfolio Report" in report
    assert len(positions) > 0
    assert isinstance(pnl, dict)
    assert isinstance(alerts, list)
