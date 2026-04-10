# Borg DeFi V2 — Final Specification

**Status:** APPROVED FOR BUILD
**Date:** 2026-03-30
**Research Basis:** 3 parallel research tracks (mechanism design, ML feedback loops, web3 incentives)

---

## 1. Design Decisions (From Research Synthesis)

### What we're taking from each research track:

**From Mechanism Design:**
- Beta-Binomial reputation model (Bayesian, principled, simple)
- Logarithmic scoring rule for confidence calibration
- VCG-inspired contribution scoring (agents rewarded by marginal value they add)

**From ML Feedback Loops:**
- Thompson Sampling for exploration/exploitation (recommend proven strategies but explore new ones)
- Exponential temporal decay (recent outcomes weighted higher, half-life configurable)
- Concept drift detection (flag when a strategy's recent performance diverges from historical)

**From Web3 Incentives:**
- Phase 1: NO TOKEN. Social vouching + reputation points + spot-checks
- Progressive trust (new agents start low, earn influence)
- On-chain attestation where available (tx hashes as proof)
- Privacy: only share % returns, never wallet addresses or amounts

### What we're explicitly NOT building (yet):
- ZK proofs (overkill at <100 agents)
- Token staking/slashing (premature — build culture first)
- Prediction markets (need liquidity we don't have)
- Federated learning (future phase)
- Full DAO governance (admin-controlled for now)

---

## 2. Core Architecture

### 2.1 Three Operations

```
RECOMMEND  →  "I have $X of token Y on chain Z. What should I do?"
               Returns: ranked strategies with collective evidence

EXECUTE    →  Agent picks a strategy, executes, waits for outcome

RECORD     →  Agent reports outcome. Pack stats update. Loop closes.
```

That's the entire system. Everything else is implementation detail.

### 2.2 Data Flow

```
Agent A                          Borg Collective                    Agent B
   │                                   │                               │
   │─── recommend(USDC, base) ────────>│                               │
   │<── [aave-lending: 12 agents,      │                               │
   │     11 profitable, 4.2% avg]      │                               │
   │                                   │                               │
   │─── execute(aave-lending) ────────>│                               │
   │    ... 30 days pass ...           │                               │
   │                                   │                               │
   │─── record(pack_id, +3.8%) ──────>│                               │
   │                                   │── pack stats updated ────────>│
   │                                   │   (sample: 13, avg: 4.17%)    │
   │                                   │                               │
   │                                   │<── recommend(USDC, base) ─────│
   │                                   │── [aave-lending: 13 agents,   │
   │                                   │    12 profitable, 4.17%] ────>│
```

### 2.3 File Structure

```
~/.hermes/borg/defi/
├── packs/                          # Strategy packs (YAML)
│   ├── yield/
│   │   ├── aave-usdc-base.yaml
│   │   ├── kamino-usdc-sol.yaml
│   │   └── compound-usdc-eth.yaml
│   ├── swap/
│   │   └── jupiter-sol-usdc.yaml
│   └── warnings/
│       └── raydium-rug-2026-03.yaml
├── outcomes/                       # Outcome records (YAML, append-only)
│   └── 2026-03/
│       ├── outcome-001.yaml
│       └── outcome-002.yaml
├── agents/                         # Agent reputation (one file per agent)
│   ├── hermes-001.yaml
│   └── hermes-002.yaml
└── config.yaml                     # User profile (wallets, risk, prefs)
```

---

## 3. Pack Format

```yaml
id: yield/aave-usdc-base
name: "Aave V3 USDC Lending on Base"
version: 3                          # increments on every outcome

# WHEN to use this
entry:
  tokens: [USDC, USDT, DAI]        # what token you need to hold
  chains: [base, ethereum, arbitrum]
  min_amount_usd: 100
  risk_tolerance: [low, medium]     # who this is for

# WHAT to do
action:
  type: lend                        # lend | lp | stake | swap
  protocol: aave-v3
  steps:
    - "Supply USDC to Aave V3 on Base"
    - "Monitor health factor if borrowing against it"

# WHEN to exit
exit:
  type: anytime                     # anytime | time_based | condition
  guidance: "No lock period. Withdraw whenever needed."

# COLLECTIVE EVIDENCE (the value)
collective:
  total_outcomes: 12
  profitable: 11
  avg_return_pct: 4.2
  median_return_pct: 4.0
  std_dev: 1.2
  min_return_pct: -0.3              # one bad debt event
  max_return_pct: 5.8
  avg_duration_days: 30
  
  # Bayesian reputation (Beta-Binomial)
  alpha: 12                         # prior(1) + wins(11)
  beta: 2                           # prior(1) + losses(1)
  reputation: 0.857                 # alpha / (alpha + beta)
  confidence_interval: [0.621, 0.970]  # 95% CI

  # Temporal: most recent outcomes
  last_5_returns: [4.1, 3.8, 5.2, 4.5, 3.9]
  trend: stable                     # improving | stable | degrading
  
  # Loss analysis
  loss_patterns:
    - pattern: "bad debt from large liquidation cascade"
      count: 1
      mitigation: "diversify across lending protocols"

# RISK
risk:
  il_risk: false
  rug_score: 0.0                    # 0=safe, 1=certain rug
  protocol_age_days: 890
  audit_status: "multiple audits, no critical findings"
  
# META
updated_at: "2026-03-30T12:00:00Z"
created_at: "2026-02-15T00:00:00Z"
```

---

## 4. Outcome Format

```yaml
outcome_id: "out-2026-03-30-hermes001-001"
pack_id: yield/aave-usdc-base
agent_id: hermes-001               # hashed, not real identity

execution:
  entered_at: "2026-03-01T08:00:00Z"
  exited_at: "2026-03-30T08:00:00Z"
  duration_days: 29
  return_pct: 3.8
  profitable: true

# What the agent learned (free text, shared with collective)
lessons:
  - "Steady 4% APY throughout March"
  - "Brief dip to 2.8% during ETH volatility, recovered in 48h"

# Verification (optional, strengthens credibility)
verification:
  tx_hash_enter: "0xabc..."        # on-chain proof of entry
  tx_hash_exit: "0xdef..."         # on-chain proof of exit
  chain: base
```

---

## 5. Recommender Algorithm

### 5.1 Scoring (Thompson Sampling + Bayesian)

```python
def recommend(query: StrategyQuery, limit=5) -> List[Recommendation]:
    candidates = load_matching_packs(query.token, query.chain, query.risk)
    
    scored = []
    for pack in candidates:
        # Skip if active warning
        if has_active_warning(pack.id):
            continue
        
        # Thompson Sample from Beta posterior
        sampled_win_rate = beta_distribution.sample(pack.alpha, pack.beta)
        
        # Combine signals
        score = (
            sampled_win_rate * 0.35           # Bayesian win probability
            + normalize(pack.avg_return_pct) * 0.30  # Average return
            + pack.confidence * 0.20          # Sample size confidence
            + temporal_freshness(pack) * 0.15 # Recency bonus
        )
        
        scored.append((pack, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    return [to_recommendation(pack, score) for pack, score in scored[:limit]]
```

### 5.2 Confidence Calculation

```python
def confidence(pack) -> float:
    """0.0 to 1.0 based on sample size and consistency."""
    n = pack.total_outcomes
    if n == 0: return 0.0
    if n < 3: return 0.1 * n  # 0.1, 0.2
    
    # Base confidence from sample size (logarithmic)
    base = min(1.0, 0.3 + 0.1 * log2(n))  # 3→0.46, 10→0.63, 50→0.86
    
    # Penalize high variance
    cv = pack.std_dev / max(abs(pack.avg_return_pct), 0.01)  # coefficient of variation
    variance_penalty = max(0, 1 - cv)
    
    return base * (0.7 + 0.3 * variance_penalty)
```

### 5.3 Temporal Decay

```python
def temporal_weight(outcome_age_days: float, half_life_days: float = 30) -> float:
    """Recent outcomes matter more. Default half-life: 30 days."""
    return 0.5 ** (outcome_age_days / half_life_days)
```

### 5.4 Concept Drift Detection

```python
def detect_drift(pack) -> Optional[str]:
    """Flag if recent performance diverges from historical."""
    if pack.total_outcomes < 10:
        return None
    
    recent = pack.last_5_returns
    historical_mean = pack.avg_return_pct
    recent_mean = mean(recent)
    
    # Z-test
    z = (recent_mean - historical_mean) / (pack.std_dev / sqrt(len(recent)))
    
    if z < -2.0:
        return f"DEGRADING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}%"
    if z > 2.0:
        return f"IMPROVING: recent avg {recent_mean:.1f}% vs historical {historical_mean:.1f}%"
    return None
```

---

## 6. Outcome Recording & Pack Update

```python
def record_outcome(outcome: Outcome) -> None:
    # 1. Save outcome to disk
    save_outcome(outcome)
    
    # 2. Load and update pack
    pack = load_pack(outcome.pack_id)
    
    # 3. Update Bayesian stats
    if outcome.profitable:
        pack.alpha += 1
    else:
        pack.beta += 1
    
    pack.total_outcomes += 1
    pack.profitable += (1 if outcome.profitable else 0)
    
    # 4. Recalculate aggregate stats (with temporal weighting)
    all_outcomes = load_outcomes_for_pack(outcome.pack_id)
    weighted_returns = [
        (o.return_pct, temporal_weight(age_days(o)))
        for o in all_outcomes
    ]
    pack.avg_return_pct = weighted_mean(weighted_returns)
    pack.std_dev = weighted_std(weighted_returns)
    pack.last_5_returns = [o.return_pct for o in all_outcomes[-5:]]
    
    # 5. Update reputation
    pack.reputation = pack.alpha / (pack.alpha + pack.beta)
    
    # 6. Check for drift
    drift = detect_drift(pack)
    if drift:
        pack.trend = "degrading" if "DEGRADING" in drift else "improving"
    
    # 7. Check for warning propagation
    if pack.beta >= 4 and pack.reputation < 0.4:
        propagate_warning(pack, "Low win rate with sufficient sample size")
    
    # 8. Bump version and save
    pack.version += 1
    save_pack(pack)
```

---

## 7. Warning Propagation

```python
def propagate_warning(pack, reason) -> None:
    """Auto-generate warning when collective evidence shows danger."""
    warning = {
        "id": f"warning/{pack.id}/{date_str()}",
        "type": "collective_warning",
        "severity": "high" if pack.reputation < 0.3 else "medium",
        "pack_id": pack.id,
        "reason": reason,
        "evidence": {
            "total_outcomes": pack.total_outcomes,
            "losses": pack.total_outcomes - pack.profitable,
            "loss_patterns": pack.loss_patterns,
            "reputation": pack.reputation,
        },
        "guidance": f"Avoid {pack.name}. {pack.total_outcomes - pack.profitable} agents lost money.",
        "created_at": now_iso(),
        "expires_at": (now() + timedelta(days=30)).isoformat(),
    }
    save_warning(warning)
```

---

## 8. Agent Reputation (Progressive Trust)

```yaml
# agents/hermes-001.yaml
agent_id: hermes-001
created_at: "2026-03-01"

# Contribution stats
outcomes_submitted: 15
outcomes_verified: 8              # had tx_hash proof
accuracy_score: 0.87              # outcomes matched collective consensus

# Trust level
trust_tier: contributor           # observer | contributor | trusted | authority
influence_weight: 1.0             # how much this agent's outcomes count

# Vouching
vouched_by: [hermes-002]
vouches_for: [hermes-003]
```

### Trust Tiers

| Tier | Requirements | Influence | Access |
|------|-------------|-----------|--------|
| observer | new agent, no history | 0.1x | read-only recommendations |
| contributor | ≥3 verified outcomes | 1.0x | full recommendations + can submit |
| trusted | ≥20 outcomes, accuracy >0.8 | 1.5x | can vouch for others |
| authority | ≥50 outcomes, vouched by 3+ trusted | 2.0x | can flag/deprecate packs |

---

## 9. User Config

```yaml
# ~/.hermes/borg/defi/config.yaml
wallets:
  solana: "7xKXtg..."
  base: "0xabc..."

risk_tolerance: medium    # low | medium | high | degen
brief_time: "08:00"       # daily digest time
timezone: "Europe/London"
quiet_hours: "22:00-08:00"

# What to alert on
alerts:
  idle_capital: true       # "you have $3K USDC doing nothing"
  position_exit: true      # "approaching recommended exit time"
  depeg: true              # stablecoin alerts
  rug_warning: true        # collective warnings
  new_opportunity: false   # don't spam with every new pool
```

---

## 10. Borg Core Integration

```python
# Bridge: agent can use standard borg_search for DeFi
def borg_search_defi(query: str) -> str:
    """
    Natural language DeFi search via borg.
    
    Examples:
      "what yield strategies work on base?"
      "any warnings for solana protocols?"
      "best strategy for idle USDC?"
    """
    recommender = DeFiRecommender()
    parsed = parse_natural_query(query)
    recs = recommender.recommend(parsed)
    return format_for_agent(recs)
```

---

## 11. What Happens to V1 Modules

| V1 Module | V2 Status | Rationale |
|-----------|-----------|-----------|
| yield_scanner | OPTIONAL | Data enrichment only — real ranking from outcomes |
| whale_tracker | OPTIONAL | Alpha signal, not core to recommendations |
| portfolio_monitor | KEEP | Needed for "what do I hold?" context |
| swap_executor | KEEP | Needed for execution |
| risk_engine | REPLACED | Collective outcomes > static risk scores |
| alpha_signal | OPTIONAL | Nice-to-have alpha, not core |
| strategy_backtester | REPLACED | Real outcomes > backtests |
| dojo_bridge | EVOLVED | Becomes record_outcome() |
| mev/ | KEEP | Execution quality |
| security/ | KEEP | Pre-swap safety |
| live_scans | KEEP | Zero-config onboarding value |

---

## 12. Implementation Plan

### Module Structure
```
borg/defi/v2/
├── __init__.py           # Public API exports
├── models.py             # StrategyQuery, Recommendation, Outcome, Pack dataclasses
├── recommender.py        # Core recommend() with Thompson Sampling
├── pack_store.py         # Load/save YAML packs
├── outcome_store.py      # Load/save YAML outcomes  
├── reputation.py         # Agent reputation, trust tiers
├── warnings.py           # Warning propagation logic
├── drift.py              # Concept drift detection
├── borg_bridge.py        # Integration with borg_search
└── seed_packs.py         # Initial strategy packs with historical data
```

### Seed Packs (Ship with System)
1. `yield/aave-usdc-base` — Aave V3 USDC lending (safest)
2. `yield/aave-usdc-ethereum` — Aave V3 USDC on Ethereum
3. `yield/compound-usdc-ethereum` — Compound V3 USDC
4. `yield/kamino-usdc-sol` — Kamino CLMM (higher risk, higher return)
5. `yield/marinade-sol` — Marinade SOL staking

Each seeded with synthetic-but-realistic outcome data to bootstrap the system.

### Build Order
1. models.py + pack_store.py + outcome_store.py (data layer)
2. recommender.py (core algorithm)
3. reputation.py + warnings.py + drift.py (intelligence layer)
4. borg_bridge.py + seed_packs.py (integration)
5. tests for everything
6. pause V1 cron jobs, wire V2 daily brief

---

## 13. Success Criteria

| Criterion | Measurement | Target |
|-----------|-------------|--------|
| recommend() returns results | Unit test | <100ms, ≥1 result for USDC/ETH/SOL |
| Outcome recording updates pack | Unit test | stats change after record |
| Bayesian reputation correct | Unit test | Beta(12,2) = 0.857 |
| Thompson Sampling explores | Unit test | new strategy gets recommended sometimes |
| Temporal decay works | Unit test | 60-day-old outcome weighs 0.25x |
| Drift detection fires | Unit test | 5 recent losses trigger alert |
| Warning auto-propagates | Unit test | 4+ losses on same pack creates warning |
| Agent trust tiers enforce | Unit test | observer can't submit outcomes |
| Borg bridge returns results | Integration test | borg_search("yield base") works |
| Pack YAML round-trip | Unit test | load → modify → save → load matches |
| E2E: submit outcome → recommendation changes | Integration test | full loop works |
| All V1 tests still pass | Regression test | 829 tests green |
| V2 tests pass | Unit + integration | target ≥100 new tests |
| Seed packs loadable | Smoke test | 5 packs load without error |

---

## 14. Definition of Done

- [ ] All models defined with proper types and defaults
- [ ] Pack store reads/writes YAML correctly
- [ ] Recommender returns ranked strategies with Thompson Sampling
- [ ] Outcome recording updates pack stats and Bayesian reputation
- [ ] Temporal decay applied to weighted stats
- [ ] Drift detection flags degrading strategies
- [ ] Warning propagation triggers on accumulated losses
- [ ] Agent reputation tracks trust tiers
- [ ] Borg bridge enables natural language search
- [ ] 5 seed packs ship with system
- [ ] ≥100 new tests, all passing
- [ ] All 829 V1 tests still passing
- [ ] Config system reads user wallets/preferences
- [ ] V1 cron jobs paused, replaced with V2 brief
