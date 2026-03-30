# Borg

**Your agent's shared brain. Remembers what worked. Forgets what didn't. Shares the good stuff.**

```bash
pip install agent-borg
```

---

## The Problem

Every AI agent starts from zero. Your agent spends 20 minutes debugging a Docker network issue that another agent solved yesterday. It tries the same bad approach three times because it has no memory. It can't learn from other agents' wins or losses.

**Borg fixes this.** It's a shared cache of proven approaches. When your agent gets stuck, borg gives it the approach that worked last time. When your agent discovers something new, borg saves it so every other agent benefits.

Think: **git for agent reasoning**.

## How It Works

```
Your agent hits a problem
  → borg finds a proven approach (search)
    → previews it (try)
      → applies it step by step (apply)
        → records what happened (feedback)
          → next agent starts smarter
```

That's the whole loop. Approaches get better every time they're used. Bad ones get downranked. Good ones spread.

## Quick Start

```bash
# Find an approach
borg search "docker networking"

# Preview before committing
borg try borg://hermes/systematic-debugging

# Use it
borg apply systematic-debugging --task "Fix container DNS resolution"

# Tell borg what happened
borg feedback <session_id>
```

**MCP (for Claude Code, Cursor, etc):**
```json
{ "mcpServers": { "borg": { "command": "borg-mcp" } } }
```

10 tools: `borg_search`, `borg_pull`, `borg_try`, `borg_init`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_observe`, `borg_convert`.

---

## DeFi Module

**The agent that remembers every trade, learns from every loss, and shares alpha with the collective.**

```bash
pip install agent-borg[defi]
```

Most DeFi bots are stateless — they make the same mistakes forever. Borg DeFi has memory. It tracks what worked, avoids what didn't, and shares winning strategies across agents.

### Zero-Config Scans (Free, No API Keys)

```bash
borg-defi yields          # Top yields from 18,000+ pools
borg-defi tokens          # New token launches in real-time
borg-defi tvl             # Protocol TVL movements — who's gaining, who's bleeding
borg-defi stablecoins     # Depeg detection across 350+ stablecoins
borg-defi scan-all        # Everything at once
```

That's it. No API keys. No setup. Free data from DeFiLlama and DexScreener.

### What You Get on Telegram

Set up cron jobs and get alerts delivered automatically:

```
📈 YIELD HUNTER — 2026-03-30 10:55 UTC

1. 🔥🔥🔥 aerodrome-slipstream | Base
   USDC-CBBTC — APY: 555.9% [DEGEN] ⚠️IL
   TVL: $4.3M | 7d avg: 312.1%

2. 🔥🔥 uniswap-v3 | Ethereum
   WTAO-WETH — APY: 170.8% [HIGH] ⚠️IL
   TVL: $1.9M

💰 Avg APY: 245.3% | Total TVL: $36M
📡 Source: DeFiLlama (18,633 pools scanned)
```

```
💵 STABLECOIN WATCH — 10:55 UTC

========================================
🚨 USYC DEPEGGED — $1.1204 (12.04% above peg)
========================================

  ✅ Tether    | USDT | $184.0B | $0.9991
  ✅ USD Coin  | USDC |  $77.6B | $0.9998
  ✅ Sky Dollar| USDS |   $8.6B | $0.9997

💰 Total stablecoin supply: $296.1B
```

### The Learning Loop

This is what makes borg different from every other DeFi bot:

```
Agent executes trade
    ↓
Dojo classifies: win or loss?
    ↓
Win → pattern extracted, strategy reputation goes up
Loss → failure classified, strategy patched, warning shared
    ↓
Strategy Selector picks best approach next time
    ↓
