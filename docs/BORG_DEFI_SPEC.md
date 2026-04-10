# Borg DeFi — Specification

**The AI agent that remembers every trade, learns from every loss, and shares alpha with the collective.**

**Status:** SPEC v1.0
**Date:** 2026-03-29
**Author:** Hermes Agent (degen mode)

---

## 1. Product Vision

### What Is It

Borg DeFi is a suite of DeFi skill packs for the Hermes+Borg agent ecosystem. It turns your Hermes agent into an autonomous on-chain operator that:

- **Watches** whale wallets, yield opportunities, liquidation targets
- **Executes** swaps, rebalances, compounds — with optimal routing
- **Learns** from every trade via Borg's session analysis (dojo)
- **Shares** successful strategies across the collective (CPI)
- **Reports** P&L, alerts, and alpha signals via Telegram/Discord

### Who Uses It

The degen running Hermes on a $5 VPS who wants:
1. Morning whale alerts on Telegram before the CT herd
2. Auto-compounding yield positions while they sleep
3. A trading agent that actually gets better over time (not the same dumb bot)
4. Access to collective alpha (what other agents discovered)

### Why It Wins

Every other DeFi bot is stateless — it does the same thing forever. Borg DeFi has **memory**:

| Feature | Generic Bot | Borg DeFi |
|---------|------------|-----------|
| Loses money on bad swap route | Does it again tomorrow | Dojo classifies the loss, patches the routing strategy |
| Misses a whale move | No awareness | Pattern saved as pack, shared with collective |
| Yield farm goes to 0% | Stays in dead pool | Auto-rotates, warns others via collective |
| Gets rekt by rug | No learning | Rug pattern detected, propagated to all agents |
| Strategy stops working | Keeps losing | Reputation engine downranks, suggests alternatives |

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER (Telegram/Discord)                       │
│   "check whales" / "what's my PnL" / "auto-compound my USDC"       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         HERMES AGENT                                 │
│   Skills loaded → DeFi packs active → Cron jobs running             │
│   MCP tools: borg_defi (analyze/execute/monitor/alert)              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌──────────────────┐ ┌────────────────┐ ┌─────────────────┐
│  DEFI SKILL PACKS│ │  BORG CORE     │ │  DOJO            │
│                  │ │                │ │                  │
│  whale-tracker   │ │  Pack store    │ │  Session reader  │
│  yield-scanner   │ │  Reputation    │ │  Win/loss class  │
│  portfolio-mon   │ │  CPI engine    │ │  Strategy patch  │
│  swap-executor   │ │  Nudge engine  │ │  Learning curve  │
│  lp-manager      │ │  Search        │ │  Reports         │
│  liquidation-w   │ │                │ │                  │
│  alpha-signal    │ │                │ │                  │
│  risk-engine     │ │                │ │                  │
└────────┬─────────┘ └────────┬───────┘ └────────┬────────┘
         │                    │                   │
         ▼                    ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       ON-CHAIN DATA LAYER                            │
│                                                                      │
│  Solana: Jupiter API, Helius RPC, Birdeye, DexScreener              │
│  EVM: 1inch, Alchemy, The Graph, Aave, Uniswap                     │
│  Data: DeFiLlama, Dune, Arkham                                      │
│  MEV: Jito (Solana), Flashbots (ETH)                                │
└─────────────────────────────────────────────────────────────────────┘
```

### The Learning Loop

```
Agent executes trade
       │
       ▼
Outcome recorded in session (state.db)
       │
       ▼
Dojo reads session → classifies outcome
  ├─ WIN: pattern extracted → pack updated → confidence ↑
  └─ LOSS: failure classified → strategy patched → shared as warning
       │
       ▼
Borg reputation scores strategy by cumulative PnL
       │
       ▼
Next trade: Nudge engine suggests highest-reputation strategy
       │
       ▼
