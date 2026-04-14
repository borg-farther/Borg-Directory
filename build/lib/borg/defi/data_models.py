"""Data models for Borg DeFi modules."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


@dataclass
class WhaleAlert:
    """Represents a whale wallet activity alert.

    Attributes:
        wallet: Wallet address (labeled if known)
        chain: Blockchain network (solana|ethereum|base|arbitrum)
        action: Activity type (swap|transfer|mint|burn|stake|unstake)
        token_in: Token sold/sent
        token_out: Token bought/received
        amount_usd: USD value of the transaction
        timestamp: Unix timestamp
        tx_hash: Transaction hash
        context: Human-readable context description
        signal_strength: Signal significance 0-1 (from learning loop)
    """
    wallet: str
    chain: str
    action: str
    token_in: str
    token_out: str
    amount_usd: float
    timestamp: float
    tx_hash: str
    context: str
    signal_strength: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wallet": self.wallet,
            "chain": self.chain,
            "action": self.action,
            "token_in": self.token_in,
            "token_out": self.token_out,
            "amount_usd": self.amount_usd,
            "timestamp": self.timestamp,
            "tx_hash": self.tx_hash,
            "context": self.context,
            "signal_strength": self.signal_strength,
        }


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class YieldOpportunity:
    """Represents a DeFi yield opportunity.
    
    Attributes:
        protocol: Protocol name (aave|compound|kamino|marinade|raydium)
        chain: Blockchain network (solana|ethereum|base|arbitrum)
        pool: Pool/vault name
        token: Deposit token symbol
        apy: Current APY percentage
        tvl: Total value locked in USD
        risk_score: Risk score 0-1 (higher = riskier)
        il_risk: Whether impermanent loss applies
        url: Protocol UI link
        last_updated: Unix timestamp of last update
    """
    protocol: str
    chain: str
    pool: str
    token: str
    apy: float
    tvl: float
    risk_score: float
    il_risk: bool
    url: str
    last_updated: float
    project_name: Optional[str] = None
    symbol: Optional[str] = None
    pool_id: Optional[str] = None
    
    def __post_init__(self):
        self.risk_score = max(0.0, min(1.0, self.risk_score))
        self.apy = max(0.0, self.apy)
        self.tvl = max(0.0, self.tvl)


@dataclass
class Position:
    """Represents a portfolio position.
    
    Attributes:
        chain: Blockchain network
        protocol: Protocol name
        token: Token symbol
        amount: Token amount
        value_usd: USD value
        entry_price: Entry price in USD
        current_price: Current price in USD
        pnl_usd: Unrealized P&L in USD
        pnl_pct: Unrealized P&L percentage
        health_factor: For lending positions (optional)
    """
    chain: str
    protocol: str
    token: str
    amount: float
    value_usd: float
    entry_price: float
    current_price: float
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    health_factor: Optional[float] = None
    position_type: str = "hold"  # hold|lp|lending|staking
    
    def __post_init__(self):
        if self.pnl_usd == 0.0 and self.entry_price > 0 and self.current_price > 0:
            self.pnl_usd = (self.current_price - self.entry_price) * self.amount
            self.pnl_pct = ((self.current_price / self.entry_price) - 1) * 100


@dataclass
class RiskAlert:
    """Risk alert for portfolio monitoring.
    
    Attributes:
        alert_type: Type of risk (concentration|health_factor|drawdown|exploit)
        severity: Risk severity (warning|critical)
        message: Human-readable alert message
        affected_positions: List of affected position tokens
        timestamp: Unix timestamp
    """
    alert_type: str
    severity: str
    message: str
    affected_positions: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = datetime.now().timestamp()


@dataclass
class SpendingLimit:
    """Spending limit configuration.
    
    Attributes:
        per_trade_limit: Max USD per single trade
        daily_limit: Max USD per day
        daily_spent: Amount already spent today
        last_reset: Unix timestamp of last daily reset
    """
    per_trade_limit: float
    daily_limit: float
    daily_spent: float = 0.0
    last_reset: float = 0.0
    
    def can_spend(self, amount_usd: float) -> bool:
        """Check if amount can be spent within limits."""
        if amount_usd > self.per_trade_limit:
            return False
        return (self.daily_spent + amount_usd) <= self.daily_limit
    
    def add_spend(self, amount_usd: float) -> None:
        """Record a spend."""
        self.daily_spent += amount_usd
    
    def reset_if_new_day(self) -> None:
        """Reset daily spent if it's a new day."""
        now = datetime.now().timestamp()
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        if self.last_reset < day_start:
            self.daily_spent = 0.0
            self.last_reset = now


@dataclass
class WhitelistedContract:
    """Whitelisted contract for transactions.
    
    Attributes:
        address: Contract address
        chain: Blockchain network
        name: Human-readable name
        contract_type: Type (router|protocol|token)
        added_at: Unix timestamp when added
    """
    address: str
    chain: str
    name: str
    contract_type: str
    added_at: float = 0.0
    
    def __post_init__(self):
        if self.added_at == 0.0:
            self.added_at = datetime.now().timestamp()


