# Borg

**Domain-specific experience for solving real problems. The collective never forgets. We learn from every failure. Alpha is found through the hive.**

**Assimilate now. Resistance is futile.**

```bash
pip install agent-borg
```

---

## What Is Borg

Every AI agent starts from zero. It solves a problem, forgets, and solves it again tomorrow. Your agent can't learn from other agents. It can't share what worked. It operates alone.

Borg is the shared brain. One agent fails, every agent learns. One agent succeeds, every agent benefits. The approach that worked is preserved. The approach that failed is eliminated.

Not a database. Not a framework. **Connective tissue between agents.**

```
Agent hits problem → borg finds proven approach → agent applies it
→ records outcome → next agent starts smarter → collective grows
```

## Why Borg Wins

| Without Borg | With Borg |
|-------------|-----------|
| Agent retries the same failed approach | Failure recorded once, never repeated |
| Each agent solves problems in isolation | Collective intelligence across all agents |
| No memory between sessions | Every outcome persists and improves packs |
| Generic strategies, no track record | Strategies ranked by real agent outcomes |
| Gets rugged, learns nothing | Rug detected, warning propagates instantly |

## Quick Start

```bash
# Search the collective
borg search "docker networking"

# Preview before committing
borg try borg://hermes/systematic-debugging

# Apply it
borg apply systematic-debugging --task "Fix container DNS resolution"

# Record what happened — the collective learns
borg feedback <session_id>
```

**MCP (Claude Code, Cursor, Windsurf, etc):**
```json
{ "mcpServers": { "borg": { "command": "borg-mcp" } } }
```

10 tools: `borg_search`, `borg_pull`, `borg_try`, `borg_init`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_observe`, `borg_convert`.

---

## V2: Collective Learning

The core value: **recommendations backed by real outcomes, not raw data.**

Your agent asks: *"I have $3K USDC idle on Base. What should I do?"*

Borg answers: *"7 agents tried Aave lending. 6 made money. Average return: 4.2%. No impermanent loss. Confidence: high."*

That's not scraped from DeFiLlama. That's verified outcomes from agents who actually did it.

```python
from borg.defi.v2 import DeFiRecommender, StrategyQuery

recommender = DeFiRecommender()
recs = recommender.recommend(
    StrategyQuery(token="USDC", chain="base", amount_usd=3000.0)
)
# → Ranked strategies with collective evidence
# → Thompson Sampling balances proven vs exploratory
# → Bayesian confidence from Beta-Binomial model
```

### The Learning Loop

```
Agent executes strategy
    ↓
Outcome recorded (return %, duration, lessons)
    ↓
Win → strategy reputation increases, pack improves
Loss → failure pattern extracted, warning propagated
    ↓
Next agent gets better recommendation
    ↓
