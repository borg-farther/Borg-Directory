# Experiment Design: Does Shared Reasoning Cache Improve AI Coding Agent Performance?

## A Pre-Registered Within-Subject Experiment

**Version:** 1.0  
**Date:** March 31, 2026  
**Target Venues:** ICSE 2027 / CHI 2027  
**Status:** Pre-registered

---

## Abstract

We present a rigorous within-subject experimental design to evaluate whether a shared reasoning cache—storing reasoning traces ("why" a solution works, what was attempted, what failed) rather than solutions themselves—improves AI coding agent performance. The design addresses seven identified flaws from prior audits: (1) ensuring cache provides reasoning traces not answers, (2) allowing agents to voluntarily query the cache, (3) including both wrong-task-cache and no-cache controls, (4) calibrating tasks to 40-60% baseline success, (5) using 2 runs per cell with median aggregation, (6) deriving thresholds from cost-benefit analysis, and (7) explicitly testing for negative transfer. This document specifies the complete pre-registered protocol, hypotheses, analysis plan, and stopping rules.

---

## 1. Research Questions

**RQ1 (Primary):** Does accessing a shared reasoning cache of correct solution traces improve coding task success rate compared to no cache access?

**RQ2 (Mechanism):** Does the benefit of reasoning traces derive from the reasoning content itself (vs. format/length confounds), as tested by comparing against wrong-task traces?

**RQ3 (Harms):** Under what conditions does the reasoning cache produce negative transfer (degraded performance compared to no cache)?

---

## 2. Hypotheses

### RQ1: Primary Effect

- **H0₁:** Median success rate with reasoning cache access ≤ median success rate without cache access (τ ≤ 0)
- **H1₁:** Median success rate with reasoning cache access > median success rate without cache access (τ > 0)

### RQ2: Mechanism (Active Control)

- **H0₂:** Success rate with correct reasoning traces ≤ success rate with wrong-task reasoning traces (τ ≤ 0)
- **H1₂:** Success rate with correct reasoning traces > success rate with wrong-task reasoning traces (τ > 0)

### RQ3: Negative Transfer

- **H0₃:** For no task does cache access degrade performance (τ ≥ 0 for all tasks)
- **H1₃:** There exists at least one task where cache access degrades performance (τ < 0 for some tasks)

**Pre-registration URL:** [TO BE ADDED UPON PRE-REGISTRATION]

---

## 3. Independent Variables

### Primary IV: Cache Condition (3 levels, within-subject)

| Level | Label | Description |
|-------|-------|-------------|
| A | No Cache | Agent operates with no reasoning cache access |
| B | Correct Reasoning Traces | Agent may voluntarily query cache containing correct reasoning traces |
| C | Wrong-Task Reasoning Traces | Agent may voluntarily query cache containing coherent reasoning traces from a DIFFERENT task |

### Secondary IVs (Controls)

| Variable | Type | Operationalization |
|----------|------|---------------------|
| Task | Within-subject (15 levels) | Unique coding task per block, Latin-squared assignment |
| Run | Within-subject (2 levels) | Repetition within condition-task cell |
| Order | Within-subject | Position in Latin square sequence (1-3) |
| Cache Query Timing | Measured | Whether/when agent queries cache (observational) |
| Cache Query Count | Measured | Number of cache queries per run (observational) |

### Rationale for Wrong-Task Control

Condition C controls for:
- **Length effects:** Wrong-task traces have identical token length to Condition B
- **Format effects:** Same structured phases as Condition B
- **Attention effects:** Same voluntary query mechanic
- **Memory effects:** Same working memory load from reading
- **Coherence effects:** Wrong-task traces ARE coherent—they just address the wrong problem

Condition C does NOT control for:
- **Correct problem-solving knowledge:** Wrong-task traces contain valid reasoning for a different task
- **Task-specific guidance:** The reasoning addresses a different problem entirely

This isolates the mechanism to "correct reasoning content for THIS task" rather than surface features. The key question becomes: does having ANY coherent reasoning help, or must it be the RIGHT reasoning?

---

## 4. Dependent Variables

### Primary DVs

**DV1: Task Success Rate**
- **Operationalization:** Binary (0 = task requirements not met, 1 = all requirements met)
- **Measurement:** Automated test suite execution + manual verification for false positives
- **Unit:** Proportion correct per condition-task-run cell
- **Threshold:** Success defined by passing all automated test cases; edge cases adjudicated by two independent raters

