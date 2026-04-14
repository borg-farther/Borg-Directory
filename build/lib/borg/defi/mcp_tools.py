"""
MCP-compatible tool functions wrapping the live scan coroutines.

These are synchronous wrappers that use asyncio.run() internally,
making them safe to call from MCP servers, CLI, or any sync context.

Functions:
    borg_defi_yields   — top yield opportunities from DeFiLlama
    borg_defi_tokens   — latest and boosted tokens from DexScreener
    borg_defi_tvl      — protocol TVL movers from DeFiLlama
    borg_defi_stablecoins — stablecoin peg monitor from DeFiLlama
    borg_defi_scan_all — runs all four scans and returns combined results
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

# aiohttp is an optional dependency — guard at import time
_AIOHTTP_AVAILABLE: bool
try:
    import aiohttp  # noqa: F401
    _AIOHTTP_AVAILABLE = True
except ImportError:
    _AIOHTTP_AVAILABLE = False

from borg.defi.cron.live_scans import (
    yield_hunter,
    token_radar,
    tvl_pulse,
    stablecoin_watch,
    run_all_scans,
)


def _check_aiohttp() -> None:
    """Raise a helpful ImportError if aiohttp is not installed."""
    if not _AIOHTTP_AVAILABLE:
        raise ImportError(
            "aiohttp is required for DeFi scans. Install it with:\n"
            "  pip install agent-borg[defi]\n"
            "  # or\n"
            "  pip install aiohttp>=3.9.0"
        )


def borg_defi_yields(
    min_apy: float = 5.0,
    min_tvl: float = 1_000_000,
    max_results: int = 15,
) -> str:
    """
    Scan DeFiLlama for top yield opportunities.

    Args:
        min_apy: Minimum APY (%) to include a pool. Default: 5.0.
        min_tvl: Minimum TVL (USD) to include a pool. Default: 1_000_000 ($1M).
        max_results: Maximum number of pools to return. Default: 15.

    Returns:
        Formatted alert string with the top yield opportunities,
        sorted by APY descending. Returns an error string on failure.

    Example:
        >>> result = borg_defi_yields(min_apy=10.0, max_results=5)
        >>> print(result)
    """
    _check_aiohttp()
    return asyncio.run(yield_hunter(
        min_tvl=min_tvl,
        min_apy=min_apy,
        max_results=max_results,
    ))


def borg_defi_tokens(max_results: int = 10) -> str:
    """
    Scan DexScreener for latest tokens and boosted/promoted tokens.

    Args:
        max_results: Maximum number of latest tokens to include. Default: 10.

    Returns:
        Formatted alert string with the latest tokens and boosted section.
        Returns an error string on failure.

    Example:
        >>> result = borg_defi_tokens(max_results=5)
        >>> print(result)
    """
    _check_aiohttp()
    return asyncio.run(token_radar(max_results=max_results))


def borg_defi_tvl(max_results: int = 20) -> str:
    """
    Scan DeFiLlama for protocol TVL and biggest movers.

    Args:
        max_results: Maximum number of protocols to show in movers section. Default: 20.

    Returns:
        Formatted alert string with top 10 TVL protocols and biggest 7d movers.
        Returns an error string on failure.

    Example:
        >>> result = borg_defi_tvl(max_results=10)
        >>> print(result)
    """
    _check_aiohttp()
    return asyncio.run(tvl_pulse(max_results=max_results))


def borg_defi_stablecoins(
    depeg_threshold: float = 0.005,
    top_n: int = 10,
) -> str:
    """
    Monitor stablecoin pegs for depeg events.

    Args:
        depeg_threshold: Price deviation from $1.0 (as fraction) to trigger a
            depeg alert. Default: 0.005 (0.5%).
        top_n: Number of top stablecoins by circulating supply to display. Default: 10.

    Returns:
        Formatted alert string listing stablecoins with peg status.
        Returns an error string on failure.

    Example:
        >>> result = borg_defi_stablecoins(depeg_threshold=0.01, top_n=5)
        >>> print(result)
    """
    _check_aiohttp()
    return asyncio.run(stablecoin_watch(
        depeg_threshold=depeg_threshold,
        top_n=top_n,
    ))


def borg_defi_scan_all() -> str:
    """
    Run all four DeFi scans (yields, tokens, TVL, stablecoins) concurrently.

    Returns:
        Combined formatted results from all four scans, separated by
        divider lines. Returns partial results if some scans fail.

    Example:
        >>> result = borg_defi_scan_all()
        >>> print(result)
    """
    _check_aiohttp()
    results = asyncio.run(run_all_scans())
    divider = "\n" + "=" * 60 + "\n"
    return divider.join(results)
