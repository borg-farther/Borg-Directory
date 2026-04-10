"""
E2E integration tests for borg/defi/cron/live_scans.py

These tests hit real free APIs and validate:
1. Schema validation — raw API responses have expected structure
2. End-to-end scan output — formatted alert strings contain expected content

All tests are marked @pytest.mark.integration and skipped when no network is available.
Each test has a 15-second timeout.

Run with: pytest -m integration borg/defi/tests/test_e2e_live.py -v
"""

import asyncio
import pytest
import time

import aiohttp

# Import the live scan functions
from borg.defi.cron.live_scans import (
    yield_hunter,
    token_radar,
    tvl_pulse,
    stablecoin_watch,
    run_all_scans,
)

# ---------------------------------------------------------------------------
# Network availability check
# ---------------------------------------------------------------------------

try:
    import socket
    socket.create_connection(("1.1.1.1", 53), timeout=3)
    HAS_NETWORK = True
except (OSError, socket.timeout):
    HAS_NETWORK = False


# ---------------------------------------------------------------------------
# API endpoints (for schema tests using aiohttp directly)
# ---------------------------------------------------------------------------

DEFILLAMA_YIELDS = "https://yields.llama.fi/pools"
DEFILLAMA_PROTOCOLS = "https://api.llama.fi/protocols"
DEFILLAMA_STABLECOINS = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
DEXSCREENER_LATEST = "https://api.dexscreener.com/token-profiles/latest/v1"
JUPITER_QUOTE = (
    "https://quote-api.jup.ag/v6/quote"
    "?inputMint=So11111111111111111111111111111111111111112"
    "&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    "&amount=100000000"
    "&slippageBps=50"
)

API_TIMEOUT = aiohttp.ClientTimeout(total=15)


# ===========================================================================
# SCHEMA VALIDATION TESTS
# These tests hit real APIs and verify response structure.
# ===========================================================================

@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestDefiLlamaYieldsSchema:
    """Schema validation for DeFiLlama /pools endpoint."""

    @pytest.mark.asyncio
    async def test_defillama_yields_schema(self):
        """GET yields.llama.fi/pools → response has 'data' list with required fields."""
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(DEFILLAMA_YIELDS) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()

        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data, "Response missing 'data' key"
        pools = data["data"]
        assert isinstance(pools, list), f"Expected 'data' to be list, got {type(pools)}"
        assert len(pools) > 0, "Expected at least one pool in 'data'"

        # Validate first pool has required fields
        pool = pools[0]
        assert "project" in pool, f"Pool missing 'project': {pool}"
        assert "chain" in pool, f"Pool missing 'chain': {pool}"
        assert "symbol" in pool, f"Pool missing 'symbol': {pool}"
        assert "apy" in pool, f"Pool missing 'apy': {pool}"
        assert "tvlUsd" in pool, f"Pool missing 'tvlUsd': {pool}"

        # Type checks
        assert isinstance(pool["project"], str), f"project should be str, got {type(pool['project'])}"
        assert isinstance(pool["chain"], str), f"chain should be str, got {type(pool['chain'])}"
        assert isinstance(pool["symbol"], str), f"symbol should be str, got {type(pool['symbol'])}"
        assert isinstance(pool["apy"], (int, float)), f"apy should be number, got {type(pool['apy'])}"
        assert isinstance(pool["tvlUsd"], (int, float)), f"tvlUsd should be number, got {type(pool['tvlUsd'])}"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestDefiLlamaProtocolsSchema:
    """Schema validation for DeFiLlama /protocols endpoint."""

    @pytest.mark.asyncio
    async def test_defillama_protocols_schema(self):
        """GET api.llama.fi/protocols → list of dicts each with name, tvl, chain or chains."""
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(DEFILLAMA_PROTOCOLS) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data)}"
        assert len(data) > 0, "Expected at least one protocol"

        for proto in data[:5]:  # Validate first 5
            assert isinstance(proto, dict), f"Protocol should be dict, got {type(proto)}"
            assert "name" in proto, f"Protocol missing 'name': {proto}"
            assert "tvl" in proto, f"Protocol missing 'tvl': {proto}"
            # chain OR chains must be present
            assert "chain" in proto or "chains" in proto, (
                f"Protocol missing both 'chain' and 'chains': {proto}"
            )


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestDefiLlamaStablecoinsSchema:
    """Schema validation for DeFiLlama /stablecoins endpoint."""

    @pytest.mark.asyncio
    async def test_defillama_stablecoins_schema(self):
        """GET stablecoins.llama.fi/stablecoins?includePrices=true → peggedAssets with circulating.peggedUSD."""
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(DEFILLAMA_STABLECOINS) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()

        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "peggedAssets" in data, "Response missing 'peggedAssets'"
        pegged = data["peggedAssets"]
        assert isinstance(pegged, list), f"Expected peggedAssets to be list, got {type(pegged)}"
        assert len(pegged) > 0, "Expected at least one stablecoin"

        # Find one with circulating dict containing peggedUSD
        found = False
        for sc in pegged[:10]:
            assert isinstance(sc, dict), f"Stablecoin should be dict, got {type(sc)}"
            assert "name" in sc, f"Stablecoin missing 'name': {sc}"
            assert "symbol" in sc, f"Stablecoin missing 'symbol': {sc}"
            assert "circulating" in sc, f"Stablecoin missing 'circulating': {sc}"
            circ = sc["circulating"]
            assert isinstance(circ, dict), f"circulating should be dict, got {type(circ)}"
            assert "peggedUSD" in circ, f"circulating missing 'peggedUSD': {sc}"
            found = True
            break

        assert found, "Could not find a stablecoin with valid circulating.peggedUSD structure"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestDexScreenerSchema:
    """Schema validation for DexScreener /token-profiles/latest/v1 endpoint."""

    @pytest.mark.asyncio
    async def test_dexscreener_latest_schema(self):
        """GET api.dexscreener.com/token-profiles/latest/v1 → list with chainId, tokenAddress."""
        async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
            async with session.get(DEXSCREENER_LATEST) as resp:
                assert resp.status == 200, f"Expected 200, got {resp.status}"
                data = await resp.json()

        assert isinstance(data, list), f"Expected list, got {type(data)}"
        # The endpoint may return empty list, but should be a list
        if len(data) > 0:
            token = data[0]
            assert "chainId" in token, f"Token missing 'chainId': {token}"
            assert "tokenAddress" in token, f"Token missing 'tokenAddress': {token}"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestJupiterQuoteSchema:
    """Schema validation for Jupiter quote API."""

    @pytest.mark.asyncio
    async def test_jupiter_quote_schema(self):
        """GET quote-api.jup.ag/v6/quote (SOL→USDC) → inAmount, outAmount, routePlan."""
        try:
            async with aiohttp.ClientSession(timeout=API_TIMEOUT) as session:
                async with session.get(JUPITER_QUOTE) as resp:
                    assert resp.status == 200, f"Expected 200, got {resp.status}"
                    data = await resp.json()
        except aiohttp.ClientConnectorDNSError as e:
            pytest.skip(f"Jupiter API unreachable (DNS failure): {e}")
        except aiohttp.ClientConnectorError as e:
            pytest.skip(f"Jupiter API unreachable (connection error): {e}")

        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "inAmount" in data, f"Quote missing 'inAmount': {data}"
        assert "outAmount" in data, f"Quote missing 'outAmount': {data}"
        assert "routePlan" in data, f"Quote missing 'routePlan': {data}"