Collective: winning strategies propagate to other agents
```

---

## 3. Phase 1 — MVP Skill Packs (Ship in 2 weeks)

### 3a. `whale-tracker`

**What:** Monitor high-value wallets on Solana/ETH. Alert on large moves via Telegram.

**Why first:** Zero execution risk. Read-only. Immediate value. Everyone wants whale alerts.

```yaml
name: whale-tracker
description: >
  Monitor whale wallets for large token movements. Alerts via Telegram
  when tracked wallets make significant swaps, transfers, or new positions.
  Learns which whale signals correlate with price moves.
version: 1.0.0
metadata:
  category: defi-signals
  chains: [solana, ethereum, base, arbitrum]
  risk: none (read-only)
  apis: [helius, alchemy, birdeye, dexscreener]
```

**Core functions:**

```python
@dataclass
class WhaleAlert:
    wallet: str              # address (labeled if known)
    chain: str               # solana|ethereum|base|arbitrum
    action: str              # swap|transfer|mint|burn|stake|unstake
    token_in: str            # token sold/sent
    token_out: str           # token bought/received
    amount_usd: float        # USD value
    timestamp: float
    tx_hash: str
    context: str             # "bought $2.1M BONK via Jupiter"
    signal_strength: float   # 0-1, how significant (from learning loop)

class WhaleTracker:
    """Monitor whale wallets and generate alerts."""

    # Configurable
    TRACKED_WALLETS: Dict[str, str]  # address → label
    MIN_USD_THRESHOLD: float = 50_000
    ALERT_COOLDOWN: int = 300  # 5 min between alerts for same wallet

    async def scan_solana(self) -> List[WhaleAlert]:
        """Scan Solana whale activity via Helius webhooks + Birdeye."""
        # Helius enhanced transactions API
        # GET https://api.helius.xyz/v0/addresses/{address}/transactions
        # Filter: amount > threshold, parse swap/transfer type

    async def scan_evm(self, chain: str) -> List[WhaleAlert]:
        """Scan EVM chain whale activity via Alchemy."""
        # Alchemy getAssetTransfers API
        # Filter by value, decode swap events from DEX routers

    def score_signal(self, alert: WhaleAlert) -> float:
        """Score signal strength using borg reputation data.
        Wallets that historically predict price moves score higher."""
        # Check borg pack: whale-{wallet_hash} reputation score
        # Factor in: historical accuracy, follow-through, timing

    def format_telegram(self, alert: WhaleAlert) -> str:
        """Format alert for Telegram delivery."""
        return (
            f"🐋 *Whale Alert*\n"
            f"{'🟢' if alert.action == 'swap' else '🔵'} "
            f"{alert.context}\n"
            f"💰 ${alert.amount_usd:,.0f}\n"
            f"📊 Signal: {'🔥' * int(alert.signal_strength * 5)}\n"
            f"🔗 [{alert.chain}]({self._explorer_url(alert)})"
        )
```

**Borg integration:**
- Each whale wallet becomes a micro-pack with accuracy reputation
- Dojo tracks: "did the price move in the direction the whale traded?"
- Over time: signal_strength improves for consistently profitable whales
- Collective: discovered whale wallets shared across agents

**Cron setup:**
```python
# Every 5 minutes: scan chains, alert on new whale moves
# hermes cron: "every 5m" → run whale_tracker.scan_all() → deliver to telegram
```

### 3b. `yield-scanner`

**What:** Find and track best yield opportunities across DeFi. Auto-compound positions.

```python
@dataclass
class YieldOpportunity:
    protocol: str          # aave|compound|kamino|marinade|raydium
    chain: str
    pool: str              # pool/vault name
    token: str             # deposit token
    apy: float             # current APY %
    tvl: float             # total value locked
    risk_score: float      # 0-1 (higher = riskier)
    il_risk: bool          # impermanent loss applicable
    url: str               # protocol UI link
    last_updated: float