**DV2: Task Completion Time**
- **Operationalization:** Wall-clock time from task start to solution submission
- **Measurement:** Server-side timestamps (not agent-reported)
- **Unit:** Seconds
- **Censoring:** Runs exceeding 10 minutes are censored and counted as failures (0)

**DV3: Token Cost**
- **Operationalization:** Total tokens consumed (input + output) per run
- **Measurement:** API-side token counting (validated per Methods section)
- **Unit:** Tokens
- **Validation:** Must pass pre-registered validation criteria before primary analysis

### Secondary DVs (Observational)

**DV4: Cache Query Rate**
- **Operationalization:** Proportion of runs where agent queries cache at least once
- **Measurement:** Logged cache access events
- **Unit:** Proportion (0-1)

**DV5: Cache Query Timing**
- **Operationalization:** Time from task start to first cache query
- **Measurement:** Server-side timestamps
- **Unit:** Seconds

**DV6: Cache Query Count**
- **Operationalization:** Number of cache queries per run
- **Measurement:** Logged cache access events
- **Unit:** Count (integer ≥ 0)

**DV7: Solution Quality (when successful)**
- **Operationalization:** Number of test cases passed / total test cases
- **Measurement:** Automated test suite
- **Unit:** Proportion (0-1)

---

## 5. Conditions

### Condition A: No Cache (Baseline)

**Setup:**
- Agent receives task description only
- No reasoning cache is available or accessible
- Agent must generate solution from scratch

**What agent sees:**
```
Task: [Full task description]
```

**What agent does NOT see:**
- No mention of reasoning cache
- No cache query interface
- No indication that prior reasoning exists

**This is the TRUE baseline** measuring unassisted agent capability.

### Condition B: Correct Reasoning Traces (Treatment)

**Setup:**
- Agent receives task description
- Agent has voluntary access to reasoning cache query interface
- Cache contains correct, complete reasoning traces from prior solutions

**What agent sees:**
```
Task: [Full task description]

[Agent may optionally query:]
> Would you like to search the reasoning cache for similar tasks?
```

**If agent queries:**
```
Reasoning trace for Task [ID]:
- Problem decomposition: [How the problem was broken down]
- Approach selection: [Why this approach was chosen]
- Attempted solutions: [What was tried]
- Failures encountered: [What didn't work and why]
- Key insights: [Critical realizations that led to solution]
- Solution rationale: [Why the final solution works]
```

**Agent may query multiple times for different phases.**

### Condition C: Wrong-Task Reasoning Traces (Active Control)

**Setup:**
- Agent receives task description
- Agent has voluntary access to reasoning cache query interface
- Cache contains reasoning traces from a DIFFERENT task (coherent but irrelevant)

**Wrong-task procedure:**
1. For each task T_i in Condition B, identify a different task T_j with similar difficulty
2. Use the complete reasoning trace from T_j (which was solved correctly)
3. Present T_j's reasoning when agent queries cache for T_i
4. Ensure no mention of task identity—the agent may not realize the trace is from another task

**What agent sees:** Identical interface to Condition B

**Critical difference:** Wrong-task traces have same length, same format, same query mechanic—and are fully coherent reasoning—but address a different problem entirely.

### Within-Subject Design Rationale

Within-subject design is appropriate because:
1. **Power:** Same tasks can be compared across conditions, reducing variance
2. **Control:** Individual task differences are eliminated as confound
3. **Ethics:** Each agent serves as its own control (no need to recruit more agents)

**Risks and mitigations:**
| Risk | Mitigation |
|------|------------|
| Learning effects (practice) | Latin square counterbalancing across conditions |
| Fatigue effects (later = worse) | Latin square ensures each condition appears equally often in each position |
| Carryover (exposure to B affects A) | Sufficient washout via different tasks in each block |
| Task-specific ceiling/floor | Calibration protocol ensures 40-60% baseline |

---

## 6. Counterbalancing: Full Latin Square

### Design Structure

**Subjects:** 15 tasks × 3 conditions × 2 runs = 90 runs per agent (primary model)
**Design:** Within-subject, full Latin square for condition × task

### Latin Square (k=15, illustrated for k=3):

For 15 tasks, we use a Williams design (balanced for first-order carryover). Full 15×15 Latin square:

```
         Task  1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
Agent 1:      A   B   C   A   B   C   A   B   C   A   B   C   A   B   C
Agent 2:      B   C   A   C   A   B   B   C   A   C   A   B   B   C   A
Agent 3:      C   A   B   B   C   A   C   A   B   B   C   A   C   A   B
... (15 agents total, Williams design)
```

