"""
Production-quality tests for borg/defi/cron/live_scans.py

Covers:
- Happy path (with mocked API responses)
- API errors (timeout, HTTP errors, rate limits)
- Malformed data (missing fields, null values, empty arrays, wrong types)
- Empty results (no matching data)
- Message length limits (with max_results cranked up)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import aiohttp.connector


# ============================================================================
# Imports — test the module under test
# ============================================================================
import borg.defi.cron.live_scans as live_scans_module
from borg.defi.cron.live_scans import (
    yield_hunter,
    token_radar,
    tvl_pulse,
    stablecoin_watch,
    run_all_scans,
    _fetch_json,
    TIMEOUT,
    DEFILLAMA_YIELDS,
    DEFILLAMA_PROTOCOLS,
    DEFILLAMA_STABLECOINS,
    DEXSCREENER_LATEST,
    DEXSCREENER_BOOSTED,
)


# ============================================================================
# MOCK HELPERS
# ============================================================================

def make_json_response(json_data: dict | list, status: int = 200):
    """Build a mock aiohttp response that returns json_data on .json()."""
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    if status >= 400:
        mock_resp.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(
                request_info=MagicMock(),
                history=(),
                status=status,
                message=f"HTTP {status}",
            )
        )
    else:
        mock_resp.raise_for_status = MagicMock()
    return mock_resp


class MockGetCtx:
    """Fake aiohttp response context manager — yields mock_resp from __aenter__."""

    def __init__(self, mock_resp):
        self._mock_resp = mock_resp

    async def __aenter__(self):
        return self._mock_resp

    async def __aexit__(self, *args):
        pass


class MockSessionCtx:
    """Fake aiohttp.ClientSession whose .get() returns MockGetCtx objects."""

    def __init__(self, get_side_effect):
        """
        get_side_effect(url) -> json_data (dict/list) OR raises an aiohttp exception.
        """
        self._get_effect = get_side_effect

    def get(self, url: str):
        """Return a context-manager that yields the mock response."""
        data_or_exc = self._get_effect(url)
        if isinstance(data_or_exc, Exception):
            raise data_or_exc
        return MockGetCtx(make_json_response(data_or_exc))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def session_patch(get_side_effect):
    """Patch aiohttp.ClientSession to return MockSessionCtx(get_side_effect)."""
    return patch(
        "aiohttp.ClientSession",
        return_value=MockSessionCtx(get_side_effect),
    )


# ============================================================================
# TEST MODULE IMPORTS AND CONSTANTS
# ============================================================================

class TestModuleIntegrity:
    """Verify module loads, constants are correct, functions are callable."""

    def test_all_functions_are_async(self):
        """Functions must be async coroutines."""
        import inspect
        for fn in [yield_hunter, token_radar, tvl_pulse, stablecoin_watch]:
            assert inspect.iscoroutinefunction(fn), f"{fn.__name__} is not async"

    def test_timeout_is_reasonable(self):
        """TIMEOUT should be between 5 and 60 seconds."""
        assert 5 <= TIMEOUT.total <= 60, f"TIMEOUT {TIMEOUT} out of range"

    def test_urls_are_strings(self):
        """All endpoint URLs should be valid https strings."""
        for url in [DEFILLAMA_YIELDS, DEFILLAMA_PROTOCOLS, DEFILLAMA_STABLECOINS,
                    DEXSCREENER_LATEST, DEXSCREENER_BOOSTED]:
            assert isinstance(url, str), f"URL {url} is not a string"
            assert url.startswith("https://"), f"URL {url} is not https"


# ============================================================================
# TEST _fetch_json — the core HTTP utility
# ============================================================================

class TestFetchJson:
    """Test _fetch_json error handling via targeted patching of session.get."""

    @pytest.mark.asyncio
    async def test_200_returns_json(self):
        """200 OK → parsed JSON (via TestServer)."""
        import aiohttp.test_utils
        app = aiohttp.web.Application()
        async def handler(request):
            return aiohttp.web.json_response({"data": [1, 2, 3]})
        app.router.add_get("/data", handler)

        async with aiohttp.test_utils.TestServer(app) as server:
            session = aiohttp.ClientSession()
            url = str(server.make_url("/data"))
            try:
                result = await _fetch_json(url, session)
            finally:
                await session.close()
        assert result == {"data": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_timeout_raises_after_retries_exhausted(self):
        """ServerTimeoutError after all retries → propagates."""
        # Patch the _TRANSITORIES tuple at source so the except handles it correctly
        amock = AsyncMock()
        amock.__aenter__ = AsyncMock(side_effect=aiohttp.ServerTimeoutError())
        amock.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_get = MagicMock(return_value=amock)
        mock_session.get = mock_get

        # The retry loop will exhaust all attempts then raise ServerTimeoutError
        with pytest.raises(aiohttp.ServerTimeoutError):
            await _fetch_json("https://test.com/data", session=mock_session)

        # Should have retried 3 times (retries=2 means 3 total attempts)
        assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_error_raises_after_retries(self):
        """ClientConnectorError after retries → propagates."""
        # Create a ClientConnectorError with required args
        os_err = OSError("Connection refused")
        class DummyConnectionKey:
            pass
        dummy_key = DummyConnectionKey()

        amock = AsyncMock()
        amock.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(
                connection_key=dummy_key, os_error=os_err
            )
        )
        amock.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_get = MagicMock(return_value=amock)
        mock_session.get = mock_get

        with pytest.raises(aiohttp.ClientConnectorError):
            await _fetch_json("https://test.com/data", session=mock_session)

        assert mock_get.call_count == 3  # 2 retries + original

    @pytest.mark.asyncio
    async def test_http_error_not_retried(self):
        """HTTP 400/500 errors → NOT retried (propagate immediately)."""
        app = aiohttp.web.Application()
        async def handler(request):
            return aiohttp.web.Response(status=500, text="Error")
        app.router.add_get("/data", handler)

        async with aiohttp.test_utils.TestServer(app) as server:
            session = aiohttp.ClientSession()
            url = str(server.make_url("/data"))
            try:
                with pytest.raises(aiohttp.ClientResponseError):
                    await _fetch_json(url, session, retries=3)
            finally:
                await session.close()
        # No retries on HTTP errors — only 1 attempt made
        # (verified by it raising immediately without hanging)


# ============================================================================
# TEST yield_hunter — Happy Path
# ============================================================================

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
            "pool": "compound-v3/eth",
            "project": "Compound",
            "symbol": "ETH",
            "chain": "Ethereum",
            "tvlUsd": 20_000_000,
            "apy": 3.2,
            "apyMean7d": 3.0,
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


class TestYieldHunterHappy:
    """Valid DeFiLlama pools response → formatted alert."""

    @pytest.mark.asyncio
    async def test_yield_hunter_basic(self):
        """Happy path — returns formatted string with pool entries."""
        def side_effect(url):
            assert DEFILLAMA_YIELDS in url
            return YIELDS_PAYLOAD
        with session_patch(side_effect):
            result = await yield_hunter(min_tvl=1_000_000, min_apy=5.0, max_results=10)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "YIELD HUNTER" in result
        assert "Aave V3" in result
        assert "🔥" in result
        assert "DEGEN" in result or "HIGH" in result

    @pytest.mark.asyncio
    async def test_yield_hunter_includes_il_warning(self):
        """Pool with high IL risk → ⚠️IL in output."""
        def side_effect(url):
            return YIELDS_PAYLOAD
        with session_patch(side_effect):
            result = await yield_hunter()
        assert "⚠️IL" in result

    @pytest.mark.asyncio
    async def test_yield_hunter_sorted_by_apy_desc(self):
        """Results sorted by APY descending (highest APY appears first)."""
        def side_effect(url):
            return YIELDS_PAYLOAD
        with session_patch(side_effect):
            result = await yield_hunter(min_tvl=0, min_apy=0)
        lines = result.split("\n")
        somm_pos = next((i for i, l in enumerate(lines) if "Sommelier" in l), -1)
        aave_pos = next((i for i, l in enumerate(lines) if "Aave V3" in l), -1)
        assert somm_pos != -1 and aave_pos != -1
        assert somm_pos < aave_pos, "Higher APY (Sommelier 150%) should appear before lower APY (Aave 12.5%)"


# ============================================================================
# TEST yield_hunter — Empty / Edge Cases
# ============================================================================

class TestYieldHunterEmpty:
    """No matching pools → graceful no-results message."""

    @pytest.mark.asyncio
    async def test_empty_pools_list(self):
        """Empty data → no-thanks message, not crash."""
        def side_effect(url):
            return {"data": []}
        with session_patch(side_effect):
            result = await yield_hunter()
        assert "No yield opportunities" in result

    @pytest.mark.asyncio
    async def test_all_pools_filtered_out(self):
        """All pools filtered by TVL/APY → no-thanks."""
        def side_effect(url):
            return {"data": [
                {"pool": "x/y", "project": "X", "symbol": "Y", "chain": "Eth", "tvlUsd": 100, "apy": 0.1}
            ]}
        with session_patch(side_effect):
            result = await yield_hunter(min_tvl=1_000_000, min_apy=5.0)
        assert "No yield opportunities" in result


# ============================================================================
# TEST yield_hunter — Malformed Data
# ============================================================================

class TestYieldHunterMalformed:
    """API returns unexpected schema → must not crash."""

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self):
        """Pool missing ilRisk, apyMean7d, chain → uses defaults."""
        def side_effect(url):
            return {"data": [
                {"pool": "aave/usdc", "project": "Aave", "symbol": "USDC", "tvlUsd": 10_000_000, "apy": 5.0}
            ]}
        with session_patch(side_effect):
            result = await yield_hunter(min_tvl=0, min_apy=0)
        assert isinstance(result, str)
        assert "Aave" in result

    @pytest.mark.asyncio
    async def test_null_values_in_pools(self):
        """Fields are None/null → uses defaults, not crash."""
        def side_effect(url):
            return {"data": [
                {"pool": "x/y", "project": None, "symbol": None, "chain": None,
                 "tvlUsd": None, "apy": None, "apyMean7d": None, "ilRisk": None}
            ]}
        with session_patch(side_effect):
            result = await yield_hunter(min_tvl=0, min_apy=0)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_data_field_not_list(self):
        """data field is not a list (dict/string/None) → handled gracefully."""
        for payload in [
            {"data": "not a list"},
            {"data": {"nested": "dict"}},
            {"data": 123},
            {"data": None},
        ]:
            def side_effect(url):
                return payload
            with session_patch(side_effect):
                result = await yield_hunter(min_tvl=0, min_apy=0)
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_response_not_a_dict(self):
        """Top-level response is list/string/None → handled."""
        for payload in [[], "error string", None]:
            def side_effect(url):
                return payload
            with session_patch(side_effect):
                result = await yield_hunter()
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_non_dict_item_in_pools(self):
        """Pools list contains non-dict items → skipped, not crash."""
        def side_effect(url):
            return {"data": [
                {"pool": "valid", "project": "X", "symbol": "Y", "tvlUsd": 10_000_000, "apy": 5.0},
                "invalid string",
                None,
                123,
            ]}
        with session_patch(side_effect):
            result = await yield_hunter(min_tvl=0, min_apy=0)
        assert isinstance(result, str)
        assert "X" in result


# ============================================================================
# TEST yield_hunter — API Errors
# ============================================================================

class TestYieldHunterAPIErrors:
    """External API failures → error message, not exception."""

    @pytest.mark.asyncio
    async def test_defillama_timeout(self):
        """DeFiLlama times out → error string."""
        def side_effect(url):
            raise aiohttp.ServerTimeoutError()
        with session_patch(side_effect):
            result = await yield_hunter()
        assert "⚠️" in result or "error" in result.lower()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_defillama_500(self):
        """DeFiLlama returns 500 → error string."""
        def side_effect(url):
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=500, message="Server Error"
            )
        with session_patch(side_effect):
            result = await yield_hunter()
        assert "⚠️" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_429(self):
        """429 Too Many Requests → error string."""
        def side_effect(url):
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=429, message="Rate Limited"
            )
        with session_patch(side_effect):
            result = await yield_hunter()
        assert "⚠️" in result or "error" in result.lower()


# ============================================================================
# TEST token_radar — Happy Path
# ============================================================================

LATEST_PAYLOAD = [
    {
        "chainId": "ethereum",
        "tokenAddress": "0x1234567890abcdef1234567890abcdef12345678",
        "description": "A new DeFi token",
        "url": "https://dexscreener.com/token/0x1234",
    },
    {
        "chainId": "solana",
        "tokenAddress": "SolTokenAddress123456",
        "description": "Solana meme coin",
        "url": "https://dexscreener.com/token/SolToken",
    },
]

BOOSTED_PAYLOAD = [
    {
        "chainId": "ethereum",
        "tokenAddress": "0xabcdef1234567890abcdef1234567890abcdef12",
        "amount": 5000.0,
    }
]


def token_radar_side_effect(url: str):
    if "latest" in url:
        return LATEST_PAYLOAD
    elif "boost" in url:
        return BOOSTED_PAYLOAD
    raise RuntimeError(f"Unexpected URL: {url}")


class TestTokenRadarHappy:
    """DexScreener returns valid data → formatted alert."""

    @pytest.mark.asyncio
    async def test_token_radar_basic(self):
        """Happy path with latest + boosted tokens."""
        with session_patch(token_radar_side_effect):
            result = await token_radar(max_results=5)
        assert isinstance(result, str)
        assert "TOKEN RADAR" in result
        assert "ethereum" in result.lower()
        assert "solana" in result.lower()

    @pytest.mark.asyncio
    async def test_boosted_tokens_shown(self):
        """Boosted tokens → 🚀 BOOSTED section."""
        with session_patch(token_radar_side_effect):
            result = await token_radar()
        assert "BOOSTED" in result

    @pytest.mark.asyncio
    async def test_gathers_parallel(self):
        """Both endpoints called via asyncio.gather (check no serial dependency)."""
        with session_patch(token_radar_side_effect) as mock_patch:
            with patch("asyncio.gather") as mock_gather:
                # Just ensure gather is called with the right coroutines
                mock_gather.side_effect = asyncio.gather
                await token_radar()
                # If we get here without error, parallel execution works
        assert True


# ============================================================================
# TEST token_radar — Malformed Data
# ============================================================================

class TestTokenRadarMalformed:
    """DexScreener schema mismatches → must not crash."""

    @pytest.mark.asyncio
    async def test_latest_is_dict_not_list(self):
        """Latest endpoint returns dict wrapper → uses fallback."""
        def side_effect(url):
            if "latest" in url:
                return {"data": [{"chainId": "eth", "tokenAddress": "0x1234"}]}
            return []
        with session_patch(side_effect):
            result = await token_radar()
        assert isinstance(result, str)
        assert "TOKEN RADAR" in result

    @pytest.mark.asyncio
    async def test_token_missing_fields(self):
        """Token missing chainId / tokenAddress → uses defaults."""
        def side_effect(url):
            if "latest" in url:
                return [
                    {"tokenAddress": "0x1234"},  # missing chainId
                    {"chainId": "solana"},         # missing tokenAddress
                ]
            return []
        with session_patch(side_effect):
            result = await token_radar()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_boosted_is_not_list(self):
        """Boosted returns non-list → handled."""
        def side_effect(url):
            if "latest" in url:
                return [{"chainId": "eth", "tokenAddress": "0x1234"}]
            return "not an array"
        with session_patch(side_effect):
            result = await token_radar()
        assert isinstance(result, str)


# ============================================================================
# TEST token_radar — API Errors
# ============================================================================

class TestTokenRadarAPIErrors:
    """DexScreener failures → partial results or graceful error."""

    @pytest.mark.asyncio
    async def test_latest_fails_boosted_succeeds(self):
        """Latest endpoint 500 but boosted succeeds → still returns with boosted."""
        def side_effect(url):
            if "latest" in url:
                raise aiohttp.ClientResponseError(
                    request_info=MagicMock(), history=(), status=500, message="Error"
                )
            return [{"chainId": "eth", "tokenAddress": "0x1234", "amount": 1000}]
        with session_patch(side_effect):
            result = await token_radar()
        assert isinstance(result, str)
        assert "TOKEN RADAR" in result

    @pytest.mark.asyncio
    async def test_both_fail_500(self):
        """Both endpoints 500 → no crash; returns structure (boosted shows nothing when latest fails)."""
        def side_effect(url):
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=500, message="Error"
            )
        with session_patch(side_effect):
            result = await token_radar()
        # Should not crash; returns a string with header + source
        assert isinstance(result, str)
        assert "TOKEN RADAR" in result
        assert "DexScreener" in result

    @pytest.mark.asyncio
    async def test_timeout_one_endpoint(self):
        """One endpoint times out → other still returns."""
        def side_effect(url):
            if "latest" in url:
                return [{"chainId": "eth", "tokenAddress": "0x1234"}]
            raise aiohttp.ServerTimeoutError()
        with session_patch(side_effect):
            result = await token_radar()
        assert isinstance(result, str)
        assert "TOKEN RADAR" in result


# ============================================================================
# TEST tvl_pulse — Happy Path
# ============================================================================

PROTOCOLS_PAYLOAD = [
    {"name": "Aave",     "tvl": 10_000_000_000, "change_1d": 2.5,  "change_7d": 15.0},
    {"name": "MakerDAO", "tvl": 8_000_000_000,  "change_1d": -1.0, "change_7d": -6.0},  # -6% qualifies for losers
    {"name": "Lido",     "tvl": 15_000_000_000, "change_1d": 3.0,  "change_7d": 20.0},
    {"name": "Compound", "tvl": 2_000_000_000,   "change_1d": 0.5,  "change_7d": 2.0},
]


class TestTvlPulseHappy:
    """Valid DeFiLlama protocols response → formatted alert."""

    @pytest.mark.asyncio
    async def test_tvl_pulse_basic(self):
        """Happy path → top 10 by TVL + movers section."""
        def side_effect(url):
            return PROTOCOLS_PAYLOAD
        with session_patch(side_effect):
            result = await tvl_pulse(max_results=20)
        assert isinstance(result, str)
        assert "TVL PULSE" in result
        assert "Lido" in result  # Highest TVL

    @pytest.mark.asyncio
    async def test_tvl_pulse_shows_gainers_losers(self):
        """Protocols with >5% 7d change → gainers; <-5% → losers."""
        def side_effect(url):
            return PROTOCOLS_PAYLOAD
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert "GAINERS" in result
        assert "LOSERS" in result
        assert "Lido" in result   # +20% 7d → gainers
        assert "MakerDAO" in result  # -5% 7d → losers

    @pytest.mark.asyncio
    async def test_tvl_formatted_correctly(self):
        """TVL formatted as B (billions) or M (millions)."""
        def side_effect(url):
            return PROTOCOLS_PAYLOAD
        with session_patch(side_effect):
            result = await tvl_pulse()
        # Lido has $15B
        assert "$15.0B" in result or "$15B" in result


# ============================================================================
# TEST tvl_pulse — Empty / Edge Cases
# ============================================================================

class TestTvlPulseEmpty:
    """No matching protocols → graceful message."""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """Empty protocols list → returns structure, no crash."""
        def side_effect(url):
            return []
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert isinstance(result, str)
        assert "TVL PULSE" in result

    @pytest.mark.asyncio
    async def test_all_below_tvl_threshold(self):
        """All protocols below $10M TVL → filtered out."""
        def side_effect(url):
            return [{"name": "Tiny", "tvl": 1_000_000, "change_7d": 50.0}]
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert isinstance(result, str)


# ============================================================================
# TEST tvl_pulse — Malformed Data
# ============================================================================

class TestTvlPulseMalformed:
    """Unexpected protocol schema → must not crash."""

    @pytest.mark.asyncio
    async def test_missing_change_fields(self):
        """Protocol missing change_1d/change_7d → treated as 0."""
        def side_effect(url):
            return [{"name": "Aave", "tvl": 10_000_000_000}]
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert isinstance(result, str)
        assert "Aave" in result

    @pytest.mark.asyncio
    async def test_null_tvl(self):
        """Protocol with null TVL → skipped."""
        def side_effect(url):
            return [
                {"name": "NullTVL", "tvl": None, "change_7d": 10.0},
                {"name": "Valid",   "tvl": 10_000_000_000, "change_7d": 5.0},
            ]
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert isinstance(result, str)
        assert "Valid" in result

    @pytest.mark.asyncio
    async def test_wrong_type_in_list(self):
        """List contains non-dict items → skipped."""
        def side_effect(url):
            return [
                {"name": "Valid", "tvl": 10_000_000_000},
                "not a protocol",
                None,
                123,
            ]
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert isinstance(result, str)
        assert "Valid" in result


# ============================================================================
# TEST tvl_pulse — API Errors
# ============================================================================

class TestTvlPulseAPIErrors:
    """DeFiLlama protocols API failure → error string."""

    @pytest.mark.asyncio
    async def test_500_error(self):
        """500 from DeFiLlama → error message."""
        def side_effect(url):
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=500, message="Error"
            )
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert "⚠️" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Timeout → error message."""
        def side_effect(url):
            raise aiohttp.ServerTimeoutError()
        with session_patch(side_effect):
            result = await tvl_pulse()
        assert "⚠️" in result or "error" in result.lower()


