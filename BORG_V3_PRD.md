# BORG V3 — PRODUCT REQUIREMENTS DOCUMENT
## From Cookbook to Brain: Collective Learning That Actually Works
## Date: 2026-03-31 | Status: DRAFT FOR REVIEW

---

# 0. WHY V3

V2 has 2,498 passing tests, 40K LOC, 22 modules, and a Thompson Sampling recommender.
But V2 test plan (67 tests, 5 agents) revealed:

- **50% functional test failures** — many due to API surface confusion (test harness, not bugs), but the confusion IS the problem
- **CLI startup takes 6 seconds** (threshold: 2s) — heavy imports on every invocation
- **No API response caching** — every DeFi call hits the network
- **No contextual selection** — selector ignores task type, uses fixed weights
- **No mutation mechanism** — packs are static after publish
- **No real collective data** — seed packs are synthetic
- **Value demo showed 45% improvement** — good but not the 10x we claim

V3 fixes the architecture, not the feature count.

---

# 1. PROBLEM STATEMENT

**For AI coding agents** that hit problems during tasks,
**Borg is** a collective reasoning cache
**That** provides the right approach at the right time based on what worked for other agents.

**The core gap:** V2 serves static YAML packs. V3 must serve *contextually selected, continuously improving* guidance that measurably reduces agent token waste and failure rates.

---

# 2. SUCCESS CRITERIA (Binary — No Ambiguity)

## 2.1 Primary Metrics (Must ALL pass for V3 ship)

| ID | Metric | Measurement | Target | Current |
|----|--------|-------------|--------|---------|
| M1 | Token reduction on debugging tasks | Before/after controlled experiment, 10 tasks, 3 agent types | >= 40% reduction | ~45% (estimated) |
| M2 | Time-to-first-value | Fresh install → first useful result | < 30 seconds | ~8.4 seconds (install) + search time |
| M3 | Collective learning proof | Agent A fails → Agent B avoids same failure | 100% propagation in < 60 seconds | Not proven with real agents |
| M4 | Selector accuracy | Correct pack recommended for task type | >= 80% precision@1 | Unknown (no contextual selector) |
| M5 | Pack improvement over time | Pack success rate increases after 50 uses | Monotonically increasing (rolling 20) | N/A (no mutation) |
| M6 | CLI startup | `borg version` response time | < 1 second | 5.89 seconds |
| M7 | Agent dogfood adoption | Agents voluntarily use borg without explicit instruction | >= 3 of 5 agents use borg_search in first 10 tasks | N/A |

## 2.2 Secondary Metrics (Informational, don't block ship)

| ID | Metric | Target |
|----|--------|--------|
| S1 | Pack corpus size (non-synthetic) | >= 20 real packs from dogfood |
| S2 | Failure memory entries | >= 100 real failure patterns |
| S3 | Agent feedback submission rate | >= 50% of sessions generate feedback |
| S4 | Cross-agent knowledge transfer | Evidence of agent B using agent A's discovery |

## 2.3 Anti-Metrics (Things we explicitly do NOT optimize for)

- Lines of code
- Number of modules
- Test count (unless tests catch real bugs)
- Feature count
- API client count

---

# 3. ARCHITECTURE — THE FOUR LAYERS

