# Borg Experiment V2: Scaled Mechanism Validation
## Does reasoning trace injection improve AI agent success rate on hard coding tasks?

**Date:** 2026-04-01
**Status:** Ready to execute
**Budget:** 150 runs max
**Timeline:** 1 week

---

## 1. What Changed From V1

| V1 (original) | V2 (this design) | Why |
|---|---|---|
| 15 tasks x 3 conditions x 2 runs = 90 | 25 tasks x 2 conditions x 3 runs = 150 | More tasks = more statistical power for binary outcomes |
| Wilcoxon signed-rank | McNemar's test | Correct test for paired binary data |
| 3 conditions (A, B, C) | 2 conditions (A, B) | C condition wastes budget; mechanism question doesn't need it |
| Latin square | Simple randomized counterbalancing | Latin square adds complexity without benefit for 1 model |
| Median of 2 runs | Majority vote of 3 runs | Median of 2 binary values is undefined |
| Sequential analysis | Run to completion | Too few runs for meaningful interim looks |
| Dose-response (5 tasks) | Dropped | Underpowered; save for follow-up |
| GPT-4o-mini replication | Dropped | 5 tasks is meaningless replication |
| alpha = 0.017 (Bonferroni/3) | alpha = 0.05 (single primary test) | Only 1 primary comparison now |

## 2. Research Question

**RQ1 (Primary):** Does injecting a correct reasoning trace improve coding task success rate compared to no trace?

**H0:** P(success|trace) <= P(success|no_trace)
**H1:** P(success|trace) > P(success|no_trace)

That's it. One question. One test.

## 3. Design

### Conditions

| Condition | Label | What the agent gets |
|---|---|---|
| A | No Trace | Task description only. No mention of any cache or trace. |
| B | Reasoning Trace | Task description + reasoning trace injected into the prompt. Agent doesn't choose whether to use it — it's given. |

### Why forced injection, not voluntary query

The pilot showed agents voluntarily query the cache. But voluntary query introduces a confound: if the agent doesn't query, B=A and we can't detect the effect. Forced injection eliminates this noise. If the mechanism works with forced injection, we can later test voluntary query as a delivery method.

### Task Requirements

Each task MUST have:
1. `setup.sh` — creates the broken repo state from scratch (no git clones, no external deps)
2. `check.sh` — deterministic pass/fail verification (exit 0 = pass, exit 1 = fail)
3. `prompt.txt` — the task description given to the agent
4. `trace.txt` — the reasoning trace for condition B
5. `check.sh` MUST fail in the starting state (verified by runner)
6. `check.sh` MUST pass when the correct fix is applied (verified manually)

### Task Difficulty Target

40-60% baseline success rate in Condition A (no trace).

This means: the agent solves the task roughly half the time without help. This is the sweet spot where:
- There's room for improvement (not ceiling)
- The task is solvable (not floor)
- The trace has signal to provide

### Task Categories

| Category | Count | Description |
|---|---|---|
| Python debugging | 8 | Fix bugs in Python code (wrong logic, edge cases, type errors) |
| Python refactoring | 5 | Restructure code while maintaining behavior |
| Multi-file debugging | 5 | Bug spans multiple files, requires cross-file reasoning |
| Data pipeline | 4 | Fix broken data processing scripts |
| Config/setup | 3 | Fix broken configs, build files, environment issues |

All tasks are Python-only (consistent environment, no dependency hell).

## 4. Reasoning Traces

### What a trace contains

```
REASONING TRACE FOR: [task title]

PROBLEM DECOMPOSITION:
- [How the problem breaks down into sub-problems]

WHAT WAS TRIED:
- [Approach 1]: [What happened, why it failed]
- [Approach 2]: [What happened, why it worked]

KEY INSIGHT:
- [The non-obvious realization that unlocks the solution]

WHERE TO LOOK:
- [Which file(s) and what to look for]

PITFALLS:
- [Common mistakes to avoid]
```

### What a trace does NOT contain
- No code snippets (beyond import names)
- No line numbers
- No exact fix description
- No step-by-step instructions

The trace provides REASONING, not ANSWERS.

### Trace Generation Protocol

For each task:
1. Solve the task manually
2. Write the trace from memory of the solving process
3. Remove any code/line-number specifics
4. Verify: an experienced developer reading the trace would know WHERE to look and WHAT approach to take, but would still need to write the code

## 5. Sample Size Justification

### Power Analysis for McNemar's Test