class YieldScanner:
    """Scan DeFi protocols for yield opportunities."""

    async def scan_defillama(self) -> List[YieldOpportunity]:
        """Scan yields via DeFiLlama API (free, no auth).

        GET https://yields.llama.fi/pools
        Returns: 10k+ pools with APY, TVL, chain, project
        """

    async def scan_solana_yields(self) -> List[YieldOpportunity]:
        """Scan Solana-specific yields: Kamino, Marinade, Raydium, Orca."""

    def rank_opportunities(self, opps: List[YieldOpportunity],
                           min_tvl: float = 1_000_000,
                           max_risk: float = 0.5) -> List[YieldOpportunity]:
        """Rank by risk-adjusted yield.
        Score = APY * (1 - risk_score) * log(TVL) / baseline
        """

    def detect_yield_changes(self, current: List, previous: List) -> List[Dict]:
        """Detect significant yield changes (>20% move) for alerts."""
```

**Cron:** Scan every hour, alert on new high-yield opportunities or significant drops.

**Borg integration:**
- Yield strategies become packs: "farm-kamino-usdc-sol" with entry/exit criteria
- Dojo tracks: actual realized yield vs advertised APY
- Reputation: protocols that consistently deliver get higher scores
- Warning propagation: "protocol X yield dropped 80% — possible exploit"

### 3c. `portfolio-monitor`

**What:** Track all positions, calculate P&L, risk alerts.

```python
@dataclass
class Position:
    chain: str
    protocol: str
    token: str
    amount: float
    value_usd: float
    entry_price: float
    current_price: float
    pnl_usd: float
    pnl_pct: float
    health_factor: Optional[float]  # for lending positions

class PortfolioMonitor:
    """Track portfolio positions and generate alerts."""

    async def get_solana_portfolio(self, wallet: str) -> List[Position]:
        """Get all Solana token holdings via Helius DAS API.
        POST https://mainnet.helius-rpc.com/?api-key=KEY
        Method: getAssetsByOwner
        """

    async def get_evm_portfolio(self, wallet: str, chain: str) -> List[Position]:
        """Get EVM holdings via Alchemy getTokenBalances."""

    def calculate_pnl(self, positions: List[Position]) -> Dict:
        """Calculate total P&L, daily change, allocation breakdown."""

    def risk_alerts(self, positions: List[Position]) -> List[str]:
        """Generate risk alerts:
        - Health factor < 1.5 on lending positions
        - Single token > 30% of portfolio
        - Unrealized loss > 20% on any position
        - Protocol with recent exploit/warning
        """

    def format_daily_report(self, positions, pnl) -> str:
        """Morning Telegram portfolio summary."""
```

---

## 4. Phase 2 — Execution Packs (Month 2)

### 4a. `swap-executor`

**What:** Execute token swaps with optimal routing.

```python
class SwapExecutor:
    """Execute swaps via Jupiter (Solana) and 1inch (EVM)."""

    async def get_quote_solana(self, input_mint: str, output_mint: str,
                                amount: int, slippage_bps: int = 50) -> Dict:
        """Get Jupiter swap quote.
        GET https://quote-api.jup.ag/v6/quote?inputMint={}&outputMint={}&amount={}&slippageBps={}
        """

    async def execute_swap_solana(self, quote: Dict, wallet_keypair) -> str:
        """Execute Solana swap via Jupiter.
        POST https://quote-api.jup.ag/v6/swap
        Sign + send transaction via Helius RPC.
        Returns: tx signature
        """

    async def get_quote_evm(self, chain: str, src: str, dst: str,
                            amount: int, slippage: float = 0.5) -> Dict:
        """Get 1inch swap quote.
        GET https://api.1inch.dev/swap/v6.0/{chainId}/swap
        """
```

**Security:** NEVER store private keys in packs. Keys stored in encrypted keyfile at `~/.hermes/borg/defi_keys.enc`. Spending limits enforced per-session.

### 4b. `lp-manager`

**What:** Manage concentrated liquidity positions on Uniswap V3 / Orca Whirlpools.

- Monitor price vs position range
- Auto-rebalance when price exits range
- Compound fees
- Track IL vs fees earned

### 4c. `liquidation-watcher`

**What:** Monitor Aave/Compound health factors, execute liquidations.

```python
class LiquidationWatcher:
    """Monitor lending protocol health factors."""

    async def scan_aave_positions(self, chain: str) -> List[Dict]:
        """Scan Aave V3 for liquidatable positions.
        Use The Graph: aave-v3 subgraph
        Query users where healthFactor < 1.1
        """

    async def execute_liquidation(self, user: str, debt_asset: str,
                                   collateral_asset: str, chain: str) -> str:
        """Execute Aave liquidation call.
        Requires flash loan or collateral upfront.
        """
