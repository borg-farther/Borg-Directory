"""
Tests for Liquidation Watcher module.

Uses mock subgraph responses to test scanning, profit estimation, and alert formatting.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio

import borg.defi.liquidation_watcher as liquidation_watcher

from borg.defi.liquidation_watcher import (
    LiquidationTarget,
    scan_aave_positions,
    scan_compound_positions,
    scan_all_positions,
    estimate_liquidation_profit,
    format_alert,
    generate_cron_entry,
    query_subgraph,
    LIQUIDATION_THRESHOLD,
    Protocol,
)


# --- Mock Data ---

MOCK_AAVE_RESPONSE = {
    "data": {
        "users": [
            {
                "id": "0x1234567890abcdef1234567890abcdef12345678",
                "healthFactor": "1.05",
                "totalCollateralUSD": "50000.0",
                "totalDebtUSD": "45000.0",
                "reserves": [
                    {
                        "underlyingAsset": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                        "symbol": "WETH",
                        "liquidityRate": "0.03",
                        "variableBorrowRate": "0.05",
                        "currentATokenBalance": "30.5",
                        "currentVariableDebt": "45000.0",
                        "currentStableDebt": "0.0",
                        "priceInUSD": "2000.0",
                    }
                ],
            },
            {
                "id": "0xabcdef1234567890abcdef1234567890abcdef12",
                "healthFactor": "0.95",
                "totalCollateralUSD": "100000.0",
                "totalDebtUSD": "95000.0",
                "reserves": [
                    {
                        "underlyingAsset": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                        "symbol": "USDC",
                        "liquidityRate": "0.04",
                        "variableBorrowRate": "0.06",
                        "currentATokenBalance": "100000.0",
                        "currentVariableDebt": "95000.0",
                        "currentStableDebt": "0.0",
                        "priceInUSD": "1.0",
                    }
                ],
            },
            {
                "id": "0x9999999999abcdef9999999999abcdef99999999",
                "healthFactor": "1.08",
                "totalCollateralUSD": "25000.0",
                "totalDebtUSD": "22000.0",
                "reserves": [],
            },
        ]
    }
}

MOCK_COMPOUND_RESPONSE = {
    "data": {
        "accounts": [
            {
                "id": "0x2222222222abcdef2222222222abcdef22222222",
                "healthScore": "0.85",  # HF = 1/0.85 = 1.176 (above threshold but close)
                "totalCollateralValue": "75000.0",
                "totalDebtValue": "70000.0",
                "tokens": [
                    {
                        "symbol": "ETH",
                        "tokenAddress": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                        "supplyBalance": "37.5",
                        "borrowBalance": "70000.0",
                        "market": {
                            "collateralFactor": "0.75",
                            "underlyingPrice": "2000.0",
                        },
                    }
                ],
            },
            {
                "id": "0x3333333333abcdef3333333333abcdef33333333",
                "healthScore": "1.15",  # HF = 1/1.15 = 0.869 (liquidatable!)
                "totalCollateralValue": "80000.0",
                "totalDebtValue": "78000.0",
                "tokens": [
                    {
                        "symbol": "WBTC",
                        "tokenAddress": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
                        "supplyBalance": "2.0",
                        "borrowBalance": "78000.0",
                        "market": {
                            "collateralFactor": "0.70",
                            "underlyingPrice": "50000.0",
                        },
                    }
                ],
            },
        ]
    }
}

MOCK_EMPTY_RESPONSE = {"data": {"users": []}}


# --- Tests for LiquidationTarget ---

class TestLiquidationTarget:
    def test_creation(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.05,
            collateral_usd=50000.0,
            debt_usd=45000.0,
            potential_profit_usd=2500.0,
        )
        assert target.user_address == "0x123"
        assert target.health_factor == 1.05
        assert target.collateral_usd == 50000.0
        assert target.debt_usd == 45000.0
        assert target.timestamp > 0

    def test_is_liquidatable(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.95,
            collateral_usd=50000.0,
            debt_usd=45000.0,
        )
        assert target.is_liquidatable() is True

        target_hf_1 = LiquidationTarget(
            user_address="0x456",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.05,
            collateral_usd=50000.0,
            debt_usd=45000.0,
        )
        assert target_hf_1.is_liquidatable() is False

    def test_is_at_risk(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.05,
            collateral_usd=50000.0,
            debt_usd=45000.0,
        )
        assert target.is_at_risk() is True

        target_safe = LiquidationTarget(
            user_address="0x456",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.5,
            collateral_usd=50000.0,
            debt_usd=30000.0,
        )
        assert target_safe.is_at_risk() is False

    def test_to_dict(self):
        target = LiquidationTarget(
            user_address="0x1234567890abcdef1234567890abcdef12345678",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=1.05,
            collateral_usd=50000.0,
            debt_usd=45000.0,
            potential_profit_usd=2500.0,
            liquidation_bonus=0.05,
        )
        d = target.to_dict()
        assert d["user_address"] == "0x1234567890abcdef1234567890abcdef12345678"
        assert d["health_factor"] == 1.05
        assert d["collateral_usd"] == 50000.0
        assert d["is_liquidatable"] is False
        assert d["is_at_risk"] is True
        assert d["liquidation_bonus"] == 5.0


# --- Tests for query_subgraph ---

class TestQuerySubgraph:
    @pytest.mark.asyncio
    async def test_query_subgraph_success(self):
        # Create mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=MOCK_AAVE_RESPONSE)

        # Create async context manager mock for the response
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Create mock session that returns our response from post()
        mock_session_instance = AsyncMock()
        mock_session_instance.post = MagicMock(return_value=mock_response)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_instance):
            result = await query_subgraph(
                "https://api.thegraph.com/subgraphs/name/aave/v3-ethereum",
                "{ users { id } }",
            )
            assert result is not None

    @pytest.mark.asyncio
    async def test_query_subgraph_error(self):
        mock_response = AsyncMock()
        mock_response.status = 400

        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session_instance = AsyncMock()
        mock_session_instance.post = MagicMock(return_value=mock_response)
        mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
        mock_session_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_instance):
            result = await query_subgraph(
                "https://api.thegraph.com/subgraphs/name/aave/v3-ethereum",
                "{ users { id } }",
            )
            assert result is None


# --- Tests for scan_aave_positions ---

class TestScanAavePositions:
    @pytest.mark.asyncio
    async def test_scan_aave_positions_success(self):
        """Test scanning Aave positions - uses integration test style."""
        original_query = liquidation_watcher.query_subgraph
        
        async def mock_query(url, query, variables=None):
            # query_subgraph normally returns data.get("data"), so we return the unwrapped response
            return MOCK_AAVE_RESPONSE["data"]
        
        # Replace the function directly
        liquidation_watcher.query_subgraph = mock_query
        try:
            targets = await scan_aave_positions("ethereum", health_threshold=1.1)
            
            assert len(targets) == 3
            # Check that all expected users are present (ordering may vary based on Graph response)
            hf_map = {t.user_address: t.health_factor for t in targets}
            assert hf_map.get("0xabcdef1234567890abcdef1234567890abcdef12") == 0.95
            assert hf_map.get("0x1234567890abcdef1234567890abcdef12345678") == 1.05
            assert hf_map.get("0x9999999999abcdef9999999999abcdef99999999") == 1.08
            
            # Verify all targets have correct protocol and chain
            for target in targets:
                assert target.protocol == Protocol.AAVE_V3.value
                assert target.chain == "ethereum"
        finally:
            liquidation_watcher.query_subgraph = original_query

    @pytest.mark.asyncio
    async def test_scan_aave_positions_empty(self):
        """Test empty result handling."""
        original_query = liquidation_watcher.query_subgraph
        
        async def mock_query(url, query, variables=None):
            return {"data": {"users": []}}
        
        liquidation_watcher.query_subgraph = mock_query
        try:
            targets = await scan_aave_positions("ethereum")
            assert len(targets) == 0
        finally:
            liquidation_watcher.query_subgraph = original_query

    @pytest.mark.asyncio
    async def test_scan_aave_positions_unsupported_chain(self):
        """Test unsupported chain returns empty list."""
        targets = await scan_aave_positions("solana")
        assert len(targets) == 0

    @pytest.mark.asyncio
    async def test_scan_aave_positions_with_limit(self):
        """Test pagination works correctly."""
        original_query = liquidation_watcher.query_subgraph
        
        # Track pagination state
        call_count = [0]  # Use list to allow modification in closure
        
        async def mock_query(url, query, variables=None):
            skip = variables.get("skip", 0) if variables else 0
            first = variables.get("first", 100) if variables else 100
            
            # Simulate pagination: return different subsets based on skip
            all_users = MOCK_AAVE_RESPONSE["data"]["users"]
            if skip >= len(all_users):
                return {"users": []}
            return {"users": all_users[skip : skip + first]}
        
        liquidation_watcher.query_subgraph = mock_query
        try:
            targets = await scan_aave_positions("ethereum", health_threshold=1.1, limit=2)
            assert len(targets) == 3
        finally:
            liquidation_watcher.query_subgraph = original_query

    @pytest.mark.asyncio
    async def test_scan_aave_positions_profit_calculation(self):
        """Test profit calculation based on liquidation bonus."""
        original_query = liquidation_watcher.query_subgraph
        
        async def mock_query(url, query, variables=None):
            # query_subgraph normally returns data.get("data"), so we return the unwrapped response
            return MOCK_AAVE_RESPONSE["data"]
        
        liquidation_watcher.query_subgraph = mock_query
        try:
            targets = await scan_aave_positions("ethereum", health_threshold=1.1)
            
            for target in targets:
                expected_profit = target.collateral_usd * 0.05
                assert abs(target.potential_profit_usd - expected_profit) < 0.01
        finally:
            liquidation_watcher.query_subgraph = original_query


# --- Tests for scan_compound_positions ---

class TestScanCompoundPositions:
    @pytest.mark.asyncio
    async def test_scan_compound_positions_success(self):
        """Test scanning Compound positions - uses integration test style."""
        original_query = liquidation_watcher.query_subgraph
        
        async def mock_query(url, query, variables=None):
            # query_subgraph normally returns data.get("data"), so we return the unwrapped response
            return MOCK_COMPOUND_RESPONSE["data"]
        
        liquidation_watcher.query_subgraph = mock_query
        try:
            targets = await scan_compound_positions("ethereum", health_threshold=1.1)
            
            assert len(targets) == 2
            
            # Build a map to check health factors regardless of ordering
            hf_map = {t.user_address: t.health_factor for t in targets}
            
            # Check health factors are calculated correctly
            # healthScore 0.85 -> HF = 1/0.85 = 1.176
            # healthScore 1.15 -> HF = 1/1.15 = 0.869
            assert abs(hf_map.get("0x2222222222abcdef2222222222abcdef22222222", 0) - (1.0 / 0.85)) < 0.001
            assert abs(hf_map.get("0x3333333333abcdef3333333333abcdef33333333", 0) - (1.0 / 1.15)) < 0.001
            
            for target in targets:
                assert target.protocol == Protocol.COMPOUND_V3.value
                assert target.chain == "ethereum"
        finally:
            liquidation_watcher.query_subgraph = original_query

    @pytest.mark.asyncio
    async def test_scan_compound_positions_empty(self):
        """Test empty result handling."""
        original_query = liquidation_watcher.query_subgraph
        
        async def mock_query(url, query, variables=None):
            return {"data": {"accounts": []}}
        
        liquidation_watcher.query_subgraph = mock_query
        try:
            targets = await scan_compound_positions("ethereum")
            assert len(targets) == 0
        finally:
            liquidation_watcher.query_subgraph = original_query

    @pytest.mark.asyncio
    async def test_scan_compound_positions_unsupported_chain(self):
        """Test unsupported chain returns empty list."""
        targets = await scan_compound_positions("solana")
        assert len(targets) == 0


# --- Tests for scan_all_positions ---

class TestScanAllPositions:
    @pytest.mark.asyncio
    async def test_scan_all_positions_combines_results(self):
        with patch("borg.defi.liquidation_watcher.scan_aave_positions", new_callable=AsyncMock) as mock_aave:
            with patch("borg.defi.liquidation_watcher.scan_compound_positions", new_callable=AsyncMock) as mock_compound:
                mock_aave.return_value = [
                    LiquidationTarget(
                        user_address="0xaave_user",
                        protocol="aave_v3",
                        chain="ethereum",
                        health_factor=1.05,
                        collateral_usd=50000.0,
                        debt_usd=45000.0,
                        potential_profit_usd=2500.0,
                    )
                ]
                mock_compound.return_value = [
                    LiquidationTarget(
                        user_address="0xcompound_user",
                        protocol="compound_v3",
                        chain="ethereum",
                        health_factor=0.95,
                        collateral_usd=30000.0,
                        debt_usd=28000.0,
                        potential_profit_usd=2400.0,
                    )
                ]

                targets = await scan_all_positions(chains=["ethereum"])

                assert len(targets) == 2
                # Should be sorted by potential_profit_usd descending
                assert targets[0].user_address == "0xaave_user"
                assert targets[1].user_address == "0xcompound_user"

    @pytest.mark.asyncio
    async def test_scan_all_positions_handles_exceptions(self):
        with patch("borg.defi.liquidation_watcher.scan_aave_positions", new_callable=AsyncMock) as mock_aave:
            with patch("borg.defi.liquidation_watcher.scan_compound_positions", new_callable=AsyncMock) as mock_compound:
                mock_aave.side_effect = Exception("Network error")
                mock_compound.return_value = []

                targets = await scan_all_positions(chains=["ethereum"])

                # Should handle exception gracefully and return empty list
                assert len(targets) == 0


# --- Tests for estimate_liquidation_profit ---

class TestEstimateLiquidationProfit:
    def test_estimate_profit_ethereum(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.95,
            collateral_usd=50000.0,
            debt_usd=45000.0,
            potential_profit_usd=2500.0,
        )

        profit = estimate_liquidation_profit(target)

        assert profit["gross_profit_usd"] == 2500.0
        assert profit["gas_cost_usd"] == 15.0  # Default Ethereum gas
        assert profit["net_profit_usd"] == 2485.0
        assert profit["is_profitable"] is True
        assert profit["roi_percent"] > 0

    def test_estimate_profit_base(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="base",
            health_factor=0.95,
            collateral_usd=10000.0,
            debt_usd=9000.0,
            potential_profit_usd=500.0,
        )

        profit = estimate_liquidation_profit(target)

        assert profit["gas_cost_usd"] == 0.50  # Base gas
        assert profit["net_profit_usd"] == 499.50
        assert profit["is_profitable"] is True

    def test_estimate_profit_with_custom_gas(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.95,
            collateral_usd=10000.0,
            debt_usd=9000.0,
            potential_profit_usd=100.0,
        )

        # High gas scenario
        profit = estimate_liquidation_profit(
            target,
            gas_price_gwei=100.0,  # 100 Gwei
            eth_price_usd=2000.0,
            gas_limit=500000,
        )

        # gas_cost = 500000 * 100 / 1e9 * 2000 = $100
        assert profit["gas_cost_usd"] == 100.0
        assert profit["net_profit_usd"] == 0.0
        assert profit["is_profitable"] is False

    def test_estimate_profit_not_profitable(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.99,
            collateral_usd=1000.0,
            debt_usd=990.0,
            potential_profit_usd=10.0,
        )

        profit = estimate_liquidation_profit(target)

        assert profit["net_profit_usd"] < 0  # Gas costs more than profit
        assert profit["is_profitable"] is False

    def test_estimate_profit_zero_debt(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.95,
            collateral_usd=10000.0,
            debt_usd=0.0,
            potential_profit_usd=500.0,
        )

        profit = estimate_liquidation_profit(target)

        # ROI should be 0 when debt is 0
        assert profit["roi_percent"] == 0


# --- Tests for format_alert ---

class TestFormatAlert:
    def test_format_alert_telegram(self):
        target = LiquidationTarget(
            user_address="0x1234567890abcdef1234567890abcdef12345678",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.95,
            collateral_usd=50000.0,
            debt_usd=45000.0,
            potential_profit_usd=2500.0,
            liquidation_bonus=0.05,
        )

        profit = estimate_liquidation_profit(target)
        alert = format_alert(target, profit, format="telegram")

        assert "LIQUIDATION OPPORTUNITY" in alert
        assert "AAVE_V3" in alert
        assert "Ethereum" in alert
        assert "0x123456...345678" in alert
        assert "0.9500" in alert
        assert "50,000.00" in alert
        assert "45,000.00" in alert
        assert "PROFITABLE" in alert

    def test_format_alert_discord(self):
        target = LiquidationTarget(
            user_address="0xabcdef1234567890abcdef1234567890abcdef12",
            protocol="compound_v3",
            chain="arbitrum",
            health_factor=1.08,
            collateral_usd=30000.0,
            debt_usd=27000.0,
            potential_profit_usd=2400.0,
            liquidation_bonus=0.08,
        )

        profit = estimate_liquidation_profit(target)
        alert = format_alert(target, profit, format="discord")

        assert "LIQUIDATION OPPORTUNITY" in alert
        assert "COMPOUND_V3" in alert
        assert "Arbitrum" in alert
        assert "1.0800" in alert
        # On Arbitrum with low gas ($2), position IS profitable
        assert "PROFITABLE" in alert
        assert "2,398.00" in alert  # Net profit = 2400 - 2

    def test_format_alert_without_profit_estimate(self):
        target = LiquidationTarget(
            user_address="0x123",
            protocol="aave_v3",
            chain="ethereum",
            health_factor=0.95,
            collateral_usd=50000.0,
            debt_usd=45000.0,
            potential_profit_usd=2500.0,
        )

        alert = format_alert(target, format="telegram")

        # Should calculate profit estimate automatically
        assert "LIQUIDATION OPPORTUNITY" in alert
        assert "AAVE_V3" in alert


# --- Tests for generate_cron_entry ---

class TestGenerateCronEntry:
    def test_generate_cron_entry(self):
        cron = generate_cron_entry(interval_minutes=5, cwd="/app")

        assert "*/5" in cron
        assert "/app" in cron
        assert "liquidation_watcher" in cron

    def test_generate_cron_entry_different_intervals(self):
        cron_10 = generate_cron_entry(interval_minutes=10)
        cron_15 = generate_cron_entry(interval_minutes=15)

        assert "*/10" in cron_10
        assert "*/15" in cron_15


# --- Tests for error handling ---

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_scan_aave_handles_missing_fields(self):
        bad_response = {
            "data": {
                "users": [
                    {
                        "id": "0x123",
                        # Missing healthFactor and other fields
                    }
                ]
            }
        }

        with patch("borg.defi.liquidation_watcher.query_subgraph", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = bad_response

            targets = await scan_aave_positions("ethereum")
            assert len(targets) == 0  # Should skip malformed entry

    @pytest.mark.asyncio
    async def test_scan_compound_handles_zero_health_score(self):
        response = {
            "data": {
                "accounts": [
                    {
                        "id": "0x123",
                        "healthScore": "0",  # Zero causes division error
                        "totalCollateralValue": "10000.0",
                        "totalDebtValue": "9000.0",
                    }
                ]
            }
        }

        with patch("borg.defi.liquidation_watcher.query_subgraph", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = response

            targets = await scan_compound_positions("ethereum")
            # Should handle gracefully and skip the bad entry
            assert len(targets) == 0

    @pytest.mark.asyncio
    async def test_scan_compound_handles_negative_health_score(self):
        response = {
            "data": {
                "accounts": [
                    {
                        "id": "0x123",
                        "healthScore": "-1",  # Invalid
                        "totalCollateralValue": "10000.0",
                        "totalDebtValue": "9000.0",
                    }
                ]
            }
        }

        with patch("borg.defi.liquidation_watcher.query_subgraph", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = response

            targets = await scan_compound_positions("ethereum")
            assert len(targets) == 0


# --- Tests for Protocol Enum ---

class TestProtocol:
    def test_protocol_values(self):
        assert Protocol.AAVE_V3.value == "aave_v3"
        assert Protocol.COMPOUND_V3.value == "compound_v3"


# --- Integration-style test ---

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_scan_flow(self):
        """Test the complete flow from scan to alert formatting."""
        with patch("borg.defi.liquidation_watcher.query_subgraph", new_callable=AsyncMock) as mock_query:
            # Return both Aave and Compound data
            mock_query.side_effect = [MOCK_AAVE_RESPONSE, MOCK_COMPOUND_RESPONSE]

            # Scan for at-risk positions
            targets = await scan_all_positions(chains=["ethereum"], health_threshold=1.1)

            # Filter profitable ones
            profitable = []
            for target in targets:
                profit = estimate_liquidation_profit(target)
                if profit["is_profitable"]:
                    profitable.append((target, profit))

            # Format alerts
            for target, profit in profitable:
                alert = format_alert(target, profit, format="telegram")
                assert "LIQUIDATION OPPORTUNITY" in alert

    @pytest.mark.asyncio
    async def test_multi_chain_scan(self):
        """Test scanning across multiple chains."""
        with patch("borg.defi.liquidation_watcher.scan_aave_positions", new_callable=AsyncMock) as mock_aave:
            with patch("borg.defi.liquidation_watcher.scan_compound_positions", new_callable=AsyncMock) as mock_compound:
                # Simulate different results per chain
                mock_aave.side_effect = [
                    [LiquidationTarget(
                        user_address="0xeth1",
                        protocol="aave_v3",
                        chain="ethereum",
                        health_factor=0.9,
                        collateral_usd=100000.0,
                        debt_usd=90000.0,
                        potential_profit_usd=5000.0,
                    )],
                    [LiquidationTarget(
                        user_address="0xarb1",
                        protocol="aave_v3",
                        chain="arbitrum",
                        health_factor=1.05,
                        collateral_usd=50000.0,
                        debt_usd=45000.0,
                        potential_profit_usd=2500.0,
                    )],
                ]
                mock_compound.return_value = []

                targets = await scan_all_positions(
                    chains=["ethereum", "arbitrum"]
                )

                assert len(targets) == 2
                # Should be sorted by profit
                assert targets[0].user_address == "0xeth1"
                assert targets[0].potential_profit_usd == 5000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
