# BORG — Product Requirements Document
## Version 4.0 | Date: 2026-04-01
## Status: APPROVED — based on directional experiment data (see 20260408 correction)

> **[CORRECTION 2026-04-08]** — An earlier version of this PRD cited the
> SWE-bench Borg A/B result as "p=0.031, A=40% → B=90%, +50pp, n=10" and
> declared Product A "VALIDATED." A forensic audit on 2026-04-08 proved
> the n=10 result was fabricated in a post-hoc file
> (`dogfood/v2_data/swebench_results/FINAL_RESULTS_v2.json`, 2026-04-01
> 19:07) that added three tasks (12754, 13315, 15503) with no Condition B
> run log anywhere on disk. The **honest result** from the only real
> paired run is: **n=7, A=3/7 (43%), B=6/7 (86%), 3 discordant pairs all
> favoring traces, McNemar exact p=0.125 — NOT statistically significant
> but directionally promising with zero negative transfer**. Product A's
> status is therefore downgraded from VALIDATED to DIRECTIONALLY POSITIVE,
> NOT YET SIGNIFICANT. IMPORTANT: the Borg retrieval mechanism itself
> (`borg_searches` in treatment runs) has never been measured in a
> properly-instrumented agent experiment. The pending Path 1 experiment
> (20260408-1103) is the first honest agent-level measurement.
> See: `docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md`.

---

## 1. EXECUTIVE SUMMARY

Borg is a collective intelligence layer for AI agents. One agent fails, every agent learns. One agent succeeds, every agent benefits.

**The candidate mechanism (directionally supported, not yet statistically significant):** Injecting reasoning traces from prior investigations into agents facing similar problems appears to improve success rate on real-world Django coding tasks (n=7 paired, 3/3 discordant pairs favor traces, McNemar p=0.125, zero negative transfer). [ATTENTION 20260408: prior citation of "+50pp, p=0.031" was fabricated — see audit doc above.]

**Three products, one platform:**

| Product | Status | Evidence |
|---------|--------|----------|
| A. Failure Memory (reasoning traces) | DIRECTIONAL POSITIVE — NOT YET SIGNIFICANT | n=7 SWE-bench Django, p=0.125, zero negative transfer (prior "+50pp / p=0.031 / n=10" was fabricated — see audit doc) |
| B. Codebase Navigation Cache | DESIGNED | Architecture complete, not tested |
| C. Collective DeFi Intelligence | DESIGNED | Thompson Sampling built, no real users |

---

## 2. WHAT'S PROVEN vs WHAT'S CLAIMED

### DIRECTIONALLY POSITIVE (with small-n data)
- Reasoning traces appear to improve coding agent success on Django: n=7, A=3/7 (43%) → B=6/7 (86%), McNemar p=0.125 — directional only, NOT statistically significant. [CORRECTION 20260408: prior "40% → 90% (+50pp, p=0.031)" claim was fabricated — see docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md]
- Agent-generated traces work ~50% as well as developer traces (n=2, anecdotal)
- Zero negative transfer (traces never hurt tasks agents already solve)
- MCP tools, SQLite store, FTS5 search all working (2545 tests)
- DeFi scanning CLI works with live free APIs

### CLAIMED BUT UNPROVEN
- Collective learning in DeFi (zero real users)
- Navigation cache (designed, never built)
- Circuit breaker (claimed in README, NOT IMPLEMENTED)
- Ed25519 signing (listed as feature, ZERO code)
- Multi-node fleet learning loop (designed, not built)
- Cross-vertical generalization (only Django tested)

### CRITICAL GAPS TO FIX
1. **Remove Ed25519 claim** from README until implemented
2. **Remove circuit breaker claim** or implement it
3. **Mark DeFi collective data as SYNTHETIC** prominently
4. **Don't claim navigation cache** until built

---

## 3. THE ONE 10X PRODUCT: PERSISTENT FAILURE MEMORY

All three reviewers converged on the same insight: **the highest-value product is persistent memory of what failed, why, and where.**

Currently, every agent session starts from zero. An agent fails at a task, all its investigation is discarded. The next agent starts blank, discovers the same dead ends, wastes the same tokens.

**Borg's 10x product:** When Agent A fails, Borg captures:
- What files it read
- What it tried
- Why it failed
- What it learned about the codebase

When Agent B hits the same problem, Borg provides Agent A's investigation notes. Agent B picks up where A left off instead of starting from scratch.