```

---

## 5. Phase 3 — Alpha Engine (Month 3)

### 5a. `alpha-signal`

Smart money flow detection, on-chain pattern recognition:
- New token accumulation by known smart wallets
- Unusual volume spikes before announcements
- Cross-chain flow patterns (bridge activity → chain destination)
- DEX pair creation monitoring (new launches)

### 5b. `risk-engine`

Portfolio-level risk scoring:
- Correlation analysis between positions
- Protocol risk assessment (TVL trends, audit status, team doxxed)
- Concentration risk alerts
- Drawdown tracking and stop-loss triggers

### 5c. `strategy-backtester`

Test strategies against historical data before deploying capital:
- Use DeFiLlama historical yield data
- Replay whale wallet historical trades
- Simulate LP positions with historical price data
- Calculate Sharpe ratio, max drawdown, win rate

---

## 6. Borg Integration — The Learning Loop

### 6.1 Trade Outcome → Dojo Analysis

Every trade execution is logged to Hermes session (state.db). Dojo reads it:

```python
# In dojo/failure_classifier.py — new DeFi error categories:
DEFI_ERROR_CATEGORIES = {
    "slippage_exceeded": {
        "patterns": [r"(?i)slippage", r"(?i)price impact too high"],
        "fix_strategy": "Reduce trade size or use limit orders",
    },
    "insufficient_liquidity": {
        "patterns": [r"(?i)insufficient liquidity", r"(?i)no route found"],
        "fix_strategy": "Split trade across multiple DEXes or wait for liquidity",
    },
    "transaction_reverted": {
        "patterns": [r"(?i)reverted", r"(?i)execution reverted"],
        "fix_strategy": "Check approval, increase gas, verify contract state",
    },
    "rug_detected": {
        "patterns": [r"(?i)honeypot", r"(?i)cannot sell", r"(?i)trading disabled"],
        "fix_strategy": "Add to rug blacklist, alert collective, cut losses",
    },
    "gas_estimation_failed": {
        "patterns": [r"(?i)gas estimation", r"(?i)out of gas"],
        "fix_strategy": "Increase gas limit, check contract complexity",
    },
}
```

### 6.2 Strategy Packs with PnL Reputation

```python
@dataclass
class DeFiPackMetadata:
    """Extended metadata for DeFi strategy packs."""
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
```

Borg reputation engine extended:
- Packs with positive PnL get promoted in search results
- Packs with consistent losses get auto-deprecated
- Borg nudges: "your yield-farming strategy lost 15% this week, consider switching to pack X (Sharpe 2.1)"

### 6.3 Collective Intelligence for DeFi

When agent A discovers:
- "Token X whale accumulation precedes 3x pump" → pattern saved as pack
- "Aave liquidation at health factor 1.02 on ETH/USDC is profitable 73% of the time" → pack
- "Raydium CLMM ±5% range on SOL/USDC yields 42% net of IL" → pack

These propagate to agent B, C, D through borg's pack distribution.

**Privacy guardrail:** Wallet addresses, private keys, and specific trade amounts NEVER propagate. Only patterns and strategies.

---

## 7. Security

### 7.1 Key Management

```
~/.hermes/borg/defi/
├── keys.enc              # AES-256 encrypted keystore
├── keys.salt             # encryption salt (random per install)
├── spending_limits.json  # per-session, per-token limits
└── approved_contracts.json  # whitelist of interactable contracts
```

**Rules:**
1. Private keys NEVER in memory longer than transaction signing
2. Spending limits enforced: max $X per trade, max $Y per day
3. Contract whitelist: only interact with approved DEX routers
4. No approval for max uint256 — approve exact amounts only
5. Rug detection before every swap: check token contract for honeypot patterns

### 7.2 Transaction Safety

```python
class TransactionGuard:
    """Pre-flight checks before any on-chain transaction."""

    def check_token(self, token_address: str, chain: str) -> Dict:
        """Run rug detection checks:
        1. Is token on known scam list?
        2. Can token be sold? (simulate sell tx)
        3. Is liquidity locked?
        4. Transfer tax > 10%? → reject
        5. Owner can pause trading? → warn
        """

    def check_spending_limit(self, amount_usd: float) -> bool:
        """Enforce per-trade and daily spending limits."""

    def check_contract(self, contract: str, chain: str) -> bool:
        """Is this contract on the approved whitelist?"""

    def require_human_approval(self, trade: Dict) -> bool:
        """For trades > $X, require human confirmation via Telegram."""