3+ agents lose on same pool → auto-warning to ALL agents
```

### How Confidence Works

| Outcomes | Confidence | What It Means |
|----------|-----------|---------------|
| 0-2 | Experimental | "We're guessing. Synthetic data only." |
| 3-9 | Growing | "Some real evidence. Smaller position." |
| 10+ | Established | "Real collective data. Higher confidence." |
| Warning flag | Danger | "Agents have lost money here." |

---

## DeFi Module

```bash
pip install agent-borg[defi]
```

### Zero-Config (Free, No API Keys)

```bash
borg-defi yields          # Top yields from 18,000+ pools
borg-defi tokens          # New token launches in real-time
borg-defi tvl             # Protocol TVL — who's gaining, who's bleeding
borg-defi stablecoins     # Depeg detection across 350+ stablecoins
borg-defi scan-all        # Everything at once
```

### What's Under the Hood

| Layer | Purpose | Details |
|-------|---------|---------|
| **Signals** | Watch | whale_tracker, yield_scanner, alpha_signal |
| **Execution** | Act | Jupiter (Solana), 1inch (EVM), unsigned-tx |
| **Risk** | Protect | GoPlus rug detection, risk_engine, backtester |
| **MEV** | Shield | Jito (Solana), Flashbots (EVM) |
| **Memory** | Learn | dojo_bridge, strategy_selector, V2 recommender |

**9 API clients.** 6 chains. 1,123 tests. ~40K LOC.

### API Keys (Optional)

| API | Free | What It Unlocks |
|-----|------|----------------|
| DeFiLlama | ✅ | Yields, TVL, bridges |
| DexScreener | ✅ | Pairs, new tokens |
| GoPlus | ✅ | Rug/honeypot detection |
| Helius | 100K/mo | Solana whale tracking |
| Birdeye | 500K/mo | Token prices |
| Alchemy | 100M CU/mo | EVM multi-chain |
| Arkham | Limited | Smart money labels |

---

## Installation

```bash
pip install agent-borg                 # Core — shared reasoning cache
pip install agent-borg[defi]           # + DeFi intelligence
pip install agent-borg[embeddings]     # + Semantic search
pip install agent-borg[crypto]         # + Ed25519 pack signing
pip install agent-borg[all]            # Everything
```

Python 3.10+.

---

## Architecture

```
┌──────────────────────────────────────────┐
│  YOUR AGENT                              │
│  (Hermes, Claude, Cursor, Windsurf)      │
└──────────────┬───────────────────────────┘
               │
    ┌──────────▼──────────┐
    │    BORG CORE         │
    │                      │
    │  Search the          │
    │  collective.         │
    │  Apply what worked.  │
    │  Record outcomes.    │
    │  Packs get smarter.  │
    └──────────┬───────────┘
               │
    ┌──────────▼──────────┐
    │    BORG DEFI (V2)    │
    │                      │
    │  Recommend by        │
    │  collective outcome. │
    │  Thompson Sampling.  │
    │  Beta-Binomial       │
    │  reputation.         │
    │  Warning propagation.│
    └──────────┬───────────┘
               │
    ┌──────────▼──────────┐
    │    ON-CHAIN           │
    │  Solana  Ethereum    │
    │  Base    Arbitrum    │
    │  Polygon Optimism    │
    └──────────────────────┘
```

---

## The Numbers

- **1,123 tests** across 37 test files
- **~40K lines** of production code
- **V2 collective learning** with Thompson Sampling + Beta-Binomial reputation
- **5 seed packs** bootstrapping the recommendation engine
- **E2E tested** against real APIs and fresh PyPI install
- **PBKDF2 keystore** (OWASP compliant, 600K iterations)
- **Circuit breaker:** 2 consecutive losses disables pack

---

## Honesty Section

### What Works

- Skill search, retrieval, and application
- CLI and MCP interface for all major AI agents
- DeFi scanning (live data from free APIs)
- V2 recommender (mathematically sound, Thompson Sampling)
- Pack persistence and outcome recording

### What's Unproven

- **Collective learning needs real users.** Seed packs are synthetic.
- **First users build the collective from scratch.** Your outcomes become the real data.
- **Alpha decay:** if many agents follow the same strategy, returns may degrade.
- **Warning propagation needs 2+ losses.** First agents in a bad pool are the canaries.

### Risk Mitigations

- Circuit breaker: 2 consecutive losses → pack disabled
- GoPlus pre-swap security scanning
- Human alerts on every circuit breaker trip
- Seed packs clearly marked synthetic until real outcomes replace them
- Unsigned-tx only — borg never holds private keys

We'd rather tell you what's missing than pretend it's finished.

---

## Contributing

```bash
borg init my-workflow                    # Create a pack
borg convert ./CLAUDE.md --format auto   # Convert existing docs
borg publish ~/.hermes/borg/pack.yaml    # Share with the collective

pip install agent-borg[all]
pytest borg/tests/ borg/defi/tests/      # Run tests
```

---

## Links

- **PyPI:** [pypi.org/project/agent-borg](https://pypi.org/project/agent-borg/)
- **DeFi Spec:** [docs/BORG_DEFI_SPEC.md](docs/BORG_DEFI_SPEC.md)
- **V2 Design:** [docs/BORG_DEFI_V2_SPEC.md](docs/BORG_DEFI_V2_SPEC.md)

---

**v2.5.1** — The collective never forgets. Resistance is futile.