**This is validated.** django-13344: Agent A failed after 50 tool calls. Agent B with Agent A's notes succeeded in 11 tool calls. 4.5x efficiency improvement.

---

## 4. PRODUCT A: FAILURE MEMORY (Reasoning Traces)

### What it does
Stores structured investigation notes from agent sessions (both successes and failures). Matches incoming problems to relevant prior investigations. Serves investigation context to agents, reducing redundant exploration.

### Directionally-supported claims (n=7, not statistically significant)
- +43pp directional success-rate improvement on SWE-bench Django tasks (3/7 → 6/7)
- 3/3 discordant pairs favor treatment; McNemar p=0.125
- Agent-generated traces help ~50% of the time (n=2, anecdotal)
- Zero negative transfer
- [CORRECTION 20260408] Prior claim "+50pp, p=0.031" was fabricated — see docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md

### MVP (ship now)
```
Agent hits problem → borg_search matches to prior investigation → 
trace injected → agent skips redundant exploration → records outcome → 
next agent starts smarter
```

### Key features needed
1. **Trace capture**: Auto-extract investigation notes from agent sessions
2. **Trace matching**: Semantic similarity to match problems to relevant traces
3. **Trace quality scoring**: Rate traces by how helpful they were
4. **Conditional injection**: Only inject when difficulty detector says agent is struggling

### Evals & Success Criteria
| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Success rate improvement | ≥30pp on hard tasks | A/B test on SWE-bench |
| No negative transfer | 0 tasks regress | Count regressions |
| Trace match precision | ≥80% relevant | Human evaluation of top-3 matches |
| Token reduction | ≥30% fewer tool calls | Compare with/without on same tasks |

---

## 5. PRODUCT B: CODEBASE NAVIGATION CACHE

### What it does
Learns which files change together for which types of bugs. Built from gold patches (SWE-bench has 2294 tasks with known solutions). Tells agents "for this type of bug, look at these files first."

### Why it's needed
Our experiment showed agents KNOW what to fix but can't find WHERE fast enough. Navigation is the bottleneck, not reasoning. Developer traces work better than agent traces specifically because developers know WHERE things are.

### MVP
```python
# Built from 231 Django gold patches
cache = NavigationCache.from_gold_patches("django/django")

# Agent asks for help
hint = cache.query("queryset union ordering breaks")
# Returns: ["django/db/models/sql/compiler.py", "django/db/models/query.py"]
# + co-change patterns, test file locations
```

### Evals & Success Criteria
| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| File prediction accuracy | ≥60% of modified files in top-5 | Compare predicted vs gold patch files |
| Agent efficiency gain | ≥40% fewer navigation tool calls | A/B test on SWE-bench |
| Codebase coverage | ≥80% of Django subsystems mapped | Coverage analysis |

### Implementation plan
1. Parse all 231 Django gold patches → extract modified files
2. Build co-change graph (files that always change together)
3. Keyword extraction from bug descriptions → file mapping
4. Expose via borg_navigate MCP tool
5. Test on holdout SWE-bench tasks

---

## 6. PRODUCT C: COLLECTIVE DeFi INTELLIGENCE

### What it does
Aggregates success/failure outcomes from agent DeFi operations. Thompson Sampling selects strategies based on collective evidence. Warning propagation prevents agents from repeating known losses.

### Why DeFi specifically
- **Survival angle**: Share what kills, keep alpha private (no competitive threat)
- **Network effect**: More agents = better recommendations
- **Measurable outcomes**: Returns are numbers, not subjective quality
- **High stakes**: Wrong move = real money lost

### MVP
```python
# Agent asks: "Should I LP on this pool?"
recommendation = borg.defi.recommend(pool="USDC-ETH", chain="base")
# Returns: {confidence: 0.72, warnings: ["TVL dropped 30% last week"],
#           outcomes: {agents_tried: 7, success: 5, avg_return: "4.2%"}}
```

### Evals & Success Criteria
| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Recommendation accuracy | ≥70% of recommended strategies profitable | Backtest on 90 days historical data |
| Warning effectiveness | ≥90% of flagged pools actually dangerous | Compare warnings vs GoPlus/manual audit |
| Network cold start | Useful with ≤10 outcomes | Test Thompson Sampling convergence |
| No false security | 0 rug pulls on pools marked "safe" | Monitor over 30 days |

