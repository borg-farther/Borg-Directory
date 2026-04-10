# Borg DeFi V2 — Collective Learning Design

**Status:** Design Draft
**Date:** 2026-03-30
**Author:** Hermes Agent

---

## Executive Summary

The current DeFi module is a data firehose. It watches whales, scans yields, monitors positions — all stateless, all isolated. The 22 modules and 829 tests produce a Bloomberg terminal, not an intelligent agent.

**The core insight**: The agent should ask "what worked for others like me?" not "what does the data say?"

The design that follows replaces the data firehose with a **collective learning system** where:
- Every recommendation is backed by real PnL outcomes from other agents
- The agent says "I have $3K USDC idle on Base" and gets back ranked strategies with evidence
- Outcome feedback automatically improves pack reputation

---

## 1. The Fundamental Shift

### Current State (V1): Data-First Architecture

```
Agent → [Whale Tracker] → Whale alerts
Agent → [Yield Scanner] → APY rankings
Agent → [Portfolio Monitor] → Position list
Agent → [Risk Engine] → Risk scores
Agent → [Swap Executor] → Execute trades

The agent makes decisions based on:
- Raw APY numbers
- Whale movement data
- Price feeds
- TVL figures

No collective memory. No outcome correlation. No learned best practices.
```

### V2 State: Outcome-First Architecture

```
Agent → "borg, $3K USDC idle on Base, what should I do?"
                    ↓
         [Collective Query Engine]
                    ↓
   ┌─────────────────────────────────────────┐
   │ Ranked strategies with evidence:        │
   │                                         │
   │ 1. Kamino USDC-SOL CLMM                 │
   │    7 agents used this. 5 profitable.    │
   │    Avg return: 23% (7-day avg).          │
   │    IL risk: moderate. Exit at 7 days.   │
   │                                         │
   │ 2. Aave USDC lending                    │
   │    12 agents. 11 profitable.             │
   │    Avg return: 4.2% (30-day).            │
   │    No IL. Low risk.                      │
   └─────────────────────────────────────────┘
                    ↓
         Agent executes strategy
                    ↓
         [Outcome recorded to Borg]
                    ↓
         [Pack reputation updated]
```

---

## 2. Core Principles

### 2.1 Agent-First API

The interface is designed for what an AI agent needs, not a human dashboard. Every question the agent asks should be answerable in a single call.

**The fundamental query:**

```python
@dataclass
class StrategyQuery:
    token: str           # "USDC", "SOL", "BTC"
    chain: str           # "base", "solana", "ethereum"
    amount_usd: float    # 3000.0
    risk_tolerance: str # "low", "medium", "high"
    duration_hours: Optional[int] = None  # for yield strategies
```

**The fundamental response:**

```python
@dataclass
class StrategyRecommendation:
    pack_id: str
    rank: int
    
    # Collective evidence
    agent_count: int           # How many agents tried this
    profitable_count: int       # How many made money
    avg_return_pct: float      # Average return across agents
    avg_duration_hours: float  # Average hold time
    
    # Strategy details
    protocol: str
    action: str                # "lend", "lp", "stake", "swap-to-yield"
    position_size_pct: float   # Recommended % of capital
    expected_apy: float        # From collective outcomes
    
    # Risk signals
    il_risk: bool
    exit_guidance: str         # "exit at 7 days", "no exit needed"
    rug_warnings: List[str]    # Active warnings from collective
    
    # Raw confidence
    confidence: float          # 0-1 based on sample size and variance
```

### 2.2 Every Recommendation Backed by Real Outcomes

No APY from DeFiLlama. No TVL from Dune. Only:

- What agents **actually earned**
- What agents **actually exited at**
- What agents **actually lost money on**

The data comes from the collective, not from data providers.

### 2.3 Minimal Moving Parts

**V1 had 22 modules:**
- whale-tracker, yield-scanner, portfolio-monitor, swap-executor, lp-manager, liquidation-watcher, alpha-signal, risk-engine, strategy-backtester, ... (18 more)

**V2 has 3 operational modes:**

| Mode | Purpose | Complexity |
|------|---------|------------|
| **Query** | Get strategy recommendations | O(1) |
| **Execute** | Record execution, return outcome after duration | O(1) |
| **Feedback** | Process outcome, update pack reputation | O(1) |

