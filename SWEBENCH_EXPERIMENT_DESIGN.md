# Borg SWE-bench Experiment: Does Reasoning Trace Injection Help Agents Solve Real-World Bugs?

## Date: 2026-04-01
## Status: Draft — pending adversarial review

---

## 1. Core Question

**Does injecting a reasoning trace (hints about the bug's nature, root cause, and approach) improve an AI agent's success rate on real-world software engineering tasks that agents genuinely struggle with?**

## 2. Why SWE-bench

Our synthetic tasks (33 single-file Python bugs) had 91% baseline pass rate — too easy. SWE-bench Verified provides:
- 500 real GitHub issues from Django, scikit-learn, matplotlib, etc.
- Published pass rates: best agents solve ~77%, meaning ~23% are genuinely hard
- Difficulty labels: `<15 min`, `15 min - 1 hour`, `1-4 hours`, `>4 hours`
- `hints_text` field: reasoning context from bug discussions (natural trace analog)
- Docker-based deterministic evaluation (test suite pass/fail)

## 3. Task Selection

### Source
SWE-bench Verified dataset, `django/django` repo only (largest subset: 231 tasks).

### Why Django only
- Consistency: same codebase, same patterns, same test infrastructure
- Reduces confound: agent familiarity with framework is constant across tasks
- Largest sample: 231 tasks gives us room to calibrate

### Difficulty targeting
We want tasks the agent solves ~40-60% of the time. Strategy:
1. Select all 42 "1-4 hours" difficulty tasks (hardest bracket with sufficient n)
2. If calibration shows these are too hard (<30%), mix in some "15 min - 1 hour" tasks
3. If too easy (>60%), the dataset's difficulty labels are wrong and we note it

### Selection criteria
- Must have `hints_text` (needed for Condition B)
- Must have 1-3 tests in FAIL_TO_PASS (tractable verification)
- Must be Django (consistent codebase)
- Final selection: 10 tasks after calibration

## 4. Conditions

### Condition A: No Trace (Baseline)
Agent receives:
```
You are an expert software engineer. Fix the bug described in the 
issue below. The Django codebase is at /workspace/django.

ISSUE:
{problem_statement}

TESTS THAT MUST PASS:
{FAIL_TO_PASS tests}

After fixing, run: python -m pytest {tests} --no-header -q
The fix is correct when all specified tests pass.
```

### Condition B: Reasoning Trace (Treatment)  
Agent receives everything in Condition A PLUS:
```
REASONING TRACE FROM BUG DISCUSSION:
{hints_text}

Use this context to guide your approach. It contains insights 
about the root cause and potential approaches from developers 
who investigated this bug.
```

### Why `hints_text` as the trace
- It's real: from actual developer discussions on GitHub issues
- It's exactly what Borg would provide: reasoning context from prior investigation
- It's NOT the answer: hints discuss approach, not provide patches
- It's the natural analog of "prior agent's reasoning about this type of problem"

### Why NOT voluntary query
- Forced injection eliminates confound of cache query behavior
- If mechanism works with forced injection, voluntary query is a UX decision
- Simpler design = more statistical power

## 5. Experimental Design

### Structure
- 10 tasks (after calibration) × 2 conditions × 3 runs = 60 runs
- Within-subject: same task tested under both conditions
- Counterbalanced: ~50% A-first, ~50% B-first (hash-deterministic per task)
- Each run: fresh Docker container from SWE-bench harness

### Primary DV: Task success (binary)
- 0 = FAIL_TO_PASS tests don't pass
- 1 = All FAIL_TO_PASS tests pass AND no PASS_TO_PASS tests broken

### Aggregation: Majority vote of 3 runs
- 2/3 or 3/3 pass → task-condition = SUCCESS
- 0/3 or 1/3 pass → task-condition = FAIL

### Primary test: McNemar's exact test
- Paired binary outcomes on 10 tasks
- One-tailed (H1: B > A)
- alpha = 0.05

## 6. Verification & Success Criteria

### Pre-experiment verification
1. **Docker harness works**: Each task's Docker image builds and tests run
2. **Baseline fails**: FAIL_TO_PASS tests actually fail before fix
3. **Gold patch works**: Applying the known solution makes tests pass
4. **Agent can interact**: delegate_task agent can navigate Django codebase in Docker
5. **Prompts are clean**: No information leakage between conditions

### During experiment
6. **Fresh state**: Every run starts from clean Docker image (no carryover)
7. **Timeout**: 15 minutes per run (SWE-bench standard)
8. **Logging**: Full agent transcript, tool calls, timestamps saved per run
9. **Blind evaluation**: check.sh runs tests automatically, no human judgment

### Post-experiment verification
10. **Data integrity**: All 60 runs completed, no missing data
11. **Counterbalance check**: Verify ~50/50 A-first/B-first split
12. **No systematic bias**: Check if order (first/second) affects success
13. **Effect reproducibility**: Any task showing B>A should show it in 2/3+ runs

### GO/NO-GO Criteria (pre-registered)

| Criterion | Threshold | Required? |
|---|---|---|
| McNemar p-value | < 0.05 (one-tailed) | Primary |
| Tasks flipping fail→success | ≥ 3 out of 10 | Secondary |
| Tasks flipping success→fail | 0 (no negative transfer) | Safety |
| Success rate improvement | ≥ 20 percentage points | Practical |

**GO**: All criteria met → Borg mechanism validated on real tasks
**CONDITIONAL GO**: p < 0.10 AND ≥ 2 flips → expand to 25 tasks
**NO-GO**: p > 0.10 OR < 2 flips → mechanism doesn't work on real tasks

## 7. Infrastructure

### Per-task setup
```
For each SWE-bench task:
1. Build Docker image with correct Django version at correct commit
2. Apply test_patch (adds failing tests)
3. Verify FAIL_TO_PASS tests fail
4. Verify gold patch makes them pass
5. Save Docker image for reuse across runs
```

### Per-run execution
```
1. Start fresh container from saved image
2. Mount agent workspace
3. Present prompt (Condition A or B)
4. Agent works via delegate_task (terminal + file tools inside container)
5. After agent finishes (or timeout): run FAIL_TO_PASS tests
6. Also run PASS_TO_PASS tests (check for regressions)
7. Record: success/fail, tool calls, wall time, agent transcript
```

### Parallelization
- 3 runs can execute in parallel (different containers)
- 10 tasks × 2 conditions × 3 runs = 60 total
- At 15 min/run with 3 parallel: ~5 hours total

## 8. Analysis Plan

### Primary analysis
McNemar's exact test on 10 paired binary outcomes.

### Contingency table
```
              B-fail    B-success
A-fail          a          b       (b = traces helped)
A-success       c          d       (c = traces hurt)
```

McNemar chi-sq = (b - c)² / (b + c), df=1

### Effect size
- Odds ratio: b/c (with Haldane correction if c=0)
- 95% CI via exact binomial

### Secondary analyses
1. Tool call comparison (Wilcoxon on matched pairs, successful runs only)
2. Time comparison (same)
3. Per-difficulty-label breakdown (descriptive)
4. Order effect check (chi-square on first-vs-second position)

### What we will report regardless of outcome
- Raw data: all 60 run results
- Contingency table
- p-value and effect size with CI
- Per-task breakdown (which tasks flipped, which didn't)
- Qualitative analysis of 2-3 most interesting cases

## 9. Threats to Validity

| Threat | Mitigation |
|---|---|
| hints_text contains the answer | Review each task's hints — exclude if hints contain patch code |
| Docker environment inconsistency | Same image per task, fresh container per run |
| Agent model variability | 3 runs per cell, majority vote aggregation |
| Task selection bias | Calibration-driven selection, not cherry-picked |
| Information leakage across conditions | Separate containers, no shared state |
| Order effects | Hash-based counterbalancing, order effect test |
| hints_text quality varies | Report per-task results; exclude tasks with empty/useless hints |
| Small n (10 tasks) | Acknowledged limitation; design maximizes power within budget |

## 10. Budget

| Phase | Runs | Est. Time | Est. Cost |
|---|---|---|---|
| Docker setup + verification | 10 tasks | 2-3 hours | $0 (local) |
| Calibration (A only) | 30 runs | 7.5 hours | ~$3 |
| Main experiment | 60 runs | 15 hours | ~$6 |
| **Total** | **90 runs** | **~25 hours** | **~$9** |

## 11. Timeline

| Day | Activity |
|---|---|
| 1 | Docker infrastructure, task selection, gold patch verification |
| 2 | Calibration runs (30 baseline runs) |
| 3 | Task selection based on calibration, main experiment (60 runs) |
| 4 | Analysis, report writing, GO/NO-GO decision |

---

## 12. What This Test Proves (And Doesn't)

### Proves (if GO)
- Reasoning traces from bug discussions improve agent success on real-world tasks
- The mechanism works on tasks that agents genuinely struggle with
- Borg's core value proposition is validated

### Doesn't prove
- That Borg can automatically match incoming tasks to relevant traces
- That agent-generated traces work as well as developer-written hints
- That the difficulty detector works
- Production-readiness

### If NO-GO
- The reasoning trace mechanism doesn't work on real tasks
- Borg's core hypothesis is disproven
- Engineering effort should go elsewhere
- This is a clean, honest result with real data
