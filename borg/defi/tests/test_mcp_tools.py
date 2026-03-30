"""
Tests for borg/defi/mcp_tools.py — MCP tool wrappers.

Covers:
- Each tool function returns a non-empty string (with mocked _fetch_json)
- aiohttp guard: ImportError raised when aiohttp is not available
- All functions are importable and callable
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# We need to test the sync wrappers, but they call asyncio.run() on
# the async live_scans functions.  We mock _fetch_json so no real
# network calls are made.

YIELDS_PAYLOAD = {
    "data": [
        {
            "pool": "aave-v3/usdc",
            "project": "Aave V3",
            "symbol": "USDC",
            "chain": "Ethereum",
            "tvlUsd": 50_000_000,
            "apy": 12.5,
            "apyMean7d": 11.0,
            "ilRisk": "none",
        },
        {
            "pool": "sommelier/btc",
            "project": "Sommelier",
            "symbol": "WBTC",
            "chain": "Ethereum",
            "tvlUsd": 5_000_000,
            "apy": 150.0,
            "apyMean7d": 120.0,
            "ilRisk": "high",
        },
    ]
}

TOKEN_RADAR_PAYLOAD_LATEST = [
    {
        "chainId": "ethereum",
        "tokenAddress": "0x1234567890abcdef1234567890abcdef12345678",
        "description": "A new DeFi token",
        "url": "https://dexscreener.com/token/0x1234",
    }
]

TOKEN_RADAR_PAYLOAD_BOOSTED = [
    {
        "chainId": "ethereum",
        "tokenAddress": "0xabcdef1234567890abcdef1234567890abcdef12",
        "amount": 5000.0,
    }
]

TVL_PAYLOAD = [
    {
        "name": "Aave",
        "tvl": 5_000_000_000,
        "change_1d": 1.5,
        "change_7d": 3.2,
    },
    {
        "name": "MakerDAO",
        "tvl": 3_000_000_000,
        "change_1d": -0.5,
        "change_7d": -2.1,
    },
]

STABLECOIN_PAYLOAD = {
    "peggedAssets": [
        {
            "name": "Tether USD",
            "symbol": "USDT",
            "price": 1.0001,
            "circulating": {"peggedUSD": 80_000_000_000},
        },
        {
            "name": "USD Coin",
            "symbol": "USDC",
            "price": 0.9992,
            "circulating": {"peggedUSD": 30_000_000_000},
        },
    ]
}


# ---------------------------------------------------------------------------
# Mock helpers (same pattern used in test_live_scans.py)
# ---------------------------------------------------------------------------

class MockGetCtx:
    def __init__(self, mock_resp):
        self._mock_resp = mock_resp

    async def __aenter__(self):
        return self._mock_resp

    async def __aexit__(self, *args):
        pass


class MockSessionCtx:
    def __init__(self, get_side_effect):
        self._get_effect = get_side_effect

    def get(self, url: str):
        data_or_exc = self._get_effect(url)
        if isinstance(data_or_exc, Exception):
            raise data_or_exc
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=data_or_exc)
        mock_resp.raise_for_status = MagicMock()
        return MockGetCtx(mock_resp)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def make_mock_session(get_side_effect):
    return patch(
        "aiohttp.ClientSession",
        return_value=MockSessionCtx(get_side_effect),
    )


# ---------------------------------------------------------------------------
# Test: each tool function returns a non-empty string (mocked _fetch_json)
# ---------------------------------------------------------------------------

class TestMcpToolsReturnNonEmpty:
    """Each tool wrapper must return a non-empty string when data is valid."""

    def test_borg_defi_yields_returns_string(self):
        """borg_defi_yields returns a non-empty string."""
        from borg.defi.cron.live_scans import DEFILLAMA_YIELDS

        def side_effect(url):
            if DEFILLAMA_YIELDS in url:
                return YIELDS_PAYLOAD
            raise RuntimeError(f"Unexpected URL: {url}")

        with make_mock_session(side_effect):
            from borg.defi import mcp_tools
            # Force re-import to pick up mocked session
            with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", True):
                result = mcp_tools.borg_defi_yields(
                    min_apy=5.0, min_tvl=1_000_000, max_results=15
                )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "YIELD HUNTER" in result

    def test_borg_defi_tokens_returns_string(self):
        """borg_defi_tokens returns a non-empty string."""
        from borg.defi.cron.live_scans import (
            DEXSCREENER_LATEST, DEXSCREENER_BOOSTED
        )

        def side_effect(url):
            if "latest" in url:
                return TOKEN_RADAR_PAYLOAD_LATEST
            elif "boost" in url:
                return TOKEN_RADAR_PAYLOAD_BOOSTED
            raise RuntimeError(f"Unexpected URL: {url}")

        with make_mock_session(side_effect):
            from borg.defi import mcp_tools
            with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", True):
                result = mcp_tools.borg_defi_tokens(max_results=10)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "TOKEN RADAR" in result

    def test_borg_defi_tvl_returns_string(self):
        """borg_defi_tvl returns a non-empty string."""
        from borg.defi.cron.live_scans import DEFILLAMA_PROTOCOLS

        def side_effect(url):
            if DEFILLAMA_PROTOCOLS in url:
                return TVL_PAYLOAD
            raise RuntimeError(f"Unexpected URL: {url}")

        with make_mock_session(side_effect):
            from borg.defi import mcp_tools
            with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", True):
                result = mcp_tools.borg_defi_tvl(max_results=20)

        assert isinstance(result, str)
        assert len(result) > 0
        assert "TVL PULSE" in result

    def test_borg_defi_stablecoins_returns_string(self):
        """borg_defi_stablecoins returns a non-empty string."""
        from borg.defi.cron.live_scans import DEFILLAMA_STABLECOINS

        def side_effect(url):
            if DEFILLAMA_STABLECOINS in url:
                return STABLECOIN_PAYLOAD
            raise RuntimeError(f"Unexpected URL: {url}")

        with make_mock_session(side_effect):
            from borg.defi import mcp_tools
            with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", True):
                result = mcp_tools.borg_defi_stablecoins(
                    depeg_threshold=0.005, top_n=10
                )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "STABLECOIN WATCH" in result

    def test_borg_defi_scan_all_returns_string(self):
        """borg_defi_scan_all returns a combined non-empty string."""

        def side_effect(url):
            if "yields" in url:
                return YIELDS_PAYLOAD
            elif "protocols" in url:
                return TVL_PAYLOAD
            elif "stablecoins" in url:
                return STABLECOIN_PAYLOAD
            elif "latest" in url:
                return TOKEN_RADAR_PAYLOAD_LATEST
            elif "boost" in url:
                return TOKEN_RADAR_PAYLOAD_BOOSTED
            raise RuntimeError(f"Unexpected URL: {url}")

        with make_mock_session(side_effect):
            from borg.defi import mcp_tools
            with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", True):
                result = mcp_tools.borg_defi_scan_all()

        assert isinstance(result, str)
        assert len(result) > 0
        # scan-all concatenates all four with dividers
        assert "YIELD HUNTER" in result
        assert "=" * 40 in result


# ---------------------------------------------------------------------------
# Test: aiohttp guard — ImportError when aiohttp is not available
# ---------------------------------------------------------------------------

class TestAiohttpGuard:
    """Guard correctly raises ImportError when aiohttp is absent."""

    def test_yields_raises_when_aiohttp_missing(self):
        """borg_defi_yields raises ImportError if aiohttp not installed."""
        import sys
        # Simulate aiohttp not installed by patching the guard at import time
        import borg.defi.mcp_tools as mcp_tools

        # Patch _AIOHTTP_AVAILABLE to False (simulating import failure)
        with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", False):
            with pytest.raises(ImportError, match="aiohttp"):
                mcp_tools.borg_defi_yields(min_apy=5.0, min_tvl=1_000_000, max_results=15)

    def test_tokens_raises_when_aiohttp_missing(self):
        """borg_defi_tokens raises ImportError if aiohttp not installed."""
        import borg.defi.mcp_tools as mcp_tools
        with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", False):
            with pytest.raises(ImportError, match="aiohttp"):
                mcp_tools.borg_defi_tokens(max_results=10)

    def test_tvl_raises_when_aiohttp_missing(self):
        """borg_defi_tvl raises ImportError if aiohttp not installed."""
        import borg.defi.mcp_tools as mcp_tools
        with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", False):
            with pytest.raises(ImportError, match="aiohttp"):
                mcp_tools.borg_defi_tvl(max_results=20)

    def test_stablecoins_raises_when_aiohttp_missing(self):
        """borg_defi_stablecoins raises ImportError if aiohttp not installed."""
        import borg.defi.mcp_tools as mcp_tools
        with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", False):
            with pytest.raises(ImportError, match="aiohttp"):
                mcp_tools.borg_defi_stablecoins(depeg_threshold=0.005, top_n=10)

    def test_scan_all_raises_when_aiohttp_missing(self):
        """borg_defi_scan_all raises ImportError if aiohttp not installed."""
        import borg.defi.mcp_tools as mcp_tools
        with patch.object(mcp_tools, "_AIOHTTP_AVAILABLE", False):
            with pytest.raises(ImportError, match="aiohttp"):
                mcp_tools.borg_defi_scan_all()


# ---------------------------------------------------------------------------
# Test: default parameter values match the task specification
# ---------------------------------------------------------------------------

class TestDefaultParameters:
    """Verify default values match the API signature."""

    def test_yields_default_params(self):
        """borg_defi_yields has correct default param values."""
        from borg.defi import mcp_tools
        import inspect
        sig = inspect.signature(mcp_tools.borg_defi_yields)
        assert sig.parameters["min_apy"].default == 5.0
        assert sig.parameters["min_tvl"].default == 1_000_000
        assert sig.parameters["max_results"].default == 15

    def test_tokens_default_params(self):
        """borg_defi_tokens has correct default max_results=10."""
        from borg.defi import mcp_tools
        import inspect
        sig = inspect.signature(mcp_tools.borg_defi_tokens)
        assert sig.parameters["max_results"].default == 10

    def test_tvl_default_params(self):
        """borg_defi_tvl has correct default max_results=20."""
        from borg.defi import mcp_tools
        import inspect
        sig = inspect.signature(mcp_tools.borg_defi_tvl)
        assert sig.parameters["max_results"].default == 20

    def test_stablecoins_default_params(self):
        """borg_defi_stablecoins has correct default values."""
        from borg.defi import mcp_tools
        import inspect
        sig = inspect.signature(mcp_tools.borg_defi_stablecoins)
        assert sig.parameters["depeg_threshold"].default == 0.005
        assert sig.parameters["top_n"].default == 10