**Key properties:**
- Each condition appears once per agent per 3-task block
- Each condition appears equally often in each position
- First-order carryover effects are balanced
- No agent sees same task-condition combination twice

### Run Assignment

Within each condition-task cell:
- 2 independent runs with different random seeds
- Order of runs randomized within agent
- Median used for aggregation (robust to outlier runs)

---

## 7. Sample Size Justification

### Power Analysis

**Design:** 15 tasks × 3 conditions × 2 runs per cell, within-subject

**Primary Analysis:** Wilcoxon signed-rank test (non-parametric, median-based)

**Effect size to detect:**  
Based on pilot data from Borg V1/V2 showing ~13% overhead reduction, we target:
- **Minimum detectable effect (MDE):** d = 0.50 (medium effect)
- **Equivalently:** 15 percentage point improvement in success rate

**Type I error rate:** α = 0.05 (two-tailed)

**Type II error rate:** β = 0.20 (80% power)

**Power calculation for within-subject design:**

Using G*Power 3.1 for Wilcoxon signed-rank test:
- Effect size dz = 0.50
- α = 0.05
- Power (1-β) = 0.80
- **Required N = 15 agent-tasks**

**Adjustments:**

| Factor | Adjustment | Rationale |
|--------|------------|-----------|
| Multiple comparisons | Bonferroni correction for 3 hypotheses | α_adj = 0.017 per test |
| Non-normality | 15% inflation | Robust to skewed distributions |
| Dropout/invalid runs | 10% inflation | Technical failures |

**Final sample (primary model):**  
Minimum 20 agents × 15 tasks = 300 agent-task observations  
Each provides 2 runs, median aggregated = 1 observation per cell  
Total cells analyzed: 20 agents × 15 tasks = 300

**Expected runtime (primary model):**  
150 total runs per machine  
5 machines × ~30 runs/machine  
At ~5 min/run: ~150 min = 2.5 hours per machine  
Total wall clock: ~2.5 hours with parallelization

### Sequential Analysis Boundaries

We will use sequential analysis (Lan-DeMets alpha-spending) to allow optional stopping with appropriate error control. See Section 12 for details.

---

## 8. Task Selection Criteria

### Inclusion Criteria

A valid task MUST satisfy ALL of the following:

**8.1 Difficulty Criterion**
- Baseline success rate (Condition A) between 40-60%
- Verified by calibration protocol (Section 9)
- No floor or ceiling effects

**8.2 Reliability Criterion**
- Inter-run agreement (3 runs in Condition A) ≥ 70%
- Tasks with all-success or all-failure across runs are excluded

**8.3 Independence Criterion**
- No task shares >20% solution code with another task
- Tasks cannot be subtasks or supertasks of each other
- Verified by automated similarity check

**8.4 Discriminability Criterion**
- Task must be solvable by the agent model being tested
- Task must fail for non-trivial reasons (not due to missing libraries or unclear specs)
- Verification via expert review

**8.5 Diversity Criterion**
- Tasks must span at least 3 different problem domains:
  - Data structures/algorithms
  - String manipulation
  - File I/O and parsing
  - API interaction
  - Testing and debugging

**8.6 Timing Criterion**
- Estimated solution time: 2-5 minutes
- Must be completable within 10-minute hard timeout

**8.7 Contamination Criterion**
- Task must NOT appear in training data (checked via membership inference)
- Task must NOT be directly answerable from public solutions

### Exclusion Criteria

A task is EXCLUDED if:
1. It fails any inclusion criterion
2. It requires domain-specific knowledge not in agent's context window
3. It requires real-world data the agent cannot access
4. It has ambiguous success criteria
5. A correct solution is longer than 500 lines (too complex to verify)

### Task Corpus Size

Minimum 18 tasks selected, 15 used, 3 held out for potential follow-up.

---

## 9. Pilot Validation

### Purpose

Before main data collection, validate that:
1. Agents voluntarily query the reasoning cache in Condition B
2. Agents can correctly parse and utilize the reasoning trace format
3. The cache interface is intuitive enough for agents to use without prompting

### Procedure

**Phase 1: Pilot Run (5 tasks, Condition B only)**

1. Select 5 tasks from the calibrated task set
2. Run each task in Condition B with 2 agents (10 total runs)
3. Log whether agents query the cache and how they use the traces

### Success Criteria