The data modules (whale tracking, yield scanning) become **optional** — the agent can still use them for alpha, but they're no longer the core value proposition.

---

## 3. Pack Structure for DeFi Strategies

### 3.1 Strategy Pack YAML

```yaml
# kamino-usdc-sol-clmm-v1
id: defi-yield/kamino-usdc-sol-clmm
name: Kamino USDC-SOL Concentrated Liquidity
version: 1.0.3

problem_class: yield-farming
description: >
  Provide concentrated liquidity on Kamino Finance for USDC-SOL pair.
  Best for stable-ish assets with range-bound price action.

# Entry criteria (when to use this strategy)
entry:
  token_in: USDC
  chain: base
  min_tvl_usd: 1_000_000
  max_risk_score: 0.6
  suggested_duration_hours: 168  # 7 days

# What to do
action:
  type: provide-clmm
  protocol: kamino
  pool: USDC-SOL
  range_mode: symmetric  # or "asymmetric"
  range_width_pct: 10   # ±5% from current price

# Exit criteria
exit:
  type: time_based
  guidance: "Exit at 7 days or when IL exceeds yield earned"
  hard_stop: 14  # days — auto-deprecate if still in position

# Collective outcome data (updated by agents)
collective:
  sample_size: 7
  profitable_count: 5
  avg_return_pct: 23.4
  avg_return_pct_after_il: 18.2
  avg_duration_hours: 162
  std_dev_return: 12.3
  min_return: -8.5
  max_return: 41.2
  
  # Loss analysis
  loss_count: 2
  loss_reasons:
    - "exited late at 21 days, IL destroyed gains"
    - "entered at range top, IL from SOL pump"

# Risk assessment (from collective data)
risk:
  il_risk: moderate
  impermanent_loss_estimate: -5 to -15%
  rug_probability: 0.0  # kamino is battle-tested
  smart_money_signal: neutral

# Metadata
metadata:
  chains: [solana]
  protocols: [kamino]
  tokens: [USDC, SOL]
  risk_tolerance: medium
  updated_at: 2026-03-29T12:00:00Z
  source: collective-outcomes

# Provenance
provenance:
  confidence: high
  evidence: "7 agents reported outcomes over 14 days"
  author_agent: borg-collective
```

### 3.2 Outcome Record (Written by Agents After Execution)

```yaml
# Outcome submitted by agent after position close
outcome_id: outcome-2026-03-30-001
pack_id: defi-yield/kamino-usdc-sol-clmm
agent_id: hermes-prod-001

# What the agent did
execution:
  entered_at: 2026-03-23T08:00:00Z
  exited_at: 2026-03-28T14:00:00Z
  duration_hours: 126
  token_in: USDC
  amount_usd: 3000.0
  actual_return_pct: 19.2
  actual_return_usd: 576.0

# Whether it matched collective prediction
result:
  profitable: true
  vs_expected_return_pct: 18.2  # collective avg
  vs_expected_return_pct_delta: +1.0  # slightly better
  
# Lessons learned
lessons:
  - "entered at mid-range, good timing"
  - "price stayed in range 95% of time"
  - "would exit at 7 days next time (120 hours was enough)"

# Raw numbers (not shared, used for aggregate stats)
raw:
  entry_price_sol: 142.50
  exit_price_sol: 148.20
  fees_earned_usd: 420.0
  il_usd: -144.0
  net_usd: 576.0
```

### 3.3 Risk/Warning Pack

```yaml
# Warning: Token or protocol has negative collective evidence
id: defi-warning/raydium-v3-rug
type: rug_warning
severity: critical

warning_for:
  protocol: raydium
  chain: solana
  pool: RAY-USDC

collective_evidence:
  agents_affected: 3
  total_lost_usd: 8472.0
  pattern: "cannot sell more than 10% of position"
  
description: >
  3 agents attempted to exit Raydium V3 USDC pool. 
  All 3 got stuck — transaction reverts when selling >10% of position.
  Honeypot pattern confirmed.

guidance: "Avoid this pool. Exit immediately if position held."

propagated_at: 2026-03-28T00:00:00Z
expires_at: 2026-04-04T00:00:00Z  # 7 days
```

---

## 4. The Borg Query Interface

### 4.1 Core Function Signature

