# BORG EXPERIMENT V3 — FIVE CAPABILITY TESTS
## Rigorous Evaluation of a Shared Reasoning Cache for AI Agents
## Date: 2026-03-31 | Version: 3.0 | Status: DESIGN COMPLETE

---

# 0. LESSONS FROM V1/V2

| Problem | Impact | V3 Fix |
|---------|--------|--------|
| Tasks too easy (18/19 control solved) | No room for cache to help | Calibrate to 40-60% control success |
| Tested prompts, not cache | Measured prompt engineering | Test actual cache retrieval |
| No counterbalancing (V1) | Order confound | Latin square counterbalancing |
| Token measurement proxy | Noisy signal | Use actual API token counts from delegate_task metadata |
| Tested all capabilities at once | Can't attribute effect | Separate experiment per capability |
| Single run per condition | High variance | 3 runs per (task, condition) pair |

---

# 1. FIVE INDEPENDENT EXPERIMENTS

Each capability gets its own experiment with its own hypothesis, metrics, and success criteria. No pooling across capabilities.

## Experiment 1: CACHE HITS
**Hypothesis:** Agent B solves a task faster when Agent A's solution is in the cache.

## Experiment 2: FAILURE MEMORY
**Hypothesis:** Agent B avoids a dead end when warned that Agent A failed there.

## Experiment 3: ANTI-PATTERN INJECTION
**Hypothesis:** Specific anti-patterns from real failures reduce error rate.

## Experiment 4: START-HERE SIGNALS
**Hypothesis:** Telling the agent which file contains the bug reduces exploration.

## Experiment 5: DIFFICULTY-GATED INTERVENTION
**Hypothesis:** Intervening only on hard tasks (no intervention on easy) improves overall efficiency.

---

# 2. EXPERIMENT 1: CACHE HITS

## 2.1 Design

```
Phase 1: Agent A solves 10 tasks. Solutions cached.
Phase 2: Agent B gets the SAME 10 tasks.
  - Control: Agent B has NO cache access
  - Treatment: Agent B can retrieve Agent A's cached solution approach

Counterbalancing: 5 tasks run control-first, 5 treatment-first.
Repetition: 3 runs per (task, condition) pair = 60 total runs.
```

## 2.2 Task Requirements
- Tasks must be HARD: control agent should succeed 40-60% of the time
- Multi-file bugs requiring reasoning about code flow
- Solution is non-obvious (not one-liner fixes)
- Cache provides: which files to look at, what the root cause was, what fix worked

## 2.3 What the Cache Provides (Treatment)
```
"For this error pattern (TypeError in data pipeline):
- ROOT CAUSE: get_user_data() returns None, not {}
- FIX: Change users.get(user_id) to users.get(user_id, {})
- ALSO: Add None check in normalize_data()
- TIME SAVED: Agent A spent 180s on wrong hypothesis before finding this"
```

## 2.4 Metrics

| Metric | Type | Primary? | How Measured |
|--------|------|----------|-------------|
| Success rate | Binary | YES | check.sh exit code |
| Tokens used | Continuous | YES | delegate_task tokens.input + tokens.output |
| Time to solution | Continuous | NO | delegate_task duration_seconds |
| Wrong approaches tried | Count | NO | Count of reverted patches |

## 2.5 Statistical Analysis
- Primary: Wilcoxon signed-rank on tokens (paired)
- Confirmatory: Exact permutation test on success rate
- Effect size: Cohen's d for tokens, odds ratio for success
- Multiple runs: Use median of 3 runs per cell
- Correction: None needed (single capability, single primary metric)

## 2.6 Success Criteria

| ID | Criterion | Target |
|----|-----------|--------|
| C1.1 | Success rate improvement | Treatment > Control by >= 20 percentage points |
| C1.2 | Token reduction | Treatment uses >= 25% fewer tokens (p < 0.05) |
| C1.3 | Effect size | Cohen's d >= 0.5 (medium effect) |

