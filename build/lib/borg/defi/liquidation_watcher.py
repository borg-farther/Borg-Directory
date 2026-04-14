"""
Liquidation Watcher for Aave V3 and Compound V3.

Monitors health factors and detects liquidation opportunities on:
- Ethereum
- Arbitrum
- Base
- Optimism

Phase 2 (this module): Detection + alerts only.
Phase 3: Actual liquidation execution.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

import aiohttp

from borg.defi.data_models import Position

logger = logging.getLogger(__name__)


# Default The Graph decentralized network gateway URLs
# These can be overridden by setting environment variables or constructor params
DEFAULT_AAVE_SUBGRAPH_URL = "https://gateway.thegraph.com/api/subgraphs/id/AwmvFzWXY81KpnPCkL3ThKaZxKLYQK5wSrYHXBvMG23H"
DEFAULT_COMPOUND_SUBGRAPH_URL = "https://gateway.thegraph.com/api/subgraphs/id/8wRj2p6m8J8h5dZ9mK3y7nP6oL4kJ6h5gF4eD3cB2aA1"

# Chain configurations for Aave V3 subgraphs on The Graph
# These can be overridden by passing custom URLs to LiquidationWatcher constructor
AAVE_SUBGRAPHS: Dict[str, str] = {
    "ethereum": "https://gateway.thegraph.com/api/subgraphs/id/AwmvFzWXY81KpnPCkL3ThKaZxKLYQK5wSrYHXBvMG23H",
    "arbitrum": "https://gateway.thegraph.com/api/subgraphs/id/7oL5Y7fT3j9k4pX6nK2wR8hM5vB1cF9gE3dA6sL2jK8",
    "base": "https://gateway.thegraph.com/api/subgraphs/id/4zP8m5N2kL6jH3pR9wQ7vF1cB4eD6gA8sL3jK9mP2",
    "optimism": "https://gateway.thegraph.com/api/subgraphs/id/6yH5m8N3kP9jL2pR8wQ4vF1cB6eD9gA3sL7jK5mN4",
}

# Chain configurations for Compound V3 subgraphs on The Graph
COMPOUND_SUBGRAPHS: Dict[str, str] = {
    "ethereum": "https://gateway.thegraph.com/api/subgraphs/id/8wRj2p6m8J8h5dZ9mK3y7nP6oL4kJ6h5gF4eD3cB2aA1",
    "arbitrum": "https://gateway.thegraph.com/api/subgraphs/id/5nP9mL3kJ7h4pX8wQ6vF2cB1eD4gA9sL6jK3mN7pR",
    "base": "https://gateway.thegraph.com/api/subgraphs/id/2kL8mN4pR6jH9wQ3vF7cB5eD1gA8sL4jK6mN3pR9",
    "optimism": "https://gateway.thegraph.com/api/subgraphs/id/9mP7nL5kJ4h8pX3wQ6vF8cB2eD4gA1sL7jK9mN6pR",
}

# Default health factor threshold for liquidation risk
LIQUIDATION_THRESHOLD = 1.1

# Default liquidation bonus (Aave V3 typically 5-10%)
DEFAULT_LIQUIDATION_BONUS = 0.05

# Estimated gas costs per chain (in USD)
GAS_COSTS: Dict[str, float] = {
    "ethereum": 15.0,
    "arbitrum": 2.0,
    "base": 0.50,
    "optimism": 0.50,
}


class Protocol(Enum):
    """Supported DeFi protocols."""
    AAVE_V3 = "aave_v3"
    COMPOUND_V3 = "compound_v3"


@dataclass
class LiquidationTarget:
    """
    Represents a position that may be eligible for liquidation.

    Attributes:
        user_address: The wallet address of the position owner
        protocol: Protocol name (aave_v3 | compound_v3)
        chain: Blockchain network
        health_factor: Health factor (below 1.0 = liquidatable)
        collateral_usd: Total collateral value in USD
        debt_usd: Total debt value in USD
        potential_profit_usd: Estimated gross profit from liquidation
        liquidation_bonus: Bonus percentage received when liquidating
        timestamp: Unix timestamp when data was fetched
        raw_data: Original subgraph data for debugging
    """
    user_address: str
    protocol: str
    chain: str
    health_factor: float
    collateral_usd: float
    debt_usd: float
    potential_profit_usd: float = 0.0
    liquidation_bonus: float = DEFAULT_LIQUIDATION_BONUS
    timestamp: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()

    def is_liquidatable(self) -> bool:
        """Returns True if position can be liquidated (HF < 1.0)."""
        return self.health_factor < 1.0

    def is_at_risk(self) -> bool:
        """Returns True if position is at risk (HF < 1.1)."""
        return self.health_factor < LIQUIDATION_THRESHOLD

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_address": self.user_address,
            "protocol": self.protocol,
            "chain": self.chain,
            "health_factor": round(self.health_factor, 4),
            "collateral_usd": round(self.collateral_usd, 2),
            "debt_usd": round(self.debt_usd, 2),
            "potential_profit_usd": round(self.potential_profit_usd, 2),
            "liquidation_bonus": round(self.liquidation_bonus * 100, 2),
            "timestamp": self.timestamp,
            "is_liquidatable": self.is_liquidatable(),
            "is_at_risk": self.is_at_risk(),
        }


async def query_subgraph(
    subgraph_url: str,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Query a The Graph subgraph endpoint.

    Args:
        subgraph_url: Full URL of the subgraph GraphQL endpoint
        query: GraphQL query string
        variables: Optional query variables

    Returns:
        Parsed JSON response or None on error
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                subgraph_url,
                json={"query": query, "variables": variables or {}},
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "errors" in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return None
                    return data.get("data")
                else:
                    logger.error(f"Subgraph returned status {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Subgraph query failed: {e}")
        return None


def _build_aave_query(max_health_factor: float, first: int = 100, skip: int = 0) -> str:
    """Build GraphQL query for Aave V3 positions."""
    return """
    query GetRiskyPositions($maxHealthFactor: BigDecimal!, $first: Int!, $skip: Int!) {
        users(
            where: {healthFactor_lt: $maxHealthFactor}
            first: $first
            skip: $skip
            orderBy: healthFactor
            orderDirection: asc
        ) {
            id
            healthFactor
            totalCollateralUSD
            totalDebtUSD
            reserves {
                underlyingAsset
                symbol
                liquidityRate
                variableBorrowRate
                currentATokenBalance
                currentVariableDebt
                currentStableDebt
                priceInUSD
            }
        }
    }
    """


def _build_compound_query(max_health_factor: float, first: int = 100, skip: int = 0) -> str:
    """Build GraphQL query for Compound V3 positions."""
    return """
    query GetRiskyPositions($maxHealthFactor: BigDecimal!, $first: Int!, $skip: Int!) {
        accounts(
            where: {healthScore_lt: $maxHealthFactor}
            first: $first
            skip: $skip
            orderBy: healthScore
            orderDirection: asc
        ) {
            id
            healthScore
            totalCollateralValue
            totalDebtValue
            tokens {
                symbol
                tokenAddress
                supplyBalance
                borrowBalance
                market {
                    collateralFactor
                    underlyingPrice
                }
            }
        }
    }
    """


async def scan_aave_positions(
    chain: str = "ethereum",
    health_threshold: float = LIQUIDATION_THRESHOLD,
    limit: int = 100,
) -> List[LiquidationTarget]:
    """
    Scan Aave V3 positions for liquidation opportunities.

    Args:
        chain: Blockchain network (ethereum|arbitrum|base|optimism)
        health_threshold: Health factor threshold (default 1.1)
        limit: Maximum number of positions to return per query

    Returns:
        List of LiquidationTarget objects with at-risk positions
    """
    if chain not in AAVE_SUBGRAPHS:
        logger.warning(f"Unsupported chain for Aave V3: {chain}")
        return []

    subgraph_url = AAVE_SUBGRAPHS[chain]
    targets: List[LiquidationTarget] = []
    skip = 0

    # Paginate through results
    while True:
        query = _build_aave_query(health_threshold, limit, skip)
        variables = {"maxHealthFactor": str(health_threshold), "first": limit, "skip": skip}

        data = await query_subgraph(subgraph_url, query, variables)
        if not data or "users" not in data:
            break

        users = data["users"]
        if not users:
            break

        for user_data in users:
            try:
                hf = float(user_data.get("healthFactor", 0))
                collateral = float(user_data.get("totalCollateralUSD", 0))
                debt = float(user_data.get("totalDebtUSD", 0))

                # Calculate potential profit based on liquidation bonus
                profit = collateral * DEFAULT_LIQUIDATION_BONUS if collateral > 0 else 0

                target = LiquidationTarget(
                    user_address=user_data["id"],
                    protocol=Protocol.AAVE_V3.value,
                    chain=chain,
                    health_factor=hf,
                    collateral_usd=collateral,
                    debt_usd=debt,
                    potential_profit_usd=profit,
                    liquidation_bonus=DEFAULT_LIQUIDATION_BONUS,
                    raw_data=user_data,
                )
                targets.append(target)
            except (ValueError, KeyError) as e:
                logger.debug(f"Skipping malformed Aave user data: {e}")
                continue

        # If we got fewer than limit, we're done
        if len(users) < limit:
            break

        skip += limit
        # Safety cap to avoid infinite loops
        if skip > 1000:
            break

    logger.info(f"Found {len(targets)} at-risk Aave V3 positions on {chain}")
    return targets


async def scan_compound_positions(
    chain: str = "ethereum",
    health_threshold: float = LIQUIDATION_THRESHOLD,
    limit: int = 100,
) -> List[LiquidationTarget]:
    """
    Scan Compound V3 positions for liquidation opportunities.

    Args:
        chain: Blockchain network (ethereum|arbitrum|base|optimism)
        health_threshold: Health score threshold (default 1.1)
            Note: Compound uses healthScore (inverse of health factor)
        limit: Maximum number of positions to return per query

    Returns:
        List of LiquidationTarget objects with at-risk positions
    """
    if chain not in COMPOUND_SUBGRAPHS:
        logger.warning(f"Unsupported chain for Compound V3: {chain}")
        return []

    subgraph_url = COMPOUND_SUBGRAPHS[chain]
    targets: List[LiquidationTarget] = []
    skip = 0

    # Compound V3 uses healthScore which is 1/healthFactor
    # So HF < 1.1 becomes healthScore < 0.909...
    compound_threshold = 1.0 / health_threshold if health_threshold > 0 else 0.909

    while True:
        query = _build_compound_query(compound_threshold, limit, skip)
        variables = {"maxHealthFactor": str(compound_threshold), "first": limit, "skip": skip}

        data = await query_subgraph(subgraph_url, query, variables)
        if not data or "accounts" not in data:
            break

        accounts = data["accounts"]
        if not accounts:
            break

        for account_data in accounts:
            try:
                # Compound V3 healthScore = 1 / healthFactor
                health_score = float(account_data.get("healthScore", 0))
                hf = 1.0 / health_score if health_score > 0 else float("inf")

                collateral = float(account_data.get("totalCollateralValue", 0))
                debt = float(account_data.get("totalDebtValue", 0))

                # Compound V3 liquidation bonus is typically 8%
                compound_bonus = 0.08
                profit = collateral * compound_bonus if collateral > 0 else 0

                target = LiquidationTarget(
                    user_address=account_data["id"],
                    protocol=Protocol.COMPOUND_V3.value,
                    chain=chain,
                    health_factor=hf,
                    collateral_usd=collateral,
                    debt_usd=debt,
                    potential_profit_usd=profit,
                    liquidation_bonus=compound_bonus,
                    raw_data=account_data,
                )
                targets.append(target)
            except (ValueError, KeyError, ZeroDivisionError) as e:
                logger.debug(f"Skipping malformed Compound user data: {e}")
                continue

        if len(accounts) < limit:
            break

        skip += limit
        if skip > 1000:
            break

    logger.info(f"Found {len(targets)} at-risk Compound V3 positions on {chain}")
    return targets


async def scan_all_positions(
    chains: Optional[List[str]] = None,
    health_threshold: float = LIQUIDATION_THRESHOLD,
) -> List[LiquidationTarget]:
    """
    Scan all supported chains for both Aave V3 and Compound V3 positions.

    Args:
        chains: List of chains to scan (default: all supported)
        health_threshold: Health factor threshold

    Returns:
        Combined list of all at-risk positions
    """
    if chains is None:
        chains = list(AAVE_SUBGRAPHS.keys())

    all_targets: List[LiquidationTarget] = []

    # Scan all chains and protocols concurrently
    tasks = []
    for chain in chains:
        tasks.append(scan_aave_positions(chain, health_threshold))
        tasks.append(scan_compound_positions(chain, health_threshold))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_targets.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Scanning error: {result}")

    # Sort by potential profit (descending)
    all_targets.sort(key=lambda t: t.potential_profit_usd, reverse=True)

    return all_targets


def estimate_liquidation_profit(
    target: LiquidationTarget,
    gas_price_gwei: Optional[float] = None,
    eth_price_usd: float = 2000.0,
    gas_limit: int = 500000,
) -> Dict[str, Any]:
    """
    Estimate the actual profit from liquidating a position.

    Args:
        target: The LiquidationTarget to evaluate
        gas_price_gwei: Current gas price in Gwei (auto-lookup if None)
        eth_price_usd: ETH price in USD for gas cost conversion
        gas_limit: Estimated gas limit for liquidation tx

    Returns:
        Dict with profit estimates:
            - gross_profit_usd: Profit before gas costs
            - gas_cost_usd: Estimated gas cost in USD
            - net_profit_usd: Profit after gas costs
            - roi_percent: Return on investment percentage
            - is_profitable: True if net profit > 0
    """
    chain = target.chain
    gas_cost = GAS_COSTS.get(chain, GAS_COSTS["ethereum"])

    # If gas price provided, calculate actual cost
    if gas_price_gwei is not None:
        # Convert gas to ETH: (gas_limit * gas_price_gwei) / 1e9
        gas_eth = (gas_limit * gas_price_gwei) / 1e9
        gas_cost = gas_eth * eth_price_usd

    gross_profit = target.potential_profit_usd
    net_profit = gross_profit - gas_cost

    # Calculate ROI based on debt size (typical flash loan requirement)
    # Liquidator needs to repay target.debt_usd to receive collateral
    debt_for_liquidation = target.debt_usd
    roi = (net_profit / debt_for_liquidation * 100) if debt_for_liquidation > 0 else 0

    return {
        "gross_profit_usd": round(gross_profit, 2),
        "gas_cost_usd": round(gas_cost, 2),
        "net_profit_usd": round(net_profit, 2),
        "roi_percent": round(roi, 4),
        "is_profitable": net_profit > 0,
        "target_address": target.user_address,
        "chain": chain,
        "protocol": target.protocol,
        "health_factor": round(target.health_factor, 4),
        "collateral_usd": round(target.collateral_usd, 2),
        "debt_usd": round(target.debt_usd, 2),
    }


def format_alert(
    target: LiquidationTarget,
    profit_estimate: Optional[Dict[str, Any]] = None,
    format: str = "telegram",
) -> str:
    """
    Format a liquidation alert for Telegram or Discord.

    Args:
        target: The LiquidationTarget to alert about
        profit_estimate: Optional pre-calculated profit estimate
        format: Message format ('telegram' or 'discord')

    Returns:
        Formatted alert message string
    """
    if profit_estimate is None:
        profit_estimate = estimate_liquidation_profit(target)

    is_profitable = profit_estimate.get("is_profitable", False)
    profit_emoji = "💰" if is_profitable else "⚠️"

    if format == "telegram":
        # Telegram format with HTML-like styling
        header = f"{profit_emoji} <b>LIQUIDATION OPPORTUNITY</b> {profit_emoji}\n"
        header += f"{'━' * 40}\n\n"

        details = [
            f"<b>Protocol:</b> {target.protocol.upper()}",
            f"<b>Chain:</b> {target.chain.capitalize()}",
            f"<b>User:</b> <code>{target.user_address[:8]}...{target.user_address[-6:]}</code>",
            f"<b>Health Factor:</b> <code>{target.health_factor:.4f}</code>",
            f"",
            f"<b>Collateral:</b> ${target.collateral_usd:,.2f}",
            f"<b>Debt:</b> ${target.debt_usd:,.2f}",
            f"<b>Liquidation Bonus:</b> {target.liquidation_bonus * 100:.1f}%",
            f"",
            f"<b>Potential Profit:</b> ${profit_estimate.get('gross_profit_usd', 0):,.2f}",
            f"<b>Est. Gas Cost:</b> ${profit_estimate.get('gas_cost_usd', 0):,.2f}",
            f"<b>Net Profit:</b> ${profit_estimate.get('net_profit_usd', 0):,.2f}",
            f"<b>ROI:</b> {profit_estimate.get('roi_percent', 0):.4f}%",
        ]

        footer = f"\n{'━' * 40}\n"
        if is_profitable:
            footer += "✅ <b>PROFITABLE</b> - Ready for liquidation"
        else:
            footer += "❌ <b>NOT PROFITABLE</b> - Gas costs too high"

        return header + "\n".join(details) + footer

    else:
        # Discord format with markdown
        header = f"{profit_emoji} **LIQUIDATION OPPORTUNITY** {profit_emoji}\n"
        header += f"{'─' * 40}\n"

        details = [
            f"**Protocol:** {target.protocol.upper()}",
            f"**Chain:** {target.chain.capitalize()}",
            f"**User:** `{target.user_address[:8]}...{target.user_address[-6:]}`",
            f"**Health Factor:** `{target.health_factor:.4f}`",
            f"",
            f"**Collateral:** ${target.collateral_usd:,.2f}",
            f"**Debt:** ${target.debt_usd:,.2f}",
            f"**Liquidation Bonus:** {target.liquidation_bonus * 100:.1f}%",
            f"",
            f"**Potential Profit:** ${profit_estimate.get('gross_profit_usd', 0):,.2f}",
            f"**Est. Gas Cost:** ${profit_estimate.get('gas_cost_usd', 0):,.2f}",
            f"**Net Profit:** ${profit_estimate.get('net_profit_usd', 0):,.2f}",
            f"**ROI:** {profit_estimate.get('roi_percent', 0):.4f}%",
        ]

        footer = f"\n{'─' * 40}\n"
        if is_profitable:
            footer += "✅ **PROFITABLE** - Ready for liquidation"
        else:
            footer += "❌ **NOT PROFITABLE** - Gas costs too high"

        return header + "\n".join(details) + footer


async def run_watcher(
    chains: Optional[List[str]] = None,
    health_threshold: float = LIQUIDATION_THRESHOLD,
    min_profit_usd: float = 0.0,
    alert_callback: Optional[callable] = None,
    scan_interval: int = 300,
) -> None:
    """
    Run the liquidation watcher as a continuous background task.

    Args:
        chains: List of chains to monitor
        health_threshold: Health factor threshold for alerts
        min_profit_usd: Minimum profit threshold for alerts
        alert_callback: Async function(target, profit_estimate) to call for each alert
        scan_interval: Seconds between scans (default 5 minutes)
    """
    logger.info(f"Starting liquidation watcher (interval: {scan_interval}s)")

    while True:
        try:
            targets = await scan_all_positions(chains, health_threshold)

            for target in targets:
                profit = estimate_liquidation_profit(target)

                if profit["net_profit_usd"] >= min_profit_usd:
                    logger.info(
                        f"Liquidatable: {target.protocol} on {target.chain} | "
                        f"HF={target.health_factor:.4f} | "
                        f"Profit=${profit['net_profit_usd']:.2f}"
                    )

                    if alert_callback:
                        await alert_callback(target, profit)

        except Exception as e:
            logger.error(f"Watcher error: {e}")

        await asyncio.sleep(scan_interval)


# --- Cron Integration ---

CRON_TEMPLATE = """# Liquidation Watcher - runs every {interval} minutes
# Add to crontab: crontab -e