```python
def borg_defi_recommend(
    query: StrategyQuery,
    limit: int = 5
) -> List[StrategyRecommendation]:
    """
    Get strategy recommendations backed by collective outcomes.
    
    Args:
        query: Token, chain, amount, risk tolerance
        limit: Max number of strategies to return (default 5)
    
    Returns:
        Ranked list of strategies with outcome evidence
    """
```

### 4.2 Internal Flow

```
borg_defi_recommend(query)
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 1. Load all strategy packs with matching entry criteria     │
│    - chain matches query.chain                              │
│    - token_in matches query.token                           │
│    - risk_tolerance <= query.risk_tolerance                 │
│    - pool TVL >= entry.min_tvl_usd                          │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Filter by collective outcome quality                     │
│    - Must have collective.sample_size >= 3                 │
│    - Exclude packs with active rug_warnings                 │
│    - Exclude packs with confidence < 0.3                   │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Score and rank                                           │
│    score = (avg_return_pct * 0.4) +                         │
│            (win_rate * 0.3) +                               │
│            (confidence * 0.2) +                             │
│            (1 / (1 + std_dev_return) * 0.1)                 │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Enrich with risk signals                                 │
│    - Check for active warnings affecting protocol/chain     │
│    - Add exit_guidance from pack                             │
│    - Add position_size_pct from pack                        │
└──────────────────────────────────────────────────────────────┘
       │
       ▼
   Return top `limit` strategies as StrategyRecommendation[]
```

### 4.3 Example Conversation

**Agent asks:**
```python
recommendations = borg_defi_recommend(
    query=StrategyQuery(
        token="USDC",
        chain="base",
        amount_usd=3000.0,
        risk_tolerance="medium",
        duration_hours=None
    )
)
```

**Agent receives:**
```
1. Kamino USDC-SOL CLMM (Base)
   7 agents | 5 profitable | Avg: 23.4% | Exit: 7 days
   
2. Aave USDC Lending (Base)  
   12 agents | 11 profitable | Avg: 4.2% | No IL

3. Compound USDC (Ethereum)
   8 agents | 7 profitable | Avg: 3.8% | No IL

4. [Excluded: Raydium pool — has active rug warning]
```

---

## 5. The Feedback Loop

### 5.1 Recording an Execution

```python
def borg_defi_record_outcome(outcome: ExecutionOutcome) -> None:
    """
    Record what happened after executing a strategy.
    
    The outcome is aggregated into the pack's collective data.
    After 3+ outcomes, the pack's confidence increases.
    After 10+ outcomes, the pack becomes a primary recommendation.
    
    Args:
        outcome: The result of executing a strategy
    """
```

### 5.2 Outcome Aggregation Logic

```python
def _update_collective_stats(pack_id: str, new_outcome: ExecutionOutcome):
    """Update pack's collective statistics with new outcome."""
    
    pack = load_pack(pack_id)
    
    # Append to outcomes list
    pack.collective.outcomes.append(new_outcome)
    
    # Recalculate aggregate stats
    all_returns = [o.actual_return_pct for o in pack.collective.outcomes]
    profitable = [o for o in pack.collective.outcomes if o.profitable]
    
    pack.collective.sample_size = len(pack.collective.outcomes)
    pack.collective.profitable_count = len(profitable)
    pack.collective.avg_return_pct = mean(all_returns)
    pack.collective.std_dev_return = stdev(all_returns)
    
    # Update guidance based on lessons
    if new_outcome.profitable and new_outcome.lessons:
        # Extract positive lessons
        for lesson in new_outcome.lessons:
            if "exit at" in lesson:
                # Update exit guidance if agent found better timing
                update_exit_guidance(pack, lesson)
    
    if not new_outcome.profitable:
        # Record failure pattern
        pack.collective.loss_count += 1
        for reason in new_outcome.loss_reasons:
            add_loss_pattern(pack, reason)
        
        # If loss pattern repeats, add warning
        if detect_common_loss_pattern(pack) > 2:
            propagate_warning(pack)
    
    save_pack(pack)
```

### 5.3 Automatic Pack Improvement

**From raw outcomes to improved guidance:**

```python
# Example: Before
exit_guidance: "Exit at 7 days or when IL exceeds yield earned"

# After 7 agents report outcomes with timing data:
exit_guidance: "Exit at 5-7 days. Agents who exited at 10+ days had 40% higher IL."

# Loss pattern detection:
# 3 agents entered Raydium pool late, all lost.
# Pattern detected → pack deprecated for Raydium
# Warning propagated to collective
```