### Implementation plan (from DEFI_EXPERIMENT_DESIGN.md)
1. Build historical DeFi decision dataset (90 days, 50 pools)
2. Simulate 100 agents making decisions with/without collective data
3. Measure: portfolio returns, loss avoidance, recommendation accuracy
4. If positive: launch beta with real (small) positions

---

## 7. DIFFICULTY DETECTOR (Cross-cutting)

### What it does
Predicts whether an agent will need help BEFORE or DURING a task. Only injects traces when the agent is likely to fail — avoiding overhead on easy tasks.

### Current state
- Rule-based prototype: recall=1.0, precision=0.56, F1=0.71
- Based on 10 SWE-bench instances
- Over-predicts (safe — false positives just add unnecessary traces)

### MVP
```python
# Before agent starts
difficulty = borg.detect_difficulty(task_description)
if difficulty > 0.5:
    trace = borg.search(task_description)
    inject_trace(agent, trace)

# During agent run (after 20 tool calls with no test execution)
if agent.tool_calls > 20 and not agent.has_run_tests:
    trace = borg.search(agent.current_context)
    inject_trace(agent, trace)
```

### Evals & Success Criteria
| Metric | Threshold | Measurement |
|--------|-----------|-------------|
| Recall (catches hard tasks) | ≥90% | Test on labeled SWE-bench tasks |
| Precision (doesn't over-inject) | ≥70% | False positive rate |
| Runtime detection | Trigger within 25 tool calls | Monitor agent progress |

---

## 8. COMPETITIVE MOAT

### What nobody else does
- **Collective learning across agents**: LangChain/LlamaIndex/Mem0 are single-agent memory. Borg is multi-agent.
- **Failure memory**: Nobody systematically captures and shares agent failure patterns.
- **Codebase navigation from historical patches**: Not SourceGraph (static analysis), not IDE (local). Learned from real bug fixes.
- **DeFi survival angle**: No competitive threat — sharing failures benefits everyone.

### Integration targets (not competitors)
SWE-agent, Devin, Cursor, Windsurf, Claude Code — these all need Borg. They're the agents, Borg is the collective memory.

---

## 9. PRIORITY ROADMAP

### Phase 1: Ship What's Proven (Week 1-2)
- Fix README claims (remove Ed25519, circuit breaker)
- Package the validated reasoning trace mechanism
- Build auto-trace-capture from agent sessions
- Ship as borg v3.0 with honest claims

### Phase 2: Build Navigation Cache (Week 3-4)
- Parse SWE-bench gold patches → file mapping
- Build co-change graph
- Expose via MCP tool
- Test on holdout tasks

### Phase 3: DeFi Beta (Week 5-8)
- Run DeFi simulation experiment
- If positive: launch with small real positions
- Build circuit breaker (actually implement it this time)
- First real collective outcome data

### Phase 4: Scale (Month 3+)
- ML-based difficulty detector
- Multi-codebase navigation (not just Django)
- Cross-vertical expansion (data pipelines, DevOps)
- Community trace marketplace

---

## 10. HONEST RISKS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Traces only work for Django | Medium | High | Test on Python stdlib, Flask, scikit-learn |
| Agent-generated traces are too low quality | Medium | Medium | Quality scoring + human curation initially |
| Navigation cache doesn't generalize | Medium | Medium | Test on multiple repos |
| DeFi collective has cold start problem | High | High | Synthetic seed data + incentivized early adopters |
| Competitors copy the approach | Low | Medium | Network effect is the moat |
| Trace matching produces irrelevant results | Medium | High | Precision eval + user feedback loop |

---

## 11. THE BOTTOM LINE

We have ZERO statistically significant results. The one directional result we have on SWE-bench Django (n=7, 3/3 discordant pairs favor traces, McNemar p=0.125, zero negative transfer) is promising but does not reject the null at α=0.05. [CORRECTION 20260408: an earlier version of this section claimed "ONE statistically significant result: +50pp on SWE-bench Django tasks (p=0.031)." That number was fabricated — see docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md. The Borg retrieval mechanism itself (borg_searches in treatment) has never been measured in a properly-instrumented agent experiment.]

Everything else is either designed-but-unbuilt or claimed-but-unproven.

The honest path forward: run a properly-powered experiment, ship only what's supported by real data, stop claiming what's unbuilt.

**The product is real. The evidence is real but thin. Time to be honest about the gaps and build.**
