# BORG V3 — LEARNING LOOP SPECIFICATION
## Continuous Collective Intelligence for AI Agents
## Date: 2026-03-31 | Status: APPROVED | Version: 1.0

---

# 1. EXECUTIVE SUMMARY

Borg V3 transforms a static reasoning cache into a continuously learning collective.
5 nodes (1 local + 4 VPS) generate real task outcomes. A 7-stage learning loop
turns those outcomes into better recommendations. The system must prove it improves
over time — monotonically increasing success rate across 200+ outcomes — or we kill it.

**What exists:** 420 outcomes across 5 nodes. Contextual Thompson Sampling selector.
Mutation engine with A/B testing. Feedback loop with drift detection. SQLite per node.
Hourly sync. 2,545 tests passing.

**What this spec adds:** The learning loop that connects all components into a
self-improving system with formal evaluation, verification, and failure safeguards.

**Core metric:** Does the system get better at recommending the right approach
for the right task over time? Yes = ship. No = kill.

---

# 2. PROBLEM STATEMENT & GOALS

## Problem
AI agents waste tokens re-deriving approaches other agents already proved.
V2 served static YAML packs. V3 must serve contextually selected, continuously
improving guidance that measurably reduces agent failure rates.

## Goals
1. Prove collective learning works (success rate improves over time)
2. Prove contextual selection beats random/static (precision@1 >= 80%)
3. Prove the system doesn't degrade (no regression across 30 days)
4. Prove cross-node knowledge transfer works (agent A's failure helps agent B)

## Non-Goals
- SaaS/multi-tenant (prove value first)
- Real-time streaming (batch sync sufficient)
- GPU-accelerated inference (CPU is fast enough)
- Pack marketplace (need packs first)

---

# 3. ARCHITECTURE

## 3.1 Learning Loop Pipeline (7 Stages)

```
┌────────────────────────────────────────────────────────────┐
│                  BORG V3 LEARNING LOOP                      │
│                                                             │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌──────────┐  │
│  │ STAGE 1 │──▶│ STAGE 2 │──▶│ STAGE 3 │──▶│ STAGE 4  │  │
│  │ Collect │   │ Local   │   │ Drift   │   │ Fleet    │  │
│  │ Outcomes│   │ Update  │   │ Detect  │   │ Sync     │  │
│  └─────────┘   └─────────┘   └─────────┘   └──────────┘  │
│       │                                          │         │
│       │         ┌─────────┐   ┌─────────┐   ┌───▼──────┐  │
│       │         │ STAGE 7 │◀──│ STAGE 6 │◀──│ STAGE 5  │  │
│       │         │ Deploy  │   │ Eval    │   │ Full     │  │
│       └────────▶│ Canary  │   │ Gate    │   │ Retrain  │  │
│                 └─────────┘   └─────────┘   └──────────┘  │
└────────────────────────────────────────────────────────────┘
```

## 3.2 Multi-Node Topology

```
                    ┌──────────────────────┐
                    │   COORDINATOR NODE   │
                    │   (Local Machine)    │
                    │                      │
                    │  Central DB (SQLite) │
                    │  Aggregator (FedProx)│
                    │  Eval Harness        │
                    │  Daily Reports       │
                    └──┬───┬───┬───┬───────┘
                       │   │   │   │
            ┌──────────┘   │   │   └──────────┐
            │              │   │              │
       ┌────▼────┐   ┌────▼───▼┐   ┌────────▼─┐
       │  VPS-1  │   │  VPS-2  │   │  VPS-3/4  │
       │ Python  │   │  JS/TS  │   │  Mixed +  │
       │ Debug   │   │  Debug  │   │  Adversar │
       │         │   │         │   │           │
       │ Local   │   │ Local   │   │  Local    │
       │ SQLite  │   │ SQLite  │   │  SQLite   │
       └─────────┘   └─────────┘   └───────────┘

  Sync: Hourly (coordinator pulls from all nodes)
  Cron: 5 tasks every 6 hours per node
  Report: Daily at 08:00 UTC
```

## 3.3 Component Map

| Component | File | Function | Trigger |
|-----------|------|----------|---------|
| ContextualSelector | core/contextual_selector.py | Thompson Sampling pack selection | Every search/suggest call |
| MutationEngine | core/mutation_engine.py | Pack evolution + A/B testing | Every 10 outcomes |
| FeedbackLoop | core/feedback_loop.py | Signal quality + drift + free-rider | Every outcome |
| BorgV3 | core/v3_integration.py | Orchestrator + SQLite + dashboard | Always running |
| MCP Server | integrations/mcp_server.py | 16 tools for agent integration | Agent requests |
| FleetSync | dogfood/sync_fleet.sh | Pull remote DBs, merge centrally | Hourly cron |
| DailyReport | dogfood/daily_report.sh | Aggregated fleet report | Daily 08:00 UTC |
| TaskRunner | dogfood/dogfood_runner.py | Execute tasks on VPS nodes | Every 6h cron |

---

# 4. LEARNING LOOP DESIGN

## Stage 1: Outcome Collection

**Trigger:** Every task completion
**Input:** Agent calls `borg_feedback` or `BorgV3.record_outcome()`

```python
OutcomeRecord = {
    "id": "uuid",
    "pack_id": "systematic-debugging",
    "agent_id": "hermes-local-001",
    "task_category": "debug",       # from contextual classifier
    "success": True,
    "tokens_used": 15000,
    "time_taken": 120.0,            # seconds
    "timestamp": "2026-03-31T14:00:00+00:00",
    "node_id": "srv1396191",
    "context_hash": "a3f2b1...",    # hash of task context for dedup
}
```

**Validation:** Every record must have: pack_id (non-empty), success (bool),
timestamp (ISO8601). Invalid records quarantined to `outcomes_quarantine` table.

## Stage 2: Local Update (Every 10 Outcomes)

**Algorithm:** Bayesian posterior update for Thompson Sampling

```
For each (pack_id, category) pair with new outcomes:
    α_new = α_old + successes
    β_new = β_old + failures
    posterior = Beta(α_new, β_new)

    Expected reward = α / (α + β)
    Uncertainty = sqrt(α*β / ((α+β)²*(α+β+1)))
```

No communication needed. Each node updates independently.

## Stage 3: Drift Detection (Continuous)

**Algorithm:** Page-Hinkley Test + Rolling Statistics

```python
class DriftDetector:
    def update(self, pack_id: str, success: bool):
        # Rolling success rate (window=50)
        rate = rolling_mean(outcomes[-50:])

        # Page-Hinkley statistic
        self.cumsum += (success - rate) - self.epsilon
        self.min_cumsum = min(self.min_cumsum, self.cumsum)
        ph_stat = self.cumsum - self.min_cumsum

        if ph_stat > self.threshold:  # default: 50
            return DriftEvent(pack_id, rate, self.baseline_rate)
```

**Trigger hierarchy:**
- PH_stat > 30: Increase exploration epsilon by 0.1
- PH_stat > 50: Flag drift, trigger Stage 5 (full retrain)
- PH_stat > 100: Emergency — revert to previous model version

## Stage 4: Fleet Sync (Every 50 Outcomes or 1 Hour)

**Protocol:** Coordinator-pull with FedProx aggregation

```
1. Coordinator SSH into each node
2. Download node's borg_v3.db
3. Extract new outcomes (since last sync)
4. INSERT OR IGNORE into central DB (dedup by context_hash)
5. Compute global posterior: weighted average of node posteriors
   global_α = Σ(n_i * α_i) / Σ(n_i)  where n_i = node outcome count
   global_β = Σ(n_i * β_i) / Σ(n_i)
6. FedProx regularization: penalize divergence from global
   local_update += μ * (local_params - global_params)
   where μ = 0.1 (proximal term weight)
```

**Message format:**
```json
{
    "node_id": "srv1396191",
    "sync_version": 42,
    "outcomes_since_last": [...],
    "local_posteriors": {"pack_id": {"alpha": 5, "beta": 2}},
    "timestamp": "2026-03-31T14:00:00Z"
}
```

## Stage 5: Full Retrain (Every 200 Outcomes or 24h or Drift)

**Trigger conditions (any):**
- 200 new outcomes since last retrain
- 24 hours since last retrain
- Drift detected (Stage 3)

**Process:**
1. Freeze current model as baseline
2. Train new model on all accumulated data
3. Hold out 20% for evaluation
4. Pass to Stage 6 (Eval Gate)

## Stage 6: Evaluation Gate

**Three-stage harness:**

```
OFFLINE (held-out 20%):
  - MRR > 0.5
  - NDCG@3 > 0.6
  - Calibration error < 0.1
  - Must beat baseline by >= 2%
  → FAIL: reject new model, keep baseline

SHADOW (20 outcomes):
  - Run new model alongside current
  - Log predictions, don't use them
  - Compare: paired t-test, p < 0.05
  - No regression allowed
  → FAIL: reject, keep baseline

CANARY (20% traffic, 50 outcomes):
  - New model serves 20% of requests
  - Monitor success rate vs current
  - Must stay within 95% CI of current
  → FAIL: auto-rollback to baseline
  → PASS: promote to 100%
```

## Stage 7: Production Deployment

**Canary → Full rollout:**
1. New model at 20% traffic for 50 outcomes
2. If success_rate_new >= success_rate_current - 0.05: promote
3. If regression > 15% in first 20 outcomes: immediate rollback
4. Log deployment event with model version hash

---

# 5. DATA MODEL

## SQLite Schema (borg_v3.db)

```sql
-- Core outcomes
CREATE TABLE outcomes (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL,
    agent_id TEXT DEFAULT '',
    task_category TEXT DEFAULT 'other',
    success INTEGER NOT NULL,
    tokens_used INTEGER DEFAULT 0,
    time_taken REAL DEFAULT 0.0,
    timestamp TEXT NOT NULL,
    node_id TEXT DEFAULT 'unknown',
    context_hash TEXT DEFAULT ''
);
CREATE INDEX idx_outcomes_pack ON outcomes(pack_id);
CREATE INDEX idx_outcomes_ts ON outcomes(timestamp);
CREATE INDEX idx_outcomes_node ON outcomes(node_id);

-- Feedback signals (quality-weighted)
CREATE TABLE feedback_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    pack_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- EXPLICIT/VOTE/IMPLIED/SILENCE
    value REAL NOT NULL,        -- 1.0=success, 0.0=failure
    timestamp TEXT NOT NULL
);

-- A/B tests
CREATE TABLE ab_tests (
    id TEXT PRIMARY KEY,
    original_pack_id TEXT NOT NULL,
    mutant_pack_id TEXT NOT NULL,
    mutation_type TEXT NOT NULL,
    status TEXT DEFAULT 'running',  -- running/completed/reverted
    created_at TEXT NOT NULL,
    uses_original INTEGER DEFAULT 0,
    uses_mutant INTEGER DEFAULT 0,
    successes_original INTEGER DEFAULT 0,
    successes_mutant INTEGER DEFAULT 0
);

-- Pack version history
CREATE TABLE pack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pack_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

-- Model versions (for learning loop)
CREATE TABLE model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_hash TEXT UNIQUE NOT NULL,
    posteriors_json TEXT NOT NULL,  -- serialized Beta posteriors
    training_outcomes INTEGER NOT NULL,
    eval_mrr REAL,
    eval_ndcg REAL,
    eval_calibration REAL,
    status TEXT DEFAULT 'candidate',  -- candidate/shadow/canary/active/reverted
    created_at TEXT NOT NULL,
    promoted_at TEXT
);

-- Sync log
CREATE TABLE sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    outcomes_synced INTEGER NOT NULL,
    sync_version INTEGER NOT NULL,
    timestamp TEXT NOT NULL
);

-- Quarantine (invalid records)
CREATE TABLE outcomes_quarantine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_data TEXT NOT NULL,
    error TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
```

---

# 6. SELECTOR OPTIMIZATION

## Mathematical Formulation

**Contextual Thompson Sampling with Hierarchical Categories:**

```
Given:
  - Task context x = (task_type, error_type, language, keywords, file_path)
  - Category c = classify(x) ∈ {debug, test, deploy, refactor, review, data, other}
  - Pack candidates P = {p₁, p₂, ..., pₖ}
  - Per-(pack, category) posterior: Beta(α_{p,c}, β_{p,c})

Selection:
  1. For each pack pᵢ:
     θᵢ ~ Beta(α_{pᵢ,c}, β_{pᵢ,c})     # Sample from posterior
     risk_i = Var[Beta(α, β)]             # Variance as risk
     score_i = θᵢ - δ·risk_i             # Risk-adjusted score

  2. With probability ε (exploration budget):
     Select pack with highest uncertainty: argmax_i Var[Beta(α_i, β_i)]

  3. With probability (1-ε):
     Select pack with highest score: argmax_i score_i

  where ε = max(0.05, 0.20 / sqrt(total_outcomes / 50))
```

**Update rule:**
```
On outcome (pack p, category c, success s):
  if s: α_{p,c} += 1
  else: β_{p,c} += 1
```

**Cold start (new pack):**
```
Prior: α₀ = 1, β₀ = 1 (uninformative)
Similarity boost: if similar pack p' exists with α' > 5:
  α₀ = 1 + 0.3 * Jaccard(keywords(p), keywords(p'))
```

---

# 7. MUTATION ENGINE

## Operators (Priority Order)

| # | Operator | Trigger | Gate |
|---|----------|---------|------|
| 1 | Anti-pattern addition | >= 3 agents fail same way | Schema validation |
| 2 | Step parameter tuning | Success vs failure comparison | Regression suite |
| 3 | Condition refinement | skip_if/inject_if usage patterns | A/B test (20 uses) |
| 4 | Phase reordering | Agents consistently skip phases | A/B test (20 uses) |
| 5 | Example substitution | Newer successful sessions available | Schema validation |

## Adaptive Mutation Rate (1/5th Rule)

```python
class AdaptiveMutationRate:
    rate = 0.1  # initial
    window = []  # last 20 mutations

    def update(self, improved: bool):
        self.window.append(improved)
        if len(self.window) >= 20:
            improvement_rate = sum(self.window[-20:]) / 20
            if improvement_rate > 0.20:
                self.rate = min(0.5, self.rate * 1.2)   # increase
            elif improvement_rate < 0.20:
                self.rate = max(0.01, self.rate * 0.8)  # decrease
```

## A/B Test Decision Rule

```
P(mutant > original) computed via:
  z = (p_m - p_o) / sqrt(p_pool * (1-p_pool) * (1/n_m + 1/n_o))
  where p_pool = (successes_m + successes_o) / (n_m + n_o)

Decision:
  if n_m >= 20 AND n_o >= 20:
    if z > 1.96: PROMOTE mutant (p < 0.05)
    if z < -1.96: REVERT to original
    else: CONTINUE testing
  if n_m + n_o > 200: STOP, pick higher success rate
```

---

# 8. FEEDBACK LOOP

## Signal Quality Hierarchy

| Signal Type | Weight | Source | Example |
|-------------|--------|--------|---------|
| EXPLICIT_CONFIRMATION | 1.0 | Agent calls borg_feedback(success=true) | "This pack solved my bug" |
| VOTE | 0.5 | Agent rates pack | Thumbs up/down |
| IMPLIED_USAGE | 0.2 | Agent completed all phases | Inferred from session |
| SILENCE | 0.0 | Agent used pack, no feedback | Ambiguous — ignored |

## Free-Rider Detection

```
free_rider_score(agent) = max(0, 1 - reports/uses)  if uses > 5
access_delay(agent) = 3600 * free_rider_score  seconds

Consequence: New pack access delayed, not blocked.
```

## Drift Detection Thresholds

| PH Statistic | Action |
|-------------|--------|
| 0-30 | Normal — no action |
| 30-50 | Warning — increase exploration ε by 0.1 |
| 50-100 | Alert — trigger full retrain (Stage 5) |
| > 100 | Emergency — revert to previous model version |

---

# 9. EVALUATION FRAMEWORK

## 9.1 Metrics

| Metric | Formula | Target | Frequency |
|--------|---------|--------|-----------|
| Success Rate @1 | correct_top_1 / total | >= 80% | Per outcome |
| MRR | mean(1/rank_of_correct) | >= 0.5 | Weekly |
| NDCG@3 | DCG@3 / idealDCG@3 | >= 0.6 | Weekly |
| Calibration | mean(|predicted_reward - actual|) | < 0.1 | Weekly |
| Token Savings | (baseline_tokens - borg_tokens) / baseline | >= 40% | Monthly |
| Adoption Rate | tasks_using_borg / total_tasks | >= 60% | Weekly |
| Sync Latency | time(sync_start → sync_complete) | < 5 min | Hourly |
| Learning Rate | slope(rolling_50_success_rate) | > 0 | Weekly |

## 9.2 ML Test Score (Adapted for Borg)

| Category | Test | Pass Criteria |
|----------|------|---------------|
| **Data** | Outcome records valid schema | 100% valid |
| **Data** | No duplicate context_hash | 0 duplicates |
| **Data** | Timestamp monotonically increasing per node | True |
| **Data** | All task categories in valid set | True |
| **Training** | Posterior update is reproducible (same seed → same result) | True |
| **Training** | Loss decreases during retrain | True |
| **Training** | No data leakage (holdout isolated) | True |
| **Model** | Policy output sums to 1.0 | True |
| **Model** | Latency p99 < 50ms | True |
| **Model** | Graceful degradation without model | Falls back to uniform |
| **Infra** | Sync completes within 5 minutes | True |
| **Infra** | Node failure doesn't corrupt central DB | True |
| **Infra** | Rollback completes within 30 seconds | True |
| **Monitor** | Success rate drop >10% triggers alert | True |
| **Monitor** | Drift detection fires on injected drift | True |
| **Monitor** | Staleness alert after 48h no update | True |

---

# 10. SUCCESS CRITERIA

All binary. No ambiguity.

| ID | Metric | Target | Measurement | Status |
|----|--------|--------|-------------|--------|
| M1 | Token reduction | >= 40% | Before/after controlled experiment, 10 tasks | PENDING |
| M2 | Time-to-first-value | < 30 seconds | Fresh install → first useful result | PENDING |
| M3 | Failure propagation | 100% in < 60s | Agent A fails → Agent B warned | PENDING |
| M4 | Selector precision@1 | >= 80% | Offline eval on 100 tasks | PENDING |
| M5 | Pack success improvement | Monotonically increasing (rolling 50) | 200+ outcomes | PENDING |
| M6 | CLI startup | < 1 second | `time borg version` | PASS (104ms) |
| M7 | Agent voluntary adoption | >= 60% | % tasks where agent uses borg_search | PENDING |
| M8 | System learns over time | Positive slope on success rate | 200+ outcomes, linear regression | PENDING |
| M9 | Fleet sync latency | < 5 minutes | Measured end-to-end | PENDING |
| M10 | Zero data loss on node failure | 0 records lost | Kill node, verify central DB | PENDING |

## Go/No-Go Decision

```
IF M1-M5 ALL PASS AND M6-M10 >= 8/10 PASS:
  → GO (ship V3 to PyPI)

IF any of M1-M5 FAIL:
  → NO-GO (fix and re-test)

IF M6-M10 < 8/10 PASS:
  → CONDITIONAL GO (ship with known issues documented)
```

---

# 11. VERIFICATION PLAN

| Metric | How Measured | When | Who |
|--------|------------|------|-----|
| M1 | Prepare 10 debugging tasks. Run with and without borg. Count tokens. | Day 14 | Orchestrator |
| M2 | Docker container, fresh pip install, time to first search result | Day 7 | A5 agent |
| M3 | Record failure on VPS1, check VPS2-4 see warning within 60s | Day 7 | Sync test |
| M4 | 100 (task, correct_pack) pairs from dogfood. Run selector offline. | Day 14 | Eval harness |
| M5 | Plot rolling-50 success rate. Fit linear regression. Slope > 0. | Day 21 | Dashboard |
| M6 | `time borg version` on fresh install | Done | PASS |
| M7 | Configure borg as optional. Count % tasks using borg_search. | Day 14 | Telemetry |
| M8 | Linear regression on daily success rates. p-value < 0.05. | Day 30 | Statistics |
| M9 | Time sync_fleet.sh end-to-end. Median of 10 runs. | Day 7 | Cron |
| M10 | Kill VPS3 process. Run sync. Verify all VPS3 data in central DB. | Day 7 | Chaos test |

---

# 12. INTEGRATION PLAN

```
Phase 0 (DONE): Fix CLI startup, add API caching, clean imports
Phase 1 (DONE): Contextual selector, mutation engine, feedback loop
Phase 2 (DONE): V3 integration layer, MCP server wiring
Phase 3 (DONE): Fleet deployment, sync, crons
Phase 4 (NOW):  Learning loop activation — connect all 7 stages
Phase 5 (Day 7): First evaluation gate run
Phase 6 (Day 14): Controlled experiment (M1, M4, M7)
Phase 7 (Day 21): Learning proof (M5, M8)
Phase 8 (Day 30): Go/No-Go decision
```

---

# 13. FAILURE MODES & MITIGATIONS

| # | Failure Mode | Probability | Impact | Mitigation |
|---|-------------|-------------|--------|------------|
| F1 | Data leakage (future info in training) | Low | High | Strict temporal splits, no lookahead |
| F2 | Training-serving skew | Medium | High | Same code for training and serving |
| F3 | Concept drift undetected | Medium | High | Multi-signal drift detection (Stage 3) |
| F4 | Reward hacking | Low | Critical | Manual audit of top-rewarded mutations |
| F5 | Cold start — new pack gets no traffic | High | Medium | Exploration budget ε >= 5% always |
| F6 | Feedback loop — model influences its training data | High | Medium | Diversity bonus, penalize repetition |
| F7 | Free-rider — agents consume without contributing | High | Low | Free-rider detection + delayed access |
| F8 | Herding — all nodes converge to same strategy | Medium | Medium | Per-node local model, forced diversity |
| F9 | Node failure loses data | Medium | High | Append-only log, hourly sync to central |
| F10 | Groupthink — bad strategy persists | Low | Critical | Circuit breaker (2 losses = disable) |
| F11 | Overfitting to noisy labels | Medium | Medium | Min 50 outcomes before training uses node data |
| F12 | Failure cascade | Low | Critical | Auto-rollback on 15% regression |

---

# 14. RISK REGISTER

| Risk | Probability | Impact | Owner | Mitigation | Status |
|------|------------|--------|-------|------------|--------|
| Dogfood shows borg doesn't help | Medium | Critical | AB | Kill honestly. Better at 5 nodes than 500. | Monitoring |
| VPS expire before results (2026-04-18) | High | High | AB | Renew before Apr 15 or extract data | ACTION NEEDED |
| Contextual selector overfits to dogfood tasks | Medium | High | System | Hold out 20% of tasks for blind eval | Built |
| Mutation engine degrades pack quality | Low | High | System | A/B testing + auto-rollback | Built |
| Small sample size (420 outcomes) insufficient | Medium | Medium | System | Continue generating, 30 tasks/day target | Running |
| Non-IID data across nodes | High | Medium | System | FedProx regularization (μ=0.1) | Designed |

---

# 15. IMPLEMENTATION ROADMAP

```
WEEK 1 (Apr 1-7): ACTIVATE LEARNING LOOP
├── Connect 7 stages in BorgV3.run_maintenance()
├── Implement model_versions table + versioning
├── First offline evaluation (MRR, NDCG@3)
├── Verify sync latency (M9)
├── Chaos test: kill VPS3, verify no data loss (M10)
└── Target: 600+ total outcomes

WEEK 2 (Apr 8-14): EVALUATION
├── Run controlled experiment (M1: token reduction)
├── Run selector offline eval (M4: precision@1)
├── Measure agent voluntary adoption (M7)
├── First A/B test of mutated pack
├── Deploy shadow mode for new model
└── Target: 1000+ total outcomes

WEEK 3 (Apr 15-21): LEARNING PROOF
├── Plot rolling success rate (M5: monotonic?)
├── Linear regression on daily rates (M8: positive slope?)
├── Cross-node transfer test (M3: failure propagation)
├── Canary deployment of first evolved model
├── RENEW VPS BEFORE APR 18
└── Target: 1500+ total outcomes

WEEK 4 (Apr 22-30): SHIP OR KILL
├── Final metrics collection
├── Go/No-Go scorecard
├── If GO: publish V3 to PyPI
├── If NO-GO: document why, archive learnings
├── Update marketing with REAL numbers
└── Target: 2000+ total outcomes
```

---

# 16. APPENDIX: DESIGN DECISION LOG

| # | Decision | Rationale | Source |
|---|----------|-----------|--------|
| D1 | TFX-style pipeline with stage contracts | Prevents data quality issues from cascading | Google TFX |
| D2 | Event-triggered training, not continuous | Save compute, retrain only when needed | Vertex AI |
| D3 | Interpretability first | Debug learning failures before scaling | Rules of ML |
| D4 | Dual metrics (offline + online) | Offline can mislead without online validation | Google Search |
| D5 | Tiered update cadence (10/50/200) | Balance responsiveness with stability | YouTube/Netflix |
| D6 | Hybrid global + local model | Handle non-IID without losing personalization | Federated Learning |
| D7 | Multi-signal drift detection | Single signal too noisy at small scale | Production ML |
| D8 | Thompson Sampling + epsilon decay | Best empirical E/E balance for multi-modal rewards | Bandit literature |
| D9 | FedProx aggregation (μ=0.1) | Handles heterogeneous nodes, simple to implement | Li et al., 2020 |
| D10 | Global + local architecture | Prevents premature convergence | FL research |
| D11 | Coordinator-pull sync | Simpler than push, handles node downtime | Practical ops |
| D12 | MRR + NDCG@3 + calibration | Standard ranking quality metrics | Google Search |
| D13 | Bayesian A/B testing | Small-sample friendly, no fixed sample size | Sequential testing |
| D14 | Daily/weekly/monthly tracking | Multi-timescale catches different problems | Google SRE |
| D15 | Three-stage eval harness | Catches issues at cheapest stage first | TFX Evaluator |
| D16 | ML Test Score rubric | Systematic, prevents blind spots | Breck et al., 2017 |
| D17 | Explicit failure mode matrix | Forces mitigation before problems occur | Risk engineering |
| D18 | Learning verification suite | Proves the system learns, not just runs | Scientific method |
| D19 | Regression gates with auto-rollback | Prevents shipping degraded models | Google SRE |
| D20 | Random failure injection | Builds resilience through adversarial testing | Netflix Chaos Monkey |

---

*This specification is the single source of truth for Borg V3's learning loop.*
*Every claim must be verified. Every metric must be measured.*
*Build the measurement tool before building the product.*
*Resistance is futile.*