---

## 6. User Communication

### 6.1 What the Agent Tells the User

**On idle capital (Telegram message):**

```
You have $3,000 USDC idle on Base.

Best strategy from collective evidence:
• Kamino USDC-SOL CLMM
  7 agents tried this. 5 made money.
  Average return: 23% (7-day average)
  Impermanent loss: moderate risk
  Suggestion: Enter with 50% of capital ($1,500)
  Exit guidance: 7 days max

• Aave USDC Lending (safer)
  12 agents. 11 profitable.
  Average return: 4.2% (30-day)
  No IL risk. Enter with up to 100%.

Which do you want to proceed with?
```

**On position update (Telegram message):**

```
Your Kamino USDC-SOL position:
• Current value: $1,842 (+12.4% since entry)
• Days in position: 5/7 recommended
• IL risk: Increasing as SOL price rises

Collective guidance: Consider exiting at day 7.
3 agents who held past 10 days saw higher IL than earned fees.

Action recommended: [Exit] [Hold] [Add more]
```

**On rug warning (Telegram message):**

```
⚠️ COLLECTIVE WARNING
Raydium USDC pool has rug pattern detected.
3 agents unable to exit positions.
DO NOT enter this pool. Exit if held.
```

### 6.2 When to Communicate

| Event | Trigger | Message |
|-------|---------|---------|
| Idle capital detected | On wallet scan | Recommend strategies with evidence |
| Position entry executed | On swap confirmation | Confirm with expected exit timing |
| Position approaching exit | At 80% of duration | Alert with collective guidance |
| Yield drop detected | APY drops >20% | Alert with alternative strategies |
| Rug warning | On collective propagation | Immediate alert if held |

---

## 7. Simplest Implementation (80% of Value)

### 7.1 Core Classes

```python
# borg/defi/v2/recommender.py
@dataclass
class StrategyQuery:
    token: str
    chain: str
    amount_usd: float
    risk_tolerance: str = "medium"
    duration_hours: Optional[int] = None

@dataclass
class StrategyRecommendation:
    pack_id: str
    rank: int
    agent_count: int
    profitable_count: int
    avg_return_pct: float
    avg_duration_hours: float
    protocol: str
    action: str
    position_size_pct: float
    expected_apy: float
    il_risk: bool
    exit_guidance: str
    rug_warnings: List[str]
    confidence: float

class DeFiRecommender:
    """Query collective outcomes for strategy recommendations."""
    
    def __init__(self, packs_dir: Path):
        self.packs_dir = packs_dir
    
    def recommend(
        self, 
        query: StrategyQuery, 
        limit: int = 5
    ) -> List[StrategyRecommendation]:
        """Return ranked strategies with collective evidence."""
        
        # Load matching packs
        packs = self._load_matching_packs(query)
        
        # Filter by quality
        packs = [p for p in packs if p.collective.sample_size >= 3]
        packs = [p for p in packs if not self._has_rug_warning(p)]
        
        # Score and rank
        scored = []
        for pack in packs:
            score = self._calculate_score(pack)
            rec = self._to_recommendation(pack, score)
            scored.append(rec)
        
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]
    
    def record_outcome(self, outcome: ExecutionOutcome) -> None:
        """Record an execution outcome and update pack."""
        
        pack = self._load_pack(outcome.pack_id)
        
        # Update collective stats
        pack.collective.outcomes.append(outcome)
        self._recalculate_stats(pack)
        
        # Generate/update guidance
        self._update_guidance(pack)
        
        # Check for warning propagation
        if pack.collective.loss_count >= 3:
            self._check_loss_patterns(pack)
        
        self._save_pack(pack)

# borg/defi/v2/pack.py
@dataclass
class DeFiStrategyPack:
    id: str
    name: str
    version: str
    
    entry: EntryCriteria
    action: ActionSpec
    exit: ExitGuidance
    
    collective: CollectiveStats
    risk: RiskAssessment
    
    metadata: Metadata
    provenance: Provenance

@dataclass  
class CollectiveStats:
    outcomes: List[ExecutionOutcome]
    sample_size: int = 0
    profitable_count: int = 0
    avg_return_pct: float = 0.0
    std_dev_return: float = 0.0
    loss_count: int = 0
    loss_patterns: List[str] = field(default_factory=list)

@dataclass
class ExecutionOutcome:
    outcome_id: str
    pack_id: str
    agent_id: str
    entered_at: datetime
    exited_at: datetime
    duration_hours: float
    token_in: str
    amount_usd: float
    actual_return_pct: float
    actual_return_usd: float
    profitable: bool
    lessons: List[str] = field(default_factory=list)
    loss_reasons: List[str] = field(default_factory=list)
```

