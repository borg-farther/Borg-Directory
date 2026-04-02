# Borg SWE-bench A/B Experiment — Formal Specification
## Version: 1.0 | Date: 2026-04-01 | Status: PRE-REGISTERED

---

## 1. RESEARCH QUESTION

**Does injecting a reasoning trace (developer discussion context about a bug) improve an AI coding agent's success rate on real-world Django bugs?**

## 2. HYPOTHESES (Pre-Registered)

**H0 (Null):** The proportion of tasks where B succeeds and A fails equals the proportion where A succeeds and B fails. (Traces have no effect.)

**H1 (Alternative):** The proportion of tasks where B succeeds and A fails EXCEEDS the proportion where A succeeds and B fails. (Traces improve success rate.)

**Direction:** One-tailed. We hypothesize B > A.

## 3. DESIGN

### 3.1 Within-Subject Paired Design
- Each task is tested under BOTH conditions
- Same task, same Docker image, same test suite
- Difference: only the prompt content varies

### 3.2 Conditions

**Condition A (Control):** Agent receives bug report + test list only.
**Condition B (Treatment):** Agent receives bug report + test list + hints_text reasoning trace.

### 3.3 Sample
- 12 SWE-bench Verified Django tasks
- Difficulty: "1-4 hours" (hard) and "15 min - 1 hour" (medium)  
- All hints_text verified: no patch diffs, no solution code, >50 chars
- Calibration baseline: 42% pass rate (5/12 pass Condition A)

### 3.4 Runs Per Cell
- 3 runs per task-condition cell
- Total: 12 tasks × 2 conditions × 3 runs = 72 runs
- Aggregation: majority vote (2/3 or 3/3 = SUCCESS)

### 3.5 Counterbalancing
- Order determined by SHA256(task_id + "borg-v3") mod 2
- ~50% tasks get A-first, ~50% B-first
- Each run uses a fresh workspace (no carryover)

## 4. TASK LIST (12 tasks)

| # | Task ID | Difficulty | Cal. Result | Hints Quality | Hints Length |
|---|---------|-----------|-------------|---------------|-------------|
| 1 | django__django-10554 | 1-4 hours | FAIL | WEAK | 338 |
| 2 | django__django-11087 | 15 min-1h | PASS | GOOD | 7256 |
| 3 | django__django-11138 | 1-4 hours | FAIL | WEAK | 166 |
| 4 | django__django-11265 | 15 min-1h | PASS | GOOD | 4994 |
| 5 | django__django-11400 | 1-4 hours | PASS | OK | 1056 |
| 6 | django__django-12708 | 1-4 hours | PASS | OK | 421 |
| 7 | django__django-12754 | 15 min-1h | FAIL | GOOD | 13753 |
| 8 | django__django-13315 | 15 min-1h | FAIL | GOOD | 6700 |
| 9 | django__django-13344 | 1-4 hours | FAIL | GOOD | 1554 |
| 10 | django__django-15128 | 1-4 hours | PASS | GOOD | 8382 |
| 11 | django__django-15503 | 1-4 hours | FAIL | OK | 634 |
| 12 | django__django-16560 | 1-4 hours | FAIL | WEAK | 355 |

## 5. VERIFICATION PROTOCOL

### 5.1 Pre-Experiment Verification (MUST PASS BEFORE ANY RUNS)

**V1: Gold Patch Test** — For each task:
1. Start fresh container from Docker image
2. Apply test_patch (add failing tests)
3. Verify FAIL_TO_PASS tests FAIL (confirms bug is present)
4. Apply gold patch (known solution)
5. Verify FAIL_TO_PASS tests PASS (confirms task IS solvable)
6. Record: task_id, tests_fail_before=True, tests_pass_after=True

**V2: Hints Contamination Audit** — For each task:
1. Verify hints_text does NOT contain diff/patch syntax
2. Verify hints_text does NOT contain lines from gold patch
3. Verify hints_text length is >50 characters
4. Record: task_id, contamination_check=PASS