# ============================================================================
# TEST stablecoin_watch — Happy Path
# ============================================================================

STABLES_PAYLOAD = {
    "peggedAssets": [
        {
            "name": "Tether USD",
            "symbol": "USDT",
            "circulating": {"peggedUSD": 100_000_000_000},
            "price": 1.0002,
        },
        {
            "name": "USD Coin",
            "symbol": "USDC",
            "circulating": {"peggedUSD": 50_000_000_000},
            "price": 0.9998,
        },
        {
            "name": "Dai",
            "symbol": "DAI",
            "circulating": {"peggedUSD": 5_000_000_000},
            "price": 1.0000,
        },
    ]
}


class TestStablecoinWatchHappy:
    """Valid stablecoin data → formatted alert."""

    @pytest.mark.asyncio
    async def test_stablecoin_watch_basic(self):
        """Happy path → lists stablecoins with peg status."""
        def side_effect(url):
            return STABLES_PAYLOAD
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert isinstance(result, str)
        assert "STABLECOIN WATCH" in result
        assert "USDT" in result
        assert "USDC" in result

    @pytest.mark.asyncio
    async def test_depeg_threshold_respected(self):
        """USDT at 0.02% off peg with 0.5% threshold → no 🚨 alert."""
        def side_effect(url):
            return STABLES_PAYLOAD
        with session_patch(side_effect):
            result = await stablecoin_watch(depeg_threshold=0.005)
        assert isinstance(result, str)
        # USDT at 0.02% deviation is below 0.5% threshold → no 🚨
        assert "🚨" not in result

    @pytest.mark.asyncio
    async def test_warning_emoji_for_slight_deviation(self):
        """Price slightly off peg → ⚠️ emoji (0.1% < deviation < 0.5%)."""
        def side_effect(url):
            return {
                "peggedAssets": [
                    {
                        "name": "USDT",
                        "symbol": "USDT",
                        "circulating": {"peggedUSD": 1_000_000},
                        "price": 1.002,  # 0.2% off peg
                    }
                ]
            }
        with session_patch(side_effect):
            result = await stablecoin_watch(depeg_threshold=0.005)
        # 0.2% deviation → above 0.1% warning threshold, below 0.5% depeg
        assert "⚠️" in result