### 7.2 File Structure

```
~/.hermes/borg/defi-v2/
├── packs/
│   ├── kamino-usdc-sol-clmm/
│   │   └── pack.yaml
│   ├── aave-usdc-lending/
│   │   └── pack.yaml
│   └── defi-warning/
│       ├── raydium-rug/
│       │   └── pack.yaml
│       └── [other warnings]
├── outcomes/
│   ├── 2026-03/
│   │   ├── outcome-001.yaml
│   │   └── outcome-002.yaml
│   └── [archived by month]
└── config.yaml
```

### 7.3 Public API

```python
# Single file: borg/defi/v2/api.py

from borg.defi.v2 import (
    StrategyQuery,
    StrategyRecommendation,
    DeFiRecommender,
    ExecutionOutcome,
    WarningSeverity,
)

# Agent interface
recommender = DeFiRecommender()

# Get recommendations
recs = recommender.recommend(
    StrategyQuery(
        token="USDC",
        chain="base", 
        amount_usd=3000.0,
        risk_tolerance="medium"
    )
)

# Record execution
recommender.record_outcome(
    ExecutionOutcome(
        outcome_id="outcome-001",
        pack_id="defi-yield/kamino-usdc-sol-clmm",
        agent_id="hermes-prod-001",
        entered_at=datetime.utcnow() - timedelta(days=5),
        exited_at=datetime.utcnow(),
        duration_hours=120,
        token_in="USDC",
        amount_usd=1500.0,
        actual_return_pct=18.2,
        actual_return_usd=273.0,
        profitable=True,
        lessons=["entered mid-range", "price stayed in range 95% of time"]
    )
)

# Check warnings
warnings = recommender.get_active_warnings(chain="solana", protocol="raydium")
```

### 7.4 Borg Integration

```python
# borg/defi/v2/borg_integration.py

def borg_search_defi(query: str) -> str:
    """Bridge to existing borg search for DeFi context.
    
    Allows the agent to ask:
    - "what yield strategies worked on base?"
    - "show me DeFi packs with >20% avg return"
    - "any rug warnings active?"
    """
    recommender = DeFiRecommender()
    
    if "rug warning" in query.lower():
        warnings = recommender.get_all_warnings()
        return format_warnings(warnings)
    
    # Parse query into StrategyQuery
    parsed = parse_defi_query(query)
    recs = recommender.recommend(parsed)
    
    return format_recommendations(recs)
```

---

## 8. How This Differs from V1

| Aspect | V1 (Data Firehose) | V2 (Collective Learning) |
|--------|-------------------|--------------------------|
| **Core question** | "What does the data say?" | "What worked for others like me?" |
| **Yield data source** | DeFiLlama API | Collective agent outcomes |
| **Strategy selection** | APY ranking, TVL filtering | Win rate, avg return, confidence |
| **Risk signals** | GoPlus security scans | Actual rug detections from agents |
| **Entry guidance** | Manual research | Collective timing data |
| **Exit guidance** | User decides | "Agents who exited at X days had Y result" |
| **Learning** | Per-agent, isolated | Shared across all agents |
| **Whale tracking** | Alert on any whale move | "Which whales predicted price moves?" |
| **Module count** | 22 modules | 3 operational modes |

### Why V2 is Better

1. **No data source dependency**: The system doesn't need DeFiLlama to function. If the API goes down, collective outcomes still work.

2. **Self-calibrating**: The system gets more accurate as more agents use it. More agents → more outcomes → better recommendations.

3. **Real risk signals**: Instead of "this token might be a rug" (GoPlus), the system says "3 agents got stuck trying to exit this pool."

4. **Actionable guidance**: "7 agents entered. 5 made money. Exit at 7 days." vs. "APY: 42%. TVL: $10M. Risk: medium."

5. **Alpha propagation**: When an agent discovers a profitable strategy, it's automatically available to all other agents.

---

## 9. Implementation Phases

### Phase 1: Core (1 week)