# ===========================================================================
# END-TO-END SCAN TESTS
# These tests call the actual live_scans.py functions and verify output.
# ===========================================================================

@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestYieldHunterE2E:
    """End-to-end test for yield_hunter()."""

    @pytest.mark.asyncio
    async def test_yield_hunter_e2e(self):
        """yield_hunter() output contains 'YIELD HUNTER', emoji, and mentions APY."""
        result = await yield_hunter()

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result) > 0, "yield_hunter returned empty string"
        assert "YIELD HUNTER" in result, f"Output missing 'YIELD HUNTER': {result[:200]}"
        assert "🔥" in result or "📊" in result, f"Output missing emoji: {result[:200]}"
        assert "APY" in result or "apy" in result.lower(), f"Output mentions APY: {result[:200]}"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestTVLPulseE2E:
    """End-to-end test for tvl_pulse()."""

    @pytest.mark.asyncio
    async def test_tvl_pulse_e2e(self):
        """tvl_pulse() output contains 'TVL PULSE' and 'Total DeFi TVL'."""
        result = await tvl_pulse()

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result) > 0, "tvl_pulse returned empty string"
        assert "TVL PULSE" in result, f"Output missing 'TVL PULSE': {result[:200]}"
        assert "Total DeFi TVL" in result, f"Output missing 'Total DeFi TVL': {result[:200]}"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestStablecoinWatchE2E:
    """End-to-end test for stablecoin_watch()."""

    @pytest.mark.asyncio
    async def test_stablecoin_watch_e2e(self):
        """stablecoin_watch() output contains 'STABLECOIN WATCH' and mentions USDT or USDC."""
        result = await stablecoin_watch()

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result) > 0, "stablecoin_watch returned empty string"
        assert "STABLECOIN WATCH" in result, f"Output missing 'STABLECOIN WATCH': {result[:200]}"
        assert "USDT" in result or "USDC" in result, f"Output mentions USDT or USDC: {result[:200]}"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(15)
class TestTokenRadarE2E:
    """End-to-end test for token_radar()."""

    @pytest.mark.asyncio
    async def test_token_radar_e2e(self):
        """token_radar() output contains 'TOKEN RADAR'."""
        result = await token_radar()

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result) > 0, "token_radar returned empty string"
        assert "TOKEN RADAR" in result, f"Output missing 'TOKEN RADAR': {result[:200]}"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_NETWORK, reason="No network")
@pytest.mark.timeout(30)
class TestAllScansPerformance:
    """Performance test: run_all_scans() completes within 30 seconds."""

    @pytest.mark.asyncio
    async def test_all_scans_complete_under_30s(self):
        """run_all_scans() returns 4 results and completes in under 30 seconds."""
        start = time.monotonic()
        results = await run_all_scans()
        elapsed = time.monotonic() - start

        assert isinstance(results, list), f"Expected list, got {type(results)}"
        assert len(results) == 4, f"Expected 4 scan results, got {len(results)}"
        assert elapsed < 30, f"run_all_scans took {elapsed:.1f}s, expected <30s"

        # Each result should be a non-empty string
        for i, r in enumerate(results):
            assert isinstance(r, str), f"Result {i} should be str, got {type(r)}"
            assert len(r) > 0, f"Result {i} is empty"