| Criterion | Threshold | Action if Failed |
|-----------|-----------|------------------|
| Cache query rate | ≥ 60% (≥ 3/5 tasks) | Redesign cache interface |
| Trace parsing | Agent uses trace info in solution | Retrain trace format |
| Voluntary query | Agents query without explicit prompting | Add interface hints |

### Decision Rules

- **Proceed to main experiment** if cache query rate ≥ 60%
- **Redesign interface** if query rate < 60%, then re-pilot
- Pilot data is NOT included in main analysis

### Pilot Budget

10 runs (5 tasks × 2 runs) = 10 runs total

---

## 10. Calibration Protocol

### Purpose

Establish that selected tasks have 40-60% baseline success rate in Condition A.

### Procedure

**Phase 1: Initial Screening (N=5 agents, 2 runs each)**

1. Select 18 candidate tasks
2. Run each task in Condition A (no cache) with 5 different agent instances (different seeds)
3. Record success rate for each task

**Phase 2: Difficulty Adjustment**

For each task:

| If observed success rate | Action |
|---------------------------|--------|
| < 30% | Increase difficulty or exclude |
| 30-39% | Provide additional hints in spec |
| 40-60% | Accept as-is |
| 61-70% | Add distractor requirements |
| > 70% | Substantially rework task |

**Phase 3: Verification (N=10 agents, 2 runs each)**

1. Run accepted tasks with 10 agents (Condition A only)
2. Verify success rate remains in 40-60% range
3. Calculate 95% CI; exclude if CI width > 20%

**Phase 4: Final Selection**

- Select exactly 15 tasks with verified 40-60% success
- Document all exclusion decisions
- Freeze task specifications

### Calibration Timeline

- Week 1: Phase 1 screening
- Week 2: Phase 2 adjustments + Phase 3 verification
- Week 3: Phase 4 finalization + pre-registration

### Calibration Data

Calibration data is collected under Condition A only (no cache) to establish true baseline difficulty. This data is NOT included in the main analysis (different agent pool, different purpose).

---

## 11. Model Specification

### Primary Model

- **Model:** Claude Sonnet 4
- **Interface:** delegate_task
- **Temperature:** 0 (fixed, deterministic)
- **Runs:** 15 tasks × 3 conditions × 2 runs = 90 runs

### Replication Model

- **Model:** GPT-4o-mini
- **Scope:** Top 5 tasks only (highest difficulty discrimination)
- **Runs:** 5 tasks × 3 conditions × 2 runs = 30 runs
- **Purpose:** Test generalizability of findings to weaker model class

### Hypothesis for Model Comparison

We hypothesize that weaker models benefit MORE from reasoning traces than stronger models. If correct, reasoning cache benefits should be larger for GPT-4o-mini than for Claude Sonnet 4.

### Total Budget

| Component | Runs |
|-----------|------|
| Primary model (Claude Sonnet 4) | 90 |
| Replication model (GPT-4o-mini) | 30 |
| Pilot validation | 10 |
| **Subtotal** | **130** |

### Limitation

Results may not generalize to all models. Testing only two models limits external validity; future work should test additional model families.

---

## 12. Measurement Protocol

### Pre-Run Validation

**Token Measurement Validation (REQUIRED FIRST):**

1. Before any experimental runs, validate token counting:
   - Use 10 pre-known input/output pairs
   - Compare API-reported tokens vs. local tiktoken counting
   - Require: correlation > 0.99, max absolute error < 50 tokens
   - If fails: recalibrate and retest

2. Validate on at least 3 different task types before proceeding

### Per-Run Protocol

**Step 0: Environment Setup (Automated)**
```
- Reset agent environment to clean state
- Load task specification
- Initialize logging infrastructure
- Record start timestamp
```

**Step 1: Task Presentation (t=0)**
```
- Present task description to agent
- Start wall-clock timer
- Begin token counting
- Log: agent_id, task_id, condition, run_number, timestamp
```

**Step 2: Agent Execution (t=0 to t≤600s)**
```
- Agent processes task
- If Condition B or C: Agent may query cache at any time
- All cache queries logged with timestamps
- Agent submits solution or times out
```

**Step 3: Solution Verification (Automated)**
```
- Run automated test suite on submitted solution
- Record: pass/fail, test cases passed/total, execution time
- If timeout: record as failure, log censored indicator
```

**Step 4: Token Counting (Post-Hoc)**
```
- Query API for total tokens consumed
- Cross-validate with local counter
- Record both values
```

**Step 5: Quality Rating (if success)**
```
- Run additional edge case tests
- Rate solution quality (partial credit for inefficient solutions)
- Log quality score
```