@dataclass
class YieldChange:
    """Represents a significant yield change.
    
    Attributes:
        pool_id: Pool identifier
        protocol: Protocol name
        chain: Blockchain network
        previous_apy: Previous APY percentage
        current_apy: Current APY percentage
        change_pct: Percentage change
        is_spike: True if yield increased significantly
    """
    pool_id: str
    protocol: str
    chain: str
    previous_apy: float
    current_apy: float
    change_pct: float
    is_spike: bool


@dataclass
class PortfolioSummary:
    """Portfolio summary for reporting.

    Attributes:
        total_value_usd: Total portfolio value in USD
        total_pnl_usd: Total unrealized P&L in USD
        total_pnl_pct: Total P&L percentage
        daily_change_usd: USD change in last 24h
        daily_change_pct: Percentage change in last 24h
        positions: List of positions
        risk_alerts: List of risk alerts
        allocations: Dict of token -> percentage
    """
    total_value_usd: float
    total_pnl_usd: float
    total_pnl_pct: float
    daily_change_usd: float
    daily_change_pct: float
    positions: List[Position]
    risk_alerts: List[RiskAlert]
    allocations: Dict[str, float]


@dataclass
class DeFiPackMetadata:
    """Extended metadata for DeFi strategy packs.

    Attributes:
        total_trades: Total number of trades
        winning_trades: Number of profitable trades
        total_pnl_usd: Total P&L in USD
        max_drawdown_pct: Maximum drawdown percentage
        sharpe_ratio: Risk-adjusted return metric
        win_rate: Percentage of winning trades
        avg_return_per_trade: Average return per trade
        last_trade_timestamp: Unix timestamp of last trade
        chains: List of chains involved
        protocols: List of protocols used
    """
    total_trades: int = 0
    winning_trades: int = 0
    total_pnl_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_return_per_trade: float = 0.0
    last_trade_timestamp: float = 0.0
    chains: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "total_pnl_usd": self.total_pnl_usd,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "win_rate": self.win_rate,
            "avg_return_per_trade": self.avg_return_per_trade,
            "last_trade_timestamp": self.last_trade_timestamp,
            "chains": self.chains,
            "protocols": self.protocols,
        }


@dataclass
class TokenPrice:
    """Token price data.

    Attributes:
        symbol: Token symbol
        address: Token contract address
        price: Price in USD
        price_native: Price in native token
        timestamp: Unix timestamp
        volume_24h: 24h trading volume
    """
    symbol: str
    address: str
    price: float = 0.0
    price_native: float = 0.0
    timestamp: float = 0.0
    volume_24h: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "address": self.address,
            "price": self.price,
            "price_native": self.price_native,
            "timestamp": self.timestamp,
            "volume_24h": self.volume_24h,
        }


@dataclass
class OHLCV:
    """OHLCV candle data for charts.

    Attributes:
        timestamp: Unix timestamp
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume
        symbol: Token symbol
        address: Token address
    """
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""
    address: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "symbol": self.symbol,
            "address": self.address,
        }


@dataclass
class Transaction:
    """Enhanced transaction data.

    Attributes:
        signature: Transaction signature/hash
        slot: Block slot number
        timestamp: Unix timestamp
        fee: Transaction fee
        status: Transaction status (success|failed)
        type: Transaction type (swap|transfer|native|unknown)
        accounts: List of accounts involved
        token_balances: Token balance changes
        error: Error message if failed
    """
    signature: str
    slot: int
    timestamp: float
    fee: int
    status: str
    type: str
    accounts: List[str] = field(default_factory=list)
    token_balances: Dict[str, Dict[str, float]] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature": self.signature,
            "slot": self.slot,
            "timestamp": self.timestamp,
            "fee": self.fee,
            "status": self.status,
            "type": self.type,
            "accounts": self.accounts,
            "token_balances": self.token_balances,
            "error": self.error,
        }


@dataclass
class DexPair:
    """DEX pair data.

    Attributes:
        pair_address: Pair contract address
        base_token: Base token symbol
        base_token_address: Base token contract address
        quote_token: Quote token symbol
        quote_token_address: Quote token contract address
        price_usd: Current price in USD
        volume_24h: 24h trading volume
        liquidity_usd: Liquidity in USD
        tx_count_24h: 24h transaction count
        price_change_24h: 24h price change percentage
        chain: Blockchain network
        dex: DEX name
        timestamp: Unix timestamp
    """
    pair_address: str
    base_token: str
    base_token_address: str
    quote_token: str
    quote_token_address: str
    price_usd: float = 0.0
    volume_24h: float = 0.0
    liquidity_usd: float = 0.0
    tx_count_24h: int = 0
    price_change_24h: float = 0.0
    chain: str = ""
    dex: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pair_address": self.pair_address,
            "base_token": self.base_token,
            "base_token_address": self.base_token_address,
            "quote_token": self.quote_token,
            "quote_token_address": self.quote_token_address,
            "price_usd": self.price_usd,
            "volume_24h": self.volume_24h,
            "liquidity_usd": self.liquidity_usd,
            "tx_count_24h": self.tx_count_24h,
            "price_change_24h": self.price_change_24h,
            "chain": self.chain,
            "dex": self.dex,
            "timestamp": self.timestamp,
        }