```
┌──────────────────────────────────────────────────────────────────┐
│                     AGENT (Hermes, Claude, Cursor)                │
│                                                                   │
│  Task starts → borg_observe() → contextual guidance injected     │
│  Agent stuck → borg_suggest() → relevant pack + anti-patterns    │
│  Task ends → borg_feedback() → outcome recorded                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ MCP / Python API
┌───────────────────────────▼──────────────────────────────────────┐
│  LAYER 1: CONTEXTUAL SELECTOR                                    │
│                                                                   │
│  Input: task_type, error_type, language, agent_id, history       │
│  Output: ranked pack list with confidence intervals               │
│                                                                   │
│  Algorithm: Hierarchical Contextual Thompson Sampling             │
│    Level 1: Task category classifier (code/debug/test/deploy)     │
│    Level 2: Within-category Thompson Sampling with context        │
│    Exploration budget: 20% explicit, not additive freshness       │
│    Cold start: collaborative filtering from similar packs         │
│                                                                   │
│  Scoring:                                                         │
│    score(ctx, pack) = E[reward|ctx, pack]                         │
│                     + β · uncertainty(pack|ctx)                    │
│                     - δ · risk_penalty(pack, ctx)                  │
│    Where β adapts: high when few observations, low when many      │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│  LAYER 2: PACK STORE + FAILURE MEMORY                            │
│                                                                   │
│  SQLite (WAL mode) with:                                          │
│  - packs: versioned YAML with lineage tracking                    │
│  - outcomes: (agent_id, pack_id, task_ctx, result, tokens, time)  │
│  - failures: (error_pattern, wrong_approaches, correct_approach)  │
│  - warnings: (token/pool/contract, severity, agent_count)         │
│                                                                   │
│  Signals (StackOverflow model):                                   │
│    Tier 1: Explicit confirmation ("this worked") — weight 1.0     │
│    Tier 2: Vote/rating — weight 0.5                                │
│    Tier 3: Implied usage (agent used pack, didn't complain) — 0.2  │
│    Tier 4: Silence — weight 0 (ambiguous)                          │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│  LAYER 3: MUTATION ENGINE                                         │
│                                                                   │
│  Trigger: pack has >= 10 outcomes AND success_rate < 0.7           │
│  OR: agent feedback suggests specific improvement                  │
│                                                                   │
│  Operators (in priority order):                                   │
│  1. Anti-pattern addition — from failure memory                    │
│  2. Step parameter tuning — from successful variant comparison     │
│  3. Condition refinement — from skip/inject usage patterns         │
│  4. Phase reordering — from time-to-completion data                │
│  5. Example substitution — from recent successful sessions         │
│                                                                   │
│  Quality Gates:                                                    │
│  - Schema validation (immediate)                                   │
│  - Regression test against known-good tasks (automated)            │
│  - A/B test: 50/50 split for 20 uses, must beat original          │
│  - Rollback: auto-revert if mutant success rate < original - 10%   │
│                                                                   │
│  Mutation rate: adaptive (1/5th rule)                              │
│  - If > 20% of mutations improve: increase rate                    │
│  - If < 20% of mutations improve: decrease rate                    │
│  - Macro-mutations (wholesale restructure) at 1% frequency         │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│  LAYER 4: COLLECTIVE AGGREGATION                                  │
│                                                                   │
│  Anti-degradation mechanisms:                                      │
│  - Display confidence intervals, not point estimates               │
│  - Hide adoption counts until 5+ independent task types            │
│  - Require minimum 3 outcomes before promoting                     │
│  - Circuit breaker: 2 consecutive losses = disable                 │
│  - Contribution scoring: free-riders get delayed access            │
│  - Diversity maintenance: min 1 pack per task category preserved   │
│                                                                   │
│  Aggregation:                                                      │
│  - FedProx-style: global score = Σ(agent_score * agent_weight)     │
│    with regularization ||local - global||² to prevent overfitting   │
│  - Agent weight = f(contribution_count, accuracy_history)           │
│  - Drift detection: Page-Hinkley test on rolling success rate       │
│  - On drift: reset posterior for affected packs                     │
└──────────────────────────────────────────────────────────────────┘
```

---

# 4. SELECTOR OPTIMIZATION — WHY CONTEXTUAL TS > CURRENT FIXED BLEND

## 4.1 Current Selector (V2)

```
score = win_rate * 0.35 + return * 0.30 + confidence * 0.20 + freshness * 0.15
```

Problems:
1. **Context-blind** — same recommendation for debugging Python TypeError and deploying Kubernetes
2. **Fixed weights** — 0.35/0.30/0.20/0.15 are arbitrary, not learned
3. **Freshness is additive** — a pack with 0.1 win rate gets boosted by freshness
4. **No uncertainty modeling** — doesn't distinguish "good with 100 observations" from "good with 2"
5. **No exploration budget** — exploration happens accidentally via freshness, not intentionally

## 4.2 Proposed Selector (V3)

**Hierarchical Contextual Thompson Sampling:**

```python
class ContextualSelector:
    def select(self, task_context: TaskContext) -> RankedPacks:
        # Level 1: Classify task category
        category = self.classifier.predict(task_context)
        # → {debug, test, deploy, refactor, review, data, other}
        
        # Level 2: Within category, contextual Thompson Sampling
        candidates = self.pack_store.get_by_category(category)
        
        scored = []
        for pack in candidates:
            # Posterior: Beta(successes + 1, failures + 1)
            alpha = pack.successes_in_context(task_context) + 1
            beta = pack.failures_in_context(task_context) + 1
            
            # Sample from posterior
            sampled_reward = np.random.beta(alpha, beta)
            
            # Risk penalty (variance-based)
            risk = beta_variance(alpha, beta)
            
            scored.append((pack, sampled_reward - self.risk_coeff * risk))
        
        # Exploration budget: 20% of time, pick by information gain
        if random.random() < 0.20:
            return self.pick_by_information_gain(candidates, task_context)
        
        return sorted(scored, key=lambda x: -x[1])
```