**Step 6: Data Recording**
```
- Save all logs to experiment database
- Record end timestamp
- Verify data integrity (checksum)
```

### Data Integrity Checks

After each run:
1. Verify all required fields populated
2. Verify timestamps are sequential and non-negative
3. Verify token counts are non-negative
4. Flag any anomalies for review

### Observer Protocol

Human observers monitor a random 20% of runs for:
- Technical failures (system errors)
- Protocol deviations
- Emergent behaviors of interest

Observers use standardized observation forms and are blind to condition when possible.

---

## 14. Analysis Plan

### Pre-Registration

Full analysis plan pre-registered at AsPredicted.org before data collection begins.

### Data Exclusion Rules (Pre-Registered)

Runs are excluded if:
1. Technical failure (system error, API timeout)
2. Protocol deviation (wrong condition delivered)
3. Suspicious patterns (too fast, no real computation)

**NOT excluded:**
- Runs where agent failed to solve task (this is data)
- Runs where agent did not query cache (this is data)

### Primary Analysis

**DV:** Task success (binary: 0/1)  
**Aggregation:** Median across 3 runs per condition-task cell  
**Test:** Wilcoxon signed-rank test (within-subject, matched pairs)

#### Primary Contrast: Condition B vs. Condition A

```
H0: median(B - A) ≤ 0
H1: median(B - A) > 0
Test: One-tailed Wilcoxon signed-rank, α = 0.017 (Bonferroni)
```

#### Secondary Contrast: Condition B vs. Condition C

```
H0: median(B - C) ≤ 0
H1: median(B - C) > 0
Test: One-tailed Wilcoxon signed-rank, α = 0.017 (Bonferroni)
```

#### Negative Transfer Analysis: Condition B vs. Condition A per Task

```
For each task i:
  H0: median(B_i - A_i) ≥ 0
  H1: median(B_i - A_i) < 0
  Test: One-tailed Wilcoxon signed-rank, α = 0.05/task
```

### Effect Size Estimation

**Primary effect size:** Cohen's d for paired samples

```
d = (mean difference) / (SD of differences)
```

**95% confidence interval:** Bootstrap CI with 10,000 resamples

**Reporting:** d and CI reported for all contrasts

### Bayesian Analysis

**Prior:** Informed by pilot data (Borg V1/V2)

We use a weakly informative prior for the treatment effect:
- Normal(0, 0.5) for standardized effect size

**Posterior:** Computed via Markov Chain Monte Carlo (MCMC)

```
Model: success_ij ~ Bernoulli(p_ij)
       logit(p_ij) = β0 + β_condition[j] + β_task[k] + ε_i
       β_condition[1] = 0 (constraint)
       β_condition[2], β_condition[3] ~ Normal(0, 0.5)
```

**Key outputs:**
1. Posterior probability that P(B > A) > 0.90
2. Posterior probability that P(B > C) > 0.90
3. Bayes Factor for H1 vs. H0

**Interpretation thresholds:**
- BF > 10: Strong evidence for H1
- BF > 30: Very strong evidence for H1
- BF < 0.1: Strong evidence for H0

### Secondary DVs: Observational Analyses

**Cache Query Rate Analysis:**
- Proportion of runs with ≥1 cache query by condition
- Chi-square test for condition differences

**Cache Query Timing Analysis:**
- Time to first query by condition and task
- Regression: timing ~ condition + task + run

**Token Cost Analysis:**
- Compare tokens: Condition B vs. A vs. C
- Does cache REDUCE total tokens (by avoiding redundant reasoning)?

### Missing Data Handling

**If < 5% missing:** Complete case analysis (listwise deletion)

**If 5-20% missing:** Multiple imputation (MICE), 20 imputations

**If > 20% missing:** Sensitivity analyses; report and discuss

### Multiple Comparison Corrections

| Analysis | Correction | Adjusted α |
|----------|------------|------------|
| RQ1 (B vs A) | Bonferroni (3 tests) | 0.017 |
| RQ2 (B vs C) | Bonferroni (3 tests) | 0.017 |
| RQ3 (per-task negative transfer) | Holm-Bonferroni | 0.05 |
| Secondary DVs | FDR (Benjamini-Hochberg) | q = 0.05 |

---

## 15. Dose-Response Analysis

### Purpose

Test whether reasoning trace QUALITY affects cache benefit, not just presence/absence.

### Design

For 5 of the 15 tasks, we create TWO quality levels of reasoning traces:

**High Quality Trace:**
- Detailed, accurate, specific to the exact bug
- Step-by-step reasoning tailored to the exact problem
- Clear explanation of why approaches work or fail

**Low Quality Trace:**
- Vague, partially accurate, generic approach
- General strategy without task-specific details
- Could apply to many similar problems but not this exact one

### Example: Palindrome Task

**High Quality:**
```
The key insight is that we need to NORMALIZE first (remove non-alphanumeric)
before checking symmetry. I tried handling punctuation inline with the two-pointer
but got IndexError when pointers crossed. The fix is to use while loops with
proper boundary checks AND normalize upfront: filtered = ''.join(c.lower() for c
in s if c.isalnum()). Then filtered == filtered[::-1] handles all cases.
```

**Low Quality:**
```
For string problems, consider different approaches. Sometimes two-pointer works,
sometimes reverse-and-compare. Handle edge cases like empty strings. Make sure to
consider case sensitivity. Test your solution with various inputs.
```

### Runs

- 5 tasks × 2 quality levels × 2 runs = 20 extra runs
- These runs use Condition B interface but with quality-manipulated traces
- Analyzed separately from primary analysis (secondary/exploratory)

### Analysis

Compare high-quality vs low-quality trace performance within the 5 selected tasks.

### Budget Addition

| Component | Runs |
|-----------|------|
| Primary (15 tasks × 3 conditions × 2 runs) | 90 |
| Replication (5 tasks × 3 conditions × 2 runs) | 30 |
| Pilot validation | 10 |
| Dose-response (5 tasks × 2 qualities × 2 runs) | 20 |
| **Total** | **150** |

---

## 16. Stopping Rules

### Sequential Analysis (Alpha-Spending)

We use the Lan-DeMets implementation of the O'Brien-Fleming alpha-spending function to allow optional stopping with proper error control.

**Interim analyses:** After 25%, 50%, 75% of planned observations

**Alpha-spending:**
| Information | Cumulative α spent |
|-------------|-------------------|
| 25% | 0.001 |
| 50% | 0.005 |
| 75% | 0.015 |
| 100% | 0.05 |

**Decision boundaries:** Computed precisely using ldBounds function in gsDesign package.

### Early Stopping for Success

**Stop early if:**
- Posterior probability P(B > A) > 0.99 at interim
- AND P(B > C) > 0.95 at interim
- AND no evidence of negative transfer

### Early Stopping for Futility

**Stop early if:**
- Posterior probability P(B > A) > 0.50 never exceeds 0.70 after 75% of data
- OR Bayes Factor for H0 vs H1 > 10

### Minimum Running Time

**Minimum:** 50% of planned observations before any stopping decision

This ensures adequate estimate of variability before claiming no effect.

---

## 17. Reasoning Traces: Concrete Examples

### What a Reasoning Trace IS

A reasoning trace explains the **WHY** behind a solution:
- How the problem was decomposed
- Why this approach was chosen
- What was attempted and failed
- Key insights that led to solution
- Why the final solution works

### What a Reasoning Trace is NOT

- NOT the answer itself (no code snippets beyond imports)
- NOT step-by-step code generation
- NOT a tutorial

### Example Task

```
Task: "Write a function that validates whether a given string is a valid palindrome,
ignoring spaces, punctuation, and case. Return True if valid palindrome, False otherwise."
```

### Example Correct Reasoning Trace (Condition B)

```yaml
Task-ID: palindrome-validation
Problem-Decomposition:
  - "The core challenge is normalizing the input (removing non-alphanumeric) 
     and then checking symmetry"
  - "I initially thought to use regex, but realized str.isalnum() is simpler"
  - "Lowercasing handles case insensitivity in one step"
Approach-Selection:
  - "Two-pointer technique: start from both ends, compare characters"
  - "Alternative considered: reverse string and compare (rejected due to O(n) extra space)"
  - "Chose two-pointer for O(1) space complexity"
Attempts:
  - "First attempt: tried to handle punctuation inline with two-pointer"
  - "Failed: got IndexError when pointer crossed"
  - "Fix: use while loops with proper boundary checks"
Failures-Encountered:
  - "Forgot empty string edge case - pointer logic broke"
  - "Learned: always validate input or handle empty explicitly"
  - "Did not fail for: single character (returns True correctly)"
Key-Insights:
  - "Two-pointer is elegant for symmetric problems"
  - "Normalizing first simplifies comparison logic significantly"
  - "Python's slicing [::-1] is clean but uses extra space - trade-off to consider"
Solution-Rationale:
  - "Normalize: filtered = ''.join(c.lower() for c in s if c.isalnum())"
  - "Compare: filtered == filtered[::-1]"
  - "This handles all edge cases: empty returns True, single char returns True,
     mixed case works, punctuation/spaces ignored"
```