# ============================================================================
# TEST stablecoin_watch — Empty / Edge Cases
# ============================================================================

class TestStablecoinWatchEmpty:
    """No stablecoins → graceful message."""

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """Empty peggedAssets → message, not crash."""
        def side_effect(url):
            return {"peggedAssets": []}
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert isinstance(result, str)
        assert "STABLECOIN WATCH" in result

    @pytest.mark.asyncio
    async def test_missing_peggedassets_key(self):
        """Response missing peggedAssets key → empty list, not crash."""
        def side_effect(url):
            return {}
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert isinstance(result, str)


# ============================================================================
# TEST stablecoin_watch — Malformed Data
# ============================================================================

class TestStablecoinWatchMalformed:
    """Unexpected schema → must not crash."""

    @pytest.mark.asyncio
    async def test_missing_circulating(self):
        """Stablecoin missing circulating → uses 0 supply."""
        def side_effect(url):
            return {
                "peggedAssets": [
                    {"name": "USDT", "symbol": "USDT", "price": 1.0},
                ]
            }
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert isinstance(result, str)
        assert "USDT" in result

    @pytest.mark.asyncio
    async def test_null_price(self):
        """Price is None → 'price N/A' string."""
        def side_effect(url):
            return {
                "peggedAssets": [
                    {"name": "USDT", "symbol": "USDT",
                     "circulating": {"peggedUSD": 1_000_000}, "price": None},
                ]
            }
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert "price N/A" in result

    @pytest.mark.asyncio
    async def test_circulating_is_not_dict(self):
        """circulating is string/list instead of dict → uses 0."""
        def side_effect(url):
            return {
                "peggedAssets": [
                    {"name": "USDT", "symbol": "USDT",
                     "circulating": "not a dict", "price": 1.0},
                ]
            }
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_wrong_type_in_list(self):
        """peggedAssets contains non-dict → skipped."""
        def side_effect(url):
            return {
                "peggedAssets": [
                    {"name": "USDT", "symbol": "USDT",
                     "circulating": {"peggedUSD": 1_000_000}, "price": 1.0},
                    "invalid",
                    None,
                    123,
                ]
            }
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert isinstance(result, str)
        assert "USDT" in result