## 4.3 Why This Is Optimal

| Property | V2 Fixed Blend | V3 Contextual TS | Evidence |
|----------|---------------|------------------|----------|
| Context-aware | No | Yes | Netflix, YouTube, RouteLLM all use contextual bandits |
| Exploration controlled | Accidental (freshness) | Explicit 20% budget | Spotify, Google use explicit budgets |
| Uncertainty modeled | No (point estimate) | Yes (posterior width) | Bayesian decision theory |
| Adapts to drift | No | Yes (change detection reset) | ADWIN, Page-Hinkley proven |
| Handles cold start | Poorly (freshness boost only) | CF from similar packs | Meta-learning literature |
| Regret bound | Unknown | O(√(KT ln K)) | Thompson Sampling proven |

## 4.4 Eval Plan for Selector

```
EVAL-SEL-001: Offline evaluation
  - Dataset: 100 (task, correct_pack) pairs from dogfood
  - Metric: precision@1, precision@3, MRR
  - Baseline: V2 fixed blend
  - Target: V3 contextual TS beats V2 by >= 20% on precision@1

EVAL-SEL-002: Online A/B test
  - 50% traffic V2 selector, 50% V3 selector
  - Metric: task success rate, tokens consumed
  - Duration: 100 tasks per arm minimum
  - Target: V3 arm shows >= 15% higher success rate

EVAL-SEL-003: Cold start test
  - Add 5 new packs with 0 observations
  - Measure: how many uses until selector correctly recommends them
  - Target: < 10 uses to reach precision@3 = 0.5
```

---

# 5. MUTATION ENGINE — EVALS

```
EVAL-MUT-001: Anti-pattern addition from failure memory
  - Setup: 3 agents fail on same error pattern
  - Expectation: mutation engine adds anti-pattern to relevant pack
  - Gate: mutated pack must not regress on regression suite
  - Metric: next agent avoids the error on first attempt

EVAL-MUT-002: A/B test of mutant vs original
  - Setup: mutant created by step parameter tuning
  - Run: 20 tasks on original, 20 on mutant
  - Metric: success rate difference with 95% CI
  - Gate: mutant must be statistically non-inferior (p < 0.05)

EVAL-MUT-003: Mutation rate adaptation
  - Track: % of mutations that improve pack success rate
  - If > 20%: increase mutation rate (packs are underfitting)
  - If < 20%: decrease mutation rate (packs are overfitting to noise)
  - Metric: rolling 20-mutation improvement rate
```

---

# 6. FEEDBACK LOOP — EVALS

```
EVAL-FB-001: Signal quality hierarchy
  - Explicit confirmation weight = 1.0
  - Vote weight = 0.5
  - Implied usage weight = 0.2
  - Silence weight = 0.0
  - Eval: does weighting produce better pack rankings than uniform?

EVAL-FB-002: Free-rider detection
  - Agent uses borg 10 times, reports back 0 times
  - Expectation: agent marked as free-rider after 5 unreported uses
  - Consequence: delayed access to new packs (not blocked)

EVAL-FB-003: Drift detection
  - Inject sudden success rate drop for a pack
  - Expectation: Page-Hinkley test detects within 5 observations
  - Response: posterior reset, pack enters re-evaluation

EVAL-FB-004: Anti-herding
  - 5 agents adopt pack A early
  - Agent 6 has local signal that pack B is better
  - Eval: does agent 6 still try B? (information cascade prevention)
  - Mechanism: confidence intervals + diversity maintenance
```

---

# 7. DOGFOOD ARCHITECTURE

## 7.1 Fleet Topology