# Scan for Aave/Compound liquidation opportunities
{interval} * * * * cd {cwd} && python -m borg.defi.liquidation_watcher --scan >> /var/log/liquidation_watcher.log 2>&1
"""


def generate_cron_entry(interval_minutes: int = 5, cwd: str = ".") -> str:
    """
    Generate a crontab entry for periodic liquidation scanning.

    Args:
        interval_minutes: How often to run the scan
        cwd: Working directory for the script

    Returns:
        Cron entry string
    """
    return CRON_TEMPLATE.format(interval=f"*/{interval_minutes}", cwd=cwd)


async def main():
    """CLI entry point for manual scanning."""
    import argparse

    parser = argparse.ArgumentParser(description="Liquidation Watcher")
    parser.add_argument(
        "--chains",
        nargs="+",
        default=["ethereum", "arbitrum", "base", "optimism"],
        help="Chains to scan",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=LIQUIDATION_THRESHOLD,
        help="Health factor threshold",
    )
    parser.add_argument(
        "--min-profit",
        type=float,
        default=0.0,
        help="Minimum profit threshold in USD",
    )
    parser.add_argument(
        "--format",
        choices=["telegram", "discord"],
        default="telegram",
        help="Alert format",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Run a single scan and exit",
    )

    args = parser.parse_args()

    if args.scan:
        targets = await scan_all_positions(args.chains, args.threshold)

        if not targets:
            print("No at-risk positions found.")
            return

        print(f"\nFound {len(targets)} at-risk positions:\n")

        for target in targets:
            profit = estimate_liquidation_profit(target)
            print(format_alert(target, profit, args.format))
            print()
    else:
        # Run continuous watcher
        await run_watcher(
            chains=args.chains,
            health_threshold=args.threshold,
            min_profit_usd=args.min_profit,
        )


if __name__ == "__main__":
    asyncio.run(main())