**V3: Prompt Integrity Check** — For each task:
1. Generate Condition A prompt and Condition B prompt
2. Verify Condition A prompt does NOT contain hints_text
3. Verify Condition B prompt DOES contain hints_text
4. Verify both prompts contain identical bug report and test list
5. Diff the two prompts — only difference should be the trace section

**V4: Environment Reproducibility** — For 3 randomly selected tasks:
1. Run setup_workspace() twice
2. Verify both workspaces produce identical file trees
3. Verify tests produce identical results in both

### 5.2 Per-Run Verification

**V5: Pre-Run State Check**
1. Verify FAIL_TO_PASS tests FAIL before agent starts
2. If tests pass before fix → INVALID RUN (exclude + investigate)

**V6: Post-Run State Check**  
1. Run FAIL_TO_PASS tests
2. Record: pass/fail, exact test output, exit code
3. If any FAIL_TO_PASS test is missing → INVALID RUN

**V7: No Test Modification Check**
1. After agent finishes, verify test files are UNMODIFIED
2. git diff on tests/ directory — must be empty
3. If test files modified → INVALID RUN (agent cheated)

### 5.3 Post-Experiment Verification

**V8: Cross-Condition Consistency**
1. For tasks where both A and B pass: verify both produced valid fixes
2. For tasks where A passes but B fails: investigate — possible negative transfer
3. Report any anomalies

**V9: Order Effect Check**
1. Compare success rates for A-first vs B-first tasks
2. Fisher's exact test on order × success
3. If p < 0.10: report order effect as limitation

## 6. SUCCESS CRITERIA (Pre-Registered)

### 6.1 Primary (ALL must be met for GO)

| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Statistical significance | McNemar's exact test (one-tailed) | p < 0.05 |
| Minimum effect size | Discordant pairs favoring B | ≥ 3 tasks flip fail→pass |
| No harm | Tasks flipping pass→fail | 0 (zero negative transfer) |

### 6.2 Secondary (Informational)

| Criterion | Metric | Threshold |
|-----------|--------|-----------|
| Practical significance | Success rate improvement | ≥ 15 percentage points |
| Robustness | B success on majority-vote | ≥ 2/3 runs for each flipped task |
| Consistency | Same tasks flip across runs | ≥ 2/3 agreement |

### 6.3 Decision Rules

**GO:** All primary criteria met → Borg mechanism validated. Invest in difficulty detector + production trace generation.

**CONDITIONAL GO:** p < 0.10 AND ≥ 2 flips AND 0 negative → Run additional 13 tasks for more power.

**NO-GO:** p ≥ 0.10 OR < 2 flips OR any negative transfer → Mechanism doesn't work on real tasks. Kill product hypothesis.

## 7. STATISTICAL ANALYSIS PLAN

### 7.1 Primary Analysis: McNemar's Exact Test

Contingency table on 12 paired binary outcomes (majority-vote aggregated):

```
              B-fail    B-pass
A-fail          a          b       (b = traces helped)
A-pass          c          d       (c = traces hurt)
```

Test statistic: Under H0, b/(b+c) = 0.5
P-value: Exact binomial P(X ≥ b | n=b+c, p=0.5), one-tailed

### 7.2 Secondary Analysis: Mixed-Effects Logistic Regression

Using all 72 individual runs (not aggregated):

```
success ~ condition + (1|task) + (1|task:run)
```

- Fixed effect: condition (A vs B)
- Random intercept: task (accounts for task difficulty variation)  
- Random slope: task:run (accounts for run-to-run variation within task)

Report: odds ratio with 95% CI, p-value from Wald test

### 7.3 Effect Size

- McNemar's OR: b/c (with Haldane correction +0.5 if c=0)
- Cohen's g: (b-c)/(b+c) for McNemar's
- 95% CI via exact binomial

