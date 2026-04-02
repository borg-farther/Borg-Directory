# AUDIT SYNTHESIS — THREE INDEPENDENT REVIEWS
## What the Auditors Agree On
## Date: 2026-03-31

---

# VERDICTS

| Auditor | Rating | Core Criticism |
|---------|--------|----------------|
| **Methodologist** | CRITICAL FLAWS | 14 flaws. Cache hit = copy-paste, not intelligence. Failure memory = prompt injection. Token measurement unverified. |
| **Academic** | BORDERLINE | Would not pass ICSE/NeurIPS in current form. Good controls (shuffled cache), but power analysis optimistic, thresholds arbitrary. |
| **Competitive** | OPPORTUNITY | Industry doesn't measure efficiency. Borg could pioneer evidence-based agent improvement — IF the evidence is real. |

---

# CONSENSUS: 7 THINGS ALL THREE AUDITORS FLAG

## 1. WE'RE TESTING RETRIEVAL, NOT INTELLIGENCE
All three identify that giving Agent B a cached solution is just retrieval — like RAG with extra steps. The academic says "distinguish this from RAG." The methodologist says "this is solution copy-paste." The competitor analysis says "no one else does this, but that might be because it doesn't work."

**FIX:** Cache should provide REASONING TRACES (why Agent A explored paths X, Y, Z, why Z worked) not the ANSWER. Agent B should still reason independently.

## 2. FAILURE MEMORY = PROMPT INJECTION
The warning "do not try approach X" is an instruction, not knowledge transfer. The agent is complying with instructions, not learning.

**FIX:** Provide failure CONTEXT ("Agent A tried X and got error Y after 3 minutes") without the prohibition. Let Agent B decide whether to try X.

## 3. SUCCESS THRESHOLDS ARE ARBITRARY
25% token reduction, 70% avoidance rate, d=0.5 — none derived from cost-benefit analysis or variance estimates.

**FIX:** Derive thresholds from: (a) what reduction would make borg worth installing? (cost of borg vs savings), (b) what effect size is realistic given V1/V2 variance?

## 4. TASKS WERE TOO EASY (V1/V2), CALIBRATION IS CRITICAL
18/19 control success means no room for improvement. All three agree: 40-60% control success is the sweet spot.

**FIX:** Pre-calibrate by running each task 5x with baseline agent. Only keep tasks in the 30-70% bracket.

## 5. TOKEN MEASUREMENT IS UNVERIFIED
V3 claims "actual API tokens" but provides no verification. The actual measurement method (delegate_task metadata) has never been validated.

**FIX:** Before running experiments, verify that delegate_task token counts match actual API billing.

## 6. ECOLOGICAL VALIDITY IS WEAK
Synthetic seeded bugs with known wrong approaches are not how real agents encounter problems. Forced retrieval protocols don't reflect voluntary usage.

**FIX:** Include at least some tasks from real codebases (SWE-bench style). Allow agents to CHOOSE whether to use cache — don't force it.

## 7. NEGATIVE TRANSFER IS UNTESTED
V2 showed treatment was worse on 74% of tasks. V3 has no experiment that deliberately tests when cache HURTS. This is the most important safety question.

**FIX:** Add Experiment 0: measure how often cache entries are WRONG or MISLEADING and quantify the damage.

---

# WHAT SHOULD CHANGE

## DROP from V3:
- Experiment 2 (Failure Memory) in current form — it's prompt injection
- Experiment 4 (Start-Here) — too similar to cache hits

## REDESIGN:
- Experiment 1 (Cache Hits): Provide reasoning traces, not answers
- Experiment 2 (Failure Memory): Provide failure context, not prohibitions
- All experiments: Allow agent CHOICE to use cache (don't force)

## ADD:
- Experiment 0: Negative transfer — when does cache HURT?
- Token measurement validation step
- At least 5 tasks from real repos (SWE-bench style)
- Cost-benefit derived thresholds

## KEEP:
- Shuffled cache control (all three auditors praise this)
- 3 runs per cell with median aggregation
- Counterbalancing via Latin square
- Pre-calibration protocol (40-60% bracket)
- Independent analysis (Team C blind to Team A)
- Bayesian analysis alongside frequentist

---

# THE MINIMUM VIABLE EXPERIMENT

Based on all three audits, the smallest experiment that answers the core question:

**ONE EXPERIMENT: Does the reasoning cache improve agent performance on hard tasks?**

Design:
1. Pre-calibrate 15 tasks to 40-60% control success rate (requires ~75 calibration runs)
2. Cache provides REASONING TRACES from Agent A, not answers
3. Agent B can CHOOSE to query cache (not forced)
4. Shuffled cache control (wrong task traces)
5. 3 runs per (task, condition) = 15 × 3 × 3 conditions = 135 runs
6. Primary metric: success rate (binary, exact permutation test)
7. Secondary: tokens (Wilcoxon signed-rank)
8. Threshold: 20 percentage point success rate improvement (derived from: if cache costs $X/month in maintenance, it needs to save $Y in reduced agent failures)

Total: ~210 runs (75 calibration + 135 experiment)

This is achievable in 1 week on the current fleet.

---

# HONEST ASSESSMENT

The V3 spec as written would produce data, but the data would be unreliable because:
- It tests retrieval/prompting, not the actual cache product
- The thresholds are arbitrary so "pass" is meaningless
- Ecological validity is low (synthetic tasks, forced protocols)

The REDESIGNED experiment would be smaller, faster, and produce more trustworthy data because:
- It tests the actual mechanism (reasoning traces, not answers)
- Agent choice makes it ecologically valid
- Cost-derived thresholds make "pass" meaningful
- The shuffled control definitively isolates knowledge from overhead

**Three auditors, one conclusion: redesign before running.**