```python
# Files to create/modify
borg/defi/v2/
├── api.py              # Main public interface
├── pack.py             # Data structures
├── recommender.py      # Core query engine
├── pack_store.py       # Load/save packs
├── outcome_store.py    # Load/save outcomes
└── __init__.py

# Modify
borg/defi/__init__.py   # Export v2 API
```

**Deliverable**: Agent can query `recommender.recommend(query)` and get ranked strategies with collective evidence.

### Phase 2: Outcome Recording (1 week)

```python
# New files
borg/defi/v2/
├── outcome_recorder.py  # Record execution outcomes
├── stats_calculator.py  # Recalculate aggregate stats
└── guidance_updater.py  # Update exit guidance from lessons
```

**Deliverable**: Agent can call `record_outcome()` and see pack stats update in real-time.

### Phase 3: Borg Integration (3 days)

```python
# Modify
borg/defi/v2/borg_integration.py  # Bridge to borg_search
borg/core/search.py              # Add DeFi search mode
```

**Deliverable**: `borg_search("yield strategies base USDC")` returns collective recommendations.

### Phase 4: Warning Propagation (2 days)

```python
# New files
borg/defi/v2/warning_manager.py  # Detect and propagate warnings
```

**Deliverable**: When 3+ agents lose on same pool, warning auto-propagates to all agents.

---

## 10. Migration from V1

### What to Keep

- Wallet readers (Helius/Alchemy) — still needed to know idle capital
- Swap execution (Jupiter/1inch) — still needed to execute
- MEV protection (Jito/Flashbots) — still needed for execution quality

### What to Deprecate

- `whale_tracker` module → replace with collective "which whales predicted moves"
- `yield_scanner` module → replace with collective outcomes query
- `risk_engine` (scanner part) → replace with collective rug warnings
- `alpha_signal` module → replace with collective pattern detection

### What to Keep as Optional

- `portfolio_monitor` → still useful for the "what do I have?" question
- `liquidation_watcher` → useful alpha but not core to collective learning

### Migration Path

```python
# Old way
from borg.defi.yield_scanner import YieldScanner
scanner = YieldScanner()
opportunities = await scanner.scan_defillama()
# Filter by APY, TVL, risk manually

# New way  
from borg.defi.v2 import DeFiRecommender, StrategyQuery
recommender = DeFiRecommender()
recs = recommender.recommend(
    StrategyQuery(token="USDC", chain="base", amount_usd=3000.0)
)
# recs already filtered and ranked by collective outcomes
```

---

## 11. Concrete YAML Examples

### A. High-Quality Pack (Ready for Production)

```yaml
# defi-yield/aave-usdc-base
id: defi-yield/aave-usdc-base
name: Aave USDC Lending (Base)
version: 1.0.2

entry:
  token_in: USDC
  chain: base
  min_tvl_usd: 5_000_000
  max_risk_score: 0.3

action:
  type: lend
  protocol: aave-v3
  position_type: variable-rate-lending

exit:
  type: anytime
  guidance: "No lock. Withdraw anytime. Ideal for idle USDC."

collective:
  sample_size: 12
  profitable_count: 11
  avg_return_pct: 4.2
  avg_return_pct_after_il: 4.2  # no IL for lending
  avg_duration_hours: 720
  std_dev_return: 1.2
  min_return: 3.1
  max_return: 5.8
  loss_count: 1
  loss_reasons:
    - "socialized loss due to bad debt from huge liquidation"

risk:
  il_risk: false
  rug_probability: 0.0
  smart_money_signal: high

metadata:
  chains: [base, ethereum, arbitrum]
  protocols: [aave-v3]
  tokens: [USDC]
  risk_tolerance: low
  updated_at: 2026-03-29T00:00:00Z
```

### B. Pack Needing More Data

```yaml
# defi-yield/new-pool-xyz
id: defi-yield/new-pool-xyz
name: New Protocol XYZ LP
version: 1.0.0

entry:
  token_in: USDC
  chain: base
  min_tvl_usd: 100_000
  max_risk_score: 0.7

action:
  type: lp
  protocol: xyz-finance
  pool: USDC-WETH

exit:
  type: time_based
  guidance: "No data yet. Recommend waiting for more outcomes."
  hard_stop: 30

collective:
  sample_size: 2
  profitable_count: 1
  avg_return_pct: 8.5
  avg_return_pct_after_il: 6.2
  avg_duration_hours: 96
  std_dev_return: 0.0
  min_return: -2.3
  max_return: 19.3
  loss_count: 1
  loss_reasons:
    - "IL from ETH pump during 48h hold"

risk:
  il_risk: high
  rug_probability: 0.3  # new protocol, higher risk
  smart_money_signal: unknown

metadata:
  chains: [base]
  protocols: [xyz-finance]
  tokens: [USDC, WETH]
  risk_tolerance: high
  updated_at: 2026-03-28T00:00:00Z
  confidence_status: low-sample
```