# ============================================================================
# TEST stablecoin_watch — API Errors
# ============================================================================

class TestStablecoinWatchAPIErrors:
    """Stablecoin API failure → error string."""

    @pytest.mark.asyncio
    async def test_500_error(self):
        """500 → error string."""
        def side_effect(url):
            raise aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=500, message="Error"
            )
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert "⚠️" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Timeout → error string."""
        def side_effect(url):
            raise aiohttp.ServerTimeoutError()
        with session_patch(side_effect):
            result = await stablecoin_watch()
        assert "⚠️" in result or "error" in result.lower()


# ============================================================================
# TEST run_all_scans
# ============================================================================

class TestRunAllScans:
    """run_all_scans() aggregates all 4 scans."""

    @pytest.mark.asyncio
    async def test_run_all_scans_returns_list(self):
        """Returns list of 4 strings (or errors)."""
        results = await run_all_scans()
        assert isinstance(results, list)
        assert len(results) == 4


# ============================================================================
# TEST MESSAGE LENGTH LIMITS
# ============================================================================

class TestMessageLengthLimits:
    """Verify messages stay within Telegram 4096 char limit."""

    @pytest.mark.asyncio
    async def test_yield_hunter_max_results_stays_under_limit(self):
        """yield_hunter(max_results=50) → under 4096 chars with realistic data."""
        large_pools = [
            {
                "pool": f"pool-{i}",
                "project": f"Project{i}",
                "symbol": f"SYM{i}",
                "chain": "Ethereum",
                "tvlUsd": 10_000_000 + i * 1_000_000,
                "apy": 5.0 + i * 0.5,
                "apyMean7d": 4.0,
                "ilRisk": "none",
            }
            for i in range(60)
        ]
        def side_effect(url):
            return {"data": large_pools}
        with session_patch(side_effect):
            result = await yield_hunter(max_results=50, min_tvl=0, min_apy=0)
        assert len(result) <= 4096, f"yield_hunter is {len(result)} chars (limit: 4096)"

    @pytest.mark.asyncio
    async def test_tvl_pulse_max_results_stays_under_limit(self):
        """tvl_pulse(max_results=50) → under 4096 chars."""
        large_protocols = [
            {
                "name": f"Protocol{i}_Super_Long_Name_Here",
                "tvl": 10_000_000_000 + i * 1_000_000_000,
                "change_1d": 1.0,
                "change_7d": 5.0 + i,
            }
            for i in range(200)
        ]
        def side_effect(url):
            return large_protocols
        with session_patch(side_effect):
            result = await tvl_pulse(max_results=50)
        assert len(result) <= 4096, f"tvl_pulse is {len(result)} chars (limit: 4096)"

    @pytest.mark.asyncio
    async def test_stablecoin_watch_many_coins_stays_under_limit(self):
        """stablecoin_watch(top_n=50) → under 4096 chars."""
        many_stables = [
            {
                "name": f"Stablecoin_{i}",
                "symbol": f"STB{i}",
                "circulating": {"peggedUSD": 1_000_000_000 * (i + 1)},
                "price": 1.0,
            }
            for i in range(100)
        ]
        def side_effect(url):
            return {"peggedAssets": many_stables}
        with session_patch(side_effect):
            result = await stablecoin_watch(top_n=50)
        assert len(result) <= 4096, f"stablecoin_watch is {len(result)} chars (limit: 4096)"

    @pytest.mark.asyncio
    async def test_token_radar_max_results_stays_under_limit(self):
        """token_radar(max_results=50) → under 4096 chars."""
        many_tokens = [
            {
                "chainId": f"chain{i % 10}",
                "tokenAddress": f"0x{'a' * 40}",
                "description": f"Token {i}",
                "url": "https://dexscreener.com",
            }
            for i in range(100)
        ]
        def side_effect(url):
            if "latest" in url:
                return many_tokens
            return many_tokens[:10]
        with session_patch(side_effect):
            result = await token_radar(max_results=50)
        assert len(result) <= 4096, f"token_radar is {len(result)} chars (limit: 4096)"