### Example Wrong-Task Reasoning Trace (Condition C)

Same format, same length, SAME level of detail, but from a DIFFERENT task. This trace is from a "binary search tree validation" task, not the palindrome task:

```yaml
Task-ID: binary-search-tree-validation
Problem-Decomposition:
  - "The core challenge is validating BST properties—left subtree < root < right subtree"
  - "I initially thought to just check immediate children, but that's insufficient"
  - "Need to track allowed min/max bounds as I traverse"
Approach-Selection:
  - "Two approaches: (1) in-order traversal checking sortedness, (2) recursive with bound checking"
  - "Chose recursive with bounds for clarity and O(n) guarantees"
  - "Alternative: iterative with stack (rejected—more complex)"
Attempts:
  - "First attempt: checked only local parent-child relationships"
  - "Failed: tree like [5,3,7,1,4,6,8] passes local check but isn't valid BST"
  - "Fix: track min/max bounds from ancestors during traversal"
Failures-Encountered:
  - "Forgot to update bounds when recursing left vs right"
  - "Learned: left bound stays same, right bound updates when going right"
  - "Edge case: duplicate values—decided to reject as invalid"
Key-Insights:
  - "Bounds checking is elegant for BST validation"
  - "In-order traversal + sortedness check is equivalent but less intuitive"
  - "Recursion naturally handles the bound propagation"
Solution-Rationale:
  - "validate(node, min_val, max_val): recursively check with updated bounds"
  - "If node.val <= min_val or >= max_val: invalid"
  - "This handles all edge cases: empty tree, single node, duplicates"
```

**Key difference:** This is perfectly coherent reasoning—but about a completely different problem. It cannot help the agent solve the palindrome task.

### Validation that Wrong-Task Traces are Coherent

Since wrong-task traces are fully coherent (not shuffled), we verify that they are actually from a different task:

1. Task identity check: Verify no mention of the target task's specific terminology
2. Problem domain check: Ensure trace addresses a different problem class
3. Solution approach check: Confirm the solution method doesn't transfer to target task

```python
def verify_wrong_task(trace, target_task):
    """
    Returns True if trace is coherent but addresses a different task.
    """
    # Check trace doesn't mention target task concepts
    target_concepts = extract_key_concepts(target_task)
    trace_text = trace.lower()
    for concept in target_concepts:
        if concept.lower() in trace_text:
            return False  # Contains target task info
    return True  # Coherent but different
```

---

## 18. Cost-Benefit Thresholds

### Threshold Derivation

Thresholds are derived from COST-BENEFIT analysis, not arbitrary convention.

**Costs:**
| Cost | Value | Source |
|------|-------|--------|
| Engineering time | $200/hour | Team market rate |
| Compute (cache infrastructure) | $0.10/1K tokens | Cloud pricing |
| Agent time (inference) | $0.15/1K tokens | API pricing |
| Human review | $50/task | Annotation cost |

**Benefits:**
| Benefit | Value | Source |
|---------|-------|--------|
| Reduced agent failures | $X per % improvement | User value study |
| Reduced compute (if cache helps) | $0.10/1K tokens saved | Cloud pricing |
| Improved user satisfaction | $Y per task | Proxy: willingness to pay |

### Decision Thresholds

**Minimum Meaningful Effect (MME):**
- At least 10 percentage point improvement in success rate
- OR at least 20% reduction in tokens per successful task
- OR combination of both

**Minimum Detectable Effect (MDE):**
- 15 percentage points (based on power analysis)
- Below this, effect not practically meaningful

**Equivalence Boundary:**
- Within ±5 percentage points considered equivalent
- Cache not WORSE by more than 5pp on any task

**Negative Transfer Threshold:**
- If ANY task shows >10pp DECREASE in Condition B vs A
- Investigate immediately
- Report as harm

---

## 17. Technical Implementation

### Infrastructure

```
Experiment Controller
    ├── Task Manager (load, validate, rotate)
    ├── Agent Pool (7 parallel agents per machine)
    ├── Cache Server (B and C conditions)
    ├── Logger (centralized, immutable)
    ├── Token Counter (API-side + local validation)
    └── Database (PostgreSQL, append-only)
```

### Agent Interface