### C. Deprecated Pack (Rugging)

```yaml
# defi-warning/xyz-rugged
id: defi-warning/xyz-rugged
type: rug_warning
severity: critical

warning_for:
  protocol: xyz-finance
  chain: base
  pool: USDC-WETH

collective_evidence:
  agents_affected: 4
  total_lost_usd: 12840.0
  pattern: "Owner can pause trading. All exits reverted."
  
description: >
  4 agents entered xyz-finance USDC-WETH pool. 
  When attempting to exit, all transactions reverted.
  Owner had pause function that blocked all trades.
  Funds permanently stuck.

guidance: "DO NOT ENTER. If position held, cannot exit."

propagated_at: 2026-03-27T00:00:00Z
expires_at: 2026-04-03T00:00:00Z

# This pack also marks the strategy pack as deprecated
affected_strategy_packs:
  - defi-yield/xyz-usdc-lp
```

---

## 12. Error Handling

### Empty Collective (No Outcomes Yet)

```python
if pack.collective.sample_size < 3:
    return StrategyRecommendation(
        ...
        confidence=0.1,
        exit_guidance="No collective data yet. High uncertainty.",
        rug_warnings=[]
    )
```

### Conflicting Outcomes (High Variance)

```python
if pack.collective.std_dev_return > 20:
    # Large variance — add warning
    exit_guidance = (
        f"High variance in outcomes (std={pack.collective.std_dev_return:.1f}%). "
        f"Some agents lost {pack.collective.min_return:.1f}%, others made {pack.collective.max_return:.1f}%. "
        f"Recommended: smaller position size (20% of capital)."
    )
```

### Sample Size vs. Confidence

| Sample Size | Confidence | Action |
|-------------|------------|--------|
| 0-2 | 0.0-0.2 | Show but mark as experimental |
| 3-5 | 0.2-0.4 | Include with warning |
| 6-9 | 0.4-0.6 | Include as secondary option |
| 10+ | 0.6-1.0 | Include as primary recommendation |

---

## 13. Privacy and Security

### What is NOT Shared

- Wallet addresses
- Private keys
- Specific dollar amounts (only % returns)
- Agent identities (only aggregate counts)

### What IS Shared

- Strategy outcomes (return %, duration)
- Loss patterns (what went wrong)
- Warning signals (rug detected, pool unsafe)
- Entry/exit timing patterns

### Data Model for Privacy

```python
# NOT shared (kept local only)
local_data:
  wallet_address: "..."  # Never shared
  specific_amount: 3000   # Never shared
  agent_identity: "..."   # Never shared

# Shared (only aggregate)
collective_data:
  avg_return_pct: 23.4   # ✅ Percentage only
  duration_hours: 168     # ✅ Timing only
  profitable_count: 5     # ✅ Count only
  loss_pattern: "exited late"  # ✅ Pattern only
```

---

## 14. Testing Strategy

### Unit Tests (Core Logic)

```python
# test_recommender.py
def test_recommend_filters_by_chain():
    recommender = DeFiRecommender(packs_dir=test_packs)
    recs = recommender.recommend(
        StrategyQuery(token="USDC", chain="ethereum", ...)
    )
    assert all(r.chain == "ethereum" for r in recs)

def test_recommend_excludes_rug_warnings():
    recommender = DeFiRecommender(packs_dir=test_packs)
    recs = recommender.recommend(
        StrategyQuery(token="USDC", chain="base", ...)
    )
    assert "raydium" not in [r.protocol for r in recs]

def test_recommend_ranked_by_collective_score():
    recommender = DeFiRecommender(packs_dir=test_packs)
    recs = recommender.recommend(...)
    assert recs[0].avg_return_pct >= recs[1].avg_return_pct

def test_outcome_recording_updates_stats():
    recommender = DeFiRecommender(packs_dir=test_packs)
    initial = recommender.get_pack("test-pack").collective.sample_size
    
    recommender.record_outcome(outcome)
    
    updated = recommender.get_pack("test-pack").collective.sample_size
    assert updated == initial + 1
```