## 2.7 Controls
- SHUFFLED CACHE control: Agent B gets cache entries from DIFFERENT tasks (wrong solutions). This isolates "having cache" from "having the RIGHT cache."
- If shuffled cache helps as much as correct cache, the effect is retrieval overhead, not knowledge.

---

# 3. EXPERIMENT 2: FAILURE MEMORY

## 3.1 Design

```
Phase 1: Seed failure memory. Run Agent A on 10 hard tasks.
  Agent A fails on some. Record: which approach failed, why, error message.
Phase 2: Agent B gets the SAME 10 tasks.
  - Control: No failure warnings
  - Treatment: Before starting, inject "WARNING: Approach X was tried 
    by another agent and failed because Y. Do not try approach X."
  - Shuffled Control: Inject warnings from WRONG tasks (irrelevant warnings)
```

## 3.2 Task Requirements
- Tasks with KNOWN WRONG APPROACHES (common traps)
- Example: "Don't modify the JWT middleware — the auth bug is in the DB connection pool"
- Control agent should try the wrong approach >= 50% of the time

## 3.3 What the Warning Provides (Treatment)
```
"WARNING: 2 agents tried to fix this by modifying src/auth.py. Both failed.
The actual root cause is in src/db.py line 42 — the connection pool max_size
is set to 1, causing serialized access under load.
DO NOT modify auth.py."
```

## 3.4 Metrics

| Metric | Primary? | How Measured |
|--------|----------|-------------|
| Avoidance rate (did agent skip the wrong approach?) | YES | Check if agent modified the warned file |
| Success rate | YES | check.sh exit code |
| Tokens on wrong approach | NO | Tokens consumed before pivoting away from warned approach |

## 3.5 Success Criteria

| ID | Criterion | Target |
|----|-----------|--------|
| C2.1 | Avoidance rate | >= 70% of warned agents skip the wrong approach |
| C2.2 | Success rate improvement | Treatment > Control by >= 15 percentage points |
| C2.3 | Shuffled control shows NO benefit | Shuffled warning avoidance rate < 30% |

---

# 4. EXPERIMENT 3: ANTI-PATTERN INJECTION

## 4.1 Design

```
Tasks with KNOWN anti-patterns that cause failure.
  - Control: Agent gets task description only
  - Treatment: Agent gets task description + specific anti-pattern warning
  
Anti-patterns are SPECIFIC, not generic:
  NOT: "Don't read every file first"
  YES: "In this codebase, the error handler at line 15 silently swallows
       exceptions. Don't assume an empty return means success."
```

## 4.2 Metrics

| Metric | Primary? |
|--------|----------|
| Error rate (specific error type avoided) | YES |
| Success rate | YES |
| Time to first correct action | NO |

## 4.3 Success Criteria

| ID | Criterion | Target |
|----|-----------|--------|
| C3.1 | Error rate reduction | Treatment error rate <= 50% of control error rate |
| C3.2 | Anti-pattern compliance | >= 80% of agents heed the anti-pattern |

---

# 5. EXPERIMENT 4: START-HERE SIGNALS

## 5.1 Design

```
Multi-file tasks where the bug could be in any of 5+ files.
  - Control: Agent gets error message + full repo
  - Treatment: Agent gets error message + "Start here: src/utils.py line 42"

The START-HERE signal tells the agent WHICH FILE to look at first,
not how to fix the bug.
```

## 5.2 Metrics

| Metric | Primary? |
|--------|----------|
| Files read before finding bug | YES (lower = better) |
| Tokens to first correct edit | YES |
| Total tokens | NO |
| Success rate | NO (should be similar — the signal helps efficiency, not correctness) |

## 5.3 Success Criteria

| ID | Criterion | Target |
|----|-----------|--------|
| C4.1 | Files read before bug found | Treatment reads >= 50% fewer files |
| C4.2 | Tokens to first correct edit | Treatment uses >= 30% fewer tokens |

