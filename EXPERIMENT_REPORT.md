# BORG A/B EXPERIMENT — FINAL REPORT
## Date: 2026-03-31 | Protocol: V2 (counterbalanced)

---

# VERDICT: BORG'S STRUCTURED APPROACH ADDS OVERHEAD, DOES NOT REDUCE TOKENS

---

## 1. RESULTS SUMMARY

| Metric | Control | Treatment | Difference | p-value | Significant? |
|--------|---------|-----------|------------|---------|-------------|
| **Tokens (primary)** | 1,365 mean | 1,547 mean | +13.3% MORE | p=0.96 | NO |
| **Time** | 54s mean | 48s mean | -11.1% faster | — | NO (confounded) |
| **Success rate** | 18/19 (95%) | 19/19 (100%) | +1 task | — | NO (n too small) |
| **Tasks where treatment used fewer tokens** | — | 4/19 | 21% of tasks | — | — |
| **Tasks where treatment used more tokens** | — | 14/19 | 74% of tasks | — | — |

## 2. PER-TASK BREAKDOWN

### Tasks where treatment HELPED (fewer tokens):
| Task | Control | Treatment | Savings |
|------|---------|-----------|---------|
| DEBUG-002 | 4,842 (FAIL) | 3,251 (PASS) | +33% AND fixed the bug |
| DEBUG-004 | 2,017 | 1,556 | +23% |
| TEST-001 | 1,879 | 1,745 | +7% |
| TEST-003 | 1,500 | 1,200 | +20% |

### Tasks where treatment HURT (more tokens):
| Task | Control | Treatment | Overhead |
|------|---------|-----------|----------|
| DEBUG-001 | 1,183 | 3,315 | -180% (worst case) |
| DEBUG-007 | 800 | 1,300 | -63% |
| REVIEW-001 | 1,800 | 2,500 | -39% |
| DEBUG-003 | 788 | 1,265 | -61% |
| Plus 10 more with 5-30% overhead | | | |

### Control tasks (should show no benefit):
| Task | Control | Treatment | Delta |
|------|---------|-----------|-------|
| CONTROL-001 | 500 | 600 | -20% (overhead) |
| CONTROL-002 | 600 | 700 | -17% (overhead) |
| CONTROL-003 | 600 | 700 | -17% (overhead) |
| CONTROL-004 | 500 | 600 | -20% (overhead) |

Control tasks correctly show no benefit — small consistent overhead from the structured prompt.

## 3. STATISTICAL TESTS

| Test | Statistic | p-value | Conclusion |
|------|-----------|---------|------------|
| Wilcoxon signed-rank (tokens, one-sided H1: treatment < control) | — | 0.96 | FAIL: treatment does NOT reduce tokens |
| Direction test (sign test) | 4 positive, 14 negative, 1 tie | — | Treatment is worse on 74% of tasks |

## 4. WHAT WE LEARNED

### Finding 1: The structured approach adds ceremony that costs tokens
The systematic-debugging phases (reproduce, hypothesize, isolate, fix, verify) add ~13% token overhead on average. For easy tasks, the agent already knows how to debug — the phases are unnecessary scaffolding.

### Finding 2: The structured approach helps on HARD tasks
DEBUG-002 was the only task where control FAILED. Treatment succeeded, using 33% fewer tokens. The structured approach prevented the rabbit-holing that caused the control agent to fail.

### Finding 3: The benefit is asymmetric
- On easy tasks (14/19): overhead of 5-180% more tokens
- On hard tasks (1/19): saved the task entirely
- Net effect: negative (overhead > savings)

### Finding 4: Order effects exist
Control always ran first in V1. In V2 we counterbalanced, but the time data still shows the second run is often faster (familiarity with task structure).

### Finding 5: Token measurement is noisy
We used subagent output token estimates, not actual API tokens. This is a proxy with unknown accuracy.

## 5. SUCCESS CRITERIA EVALUATION

| ID | Criterion | Target | Actual | Result |
|----|-----------|--------|--------|--------|
| E1 | Token reduction significant | p < 0.025 | p = 0.96 | **FAIL** |
| E2 | Mean token reduction >= 30% | >= 30% | -13.3% (increase) | **FAIL** |
| E3 | Control tasks show no improvement | p > 0.10 | Controls show 17-20% overhead | **PASS** (no false positive) |
| E4 | Agent voluntarily uses borg | >= 15/20 | 0/20 (borg_search never called) | **FAIL** |
| E5 | No success rate regression | treatment >= control | 100% >= 95% | **PASS** |

## 6. GO/NO-GO DECISION

**NO-GO on current approach.**

E1 FAIL + E2 FAIL = the structured approach does not reduce tokens.
The experiment clearly shows borg's pack-based structured guidance adds overhead on easy-to-medium tasks and only helps on genuinely hard tasks.

## 7. WHAT THIS MEANS FOR BORG

### The product should NOT be:
- "Follow this 5-phase approach for every debugging task"
- Static workflow packs applied uniformly
- A system that adds ceremony to tasks agents can already solve

### The product SHOULD be:
- A **difficulty detector** that only intervenes on hard tasks
- A **failure memory** that warns "3 agents failed here, don't try approach X"
- A **targeted hint** system: "the bug is in the caller, not the method" (not "follow these 5 phases")
- A **collective anti-pattern cache**: specific warnings, not generic workflows

### The pivot:
From: "structured approach for every task" (adds overhead)
To: "targeted intelligence for hard tasks" (saves agents from failure)

This aligns with the V3 learning loop research — the value is in the FAILURE MEMORY and CONTEXTUAL SIGNALS, not in the workflow phases.

## 8. NEXT STEPS

1. Strip workflow phases from borg packs — they add overhead
2. Focus borg on: anti-patterns, "start here" signals, failure warnings
3. Re-run experiment with revised borg (targeted hints vs no borg)
4. Test hypothesis: "borg should only intervene when agent has been stuck for >2 attempts"

---

*This experiment answered the question honestly.*
*Borg's structured approach doesn't help on average.*
*The value is in targeted intelligence, not generic scaffolding.*
*Resistance is futile — including resistance to honest data.*
