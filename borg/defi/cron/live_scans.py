"""
Live DeFi scan functions — zero-config, free APIs only.

These hit DeFiLlama and DexScreener (no auth needed) and return
formatted alert strings ready for Telegram/Discord delivery.

Usage:
    alerts = await yield_hunter()
    alerts = await token_radar()
    alerts = await tvl_pulse()
    alerts = await stablecoin_watch()
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)

DEFILLAMA_YIELDS = "https://yields.llama.fi/pools"
DEFILLAMA_PROTOCOLS = "https://api.llama.fi/protocols"
DEFILLAMA_STABLECOINS = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
DEXSCREENER_LATEST = "https://api.dexscreener.com/token-profiles/latest/v1"
DEXSCREENER_BOOSTED = "https://api.dexscreener.com/token-boosts/latest/v1"

# Timeout for API calls
TIMEOUT = aiohttp.ClientTimeout(total=20)


_TRANSITORIES = (
    aiohttp.ClientConnectorError,
    aiohttp.ServerTimeoutError,
    aiohttp.ClientTimeout,
    asyncio.TimeoutError,
)


async def _fetch_json(url: str, session: Optional[aiohttp.ClientSession] = None, retries: int = 2) -> dict:
    """Fetch JSON from URL with retry on transient failures.

    Args:
        url: The URL to fetch.
        session: Optional existing session ( caller manages lifecycle ).
        retries: Number of retry attempts on connection/timeout errors.

    Raises:
        aiohttp.ClientResponseError: On HTTP 4xx/5xx after exhausting retries.
        aiohttp.ClientError: On unresolved connection errors.
    """
    close_session = False
    if session is None:
        session = aiohttp.ClientSession(timeout=TIMEOUT)
        close_session = True
    last_error: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            # Only retry transient errors (connection/timeouts); re-raise HTTP errors immediately
            if attempt < retries and _is_transient(e):
                last_error = e
                await asyncio.sleep(0.5 * (attempt + 1))
                continue
            # Either out of retries or a non-transient error — re-raise
            if isinstance(e, aiohttp.ClientError):
                raise
            # Other exceptions (ValueError from bad JSON, etc.) — wrap and raise
            raise aiohttp.ClientError(str(e)) from e
    # Retries exhausted (should not reach here if we raise above)
    raise last_error or RuntimeError(f"Failed to fetch {url} after {retries} retries")


def _is_transient(e: BaseException) -> bool:
    """Return True if this exception is a transient network error worth retrying."""
    return (
        isinstance(e, _TRANSITORIES)
        or (
            isinstance(e, aiohttp.ClientError)
            and not isinstance(e, aiohttp.ClientResponseError)
        )
    )


# ---------------------------------------------------------------------------
# 1. YIELD HUNTER — top yield opportunities, every 2h
# ---------------------------------------------------------------------------

async def yield_hunter(
    min_tvl: float = 1_000_000,
    min_apy: float = 5.0,
    max_results: int = 15,
    degen_threshold: float = 100.0,
) -> str:
    """
    Scan DeFiLlama for top yield opportunities.

    Returns formatted alert string.
    """
    try:
        data = await _fetch_json(DEFILLAMA_YIELDS)
        pools = data.get("data", []) if isinstance(data, dict) else []
        if not isinstance(pools, list):
            pools = []

        # Filter: real TVL, positive APY, not stablecoin-only boring stuff
        filtered = [
            p for p in pools
            if isinstance(p, dict)
            and (p.get("tvlUsd") or 0) >= min_tvl
            and (p.get("apy") or 0) >= min_apy
            and p.get("project")
            and p.get("symbol")
        ]

        # Sort by APY descending
        top = sorted(filtered, key=lambda x: x.get("apy", 0), reverse=True)[:max_results]

        if not top:
            return "No yield opportunities found matching criteria."

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"📈 YIELD HUNTER — {now}\n"]

        for i, p in enumerate(top, 1):
            apy = p.get("apy", 0)
            tvl = p.get("tvlUsd", 0)
            project = p.get("project", "?")
            chain = p.get("chain", "?")
            symbol = p.get("symbol", "?")
            apy_7d = p.get("apyMean7d", 0) or 0
            il_risk = p.get("ilRisk", "none")

            # Emoji coding
            if apy >= 500:
                emoji = "🔥🔥🔥"
                tag = " [DEGEN]"
            elif apy >= degen_threshold:
                emoji = "🔥🔥"
                tag = " [HIGH]"
            elif apy >= 20:
                emoji = "🔥"
                tag = ""
            else:
                emoji = "📊"
                tag = ""

            # IL warning
            il_warn = " ⚠️IL" if il_risk not in ("none", "no", None, "") else ""

            lines.append(
                f"{i}. {emoji} {project} | {chain}\n"
                f"   {symbol} — APY: {apy:.1f}%{tag}{il_warn}\n"
                f"   TVL: ${tvl/1e6:.1f}M | 7d avg: {apy_7d:.1f}%"
            )

        # Summary stats
        avg_apy = sum(p.get("apy", 0) for p in top) / len(top)
        total_tvl = sum(p.get("tvlUsd", 0) for p in top)
        degen_count = sum(1 for p in top if (p.get("apy", 0) or 0) >= degen_threshold)

        lines.append(f"\n💰 Avg APY: {avg_apy:.1f}% | Total TVL: ${total_tvl/1e6:.0f}M | Degen pools: {degen_count}")
        lines.append(f"📡 Source: DeFiLlama ({len(pools):,} pools scanned)")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"yield_hunter error: {e}")
        return f"⚠️ Yield Hunter error: {e}"


# ---------------------------------------------------------------------------
# 2. TOKEN RADAR — new tokens and trending, every 5min
# ---------------------------------------------------------------------------

async def token_radar(max_results: int = 10) -> str:
    """
    Scan DexScreener for latest and boosted tokens.

    Returns formatted alert string.
    """
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            latest_data, boosted_data = await asyncio.gather(
                _fetch_json(DEXSCREENER_LATEST, session),
                _fetch_json(DEXSCREENER_BOOSTED, session),
                return_exceptions=True,
            )

        now = datetime.now(timezone.utc).strftime("%H:%M UTC")
        lines = [f"🔭 TOKEN RADAR — {now}\n"]

        # Latest tokens — if latest endpoint fails, log and show boosted only
        if isinstance(latest_data, Exception):
            logger.warning("token_radar: latest endpoint failed: %s", latest_data)
            latest = []
        elif isinstance(latest_data, list):
            latest = latest_data[:max_results]
        elif isinstance(latest_data, dict):
            latest = latest_data.get("data", latest_data.get("tokens", []))[:max_results]
        else:
            latest = []

        if latest:
            lines.append("🆕 LATEST TOKENS:")
            seen_chains = {}
            for t in latest:
                if not isinstance(t, dict):
                    continue
                chain = t.get("chainId", "?")
                addr = t.get("tokenAddress", "?")
                url = t.get("url", "")
                desc = t.get("description", "")[:60] if t.get("description") else ""

                short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr
                lines.append(f"  ⚡ {chain} | {short_addr}")
                if desc:
                    lines.append(f"     {desc}")
                seen_chains[chain] = seen_chains.get(chain, 0) + 1

            chain_summary = ", ".join(f"{c}:{n}" for c, n in sorted(seen_chains.items(), key=lambda x: -x[1]))
            lines.append(f"  Chains: {chain_summary}")

        # Boosted tokens (paid promotion — worth watching)
        if isinstance(boosted_data, list) and boosted_data:
            boosted = boosted_data[:5]
            lines.append("\n🚀 BOOSTED (promoted):")
            for t in boosted:
                chain = t.get("chainId", "?")
                addr = t.get("tokenAddress", "?")
                amount = t.get("amount", 0)
                short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr
                lines.append(f"  💎 {chain} | {short_addr} | boost: ${amount}")

        lines.append(f"\n📡 Source: DexScreener")
        return "\n".join(lines)

    except Exception as e:
        logger.error(f"token_radar error: {e}")
        return f"⚠️ Token Radar error: {e}"


# ---------------------------------------------------------------------------
# 3. TVL PULSE — protocol TVL movers, every 6h
# ---------------------------------------------------------------------------

async def tvl_pulse(max_results: int = 20) -> str:
    """
    Scan DeFiLlama for TVL movements — biggest movers first.

    Returns formatted alert string.
    """
    try:
        data = await _fetch_json(DEFILLAMA_PROTOCOLS)

        # Filter to real protocols with TVL
        raw_protocols = data if isinstance(data, list) else data.get("data", [])
        protocols = [
            p for p in raw_protocols
            if isinstance(p, dict)
            and (p.get("tvl") or 0) > 10_000_000
            and p.get("name")
        ]

        # Sort by 7d change (biggest movers)
        protocols_with_change = [
            p for p in protocols if p.get("change_7d") is not None
        ]
        movers = sorted(
            protocols_with_change,
            key=lambda x: abs(x.get("change_7d", 0) or 0),
            reverse=True
        )[:max_results]

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines = [f"📊 TVL PULSE — {now}\n"]

        # Top 10 by TVL
        top_tvl = sorted(protocols, key=lambda x: x.get("tvl", 0) or 0, reverse=True)[:10]
        lines.append("🏆 TOP 10 BY TVL:")
        for i, p in enumerate(top_tvl, 1):
            tvl = p.get("tvl", 0) or 0
            change_1d = p.get("change_1d", 0) or 0
            change_7d = p.get("change_7d", 0) or 0
            name = p.get("name", "?")

            # Trend emoji
            if change_7d > 10:
                trend = "🟢📈"
            elif change_7d > 0:
                trend = "🟢"
            elif change_7d > -10:
                trend = "🔴"
            else:
                trend = "🔴📉"

            if tvl >= 1e9:
                tvl_str = f"${tvl/1e9:.1f}B"
            else:
                tvl_str = f"${tvl/1e6:.0f}M"

            lines.append(f"  {i:2d}. {trend} {name:20s} | {tvl_str:>8s} | 24h:{change_1d:+.1f}% | 7d:{change_7d:+.1f}%")

        # Biggest movers section
        lines.append("\n🔄 BIGGEST 7D MOVERS:")
        gainers = [p for p in movers if (p.get("change_7d", 0) or 0) > 5][:5]
        losers = [p for p in movers if (p.get("change_7d", 0) or 0) < -5][:5]

        if gainers:
            lines.append("  📈 GAINERS:")
            for p in gainers:
                tvl = p.get("tvl", 0) or 0
                change = p.get("change_7d", 0) or 0
                name = p.get("name", "?")
                tvl_str = f"${tvl/1e6:.0f}M" if tvl < 1e9 else f"${tvl/1e9:.1f}B"
                lines.append(f"    🟢 {name:20s} | {tvl_str:>8s} | {change:+.1f}%")

        if losers:
            lines.append("  📉 LOSERS:")
            for p in losers:
                tvl = p.get("tvl", 0) or 0
                change = p.get("change_7d", 0) or 0
                name = p.get("name", "?")
                tvl_str = f"${tvl/1e6:.0f}M" if tvl < 1e9 else f"${tvl/1e9:.1f}B"
                lines.append(f"    🔴 {name:20s} | {tvl_str:>8s} | {change:+.1f}%")

        total_tvl = sum(p.get("tvl", 0) or 0 for p in protocols)
        lines.append(f"\n💰 Total DeFi TVL: ${total_tvl/1e9:.1f}B across {len(protocols)} protocols")
        lines.append(f"📡 Source: DeFiLlama")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"tvl_pulse error: {e}")
        return f"⚠️ TVL Pulse error: {e}"


# ---------------------------------------------------------------------------
# 4. STABLECOIN WATCH — depeg alerts, every 30min
# ---------------------------------------------------------------------------

async def stablecoin_watch(
    depeg_threshold: float = 0.005,  # 0.5% from peg
    top_n: int = 10,
) -> str:
    """
    Monitor stablecoin pegs and supply changes.

    Returns formatted alert string. Alerts on depeg events.
    """
    try:
        data = await _fetch_json(DEFILLAMA_STABLECOINS)
        stables = data.get("peggedAssets", []) if isinstance(data, dict) else []

        # Sort by circulating supply
        stables_sorted = sorted(
            [s for s in stables if isinstance(s, dict)],
            key=lambda x: (x.get("circulating", {}).get("peggedUSD", 0) or 0)
            if isinstance(x.get("circulating"), dict) else 0,
            reverse=True,
        )[:top_n]

        now = datetime.now(timezone.utc).strftime("%H:%M UTC")
        lines = [f"💵 STABLECOIN WATCH — {now}\n"]

        total_supply = 0
        depeg_alerts = []

        for s in stables_sorted:
            if not isinstance(s, dict):
                continue
            name = s.get("name", "?")
            symbol = s.get("symbol", "?")
            circulating = s.get("circulating", {})
            supply = circulating.get("peggedUSD", 0) or 0 if isinstance(circulating, dict) else 0
            price = s.get("price", None)
            total_supply += supply

            supply_str = f"${supply/1e9:.1f}B" if supply >= 1e9 else f"${supply/1e6:.0f}M"

            if price is not None:
                deviation = abs(price - 1.0)
                price_str = f"${price:.4f}"

                if deviation > depeg_threshold:
                    # DEPEG ALERT
                    direction = "above" if price > 1.0 else "below"
                    depeg_alerts.append(f"🚨 {name} ({symbol}) DEPEGGED — ${price:.4f} ({deviation*100:.2f}% {direction} peg)")
                    emoji = "🚨"
                elif deviation > 0.001:
                    emoji = "⚠️"
                else:
                    emoji = "✅"

                lines.append(f"  {emoji} {name:15s} | {symbol:6s} | {supply_str:>8s} | {price_str}")
            else:
                lines.append(f"  ❓ {name:15s} | {symbol:6s} | {supply_str:>8s} | price N/A")

        # Depeg alerts at the top if any
        if depeg_alerts:
            alert_section = "\n".join(depeg_alerts)
            lines.insert(1, f"\n{'='*40}\n{alert_section}\n{'='*40}\n")

        lines.append(f"\n💰 Total stablecoin supply: ${total_supply/1e9:.1f}B")
        lines.append(f"📡 Source: DeFiLlama ({len(stables)} stablecoins tracked)")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"stablecoin_watch error: {e}")
        return f"⚠️ Stablecoin Watch error: {e}"


# ---------------------------------------------------------------------------
# Run all scans (for testing)
# ---------------------------------------------------------------------------

async def run_all_scans() -> List[str]:
    """Run all 4 scans and return results."""
    results = await asyncio.gather(
        yield_hunter(),
        token_radar(),
        tvl_pulse(),
        stablecoin_watch(),
        return_exceptions=True,
    )
    return [str(r) for r in results]


if __name__ == "__main__":
    async def main():
        results = await run_all_scans()
        for r in results:
            print(r)
            print("\n" + "=" * 60 + "\n")

    asyncio.run(main())