**Setup:**
- n = 25 paired observations (tasks)
- Each task aggregated to majority-vote success (3 runs → binary)
- Expected: ~50% baseline success (calibrated)
- Expected effect: +34pp (based on pilot)
- So: P(A=fail, B=success) ≈ 0.34, P(A=success, B=fail) ≈ 0.00

**McNemar's test discordant pairs:**
- Discordant pairs ≈ 8-9 out of 25 (34% of tasks flip from fail to success)
- At n_discordant = 8, McNemar chi-sq = 8.0, p = 0.005 (one-tailed)
- At n_discordant = 6, McNemar chi-sq = 6.0, p = 0.014
- At n_discordant = 5, McNemar chi-sq = 5.0, p = 0.025

**Power estimate:**
- If true effect = 34pp: ~85% power at alpha = 0.05
- If true effect = 20pp: ~55% power (marginal)
- Minimum detectable effect at 80% power: ~28pp

**GO threshold (pre-registered):**
- Primary: McNemar p < 0.05 (one-tailed)
- Secondary: >= 6 tasks flip from fail→success with trace
- Practical: success rate improvement >= 20pp

## 6. Counterbalancing

Simple randomized order:
- For each task, randomly assign order: A-first or B-first
- ~50% of tasks get A first, ~50% get B first
- Seed: SHA256(task_id + "borg-v2") mod 2

Between runs within a condition: different random seeds for the agent.

## 7. Measurement

### Per-Run Data

```json
{
  "task_id": "string",
  "condition": "A|B",
  "run": 1|2|3,
  "order": 1|2,
  "success": true|false,
  "tool_calls": int,
  "wall_time_seconds": float,
  "agent_output": "string",
  "error": null|"string",
  "timestamp": "ISO8601"
}
```

### Aggregation

Per task-condition: majority vote of 3 runs → binary success/fail

### Primary Analysis

McNemar's exact test (one-tailed) on 25 paired binary outcomes.

### Secondary Analyses

1. **Effect size:** Odds ratio with 95% CI
2. **Tool call comparison:** Wilcoxon signed-rank on tool calls (B vs A, successful runs only)
3. **Per-category breakdown:** Success rate by task category (descriptive only)
4. **Negative transfer check:** Count tasks where B < A (should be ~0)

## 8. Execution Protocol

### Phase 1: Task Building (day 1-2)
- Build 30 candidate tasks (25 needed, 5 spare)
- Each task: setup.sh, check.sh, prompt.txt, trace.txt
- Verify: setup.sh creates state, check.sh fails, manual fix makes check.sh pass

### Phase 2: Calibration (day 2-3)
- Run each task 5x in Condition A (no trace)
- Keep tasks with 2-3/5 success (≈40-60%)
- Drop tasks with 0-1/5 or 4-5/5 success
- Select exactly 25 tasks

### Phase 3: Main Experiment (day 3-5)
- 25 tasks × 2 conditions × 3 runs = 150 runs
- Counterbalanced order per task
- Fresh environment per run (copy repo from template)
- 10-minute timeout per run

### Phase 4: Analysis (day 5-6)
- Aggregate to majority-vote
- McNemar's test
- Effect size + CI
- GO/NO-GO decision

## 9. GO/NO-GO Criteria

| Criterion | Threshold | Decision |
|---|---|---|
| McNemar p < 0.05 | Primary | Must pass for GO |
| >= 6 tasks flip fail→success | Secondary | Must pass for GO |
| 0 tasks flip success→fail | Safety | If violated, investigate |
| Success rate improvement >= 20pp | Practical | Must pass for GO |

**GO:** All criteria met → build difficulty detector + run product experiment
**CONDITIONAL GO:** p < 0.10 and >= 4 flips → expand to 40 tasks
**NO-GO:** p > 0.10 or < 4 flips → mechanism doesn't scale, kill project

## 10. What This Does NOT Test

1. Difficulty detection (tested in follow-up experiment)
2. Real traces from prior agent sessions (tested in follow-up)
3. Voluntary query vs forced injection (tested in follow-up)
4. Multiple agent models (tested in follow-up)
5. Token cost impact (measured but not a decision criterion)

This experiment answers ONE question: does the mechanism work at scale?

---

**Total cost:** ~150 delegate_task runs × ~$0.05 = ~$7.50
**Total time:** ~150 runs × 5 min = 12.5 hours, parallelized across 5 nodes = ~2.5 hours
**Total calendar:** 5-6 days including task building and calibration