### 7.4 Power Calculation

With 12 tasks, McNemar's at alpha=0.05 (one-tailed):
- If b=3, c=0: p = 0.5^3 = 0.125 (NOT significant)
- If b=4, c=0: p = 0.5^4 = 0.0625 (NOT significant)  
- If b=5, c=0: p = 0.5^5 = 0.03125 (SIGNIFICANT ✓)
- If b=3, c=0 with one-tailed exact: p = 0.125 (need ≥5)

**Minimum detectable effect: 5 tasks must flip fail→pass with 0 flipping pass→fail.**

Given 7 tasks failed calibration, we need ≥5 of those 7 to flip. That's a 71% improvement rate among failed tasks. This is a HIGH bar — appropriately demanding for a GO decision.

## 8. EXECUTION PROTOCOL

### Phase 1: Pre-Verification (BEFORE any experiment runs)
1. Run V1 (gold patch test) on all 12 tasks
2. Run V2 (hints contamination) on all 12 tasks
3. Run V3 (prompt integrity) on all 12 tasks
4. Run V4 (environment reproducibility) on 3 tasks
5. Document all results in verification_log.json
6. PROCEED ONLY IF all verifications pass

### Phase 2: Experiment Execution
For each task (in counterbalanced order):
1. Set up fresh workspace (setup_batch.py)
2. Run V5 (pre-run state check)
3. Launch agent via delegate_task with appropriate prompt
4. After agent completes: Run V6 (post-run state check)
5. Run V7 (no test modification check)
6. Record all data
7. Cleanup workspace
8. Repeat for 3 runs per condition

### Phase 3: Analysis
1. Compile all 72 run results
2. Aggregate to majority-vote per task-condition
3. Build contingency table
4. Run McNemar's exact test
5. Run GLMM
6. Run verification checks V8, V9
7. Generate report

## 9. DATA RECORDING

Each run produces:
```json
{
  "task_id": "string",
  "condition": "A|B",
  "run": 1|2|3,
  "order": 1|2,
  "success": true|false,
  "verification": {
    "pre_tests_fail": true|false,
    "post_tests_result": "pass|fail|error",
    "test_files_modified": true|false,
    "exit_code": int
  },
  "agent": {
    "tool_calls": int,
    "wall_time_seconds": float,
    "model": "string",
    "max_iterations_hit": true|false
  },
  "test_output": "string (last 1000 chars)",
  "timestamp": "ISO8601"
}
```

## 10. THREATS TO VALIDITY

| Threat | Mitigation | Residual Risk |
|--------|-----------|---------------|
| hints_text = answer, not trace | Filtered for diffs/solution code | Medium — some hints may implicitly reveal fix |
| Agent model variability | 3 runs per cell, majority vote | Low |
| Test patch application failure | V1 gold patch verification | Low |
| Order effects | Counterbalanced, V9 check | Low |
| Docker environment drift | Fresh workspace per run | Very low |
| Agent learns from prompts | Subagents have no memory | None |
| Experimenter bias | Automated verification, pre-registered | None |
| Small n (12 tasks) | Acknowledged; require ≥5 flips for significance | Medium |

## 11. WHAT THIS PROVES AND DOESN'T PROVE

### Proves (if GO)
- Developer-written reasoning context helps AI agents fix real bugs
- The improvement is ≥ 5 out of 7 failed tasks (≥71% recovery rate)
- No negative transfer on tasks agents already solve

### Does NOT prove
- That agent-generated traces would work equally well
- That Borg can automatically match tasks to relevant traces
- That the difficulty detector works
- Production readiness

### If NO-GO
- Developer reasoning context does NOT reliably help agents fix real bugs
- The mechanism from the pilot (n=3) does not replicate at scale
- Borg's core hypothesis is disproven with real-world data
---

**This spec is FROZEN. No modifications after experiment execution begins.**