```
┌─────────────────────────────────────────────────────────┐
│                    BORG CENTRAL                          │
│              (This Hermes instance)                      │
│                                                          │
│  SQLite DB: packs, outcomes, failures, warnings          │
│  Mutation engine: runs after every 10 outcomes           │
│  Aggregation: FedProx-style, runs hourly                │
│  Dashboard: cron job → discord report daily              │
└────────────────────────┬────────────────────────────────┘
                         │ SSH + rsync (DB sync)
        ┌────────────────┼───────────────────────┐
        │                │                       │
   ┌────▼────┐    ┌──────▼──────┐    ┌──────────▼──────────┐
   │ VPS-1   │    │   VPS-2     │    │     VPS-3 + VPS-4   │
   │ HERMES  │    │   HERMES    │    │     HERMES (x2)     │
   │ Agent   │    │   Agent     │    │     Agents          │
   │         │    │             │    │                      │
   │ Tasks:  │    │ Tasks:      │    │ Tasks:               │
   │ Python  │    │ JavaScript  │    │ Mixed / adversarial  │
   │ debug   │    │ debug       │    │ real-world tasks     │
   │ + test  │    │ + deploy    │    │ from GitHub issues   │
   └─────────┘    └─────────────┘    └──────────────────────┘
```

## 7.2 Hostinger VPS Setup

Each VPS needs:
1. Hermes installed with borg MCP configured
2. SSH key for DB sync back to central
3. Task queue (GitHub issues or curated task list)
4. Auto-reporting: after each task, submit borg_feedback
5. Telemetry: log tokens consumed, time, success/failure

```bash
# Per VPS setup script
apt update && apt install -y python3.12 git curl
pip install agent-borg[all] hermes-ai
# Configure borg MCP
mkdir -p ~/.config/hermes
cat > ~/.config/hermes/mcp.json << 'EOF'
{"mcpServers": {"borg": {"command": "borg-mcp"}}}
EOF
# Sync script (runs every 5 minutes)
# rsync borg.db to central, pull latest packs
```

## 7.3 Task Distribution

| VPS | Domain | Task Source | Volume |
|-----|--------|------------|--------|
| VPS-1 | Python debugging | Curated bugs from open-source repos | 10 tasks/day |
| VPS-2 | JS/TS debugging | Same methodology, different language | 10 tasks/day |
| VPS-3 | Mixed real-world | GitHub "good first issue" labels | 5 tasks/day |
| VPS-4 | Adversarial | Tasks designed to break borg recommendations | 5 tasks/day |

## 7.4 Dogfood Evals

```
EVAL-DOG-001: Cold start to collective value
  - Day 1: All VPS start with empty borg DB
  - Metric: by day 7, pack success rate > day 1 success rate
  - Target: >= 20% improvement in success rate over 7 days

EVAL-DOG-002: Cross-language transfer
  - VPS-1 discovers anti-pattern for NoneType errors
  - Metric: VPS-2 avoids equivalent null-reference in JS
  - Target: cross-language transfer within 24 hours

EVAL-DOG-003: Adversarial resilience
  - VPS-4 submits deliberately bad feedback
  - Metric: collective quality does not degrade
  - Target: bad feedback detected and filtered within 5 submissions

EVAL-DOG-004: Token savings measurement
  - Controlled experiment: same tasks with and without borg
  - Metric: actual tokens consumed (not estimated)
  - Target: >= 40% token reduction by day 14

EVAL-DOG-005: Agent voluntary adoption
  - Configure borg as available but not required
  - Metric: % of tasks where agent chooses to call borg_search
  - Target: >= 60% voluntary usage by day 7
```

---

# 8. IMPLEMENTATION ROADMAP

## Phase 0: Fix What's Broken (Days 1-2)
- [ ] Fix CLI startup time: lazy imports for uvicorn/fastapi/httpx
- [ ] Add DeFi response caching (5-minute TTL)
- [ ] Clean up API surface: consistent import paths
- [ ] Fix 6 failing unit tests

## Phase 1: Contextual Selector (Days 3-7)
- [ ] Task category classifier (simple: regex on error type + file extension)
- [ ] Context-aware Thompson Sampling (replace fixed blend)
- [ ] Explicit 20% exploration budget
- [ ] Cold start: similarity-based prior from pack embeddings
- [ ] EVAL-SEL-001 offline evaluation

## Phase 2: Feedback Loop (Days 8-12)
- [ ] Signal quality hierarchy (explicit > vote > implied > silence)
- [ ] Auto-feedback: borg auto-detects task completion and submits
- [ ] Free-rider detection + delayed access
- [ ] Drift detection (Page-Hinkley)
- [ ] EVAL-FB-001 through EVAL-FB-004