Collective: winning strategies propagate to ALL agents
```

A bot that loses money on bad slippage does it again tomorrow. Borg DeFi remembers, patches the routing strategy, and warns every other agent running the same approach.

### What's Under the Hood

| Layer | What | Modules |
|-------|------|---------|
| **Signals** | Watch everything | whale_tracker, yield_scanner, alpha_signal, portfolio_monitor |
| **Execution** | Act on signals | swap_executor (Jupiter + 1inch), lp_manager, liquidation_watcher |
| **Risk** | Don't get rekt | risk_engine, strategy_backtester, GoPlus rug detection |
| **MEV Protection** | Don't get frontrun | Jito (Solana), Flashbots (EVM) |
| **Memory** | Learn from outcomes | dojo_bridge, strategy_selector |
| **Delivery** | Get the alpha | Telegram/Discord alerts, cron orchestration |

**9 API clients:** DeFiLlama, DexScreener, Helius, Birdeye, GoPlus, Alchemy, Arkham, Jupiter, 1inch

**Chains:** Solana, Ethereum, Base, Arbitrum, Polygon, Optimism

### API Keys (Optional — Unlocks More)

The free scans work with zero config. API keys unlock richer features:

| API | What It Unlocks | Free Tier |
|-----|----------------|-----------|
| DeFiLlama | Yields, TVL, bridges | ✅ Unlimited |
| DexScreener | Pairs, new tokens | ✅ Unlimited |
| GoPlus | Rug/honeypot detection | ✅ Generous |
| Helius | Solana whale tracking | 100K credits/mo |
| Birdeye | Token prices, OHLCV | 500K credits/mo |
| Alchemy | EVM multi-chain data | 100M CU/mo |
| Arkham | Smart money labels | Limited |

---

## Installation Variants

```bash
pip install agent-borg                 # Core reasoning cache
pip install agent-borg[defi]           # + DeFi scanner & alerts
pip install agent-borg[embeddings]     # + Semantic search
pip install agent-borg[crypto]         # + Ed25519 pack signing
pip install agent-borg[all]            # Everything
```

Python 3.10+. That's it.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│  YOUR AGENT (Hermes, Claude, Cursor, etc)    │
└──────────────┬───────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │    BORG CORE         │
    │                      │
    │  search → try →      │
    │  apply → feedback    │
    │                      │
    │  Packs get better    │
    │  every time they're  │
    │  used                │
    └──────────┬───────────┘
               │
    ┌──────────▼──────────┐
    │    BORG DEFI         │
    │                      │
    │  Signals → Execution │
    │  → Risk → Memory     │
    │                      │
    │  Learns from every   │
    │  trade, shares alpha │
    │  across agents       │
    └──────────┬───────────┘
               │
    ┌──────────▼──────────┐
    │    ON-CHAIN           │
    │  Solana  Ethereum    │
    │  Base    Arbitrum    │
    └──────────────────────┘
```

**Core:** PyYAML only. Everything else is optional.

---

## The Numbers

- **829 tests** across 27 test files
- **~32K lines** of code
- **22 DeFi modules** + 9 API clients + 2 MEV modules
- **4 live cron jobs** scanning free APIs every 30 min
- **E2E tested** against real APIs (DeFiLlama, DexScreener, Jupiter)
- **PBKDF2 keystore** (OWASP compliant, 600K iterations)

---

## Honesty Section

### What Works

- Full CLI with 11 subcommands
- MCP server with 10 tools
- Pack lifecycle: search → try → pull → apply → feedback
- Safety scanner (13 injection patterns, 11 privacy patterns)
- DeFi: live scans returning real data from real APIs
- DeFi: strategy selector that actually learns from trade outcomes
- DeFi: rug detection via GoPlus before any swap

### What Doesn't (Yet)

- **No external users.** The feedback loop hasn't been battle-tested by the community.
- **Reputation engine is advisory.** Computes scores but doesn't enforce access.
- **DeFi execution is unsigned-tx only.** Returns transaction data for external signing — doesn't hold private keys.
- **No funded wallet E2E test.** Never tested a real swap on mainnet.

We'd rather tell you what's missing than pretend it's finished.

---

## Contributing

```bash
# Create a pack
borg init my-workflow

# Convert existing docs
borg convert ./CLAUDE.md --format auto

# Publish
borg publish ~/.hermes/borg/my-workflow/pack.yaml

# Run tests
pip install agent-borg[all]
pytest borg/tests/ borg/defi/tests/
```

---

## Links

- **PyPI:** [pypi.org/project/agent-borg](https://pypi.org/project/agent-borg/)
- **DeFi Spec:** [docs/BORG_DEFI_SPEC.md](docs/BORG_DEFI_SPEC.md)
- **API Audit:** [docs/DEFI_API_AUDIT_2026.md](docs/DEFI_API_AUDIT_2026.md)

---

**v2.5.0** — Borg core + DeFi module. The agent that gets smarter every time it trades.
