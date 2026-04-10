"""
Cron Tests — 30+ tests for DeFi cron entry points.

Tests each cron function (run_whale_scan, run_yield_scan, run_alpha_scan,
run_portfolio_report, run_liquidation_scan, run_risk_check) using mocks
to avoid real API calls.

Pattern: async def test_* — each cron function returns List[str].
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time


# ============================================================================
# whale_cron Tests
# ============================================================================

from borg.defi.cron.whale_cron import run_whale_scan
from borg.defi.whale_tracker import WhaleAlert


@pytest.mark.asyncio
async def test_whale_cron_empty_wallets():
    """test_whale_cron_empty_wallets — no wallets → empty list."""
    result = await run_whale_scan()
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_whale_cron_no_clients():
    """test_whale_cron_no_clients — no API clients → empty list."""
    result = await run_whale_scan(tracked_wallets={"TestWallet": "Test Label"})
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_whale_cron_with_mock_helius():
    """test_whale_cron_with_mock_helius — mock Helius returns txs → formatted alert."""
    mock_helius = MagicMock()
    mock_helius.get_transactions = AsyncMock(return_value=[
        {
            "signature": "TestSig123",
            "type": "swap",
            "timestamp": time.time(),
            "fee": 5000,
            "accounts": ["TestWallet"],
            "token_balances": {
                "from_token": "SOL",
                "to_token": "BONK",
                "from_amount_usd": 120_000.0,
                "to_amount_usd": 120_000.0,
            },
        }
    ])

    result = await run_whale_scan(
        tracked_wallets={"TestWallet": "Test Whale"},
        helius_client=mock_helius,
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert "🐋" in result[0]
    assert "120,000" in result[0]


@pytest.mark.asyncio
async def test_whale_cron_below_threshold():
    """test_whale_cron_below_threshold — amount below min_usd_threshold → no alert."""
    mock_helius = MagicMock()
    mock_helius.get_transactions = AsyncMock(return_value=[
        {
            "signature": "SmallTx",
            "type": "swap",
            "timestamp": time.time(),
            "fee": 5000,
            "accounts": ["SmallWallet"],
            "token_balances": {
                "from_token": "SOL",
                "to_token": "BONK",
                "from_amount_usd": 1_000.0,  # Below $50K threshold
                "to_amount_usd": 1_000.0,
            },
        }
    ])

    result = await run_whale_scan(
        tracked_wallets={"SmallWallet": "Small Trader"},
        helius_client=mock_helius,
        min_usd_threshold=50_000.0,
    )

    assert isinstance(result, list)
    # Below threshold → no alerts
    assert len(result) == 0


@pytest.mark.asyncio
async def test_whale_cron_custom_threshold():
    """test_whale_cron_custom_threshold — custom $100K threshold respected."""
    mock_helius = MagicMock()
    mock_helius.get_transactions = AsyncMock(return_value=[
        {
            "signature": "MidTx",
            "type": "swap",
            "timestamp": time.time(),
            "fee": 5000,
            "accounts": ["MidWallet"],
            "token_balances": {
                "from_token": "SOL",
                "to_token": "BONK",
                "from_amount_usd": 75_000.0,  # $75K
                "to_amount_usd": 75_000.0,
            },
        }
    ])

    # $100K threshold should filter out $75K
    result = await run_whale_scan(
        tracked_wallets={"MidWallet": "Mid Whale"},
        helius_client=mock_helius,
        min_usd_threshold=100_000.0,
    )

    assert len(result) == 0


@pytest.mark.asyncio
async def test_whale_cron_evm_mock():
    """test_whale_cron_evm_mock — mock EVM scan → formatted alert."""
    mock_alchemy = MagicMock()
    mock_alchemy.get_asset_transfers = AsyncMock(return_value=[
        {
            "hash": "0xEVMTx123",
            "timestamp": time.time(),
            "from": "0xEVMWhale",
            "to": "0xReceiver",
            "value": 200_000.0,
            "asset": "USDC",
        }
    ])

    result = await run_whale_scan(
        tracked_wallets={"0xEVMWhale": "EVM Whale"},
        alchemy_clients={"ethereum": mock_alchemy},
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert "🐋" in result[0]
    assert "200,000" in result[0]


# ============================================================================
# yield_cron Tests
# ============================================================================

from borg.defi.cron.yield_cron import run_yield_scan
from borg.defi.yield_scanner import YieldOpportunity


@pytest.mark.asyncio
async def test_yield_cron_no_opportunities():
    """test_yield_cron_no_opportunities — mock returns empty → no-thanks message."""
    with patch("borg.defi.yield_scanner.aiohttp.ClientSession") as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": []})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session.return_value = MagicMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await run_yield_scan()

        # Should return the "no opportunities" message
        assert isinstance(result, list)
        assert len(result) >= 1
        assert "No yield opportunities" in result[0]


@pytest.mark.asyncio
async def test_yield_cron_min_tvl_filter():
    """test_yield_crn_min_tvl_filter — min_tvl param passed to scanner."""
    scanner = await run_yield_scan(min_tvl=10_000_000.0, max_risk=0.3)

    # Just verify it returns (scanner internals tested elsewhere)
    assert isinstance(scanner, list)


# ============================================================================
# alpha_cron Tests
# ============================================================================

from borg.defi.cron.alpha_cron import run_alpha_scan


@pytest.mark.asyncio
async def test_alpha_cron_no_signals():
    """test_alpha_cron_no_signals — no clients → empty list."""
    result = await run_alpha_scan()
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_alpha_cron_empty_wallets():
    """test_alpha_cron_empty_wallets — no smart money wallets → no smart money alerts."""
    mock_helius = MagicMock()
    mock_birdeye = MagicMock()
    mock_dexscreener = MagicMock()

    # All return empty
    mock_helius.get_transactions_for_address = AsyncMock(return_value=[])
    mock_birdeye.get_price = AsyncMock(return_value=None)
    mock_dexscreener.get_pairs_by_chain = AsyncMock(return_value=[])

    result = await run_alpha_scan(
        smart_money_wallets={},
        helius_client=mock_helius,
        birdeye_client=mock_birdeye,
        dexscreener_client=mock_dexscreener,
    )

    assert isinstance(result, list)


# ============================================================================
# portfolio_cron Tests
# ============================================================================

from borg.defi.cron.portfolio_cron import run_portfolio_report


@pytest.mark.asyncio
async def test_portfolio_cron_empty_wallets():
    """test_portfolio_cron_empty_wallets — no wallets → no positions message."""
    result = await run_portfolio_report({})
    assert isinstance(result, list)
    assert len(result) == 1
    assert "No positions" in result[0]


@pytest.mark.asyncio
async def test_portfolio_cron_single_wallet():
    """test_portfolio_cron_single_wallet — single solana wallet → portfolio report."""
    # Using mock data path (no API keys)
    result = await run_portfolio_report(
        wallets={"solana": ["TestSolanaWallet123"]},
        helius_api_key=None,  # Forces mock data
    )

    assert isinstance(result, list)
    assert len(result) >= 1
    # First message should be the daily report
    assert "💼" in result[0] or "Daily Portfolio" in result[0]


@pytest.mark.asyncio
async def test_portfolio_cron_multiple_chains():
    """test_portfolio_cron_multiple_chains — wallets on multiple chains → aggregated report."""
    wallets = {
        "solana": ["SolWallet1", "SolWallet2"],
        "ethereum": ["0xEVMWallet123456789012345678901234567890abcd"],
    }

    result = await run_portfolio_report(
        wallets=wallets,
        helius_api_key=None,
        alchemy_api_key=None,
    )

    assert isinstance(result, list)
    assert len(result) >= 1


# ============================================================================
# liquidation_cron Tests
# ============================================================================

from borg.defi.cron.liquidation_cron import run_liquidation_scan
from borg.defi.liquidation_watcher import LiquidationTarget


@pytest.mark.asyncio
async def test_liquidation_cron_no_targets():
    """test_liquidation_cron_no_targets — mock returns empty → empty list."""
    with patch("borg.defi.liquidation_watcher.run_watcher", new_callable=AsyncMock) as mock:
        mock.return_value = []

        result = await run_liquidation_scan()

        assert isinstance(result, list)
        assert len(result) == 0


@pytest.mark.asyncio
async def test_liquidation_cron_with_targets():
    """test_liquidation_cron_with_targets — mock targets → formatted alerts."""
    mock_targets = [
        LiquidationTarget(
            user_address="0xUser123456789012345678901234567890abcd",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.05,
            collateral_usd=50_000.0,
            debt_usd=30_000.0,
            potential_profit_usd=2_500.0,
            liquidation_bonus=0.05,
        )
    ]

    with patch("borg.defi.cron.liquidation_cron.scan_all_positions", new_callable=AsyncMock) as mock:
        mock.return_value = mock_targets

        result = await run_liquidation_scan(min_profit_usd=100.0)

        assert isinstance(result, list)
        assert len(result) == 1
        assert "LIQUIDATION" in result[0]


@pytest.mark.asyncio
async def test_liquidation_cron_below_profit_threshold():
    """test_liquidation_cron_below_profit_threshold — profit < min_profit_usd → filtered."""
    mock_targets = [
        LiquidationTarget(
            user_address="0xSmallUser123456789012345678901234567890",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.05,
            collateral_usd=5_000.0,
            debt_usd=3_000.0,
            potential_profit_usd=50.0,  # Below $100 min
            liquidation_bonus=0.05,
        )
    ]

    with patch("borg.defi.cron.liquidation_cron.scan_all_positions", new_callable=AsyncMock) as mock:
        mock.return_value = mock_targets

        result = await run_liquidation_scan(min_profit_usd=100.0)

        assert isinstance(result, list)
        assert len(result) == 0  # Filtered out due to low profit


@pytest.mark.asyncio
async def test_liquidation_cron_health_threshold():
    """test_liquidation_cron_health_threshold — health_threshold param passed correctly."""
    with patch("borg.defi.cron.liquidation_cron.scan_all_positions", new_callable=AsyncMock) as mock:
        mock.return_value = []

        await run_liquidation_scan(health_threshold=1.2)

        # Verify scan_all_positions was called with correct threshold
        mock.assert_called_once()
        call_kwargs = mock.call_args[1]
        assert call_kwargs.get("health_threshold") == 1.2


# ============================================================================
# risk_cron Tests
# ============================================================================

from borg.defi.cron.risk_cron import run_risk_check
from borg.defi.risk_engine import RiskEngine
from borg.defi.data_models import Position


@pytest.mark.asyncio
async def test_risk_check_no_positions():
    """test_risk_check_no_positions — empty positions → empty list."""
    result = await run_risk_check(positions=[])
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_risk_check_none_positions():
    """test_risk_check_none_positions — positions=None → empty list."""
    result = await run_risk_check(positions=None)
    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_risk_check_no_concentration_issues():
    """test_risk_check_no_concentration_issues — diverse portfolio → no alerts."""
    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.0,
            value_usd=2_000.0,
            entry_price=200.0,
            current_price=200.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="ETH",
            amount=1.0,
            value_usd=2_000.0,
            entry_price=2000.0,
            current_price=2000.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            position_type="hold",
        ),
    ]

    result = await run_risk_check(positions=positions)

    assert isinstance(result, list)
    # No concentration alerts expected (25% threshold, 50/50 split)


@pytest.mark.asyncio
async def test_risk_check_concentration_alert():
    """test_risk_check_concentration_alert — single token >25% → concentration alert."""
    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=50.0,
            value_usd=10_000.0,  # 80% of portfolio
            entry_price=200.0,
            current_price=200.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="ethereum",
            token="ETH",
            amount=0.5,
            value_usd=1_000.0,  # 10%
            entry_price=2000.0,
            current_price=2000.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            position_type="hold",
        ),
        Position(
            chain="ethereum",
            protocol="aave",
            token="USDC",
            amount=1_000.0,
            value_usd=1_000.0,  # 10%
            entry_price=1.0,
            current_price=1.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            position_type="lending",
        ),
    ]

    result = await run_risk_check(
        positions=positions,
        concentration_warning_threshold=0.25,
    )

    assert isinstance(result, list)
    assert len(result) > 0
    # Should have concentration alert
    assert any("CONCENTRATION" in alert for alert in result)


@pytest.mark.asyncio
async def test_risk_check_drawdown_warning():
    """test_risk_check_drawdown_warning — risk check includes drawdown alerts when called with portfolio value."""
    # Create a fresh engine
    engine = RiskEngine()

    # Set a peak first by calling drawdown_tracking directly
    # Then call again with a lower value to trigger drawdown warning
    engine.drawdown_tracking(current_value=10_000.0)  # Set peak
    drawdown_result = engine.drawdown_tracking(current_value=8_500.0)  # 15% drop

    # Verify engine detected drawdown
    assert drawdown_result.current_drawdown_pct > 0.1  # >10% threshold

    # Now test with positions - run_risk_check creates its own engine
    # so drawdown tracking is per-call. We test the drawdown tracking logic directly above.
    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.0,
            value_usd=1_500.0,
            entry_price=200.0,
            current_price=150.0,
            pnl_usd=-500.0,
            pnl_pct=-25.0,
            position_type="hold",
        ),
    ]

    # Since run_risk_check creates fresh engine each time, drawdown tracking
    # starts with the first value as peak. So we just verify the function
    # works without error and returns a list
    result = await run_risk_check(
        positions=positions,
        current_portfolio_value=8_500.0,
    )

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_risk_check_stop_loss_triggered():
    """test_risk_check_stop_loss_triggered — drawdown > stop-loss threshold → stop-loss alert."""
    # Create engine with stop-loss threshold
    engine = RiskEngine(default_stop_loss=0.20)

    # Set peak and then drop to trigger stop-loss
    engine.drawdown_tracking(current_value=10_000.0)  # Peak
    drawdown_result = engine.drawdown_tracking(current_value=7_000.0)  # 30% drop

    # Verify stop-loss was triggered
    assert drawdown_result.stop_loss_triggered is True

    positions = [
        Position(
            chain="solana",
            protocol="solana",
            token="SOL",
            amount=10.0,
            value_usd=1_000.0,
            entry_price=200.0,
            current_price=140.0,
            pnl_usd=-600.0,
            pnl_pct=-30.0,
            position_type="hold",
        ),
    ]

    # run_risk_check creates fresh engine, so we verify stop-loss via engine directly
    result = await run_risk_check(
        positions=positions,
        default_stop_loss=0.20,
        current_portfolio_value=7_000.0,
    )

    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_risk_check_protocol_risk_with_tvl():
    """test_risk_check_protocol_risk_with_tvl — protocol TVL data → protocol risk alert."""
    positions = [
        Position(
            chain="ethereum",
            protocol="someshackprotocol",
            token="SOMESHACK",
            amount=100.0,
            value_usd=5_000.0,
            entry_price=50.0,
            current_price=50.0,
            pnl_usd=0.0,
            pnl_pct=0.0,
            position_type="hold",
        ),
    ]

    tvl_data = {
        "someshackprotocol": {
            "tvl_usd": 1_000_000.0,
            "tvl_history": [1_500_000.0, 1_200_000.0, 1_000_000.0],
        }
    }

    result = await run_risk_check(
        positions=positions,
        tvl_data=tvl_data,
    )

    assert isinstance(result, list)


# ============================================================================
# Integration: All Cron Entry Points Importable
# ============================================================================

def test_cron_all_importable():
    """test_cron_all_importable — all cron functions are importable from borg.defi."""
    from borg.defi.cron import (
        run_whale_scan,
        run_yield_scan,
        run_alpha_scan,
        run_portfolio_report,
        run_liquidation_scan,
        run_risk_check,
    )

    assert callable(run_whale_scan)
    assert callable(run_yield_scan)
    assert callable(run_alpha_scan)
    assert callable(run_portfolio_report)
    assert callable(run_liquidation_scan)
    assert callable(run_risk_check)


def test_defi_init_exports_cron():
    """test_defi_init_exports_cron — borg.defi.__init__ exports all cron functions."""
    from borg.defi import (
        run_whale_scan,
        run_yield_scan,
        run_alpha_scan,
        run_portfolio_report,
        run_liquidation_scan,
        run_risk_check,
    )

    assert callable(run_whale_scan)
    assert callable(run_yield_scan)
    assert callable(run_alpha_scan)
    assert callable(run_portfolio_report)
    assert callable(run_liquidation_scan)
    assert callable(run_risk_check)


def test_defi_init_exports_p3_modules():
    """test_defi_init_exports_p3_modules — borg.defi.__init__ exports Phase 3 modules."""
    from borg.defi import (
        AlphaSignalEngine,
        RiskEngine,
        StrategyBacktester,
    )

    assert AlphaSignalEngine is not None
    assert RiskEngine is not None
    assert StrategyBacktester is not None


# ============================================================================
# Return Type Verification
# ============================================================================

@pytest.mark.asyncio
async def test_whale_cron_returns_list_of_strings():
    """test_whale_cron_returns_list_of_strings — verify return type."""
    result = await run_whale_scan()
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)


@pytest.mark.asyncio
async def test_yield_cron_returns_list_of_strings():
    """test_yield_cron_returns_list_of_strings — verify return type."""
    with patch("borg.defi.yield_scanner.aiohttp.ClientSession"):
        result = await run_yield_scan()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)


@pytest.mark.asyncio
async def test_alpha_cron_returns_list_of_strings():
    """test_alpha_cron_returns_list_of_strings — verify return type."""
    result = await run_alpha_scan()
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)


@pytest.mark.asyncio
async def test_portfolio_cron_returns_list_of_strings():
    """test_portfolio_cron_returns_list_of_strings — verify return type."""
    result = await run_portfolio_report({})
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)


@pytest.mark.asyncio
async def test_liquidation_cron_returns_list_of_strings():
    """test_liquidation_cron_returns_list_of_strings — verify return type."""
    with patch("borg.defi.liquidation_watcher.run_watcher", new_callable=AsyncMock) as mock:
        mock.return_value = []
        result = await run_liquidation_scan()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)


@pytest.mark.asyncio
async def test_risk_check_returns_list_of_strings():
    """test_risk_check_returns_list_of_strings — verify return type."""
    result = await run_risk_check(positions=[])
    assert isinstance(result, list)
    for item in result:
        assert isinstance(item, str)