## Phase 3: Mutation Engine (Days 13-18)
- [ ] Anti-pattern addition from failure memory (operator 1)
- [ ] A/B testing infrastructure for mutant vs original
- [ ] Adaptive mutation rate (1/5th rule)
- [ ] Rollback mechanism (auto-revert on regression)
- [ ] EVAL-MUT-001 through EVAL-MUT-003

## Phase 4: Dogfood Fleet (Days 19-24)
- [ ] Set up 4 Hostinger VPS with Hermes + Borg
- [ ] Task distribution pipeline
- [ ] DB sync mechanism
- [ ] Dashboard + daily report cron
- [ ] EVAL-DOG-001 through EVAL-DOG-005

## Phase 5: Measurement & Ship (Days 25-30)
- [ ] Run all primary metrics (M1-M7)
- [ ] Go/no-go decision
- [ ] V3 release to PyPI
- [ ] Update marketing with REAL numbers (not simulated)

---

# 9. WHAT WE LEARNED FROM V2 TESTING

| Finding | Impact | V3 Response |
|---------|--------|-------------|
| 15/15 edge cases passed | Robustness is solid | Keep — no changes needed |
| CLI takes 6 seconds | Users bounce before value | Lazy imports (Phase 0) |
| No API caching | Unnecessary network calls | 5-min TTL cache (Phase 0) |
| API surface confusion (wrong import paths) | Developers can't find functions | Consistent public API + __init__.py exports (Phase 0) |
| MCP server works well (15 tools, p95 < 300ms) | Core infrastructure is solid | Keep — no changes needed |
| Search latency p95 < 200ms | Fast enough | Keep |
| SQLite WAL handles 10 concurrent writers | DB layer is solid | Keep |
| Privacy scanner catches secrets | Security works | Keep |
| SQL injection blocked | Security works | Keep |
| V2 recommender: 2.2M ops/sec | Way faster than needed | Keep |
| Value demo: 45% step reduction | Good but not 10x | Contextual selector + mutation should push to 60%+ |
| Collective learning: not proven with real agents | The central claim is unverified | Dogfood fleet proves or disproves this (Phase 4) |

---

# 10. RISKS & MITIGATIONS

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Dogfood shows borg doesn't help | Medium | Critical | Kill the product honestly. Better to know at 5 agents than 500. |
| Contextual selector overfits to dogfood tasks | Medium | High | Hold out 20% of tasks for blind evaluation |
| Mutation engine degrades pack quality | Low | High | A/B testing + auto-rollback |
| VPS agents produce noisy feedback | High | Medium | Signal quality hierarchy + outlier detection |
| DB sync conflicts across VPS fleet | Medium | Medium | Append-only outcome log, merge on central |
| Herding in small fleet (5 agents) | High | Medium | Forced exploration budget (20%) |

---

# 11. DECISION LOG

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Thompson Sampling over UCB | Better empirical performance in multi-modal rewards (literature consensus) | UCB: more interpretable but worse in practice; EXP3: overkill for non-adversarial setting |
| Hierarchical selector | Task category narrows candidate pool → better within-category selection | Flat selector: too many candidates; pure content-based: ignores outcome data |
| FedProx over FedAvg | Handles non-IID agent experiences without overfitting to majority | FedAvg: overfits to most common task type; Gossip: too slow for 5-agent fleet |
| Immune-inspired diversity | Prevents premature convergence to single pack | No diversity control: eventually one pack dominates all categories |
| 20% explicit exploration | Netflix/Spotify validated; prevents information cascades | Additive freshness (V2): exploration is accidental and uncontrolled |
| SQLite not Postgres | Single-file, zero-ops, proven at 2.2M ops/sec | Postgres: operational overhead unjustified for current scale |
| 4 VPS dogfood | Minimum viable fleet for cross-agent learning proof | 1 agent: proves nothing about collective; 10+: premature scaling |

---

# 12. OUT OF SCOPE (V3)

- Multi-tenant SaaS (not yet — prove value first)
- Paid tiers (free until proven valuable)
- Web dashboard (CLI + Discord reports sufficient)
- GPU-accelerated embeddings (CPU is fast enough)
- Real-time streaming MCP (JSON-RPC sufficient)
- Pack marketplace (too early — need packs first)
- Mobile app (obviously)

---

*This document is the single source of truth for V3.*
*Everything not in this document is not in V3.*
*Build the measurement tool before building the product.*
*Resistance is futile.*