---

# 6. EXPERIMENT 5: DIFFICULTY-GATED INTERVENTION

## 6.1 Design

```
20 tasks: 10 easy (control succeeds 90%+) and 10 hard (control succeeds 40-60%).
  - Control: No intervention on any task
  - Treatment-ALL: Intervention on ALL tasks (like V1 experiment)
  - Treatment-GATED: Intervention ONLY on hard tasks

This tests whether the SELECTOR matters — intervene only when needed.
```

## 6.2 Metrics

| Metric | Primary? |
|--------|----------|
| Total tokens across all 20 tasks | YES |
| Success rate across all 20 tasks | YES |
| Overhead on easy tasks (Treatment-ALL vs Control) | Diagnostic |

## 6.3 Success Criteria

| ID | Criterion | Target |
|----|-----------|--------|
| C5.1 | Treatment-GATED beats Treatment-ALL on total tokens | p < 0.05 |
| C5.2 | Treatment-GATED beats Control on hard tasks | Success rate +20pp |
| C5.3 | Treatment-GATED equals Control on easy tasks | No overhead (< 5%) |

---

# 7. TASK CALIBRATION PROTOCOL

The critical failure of V1/V2 was tasks being too easy. V3 requires:

## 7.1 Pre-Calibration

Before running any experiment:
1. Run each candidate task 5 times with baseline agent (no intervention)
2. Record success rate per task
3. KEEP only tasks with 30-70% baseline success rate
4. DISCARD tasks with > 80% success (too easy) or < 20% (too hard)

## 7.2 Task Difficulty Tiers

| Tier | Control Success Rate | Use For |
|------|---------------------|---------|
| Easy | 80-100% | Experiment 5 (gated intervention) |
| Medium | 50-80% | Experiments 1, 3, 4 |
| Hard | 30-50% | Experiments 1, 2 |
| Very Hard | < 30% | Discard (underpowered) |

## 7.3 How to Make Tasks Harder

- Multiple files involved (not single-file bugs)
- Bug is in a different file than the error message suggests
- Multiple interacting bugs (fix A reveals bug B)
- Requires understanding data flow across modules
- Red herrings: misleading comments, stale documentation
- Time pressure: 10-minute timeout instead of 30

---

# 8. STATISTICAL FRAMEWORK

## 8.1 Per-Experiment Power Analysis

| Experiment | Pairs | Runs/Cell | Total Runs | Effect Size Detectable |
|-----------|-------|-----------|------------|----------------------|
| 1. Cache Hits | 10 | 3 | 60 | d=0.58 (medium) |
| 2. Failure Memory | 10 | 3 | 60 | d=0.58 |
| 3. Anti-Patterns | 10 | 3 | 60 | d=0.58 |
| 4. Start-Here | 10 | 3 | 60 | d=0.58 |
| 5. Difficulty-Gated | 20 | 3 | 180 | d=0.40 |
| **TOTAL** | | | **420** | |

## 8.2 Analysis Pipeline Per Experiment

```
Step 1: Aggregate 3 runs per cell → take median (robust to outliers)
Step 2: Normality test (Shapiro-Wilk on paired differences)
Step 3: If normal → paired t-test; if not → Wilcoxon signed-rank
Step 4: Exact permutation test as confirmatory
Step 5: Bayesian paired model for posterior distribution of effect
Step 6: Bootstrap 95% CI (BCa method, 10000 resamples)
Step 7: Effect size (Cohen's d for continuous, odds ratio for binary)
Step 8: Report: point estimate, CI, p-value, effect size, Bayes factor
```

## 8.3 Multiple Comparisons

5 experiments × 1 primary metric each = 5 tests.
Bonferroni correction: α_adj = 0.05 / 5 = 0.01 per experiment.
Report both raw and adjusted p-values.

