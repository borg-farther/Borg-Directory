"""
Concentrated Liquidity Position Manager.

Supports:
  - Uniswap V3 (EVM chains: ethereum, arbitrum, base, polygon, etc.)
  - Orca Whirlpools (Solana)

Price data via DexScreener (free, no auth).

Functions:
    LPPosition              — Dataclass tracking range, liquidity, fees, IL
    monitor_positions()     — Check if current price is within LP range
    calculate_il()          — Impermanent loss estimation
    suggest_rebalance()     — Suggest rebalancing when price exits range
    track_fees()            — Monitor fee accumulation
    format_lp_report()      — Daily LP performance report
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Enums & Constants
# ---------------------------------------------------------------------------

class Protocol(Enum):
    UNISWAP_V3 = "uniswap_v3"
    ORCA_WHIRLPOOLS = "orca_whirlpools"


class Chain(Enum):
    ETHEREUM = "ethereum"
    ARBITRUM = "arbitrum"
    BASE = "base"
    POLYGON = "polygon"
    BSC = "bsc"
    SOLANA = "solana"


class PositionStatus(Enum):
    IN_RANGE = "in_range"
    OUT_OF_RANGE_ABOVE = "out_of_range_above"  # price above upper bound
    OUT_OF_RANGE_BELOW = "out_of_range_below"   # price below lower bound
    NOT_INITIALIZED = "not_initialized"


# ---------------------------------------------------------------------------
# LPPosition Dataclass
# ---------------------------------------------------------------------------

@dataclass
class LPPosition:
    """
    Concentrated liquidity position.

    Attributes:
        protocol: Protocol (uniswap_v3 | orca_whirlpools)
        chain: Blockchain network
        pair_address: Pool/pair contract address
        token0: Token0 symbol (e.g. ETH)
        token1: Token1 symbol (e.g. USDC)
        token0_address: Token0 contract address
        token1_address: Token1 contract address

        # Range (price in USD, quote token = token1)
        lower_price: Lower bound of price range (token1 per token0)
        upper_price: Upper bound of price range (token1 per token0)

        # Liquidity
        liquidity: Virtual liquidity units (protocol-specific)
        amount0: Token0 amount deposited
        amount1: Token1 amount deposited
        value_usd: Total USD value of position

        # Fee tracking
        fees_earned_token0: Cumulative token0 fees
        fees_earned_token1: Cumulative token1 fees
        fees_earned_usd: Estimated USD value of earned fees
        last_fee_update: Unix timestamp of last fee update

        # IL tracking
        il_estimate_usd: Estimated impermanent loss in USD
        il_pct: IL as percentage of hodl value
        last_il_check: Unix timestamp of last IL calculation

        # Metadata
        position_id: Protocol-specific position ID (tokenId for Uni, position mint for Orca)
        opened_at: Unix timestamp when position was opened
        last_monitored: Unix timestamp of last price check
        status: Current position status
    """
    protocol: str
    chain: str
    pair_address: str
    token0: str
    token1: str
    token0_address: str = ""
    token1_address: str = ""

    # Price range (token1 per token0)
    lower_price: float = 0.0
    upper_price: float = 0.0

    # Liquidity
    liquidity: float = 0.0
    amount0: float = 0.0
    amount1: float = 0.0
    value_usd: float = 0.0

    # Fee tracking
    fees_earned_token0: float = 0.0
    fees_earned_token1: float = 0.0
    fees_earned_usd: float = 0.0
    last_fee_update: float = 0.0

    # IL tracking
    il_estimate_usd: float = 0.0
    il_pct: float = 0.0
    last_il_check: float = 0.0

    # Metadata
    position_id: str = ""
    opened_at: float = 0.0
    last_monitored: float = 0.0
    status: str = PositionStatus.NOT_INITIALIZED.value

    def __post_init__(self):
        if self.opened_at == 0.0:
            self.opened_at = datetime.now().timestamp()
        if self.last_monitored == 0.0:
            self.last_monitored = datetime.now().timestamp()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "chain": self.chain,
            "pair_address": self.pair_address,
            "token0": self.token0,
            "token1": self.token1,
            "token0_address": self.token0_address,
            "token1_address": self.token1_address,
            "lower_price": self.lower_price,
            "upper_price": self.upper_price,
            "liquidity": self.liquidity,
            "amount0": self.amount0,
            "amount1": self.amount1,
            "value_usd": self.value_usd,
            "fees_earned_token0": self.fees_earned_token0,
            "fees_earned_token1": self.fees_earned_token1,
            "fees_earned_usd": self.fees_earned_usd,
            "last_fee_update": self.last_fee_update,
            "il_estimate_usd": self.il_estimate_usd,
            "il_pct": self.il_pct,
            "last_il_check": self.last_il_check,
            "position_id": self.position_id,
            "opened_at": self.opened_at,
            "last_monitored": self.last_monitored,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# Uniswap V3 Position (from on-chain / indexer data)
# ---------------------------------------------------------------------------

@dataclass
class UniswapV3Position:
    """
    Uniswap V3 position data (tokenId-level).

    Attributes:
        token_id: NFT token ID
        owner: Owner wallet address
        tick_lower: Lower tick index
        tick_upper: Upper tick index
        liquidity: Virtual liquidity amount
        fee_growth_inside_last: Fee growth inside (for fee calculation)
        tokens_owed0: Collected token0 fees owed
        tokens_owed1: Collected token1 fees owed
    """
    token_id: int
    owner: str
    tick_lower: int
    tick_upper: int
    liquidity: int
    fee_growth_inside_last: int = 0
    tokens_owed0: int = 0
    tokens_owed1: int = 0

    def to_lp_position(self, pair_data: Dict[str, Any]) -> LPPosition:
        """Convert to generic LPPosition."""
        current_tick = pair_data.get("current_tick", 0)
        # Convert ticks to price: price = 1.0001^tick
        lower_price = 1.0001 ** self.tick_lower
        upper_price = 1.0001 ** self.tick_upper
        return LPPosition(
            protocol=Protocol.UNISWAP_V3.value,
            chain=pair_data.get("chain", "ethereum"),
            pair_address=pair_data.get("pair_address", ""),
            token0=pair_data.get("token0", ""),
            token1=pair_data.get("token1", ""),
            token0_address=pair_data.get("token0_address", ""),
            token1_address=pair_data.get("token1_address", ""),
            lower_price=lower_price,
            upper_price=upper_price,
            liquidity=float(self.liquidity),
            position_id=str(self.token_id),
            status=_tick_to_status(current_tick, self.tick_lower, self.tick_upper),
        )


# ---------------------------------------------------------------------------
# Orca Whirlpool Position
# ---------------------------------------------------------------------------

@dataclass
class OrcaWhirlpoolPosition:
    """
    Orca Whirlpool position data.

    Attributes:
        position_mint: SPL Token mint for the position
        whirlpool: Whirlpool address
        tick_lower_index: Lower tick index
        tick_upper_index: Upper tick index
        liquidity: Liquidity amount
        fee_owed0: Token0 fees owed
        fee_owed1: Token1 fees owed
    """
    position_mint: str
    whirlpool: str
    tick_lower_index: int
    tick_upper_index: int
    liquidity: int
    fee_owed0: int = 0
    fee_owed1: int = 0

    def to_lp_position(self, pair_data: Dict[str, Any]) -> LPPosition:
        """Convert to generic LPPosition using whirlpool tick spacing."""
        tick_spacing = pair_data.get("tick_spacing", 64)
        current_tick = pair_data.get("current_tick", 0)
        # Orca uses similar formula: price = 1.0001^tick
        lower_price = 1.0001 ** (self.tick_lower_index * tick_spacing)
        upper_price = 1.0001 ** (self.tick_upper_index * tick_spacing)
        return LPPosition(
            protocol=Protocol.ORCA_WHIRLPOOLS.value,
            chain=Chain.SOLANA.value,
            pair_address=self.whirlpool,
            token0=pair_data.get("token0", ""),
            token1=pair_data.get("token1", ""),
            token0_address=pair_data.get("token0_address", ""),
            token1_address=pair_data.get("token1_address", ""),
            lower_price=lower_price,
            upper_price=upper_price,
            liquidity=float(self.liquidity),
            position_id=self.position_mint,
            status=_tick_to_status(current_tick, self.tick_lower_index, self.tick_upper_index),
        )


# ---------------------------------------------------------------------------
# Price Fetching via DexScreener
# ---------------------------------------------------------------------------

async def get_current_price(
    token0_address: str,
    token1_address: str,
    chain: str,
    dex_client,  # DexScreenerClient instance
) -> Optional[float]:
    """
    Fetch current price from DexScreener.

    Returns price as token1 per token0 (e.g. USDC per ETH).
    Returns None if no pair found.
    """
    # Search by token1 (quote) to get pair with token0
    query = token0_address or token1_address
    pairs = await dex_client.search_pairs(query)
    if not pairs:
        return None

    # Find the pair matching our token pair
    for pair in pairs:
        if chain.lower() in pair.chain.lower():
            # Match the correct pair
            addr_match = (
                (token0_address and pair.base_token_address.lower() == token0_address.lower())
                or (token1_address and pair.quote_token_address.lower() == token1_address.lower())
            )
            if addr_match and pair.price_usd > 0:
                # DexScreener price is in USD; return token1 per token0
                # If base is token0 and quote is token1, price_usd is in USD terms
                # We need token1/token0 ratio
                return pair.price_usd
    return None


# ---------------------------------------------------------------------------
# Status Helpers
# ---------------------------------------------------------------------------

def _tick_to_status(current_tick: int, tick_lower: int, tick_upper: int) -> str:
    """Determine position status from current tick vs bounds."""
    if current_tick < tick_lower:
        return PositionStatus.OUT_OF_RANGE_BELOW.value
    elif current_tick > tick_upper:
        return PositionStatus.OUT_OF_RANGE_ABOVE.value
    else:
        return PositionStatus.IN_RANGE.value


def _price_to_status(current_price: float, lower_price: float, upper_price: float) -> str:
    """Determine position status from current price vs bounds."""
    if current_price <= 0:
        return PositionStatus.NOT_INITIALIZED.value
    if current_price < lower_price:
        return PositionStatus.OUT_OF_RANGE_BELOW.value
    elif current_price > upper_price:
        return PositionStatus.OUT_OF_RANGE_ABOVE.value
    else:
        return PositionStatus.IN_RANGE.value


# ---------------------------------------------------------------------------
# monitor_positions()
# ---------------------------------------------------------------------------

async def monitor_positions(
    positions: List[LPPosition],
    dex_client,
) -> List[LPPosition]:
    """
    Check if current price is within each position's LP range.

    Updates:
        - status
        - last_monitored
        - il_estimate_usd / il_pct (via calculate_il)

    Args:
        positions: List of LPPosition to monitor
        dex_client: DexScreenerClient instance

    Returns:
        List of updated LPPosition
    """
    updated = []
    now = datetime.now().timestamp()

    for pos in positions:
        try:
            current_price = await get_current_price(
                token0_address=pos.token0_address,
                token1_address=pos.token1_address,
                chain=pos.chain,
                dex_client=dex_client,
            )

            if current_price is not None and current_price > 0:
                pos.last_monitored = now
                pos.status = _price_to_status(current_price, pos.lower_price, pos.upper_price)

                # Estimate IL at each check
                il_usd, il_pct = calculate_il(
                    current_price=current_price,
                    lower_price=pos.lower_price,
                    upper_price=pos.upper_price,
                    value_usd=pos.value_usd,
                )
                pos.il_estimate_usd = il_usd
                pos.il_pct = il_pct
                pos.last_il_check = now

            else:
                pos.status = PositionStatus.NOT_INITIALIZED.value
                logger.warning(f"Could not fetch price for {pos.token0}/{pos.token1} on {pos.chain}")

        except Exception as e:
            logger.error(f"Error monitoring position {pos.position_id}: {e}")
            pos.status = PositionStatus.NOT_INITIALIZED.value

        updated.append(pos)

    return updated


# ---------------------------------------------------------------------------
# calculate_il()
# ---------------------------------------------------------------------------

def calculate_il(
    current_price: float,
    lower_price: float,
    upper_price: float,
    value_usd: float,
) -> tuple[float, float]:
    """
    Estimate impermanent loss for a concentrated liquidity position.

    IL occurs when the current price exits the LP range. The LP holds
    a fixed amount of token0 and token1 that shifts as price moves.

    This simplified IL model:
    - If in range: IL ≈ 0 (position is actively providing fees)
    - If out of range: IL is calculated vs a simple HODL of equal value

    Args:
        current_price: Current price (token1 per token0)
        lower_price: Lower bound of LP range
        upper_price: Upper bound of LP range
        value_usd: Current USD value of the LP position

    Returns:
        (il_usd, il_pct) — IL in USD and as percentage
    """
    if lower_price <= 0 or upper_price <= 0 or current_price <= 0:
        return 0.0, 0.0

    # If price is in range, no IL (fees offset)
    if lower_price <= current_price <= upper_price:
        return 0.0, 0.0

    # For concentrated positions, IL depends on how far price moved
    # We use a model where:
    #   - HODL value = value_usd (unchanged)
    #   - LP value = amount0 * current_price + amount1
    #
    # When price moves to extreme (below lower or above upper),
    # the position becomes 100% in one token, suffering full IL vs HODL.
    #
    # IL = |LP_value - HODL_value|
    # Simplified: IL% based on distance from range center

    range_center = (lower_price + upper_price) / 2
    if current_price < lower_price:
        # Price dropped significantly below range
        # Position is now all token0, losing token1 value
        distance = (range_center - current_price) / range_center
        # Max IL for full conversion is ~50% (when price → 0)
        il_pct = min(50.0, distance * 100)
    elif current_price > upper_price:
        # Price rose above range
        # LP is now 100% in token1 and misses token0 appreciation.
        # We use a simplified linear model: IL ≈ distance from upper * sensitivity
        # At current=2x upper → IL ~5-10%. At current=1.5x upper → IL ~2-3%
        ratio = current_price / upper_price
        if ratio > 1:
            # Linear model: il_pct = (ratio - 1) * 25
            # When ratio=2 (price doubles), il_pct=25%
            # When ratio=1.5, il_pct=12.5%
            il_pct = (ratio - 1) * 25
            il_pct = max(0, min(50, il_pct))
        else:
            il_pct = 0.0
    else:
        il_pct = 0.0

    il_usd = (il_pct / 100) * value_usd
    return il_usd, il_pct


# ---------------------------------------------------------------------------
# suggest_rebalance()
# ---------------------------------------------------------------------------

@dataclass
class RebalanceSuggestion:
    """Suggestion for rebalancing an LP position."""
    position_id: str
    pair: str  # e.g. "ETH/USDC"
    current_price: float
    lower_price: float
    upper_price: float
    current_status: str
    severity: str  # "warning" | "critical"
    message: str
    suggested_action: str  # e.g. "rebalance", "widen range", "close position"
    estimated_cost_usd: float = 0.0  # gas cost estimate for rebalancing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "pair": self.pair,
            "current_price": self.current_price,
            "lower_price": self.lower_price,
            "upper_price": self.upper_price,
            "current_status": self.current_status,
            "severity": self.severity,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


async def suggest_rebalance(
    position: LPPosition,
    dex_client,
) -> Optional[RebalanceSuggestion]:
    """
    Suggest rebalancing when price exits LP range.

    Args:
        position: LPPosition to evaluate
        dex_client: DexScreenerClient instance

    Returns:
        RebalanceSuggestion if action needed, None otherwise
    """
    if position.protocol == Protocol.UNISWAP_V3.value:
        return await _suggest_uniswap_rebalance(position, dex_client)
    elif position.protocol == Protocol.ORCA_WHIRLPOOLS.value:
        return await _suggest_orca_rebalance(position, dex_client)
    return None


async def _suggest_uniswap_rebalance(
    position: LPPosition,
    dex_client,
) -> Optional[RebalanceSuggestion]:
    """Uniswap V3 rebalance suggestion using DexScreener."""
    try:
        current_price = await get_current_price(
            token0_address=position.token0_address,
            token1_address=position.token1_address,
            chain=position.chain,
            dex_client=dex_client,
        )
    except Exception:
        current_price = None

    if current_price is None:
        return None

    status = _price_to_status(current_price, position.lower_price, position.upper_price)
    pair = f"{position.token0}/{position.token1}"

    # Gas cost estimates (USD) for EVM chains
    gas_costs = {
        "ethereum": 50.0,
        "arbitrum": 5.0,
        "base": 1.0,
        "polygon": 0.5,
        "bsc": 3.0,
    }
    estimated_gas = gas_costs.get(position.chain.lower(), 10.0)

    if status == PositionStatus.OUT_OF_RANGE_BELOW.value:
        # Price below range — consider widening lower bound or rebalancing down
        severity = "critical" if current_price < position.lower_price * 0.8 else "warning"
        return RebalanceSuggestion(
            position_id=position.position_id,
            pair=pair,
            current_price=current_price,
            lower_price=position.lower_price,
            upper_price=position.upper_price,
            current_status=status,
            severity=severity,
            message=(
                f"Price {current_price:.4f} has fallen below LP range "
                f"[{position.lower_price:.4f} - {position.upper_price:.4f}]. "
                f"Position is 100% in {position.token0}. Earned fees: ${position.fees_earned_usd:.2f}. "
                f"IL: ${position.il_estimate_usd:.2f} ({position.il_pct:.2f}%)."
            ),
            suggested_action="rebalance",
            estimated_cost_usd=estimated_gas,
        )

    elif status == PositionStatus.OUT_OF_RANGE_ABOVE.value:
        severity = "critical" if current_price > position.upper_price * 1.2 else "warning"
        return RebalanceSuggestion(
            position_id=position.position_id,
            pair=pair,
            current_price=current_price,
            lower_price=position.lower_price,
            upper_price=position.upper_price,
            current_status=status,
            severity=severity,
            message=(
                f"Price {current_price:.4f} has risen above LP range "
                f"[{position.lower_price:.4f} - {position.upper_price:.4f}]. "
                f"Position is 100% in {position.token1}. Earned fees: ${position.fees_earned_usd:.2f}. "
                f"IL: ${position.il_estimate_usd:.2f} ({position.il_pct:.2f}%)."
            ),
            suggested_action="rebalance",
            estimated_cost_usd=estimated_gas,
        )

    return None


async def _suggest_orca_rebalance(
    position: LPPosition,
    dex_client,
) -> Optional[RebalanceSuggestion]:
    """Orca Whirlpools rebalance suggestion using DexScreener."""
    try:
        current_price = await get_current_price(
            token0_address=position.token0_address,
            token1_address=position.token1_address,
            chain=Chain.SOLANA.value,
            dex_client=dex_client,
        )
    except Exception:
        current_price = None

    if current_price is None:
        return None

    status = _price_to_status(current_price, position.lower_price, position.upper_price)
    pair = f"{position.token0}/{position.token1}"

    # Solana tx costs are much lower
    estimated_cost = 0.25  # ~0.25 USD for Jupiter/Orca tx

    if status == PositionStatus.OUT_OF_RANGE_BELOW.value:
        severity = "critical" if current_price < position.lower_price * 0.8 else "warning"
        return RebalanceSuggestion(
            position_id=position.position_id,
            pair=pair,
            current_price=current_price,
            lower_price=position.lower_price,
            upper_price=position.upper_price,
            current_status=status,
            severity=severity,
            message=(
                f"Price {current_price:.4f} has fallen below LP range "
                f"[{position.lower_price:.4f} - {position.upper_price:.4f}]. "
                f"Position is 100% in {position.token0}. Earned fees: ${position.fees_earned_usd:.2f}. "
                f"IL: ${position.il_estimate_usd:.2f} ({position.il_pct:.2f}%)."
            ),
            suggested_action="rebalance",
            estimated_cost_usd=estimated_cost,
        )

    elif status == PositionStatus.OUT_OF_RANGE_ABOVE.value:
        severity = "critical" if current_price > position.upper_price * 1.2 else "warning"
        return RebalanceSuggestion(
            position_id=position.position_id,
            pair=pair,
            current_price=current_price,
            lower_price=position.lower_price,
            upper_price=position.upper_price,
            current_status=status,
            severity=severity,
            message=(
                f"Price {current_price:.4f} has risen above LP range "
                f"[{position.lower_price:.4f} - {position.upper_price:.4f}]. "
                f"Position is 100% in {position.token1}. Earned fees: ${position.fees_earned_usd:.2f}. "
                f"IL: ${position.il_estimate_usd:.2f} ({position.il_pct:.2f}%)."
            ),
            suggested_action="rebalance",
            estimated_cost_usd=estimated_cost,
        )

    return None


# ---------------------------------------------------------------------------
# track_fees()
# ---------------------------------------------------------------------------

@dataclass
class FeeUpdate:
    """Fee update for a position."""
    position_id: str
    pair: str
    protocol: str
    chain: str
    fees_token0: float
    fees_token1: float
    fees_usd: float
    timestamp: float
    elapsed_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "pair": f"{self.pair}",
            "protocol": self.protocol,
            "chain": self.chain,
            "fees_token0": self.fees_token0,
            "fees_token1": self.fees_token1,
            "fees_usd": self.fees_usd,
            "timestamp": self.timestamp,
            "elapsed_seconds": self.elapsed_seconds,
        }


def track_fees(
    position: LPPosition,
    token0_price_usd: float,
    token1_price_usd: float,
) -> FeeUpdate:
    """
    Calculate current fee accumulation for an LP position.

    Args:
        position: LPPosition to track fees for
        token0_price_usd: Current USD price of token0
        token1_price_usd: Current USD price of token1

    Returns:
        FeeUpdate with current fee state
    """
    now = datetime.now().timestamp()

    # Calculate USD value of accumulated fees
    fees_usd = (position.fees_earned_token0 * token0_price_usd +
                position.fees_earned_token1 * token1_price_usd)

    elapsed = now - position.last_fee_update if position.last_fee_update > 0 else 0.0

    update = FeeUpdate(
        position_id=position.position_id,
        pair=f"{position.token0}/{position.token1}",
        protocol=position.protocol,
        chain=position.chain,
        fees_token0=position.fees_earned_token0,
        fees_token1=position.fees_earned_token1,
        fees_usd=fees_usd,
        timestamp=now,
        elapsed_seconds=elapsed,
    )

    # Update position
    position.fees_earned_usd = fees_usd
    position.last_fee_update = now

    return update


# ---------------------------------------------------------------------------
# format_lp_report()
# ---------------------------------------------------------------------------

@dataclass
class LPReport:
    """Daily LP performance report."""
    generated_at: float
    positions_count: int
    total_value_usd: float
    total_fees_earned_usd: float
    total_il_usd: float
    in_range_count: int
    out_of_range_count: int
    rebalance_suggestions: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "generated_at_str": datetime.fromtimestamp(self.generated_at).isoformat(),
            "positions_count": self.positions_count,
            "total_value_usd": self.total_value_usd,
            "total_fees_earned_usd": self.total_fees_earned_usd,
            "total_il_usd": self.total_il_usd,
            "in_range_count": self.in_range_count,
            "out_of_range_count": self.out_of_range_count,
            "rebalance_suggestions": self.rebalance_suggestions,
        }


def format_lp_report(
    positions: List[LPPosition],
    rebalance_suggestions: Optional[List[RebalanceSuggestion]] = None,
) -> LPReport:
    """
    Generate daily LP performance report.

    Args:
        positions: List of LPPosition to report on
        rebalance_suggestions: Optional list of rebalance suggestions

    Returns:
        LPReport dataclass
    """
    now = datetime.now().timestamp()

    total_value = sum(p.value_usd for p in positions)
    total_fees = sum(p.fees_earned_usd for p in positions)
    total_il = sum(p.il_estimate_usd for p in positions)
    in_range = sum(1 for p in positions if p.status == PositionStatus.IN_RANGE.value)
    out_of_range = sum(
        1 for p in positions
        if p.status in (PositionStatus.OUT_OF_RANGE_ABOVE.value,
                        PositionStatus.OUT_OF_RANGE_BELOW.value)
    )

    suggestions = []
    if rebalance_suggestions:
        for s in rebalance_suggestions:
            if s is not None:
                suggestions.append(s.to_dict())

    return LPReport(
        generated_at=now,
        positions_count=len(positions),
        total_value_usd=total_value,
        total_fees_earned_usd=total_fees,
        total_il_usd=total_il,
        in_range_count=in_range,
        out_of_range_count=out_of_range,
        rebalance_suggestions=suggestions,
    )


def format_lp_report_text(report: LPReport) -> str:
    """
    Format LP report as human-readable text.

    Args:
        report: LPReport to format

    Returns:
        Multi-line string report
    """
    lines = [
        "=" * 60,
        "  DAILY LP PERFORMANCE REPORT",
        "=" * 60,
        f"Generated: {datetime.fromtimestamp(report.generated_at).strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "SUMMARY",
        "-" * 40,
        f"  Total Positions:     {report.positions_count}",
        f"  Total Value:          ${report.total_value_usd:,.2f}",
        f"  Total Fees Earned:   ${report.total_fees_earned_usd:,.2f}",
        f"  Total IL:             ${report.total_il_usd:,.2f}",
        f"  In Range:             {report.in_range_count}",
        f"  Out of Range:         {report.out_of_range_count}",
        "",
    ]

    if report.rebalance_suggestions:
        lines += [
            "REBALANCE ALERTS",
            "-" * 40,
        ]
        for s in report.rebalance_suggestions:
            severity_marker = "🔴" if s["severity"] == "critical" else "🟡"
            lines.append(
                f"  {severity_marker} [{s['severity'].upper()}] {s['pair']} "
                f"(pos: {s['position_id'][:8]}...)"
            )
            lines.append(f"      Price {s['current_price']:.4f} outside range "
                         f"[{s['lower_price']:.4f}-{s['upper_price']:.4f}]")
            lines.append(f"      Action: {s['suggested_action']} "
                         f"(est. cost: ${s['estimated_cost_usd']:.2f})")
            lines.append(f"      {s['message'][:100]}...")
            lines.append("")
    else:
        lines.append("  ✅ No rebalancing needed.")

    net_value = report.total_value_usd + report.total_fees_earned_usd - abs(report.total_il_usd)
    lines += [
        "NET VALUE",
        "-" * 40,
        f"  Net LP Value:         ${net_value:,.2f}",
        f"  (Value + Fees - IL)",
        "=" * 60,
    ]

    return "\n".join(lines)