### Integration Tests (Borg Bridge)

```python
# test_borg_integration.py
def test_borg_search_defi_yield():
    result = borg_search_defi("yield strategies on base")
    assert "recommendations" in result or "strategies" in result

def test_warning_propagation():
    # Create 3 losses on same pool
    record_loss("pool-a")
    record_loss("pool-a")
    record_loss("pool-a")
    
    # Warning should auto-generate
    warnings = get_active_warnings()
    assert any(w.protocol == "pool-a" for w in warnings)
```

---

## 15. Metrics for Success

### Day 1 (Launch)
- [ ] 0 outcome records in system
- [ ] 5 strategy packs loaded with historical data
- [ ] `recommend()` returns results in <100ms

### Week 1
- [ ] 50 outcomes recorded
- [ ] At least one pack reaches confidence 0.6+
- [ ] No false rug warnings propagated

### Month 1
- [ ] 500 outcomes recorded
- [ ] 10 packs with confidence 0.6+
- [ ] 0 rug incidents without warning
- [ ] Agent can query and get recommendation in 1 line of code

### Success Criteria

| Metric | Target |
|--------|--------|
| Outcome recording rate | >10/day |
| Avg recommendation response time | <100ms |
| Pack confidence at 6+ samples | >0.6 |
| Warning propagation accuracy | >90% |
| Agent adoption | 3+ agents using |

---

## 16. Appendices

### A. Complete Class Diagram

```
StrategyQuery
├── token: str
├── chain: str
├── amount_usd: float
├── risk_tolerance: str
└── duration_hours: Optional[int]

StrategyRecommendation
├── pack_id: str
├── rank: int
├── agent_count: int
├── profitable_count: int
├── avg_return_pct: float
├── avg_duration_hours: float
├── protocol: str
├── action: str
├── position_size_pct: float
├── expected_apy: float
├── il_risk: bool
├── exit_guidance: str
├── rug_warnings: List[str]
└── confidence: float

DeFiStrategyPack
├── id: str
├── name: str
├── version: str
├── entry: EntryCriteria
├── action: ActionSpec
├── exit: ExitGuidance
├── collective: CollectiveStats
├── risk: RiskAssessment
└── metadata: Metadata

ExecutionOutcome
├── outcome_id: str
├── pack_id: str
├── agent_id: str
├── entered_at: datetime
├── exited_at: datetime
├── duration_hours: float
├── token_in: str
├── amount_usd: float
├── actual_return_pct: float
├── actual_return_usd: float
├── profitable: bool
├── lessons: List[str]
└── loss_reasons: List[str]
```

### B. API Reference

```python
# Complete public API

class DeFiRecommender:
    """Main interface for collective DeFi learning."""
    
    def recommend(
        self,
        query: StrategyQuery,
        limit: int = 5
    ) -> List[StrategyRecommendation]:
        """Get strategy recommendations with collective evidence."""
        
    def record_outcome(self, outcome: ExecutionOutcome) -> None:
        """Record an execution outcome."""
        
    def get_pack(self, pack_id: str) -> Optional[DeFiStrategyPack]:
        """Get a specific pack by ID."""
        
    def get_all_warnings(
        self,
        chain: Optional[str] = None,
        protocol: Optional[str] = None
    ) -> List[Warning]:
        """Get active warnings, optionally filtered."""
        
    def get_strategy_packs(
        self,
        token: Optional[str] = None,
        chain: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> List[DeFiStrategyPack]:
        """Get all strategy packs matching criteria."""
```

### C. Migration Checklist

- [ ] Create `borg/defi/v2/` directory
- [ ] Implement `pack.py` (data structures)
- [ ] Implement `pack_store.py` (load/save)
- [ ] Implement `recommender.py` (core logic)
- [ ] Implement `outcome_store.py` (outcomes)
- [ ] Implement `api.py` (public interface)
- [ ] Create 5 seed packs with historical data
- [ ] Update `borg/defi/__init__.py` to export v2
- [ ] Write integration tests
- [ ] Deprecate V1 modules (keep compatibility)

---

**End of Design Document**