```

### 7.3 Human-in-the-Loop

Configurable approval thresholds:
- Under $100: auto-execute
- $100-$1000: execute + alert
- Over $1000: require Telegram confirmation
- Over $10000: require 2FA confirmation

---

## 8. Revenue Model

### For Users (How They Make Money)

1. **Whale signals** → front-run (legally) major moves
2. **Yield optimization** → 2-5% more APY through auto-compounding and rotation
3. **Liquidation execution** → profit from undercollateralized positions
4. **Alpha signals** → early detection of accumulation patterns
5. **Risk management** → avoid losses through proactive alerts

### For Borg Ecosystem

1. **Premium packs** — advanced strategies as paid packs (one-time or subscription)
2. **Performance fees** — 5% of profits from auto-executed strategies
3. **Signal subscriptions** — whale alerts as premium Telegram channel
4. **Pack marketplace** — strategy creators earn from pack usage
5. **Agent tokens** — Virtuals Protocol integration, agent value accrues to token

### Revenue Projection (Conservative)

| Source | Month 1 | Month 3 | Month 6 |
|--------|---------|---------|---------|
| Whale signal subs (100 users × $20/mo) | $2,000 | $6,000 | $20,000 |
| Yield optimization fees (1% of AUM) | $500 | $5,000 | $50,000 |
| Liquidation profits | $0 | $2,000 | $10,000 |
| Premium pack sales | $0 | $1,000 | $5,000 |
| **Total** | **$2,500** | **$14,000** | **$85,000** |

---

## 9. Technical Requirements

### APIs Needed (Phase 1 — all free tier)

| API | Purpose | Auth | Free Tier |
|-----|---------|------|-----------|
| Helius | Solana RPC + webhooks | API key | 1M credits/mo |
| Birdeye | Token prices, OHLCV | API key | 1000 req/day |
| DexScreener | Pair data, new pairs | None | Unlimited |
| DeFiLlama | Yields, TVL, prices | None | Unlimited |
| Alchemy | EVM RPC + transfers | API key | 300M CU/mo |
| Jupiter | Solana swap quotes | None | Unlimited |

### Dependencies

```toml
[project.optional-dependencies]
defi = [
    "aiohttp>=3.9",         # async HTTP for API calls
    "solders>=0.21",         # Solana SDK (Rust-backed, fast)
    "solana>=0.34",          # Solana Python client
    "web3>=7.0",             # EVM interaction
    "pynacl>=1.5",           # Ed25519 signing (already in borg)
    "cryptography>=42.0",    # AES keystore encryption
]
```

### Infrastructure

- **Minimum:** $5 VPS (1 CPU, 1GB RAM) — runs whale tracker + yield scanner
- **Recommended:** $20 VPS (2 CPU, 4GB RAM) — full stack with execution
- **Optimal:** $50 VPS (4 CPU, 8GB RAM) — MEV + liquidations need speed

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Whale alert accuracy | >60% signals predict correct direction within 24h | Track price 24h after alert |
| Yield improvement | >2% APY above manual farming | Compare auto-compound vs hold |
| Trade execution | >95% swaps execute successfully | Dojo session analysis |
| Learning loop | Strategy PnL improves week-over-week | Dojo learning curve |
| Collective value | Pack shared between agents leads to >0 adoption | Borg analytics |
| User retention | >50% daily active after 30 days | Session analysis |
| Rug detection | >90% honeypots caught before trade | Backtest against known rugs |
| Revenue | >$2500/mo by month 1 | Actual revenue tracking |

---

## 11. Implementation Plan

### Week 1-2: Phase 1 MVP

```
borg/defi/
├── __init__.py
├── data_models.py          # WhaleAlert, YieldOpportunity, Position, etc.
├── whale_tracker.py        # Helius + Birdeye + DexScreener
├── yield_scanner.py        # DeFiLlama + protocol-specific
├── portfolio_monitor.py    # Multi-chain portfolio tracking
├── api_clients/
│   ├── helius.py           # Solana RPC + enhanced txns
│   ├── birdeye.py          # Price data + OHLCV
│   ├── dexscreener.py      # Pair data
│   ├── defillama.py        # Yields + TVL
│   └── alchemy.py          # EVM RPC
├── security/
│   ├── keystore.py         # Encrypted key management
│   ├── tx_guard.py         # Pre-flight checks
│   └── spending_limits.py  # Rate limiting
├── cron/
│   ├── whale_cron.py       # 5-min whale scanner
│   ├── yield_cron.py       # Hourly yield scanner
│   └── portfolio_cron.py   # Daily portfolio report
└── tests/
    ├── test_whale_tracker.py
    ├── test_yield_scanner.py
    ├── test_portfolio_monitor.py
    └── test_api_clients.py