```python
# Pseudocode for agent-cache interaction
class AgentEnvironment:
    def __init__(self, condition: str):
        self.condition = condition
        self.cache_available = condition in ['B', 'C']
        self.cache = load_cache(condition)
    
    def query_cache(self, query: str) -> Optional[Dict]:
        """Called by agent at its discretion"""
        if not self.cache_available:
            return None
        # Return reasoning trace (B: correct, C: shuffled)
        return self.cache.search(query)
    
    def submit_solution(self, solution: str) -> Result:
        """Submit and evaluate"""
        return evaluator.evaluate(solution)
```

### Logging Schema

```sql
CREATE TABLE runs (
    run_id UUID PRIMARY KEY,
    agent_id VARCHAR(32),
    task_id VARCHAR(32),
    condition CHAR(1), -- A, B, or C
    run_number INTEGER, -- 1, 2, or 3
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    success BOOLEAN,
    tokens_in BIGINT,
    tokens_out BIGINT,
    tokens_total BIGINT,
    tokens_validated BOOLEAN,
    cache_queried BOOLEAN,
    cache_query_count INTEGER,
    first_query_time INTERVAL,
    timeout BOOLEAN,
    excluded BOOLEAN,
    exclusion_reason TEXT,
    checksum VARCHAR(64)
);
```

---

## 18. Threats to Validity

### Internal Validity

| Threat | Mitigation |
|--------|------------|
| History | Controlled environment, no external events |
| Maturation | Within-subject, short timeframe |
| Testing effects | Latin square balances practice/fatigue |
| Instrumentation | Validated token counting, automated scoring |
| Selection bias | Random task assignment, fixed agent pool |
| Attrition | Technical failures tracked, excluded systematically |
| Diffusion | Agents isolated, no inter-agent communication |

### External Validity

| Threat | Mitigation |
|--------|------------|
| Agent generalizability | Test on multiple agent models (Claude, GPT-4, etc.) |
| Task generalizability | 15 diverse tasks, 5+ domains |
| Context validity | Realistic coding tasks, not toy problems |

### Construct Validity

| Threat | Mitigation |
|--------|------------|
| Operationalization | Multiple DVs (success, time, tokens) |
| Mono-operation bias | 15 tasks reduce task-specific effects |

### Statistical Validity

| Threat | Mitigation |
|--------|------------|
| Power | A priori power analysis |
| Type I error | Bonferroni correction, alpha-spending |
| Type II error | Adequate N, sequential analysis |
| Non-normality | Non-parametric tests, median aggregation |
| Outliers | Winsorizing time, robust estimators |

---

## 19. Ethical Considerations

### No Human Participants

This experiment uses AI agents only, not human subjects. No IRB required.

### Resource Usage

- Total compute: ~210 runs × 5 min × 5 machines = ~87.5 machine-hours
- Estimated carbon: ~0.1 kg CO2 (minimal)
- Cost: ~$50 in API costs

### Data Sharing

Anonymized data will be shared on OSF upon publication.

---

## 20. Timeline

| Week | Milestone |
|------|-----------|
| 1 | Token validation, infrastructure testing |
| 2 | Task calibration Phase 1 (N=5) |
| 3 | Task calibration Phase 2 (N=10), pilot validation, pre-registration |
| 4 | Pilot validation (5 tasks, Condition B only) |
| 5-6 | Main data collection (primary model: 90 runs) |
| 7 | Interim analysis, potential early stopping |
| 8 | Replication model data collection (30 runs) |
| 9 | Final analysis, manuscript preparation |

**Total runs:** 150 (90 primary + 30 replication + 10 pilot + 20 dose-response)

---

## 21. Team

- **PI:** [TO BE ADDED]
- **Co-Is:** [TO BE ADDED]
- **Experiment Implementor:** [TO BE ADDED]
- **Statistical Consultant:** [TO BE ADDED]

---

## 22. References

[Pre-registered URL will go here]

[Code and data will be shared on OSF upon publication]

---

## Appendix A: Task Specifications

See /root/hermes-workspace/borg/dogfood/hard_tasks/ (15 task repos with reasoning traces)

## Appendix B: Analysis Code

See /root/hermes-workspace/borg/dogfood/final_analysis.py (1,603 lines, implements all pre-registered analyses)

## Appendix C: Example Runs

[TO BE ADDED - 3 complete example runs with all logged fields]

---

**Document version:** 1.0  
**Last updated:** March 31, 2026  
**Status:** Ready for pre-registration