## 8.4 Threats to Validity

| Threat | Type | Mitigation |
|--------|------|------------|
| Model stochasticity | Internal | 3 runs per cell, report variance |
| Task selection bias | Internal | Pre-calibration with baseline runs |
| Order effects | Internal | Latin square counterbalancing |
| Learning/carry-over | Internal | Fresh workspace per run |
| Prompt sensitivity | Construct | Canonical prompts, vary in sensitivity analysis |
| Generalizability | External | Use tasks from diverse domains |
| Cache quality | Construct | Shuffled cache control |
| Evaluator bias | Internal | Automated check.sh, no human judgment |

---

# 9. REPORTING STANDARD

Each experiment produces a report following ACM SIGSOFT empirical standards:

```
1. Research Question (RQ)
2. Hypothesis (H0 and H1, pre-registered)
3. Experimental Setup (hardware, model, temperature, seeds)
4. Task Set (with difficulty calibration data)
5. Procedure (step-by-step protocol)
6. Results Table (descriptive statistics per condition)
7. Statistical Tests (test, statistic, p-value, effect size, CI)
8. Bayesian Analysis (posterior distribution, Bayes factor)
9. Ablation (shuffled cache control results)
10. Threats to Validity (internal, external, construct)
11. Raw Data (JSON, publicly archived)
12. Replication Package (code, tasks, analysis scripts)
```

---

# 10. IMPLEMENTATION TIMELINE

```
Week 1: CALIBRATION
  - Build 30 candidate hard tasks (multi-file, multi-bug)
  - Pre-calibrate: run each 5x with baseline agent
  - Select 10 tasks per experiment from 30-70% success bracket
  - Discard easy tasks, archive hard tasks

Week 2: EXPERIMENTS 1-2
  - Experiment 1 (Cache Hits): 60 runs
  - Experiment 2 (Failure Memory): 60 runs
  - Analyze + report

Week 3: EXPERIMENTS 3-4
  - Experiment 3 (Anti-Patterns): 60 runs
  - Experiment 4 (Start-Here): 60 runs
  - Analyze + report

Week 4: EXPERIMENT 5 + SYNTHESIS
  - Experiment 5 (Difficulty-Gated): 180 runs
  - Cross-experiment synthesis
  - Final verdict on each capability
  - Publish results
```

---

# 11. GO/NO-GO PER CAPABILITY

Each capability is independently evaluated:

| Capability | GO Condition | NO-GO Condition |
|-----------|-------------|-----------------|
| Cache Hits | C1.1 AND C1.2 AND C1.3 pass | Any C1.x fails |
| Failure Memory | C2.1 AND C2.2 AND C2.3 pass | Any C2.x fails |
| Anti-Patterns | C3.1 AND C3.2 pass | Any C3.x fails |
| Start-Here | C4.1 AND C4.2 pass | Any C4.x fails |
| Difficulty-Gated | C5.1 AND C5.2 AND C5.3 pass | Any C5.x fails |

**Product decision:**
- If >= 3 capabilities GO → ship Borg V3 with those capabilities
- If 1-2 capabilities GO → ship minimal borg with only proven capabilities
- If 0 capabilities GO → kill the product

---

# 12. INDEPENDENT REVIEW PROTOCOL

Each experiment reviewed by a separate "team" (subagent with different prompt):

```
Team A: Designs experiment + runs it
Team B: Reviews design for methodological flaws BEFORE execution
Team C: Independently analyzes raw data AFTER execution (blinded to Team A's conclusions)
Team D: Attempts to REPLICATE results on different task set
```

If Team A and Team C disagree on conclusions, Team D's replication is the tiebreaker.

---

*Five capabilities. Five independent experiments. 420 agent runs.*
*Pre-calibrated tasks. Shuffled-cache controls. Bayesian analysis.*
*Independent review. Replication. No theatre.*
*The data decides what ships.*