```

### Week 3-4: Phase 2 Execution

Add swap-executor, lp-manager, liquidation-watcher.

### Week 5-8: Phase 3 Alpha + Intelligence

Add alpha-signal, risk-engine, strategy-backtester.

---

## 12. First User Experience

```
# Day 1: Install
pip install agent-borg[defi]

# Configure
hermes config set borg.defi.helius_api_key "YOUR_KEY"
hermes config set borg.defi.tracked_wallets '["whale1.sol", "whale2.sol"]'
hermes config set borg.defi.alert_channel "telegram"

# Start whale tracking
/defi track whales

# Start yield scanning
/defi scan yields --min-apy 10 --min-tvl 1000000

# Get portfolio report
/defi portfolio 0xYourWallet

# Set up overnight cron
/defi auto --whales 5m --yields 1h --portfolio daily
```

**Telegram output example:**

```
🐋 Whale Alert
🟢 whale_7kD2...x91 bought $1.2M BONK via Jupiter
💰 $1,200,000
📊 Signal: 🔥🔥🔥🔥 (this wallet: 73% win rate, avg +42%)
🔗 solscan.io/tx/...

📈 Yield Alert
🆕 New high-yield: Kamino USDC-SOL LP
📊 APY: 47.2% (was 12.3% yesterday)
💰 TVL: $23.4M
⚠️ Risk: Medium (IL exposure)
🔗 kamino.finance/...

💼 Daily Portfolio
📊 Total: $12,340 (+$234 today, +1.9%)
🟢 SOL: $5,200 (+3.1%)
🟡 BONK: $3,100 (-0.5%)
🟢 USDC-SOL LP: $4,040 (+2.1% fees earned)
⚠️ Alert: SOL is 42% of portfolio (target: <30%)
```

---

## Appendix A: Whale Wallet Starter List

Known profitable wallets (Solana):
- Smart money aggregators from Arkham/Nansen labels
- Top Raydium/Jupiter traders by volume
- VC wallets (a16z, Multicoin, Jump)
- Known influencer wallets (if public)

**These are seed data — the learning loop discovers new profitable wallets automatically.**

## Appendix B: DeFi Error → Strategy Patch Mapping

| Error | Dojo Classification | Auto-Patch |
|-------|-------------------|------------|
| "Slippage exceeded" | slippage_exceeded | Reduce size, add limit order fallback |
| "Route not found" | insufficient_liquidity | Split trade, try alternate DEX |
| "Transaction reverted" | tx_reverted | Check approval, increase gas |
| "Honeypot detected" | rug_detected | Blacklist token, warn collective |
| "Health factor below 1" | liquidation_risk | Auto-repay or add collateral |
| "Pool APY dropped >50%" | yield_decay | Auto-rotate to next best pool |
| "Bridge stuck >1hr" | bridge_timeout | Cancel + retry alternate bridge |
