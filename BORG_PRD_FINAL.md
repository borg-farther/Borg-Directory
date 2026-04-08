# BORG — Product Requirements Document
## Version 4.1 | Date: 2026-04-08
## Status: SHIPPING (v3.2.4 on PyPI) — agent-level effect UNPROVEN, classifier measured

> **[CORRECTION 2026-04-08 #1]** — An earlier version of this PRD cited the
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

> **[CORRECTION 2026-04-08 #2]** — A second audit (`docs/20260408-1118_borg_roadmap/PLUS34PP_AUDIT.md`)
> reviewed the "+34pp" figure that had been reused after correction #1.
> Finding: the directional +34pp / +43pp observation is real (n=3 discordant
> pairs all favor traces in the only real paired run) but the significance
> language that had crept back in ("appears to improve," "directionally
> supports the hypothesis," etc.) was caveat-stripping. There is **no
> statistically-supported agent-level effect of Borg retrieval as of this
> revision.** The only honest measurements are: (a) the classifier precision /
> FCR numbers below, and (b) the MiniMax P1.1 run, which showed a floor effect
> (both arms 0/10 on Django SWE-bench easy set — see `P1_MINIMAX_REPORT.md`).
> A Sonnet replication (P2.1) is in progress at the time of this revision.

---

## 1. EXECUTIVE SUMMARY

Borg is a local, offline debugging aid for Python/Django developers. It ships
as a PyPI package (`agent-borg`, current release v3.2.4) with a set of
hand-authored packs and a classifier that routes errors to the right pack —
or refuses when nothing matches.

**What is measured (v3.2.4, 2026-04-08):**
- **Classifier FCR** (false confident routes) on the 173-row Python/Django
  evaluation corpus: **53.8% → 0.58%** (measured, reproducible via
  `pytest tests/test_classifier_*.py`).
- **Classifier precision** on the same corpus: **13.1% → 93.8%**.
- **Test suite:** 1708 tests passing on v3.2.4 at the time of this revision.
- **v3.2.4 patch:** fixes a broken `borg observe → borg search` roundtrip
  where observe would emit query strings that search could not index. This
  is a correctness fix, not a marketing claim.

**What is NOT measured (and the PRD no longer claims it is):**
- There is **no statistically-supported agent-level effect** of Borg
  retrieval on task success. The only real paired SWE-bench run is n=7
  (McNemar p=0.125, directional only). The prior "+50pp / p=0.031" figure
  was fabricated (correction #1). The reused "+34pp / directionally
  supports" framing was caveat-stripped (correction #2).
- The MiniMax P1.1 agent-level run (the first properly-instrumented Borg
  retrieval measurement) showed a **floor effect** — both treatment and
  control scored 0/10 on the Django SWE-bench easy set. That is a null
  result, not a negative result, and it is a measurement on **one model
  only**.
- A Sonnet replication (P2.1) is running at the time of this revision to
  determine whether the floor effect is model-specific or mechanism-wide.

**Three products, one platform:**

| Product | Status | Evidence |
|---------|--------|----------|
| A. Failure Memory (reasoning traces) | SHIPPING classifier, AGENT-LEVEL EFFECT UNPROVEN | Classifier: FCR 0.58%, precision 93.8% on 173-row corpus (measured). Agent-level: n=7 directional-only (p=0.125) + 1 model P1.1 floor-effect null. Sonnet P2.1 in progress. See corrections #1 and #2 above. |
| B. Codebase Navigation Cache | DESIGNED | Architecture complete, not tested |
| C. Collective DeFi Intelligence | DESIGNED | Thompson Sampling built, no real users |

---

## 2. WHAT'S PROVEN vs WHAT'S CLAIMED

### MEASURED (v3.2.4, reproducible)
- **Classifier FCR:** 53.8% → 0.58% on the 173-row Python/Django evaluation
  corpus. Reproducible via the classifier test suite.
- **Classifier precision:** 13.1% → 93.8% on the same corpus.
- **Test suite:** 1708 tests passing at the v3.2.4 tag.
- **Non-Python language guard** (v3.2.2+): Borg now refuses Python answers
  for Rust / Go / JS / Docker errors instead of mis-routing them to the
  Django migration pack.
- **observe → search roundtrip** (v3.2.4): regression test covers the path
  that used to silently drop queries.
- **MCP tools, SQLite store, FTS5 search:** all running.
- **DeFi scanning CLI:** works with live free APIs (scanning only — no
  collective learning claim).

### DIRECTIONAL ONLY (small-n, not statistically significant)
- Reasoning traces on SWE-bench Django, n=7 paired, A=3/7 → B=6/7, McNemar
  exact p=0.125. This is the only real paired agent-level run Borg has.
  [CORRECTION #1: prior "40% → 90% (+50pp, p=0.031)" claim was fabricated.
  CORRECTION #2: the "+34pp, directionally supports" framing was caveat-
  stripped. See audit docs referenced at the top of this PRD.]

### MEASURED AS NULL (floor effect, 1 model)
- **P1.1 MiniMax agent-level run:** Both treatment (Borg retrieval on) and
  control (Borg off) scored 0/10 on the Django SWE-bench easy set. Interpreted
  as a floor effect (the model is too weak to produce signal either way),
  not as evidence against the mechanism. See
  `docs/20260408-1118_borg_roadmap/P1_MINIMAX_REPORT.md`.

### IN PROGRESS
- **P2.1 Sonnet replication** of the agent-level measurement. Checkpointed
  at rate-limit wait as of 2026-04-08 16:12. If Sonnet also shows 0/0 the
  floor-effect interpretation is confirmed; if Sonnet shows signal either
  way the mechanism can finally be measured.

### CLAIMED BUT UNPROVEN
- Collective learning in DeFi (zero real users)
- Navigation cache (designed, never built)
- Circuit breaker (claimed in README, NOT IMPLEMENTED)
- Ed25519 signing (listed as feature, ZERO code)
- Multi-node fleet learning loop (designed, not built)
- Cross-vertical generalization (only Python/Django classifier tested)

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

### What is measured vs. what is still open
**Measured (classifier layer, reproducible on the 173-row corpus):**
- FCR 53.8% → 0.58%
- Precision 13.1% → 93.8%
- 1708 tests passing at the v3.2.4 tag

**Directional only (n=7 SWE-bench Django paired run):**
- A=3/7 → B=6/7, McNemar exact p=0.125 (NOT statistically significant)
- 3/3 discordant pairs favor treatment
- Zero negative transfer in that run

**Null / floor effect (n=10 MiniMax, P1.1):**
- Both arms 0/10 on Django SWE-bench easy set. Not a negative result for
  the mechanism; the model is too weak to produce signal either way.

**In progress:**
- P2.1 Sonnet replication, checkpointed at rate-limit wait 2026-04-08 16:12.

**Anecdotes (labeled as such, not claims):**
- One instance where agent-generated traces appeared to help; n=2, anecdotal.

**Corrections of prior claims:**
- [CORRECTION #1 20260408-1003] "+50pp, p=0.031" was fabricated.
  See `docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md`.
- [CORRECTION #2 20260408-1118] Reused "+34pp, directionally supports"
  framing was caveat-stripped. See
  `docs/20260408-1118_borg_roadmap/PLUS34PP_AUDIT.md`.

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

As of v3.2.4 (2026-04-08):

**What is real and measured:**
- The classifier is meaningfully better. FCR 53.8% → 0.58% and precision
  13.1% → 93.8% on a 173-row Python/Django corpus, with 1708 passing tests.
  This is the only layer of Borg with reproducible quantitative evidence.
- The non-Python guard and the observe→search roundtrip fix are correctness
  wins, not marketing claims.

**What is open:**
- The agent-level effect of Borg retrieval is NOT statistically supported.
  The only real paired run is n=7, p=0.125. The P1.1 MiniMax measurement
  produced a floor-effect null (0/10 both arms). P2.1 Sonnet is still
  running. One of three things is true: (a) the mechanism works on
  stronger models and the floor effect masked it, (b) the mechanism does
  not work, or (c) we need a harder benchmark. We do not yet know which.

**What was fabricated:**
- "+50pp / p=0.031 / n=10" — fabricated in a post-hoc file (correction #1).
- "+34pp, directionally supports" — caveat-stripped from a real n=7 result
  (correction #2). Both correction blocks are preserved at the top of this
  PRD as forensic evidence.

**The honest path forward:** finish the Sonnet replication, publish whatever
result it produces, and resist writing any agent-level claim into this PRD
until a properly-powered experiment exists. The classifier can and should
ship on its own merits.

**The product is real. The classifier evidence is real. The agent-level
evidence is not. Ship the classifier, keep measuring the mechanism, and
stop promising what has not been tested.**
