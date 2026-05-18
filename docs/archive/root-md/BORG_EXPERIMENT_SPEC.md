# BORG EXPERIMENT SPEC
## Does Borg Actually Help AI Agents?
## Date: 2026-03-31 | Version: 1.0

---

# 1. THE ONE QUESTION

Does an AI coding agent that checks borg_search before starting a task
finish faster, cheaper, and more reliably than one that doesn't?

If yes → build learning loop, scale fleet, ship.
If no → kill the product honestly.

---

# 2. EXPERIMENT DESIGN

## 2.1 Structure: Paired Within-Subject

Each task runs TWICE on the SAME machine with the SAME model:
- **Run A (Control):** Agent has standard tools only (terminal, file, search_files, patch)
- **Run B (Treatment):** Same agent + borg MCP tools (borg_search, borg_observe, borg_suggest)

Paired design controls for task difficulty — we compare each task to itself.

## 2.2 Counterbalancing

To control for order effects (does going first help or hurt?):
- 50% of tasks: Control runs first, then Treatment
- 50% of tasks: Treatment runs first, then Control
- Assignment randomized per task using seeded RNG

Between paired runs: reset repo to clean state (git checkout + clean).

## 2.3 Tasks: 25 Total

| Category | Count | Borg Pack | Expected Benefit |
|----------|-------|-----------|-----------------|
| Debugging | 8 | systematic-debugging | High — structured approach prevents rabbit holes |
| Testing | 4 | test-driven-development | Medium — phases guide test-first workflow |
| Code Review | 3 | code-review | Medium — checklist catches common misses |
| Refactoring | 3 | writing-plans | Medium — structured decomposition |
| Deployment | 2 | build-review-harden-ship | Low-Medium — CI/CD is procedural |
| **Control** | **5** | **none** | **None — mechanical tasks, no reasoning needed** |

Control tasks (grep, formatting, file renaming) should show NO improvement with borg.
If they do, the experiment is measuring task framing, not borg's value.

## 2.4 Task Requirements

Each task MUST be:
1. **Self-contained:** A git repo that can be `git clone && git reset --hard`
2. **Deterministic pass/fail:** A command that returns 0 (pass) or non-zero (fail)
3. **Non-trivial:** Requires reasoning, not just mechanical steps
4. **Completable in 5-30 min:** Within agent capability but not instant
5. **Real-world:** Based on actual patterns from open-source projects

Task repos will be created at:
`/root/hermes-workspace/borg/dogfood/experiment_repos/TASK-ID/`

---

# 3. WHAT WE MEASURE

## 3.1 Primary Metric: Token Reduction (Continuous)

**Why tokens:** Directly measures wasted reasoning. Fewer tokens = agent found
the solution more efficiently. Also maps to real cost ($).

**Measurement:** Count total input + output tokens consumed during the task.
Captured from agent's API usage log.

**Why not success rate:** Binary metric needs larger sample size.
With 25 paired observations, we can detect a 45% effect on continuous metrics
but need much larger N for binary.

## 3.2 Secondary Metrics

| Metric | Type | How Measured |
|--------|------|-------------|
| Success rate | Binary | Pass condition command returns 0 |
| Time to completion | Continuous | Wall clock seconds from start to finish |
| Wrong approaches tried | Count | Number of reverted changes / failed test runs |
| Tool calls | Count | Total tool invocations during task |
| borg_search calls | Count | How many times agent voluntarily used borg (treatment only) |

## 3.3 Diagnostic Metrics (Not for hypothesis testing)

| Metric | Purpose |
|--------|---------|
| Which pack was used | Did agent pick the right pack? |
| Which phase was abandoned | Where does the pack guidance break down? |
| Agent confidence at start | Self-reported (if available) |
| Error type encountered | Categorize failure modes |

---

# 4. STATISTICAL FRAMEWORK

## 4.1 Power Analysis

```
With 25 paired observations:
- Cohen's d detectable at 80% power: 0.56
- This means we can detect ~45-50% token reduction
- If borg's true effect is 30%, we need ~50 pairs

With 20 paired observations (excluding 5 controls):
- Cohen's d detectable at 80% power: 0.64
- This means we can detect ~50-55% token reduction

Recommendation: Run each task TWICE per condition (50 total pairs)
if budget allows. Otherwise 25 pairs is minimum viable.
```

## 4.2 Analysis Plan

**Step 1: Normality check**
```python
from scipy.stats import shapiro
stat, p = shapiro(token_diffs)  # diff = control - treatment
# If p > 0.05: use paired t-test
# If p <= 0.05: use Wilcoxon signed-rank
```

**Step 2: Primary test (token reduction)**
```python
from scipy.stats import wilcoxon
stat, p = wilcoxon(control_tokens, treatment_tokens, alternative='greater')
# H0: treatment tokens >= control tokens
# H1: treatment tokens < control tokens (borg helps)
# Reject H0 if p < 0.025 (one-sided, Bonferroni-corrected)
```

**Step 3: Secondary test (success rate)**
```python
# McNemar's test for paired binary outcomes
# 2x2 table: (both pass, control pass + treatment fail, etc.)
from scipy.stats import binomtest
# b = control_pass_treatment_fail, c = control_fail_treatment_pass
# If c > b significantly: borg helps
```

**Step 4: Effect size**
```python
# Cohen's d for paired samples
d = mean(diffs) / std(diffs)
# d > 0.5: medium effect
# d > 0.8: large effect
```

**Step 5: Bootstrap CI**
```python
# 10,000 bootstrap resamples of paired differences
# 95% CI for mean token reduction
# If CI excludes 0: significant
```

## 4.3 Multiple Comparisons

Holm-Bonferroni correction across primary + secondary metrics.
3 primary comparisons → adjusted alpha = 0.05/3 = 0.017 for most significant.

## 4.4 Decision Rules

```
IF token_reduction > 0 AND p < 0.025:
  → BORG HELPS (ship it)

IF token_reduction > 0 AND 0.025 < p < 0.10:
  → TRENDING (run more tasks for power)

IF token_reduction <= 0 OR p > 0.10:
  → BORG DOESN'T HELP (kill or redesign)

IF control_tasks show improvement:
  → EXPERIMENT CONTAMINATED (redesign experiment)
```

---

# 5. EXECUTION PROTOCOL

## 5.1 Setup Phase (Day 1)

1. Create 25 task repos with seeded bugs/requirements
2. Verify each repo's pass condition works when bug is fixed
3. Verify each repo's pass condition FAILS in starting state
4. Set up token counting instrumentation
5. Randomize counterbalancing assignment
6. Dry run: 2 tasks (1 control, 1 treatment) to verify protocol

## 5.2 Run Phase (Days 2-5)

For each task in randomized order:

```
1. git clone task_repo → /tmp/experiment/TASK-ID/
2. Start token counter
3. Start timer
4. Give agent the task prompt
   - Control: standard tools only
   - Treatment: standard tools + borg MCP tools
5. Agent works until:
   - Pass condition met (SUCCESS)
   - 30 minutes elapsed (TIMEOUT → FAILURE)
   - Agent declares it can't solve (GIVE UP → FAILURE)
6. Stop timer, stop token counter
7. Run pass condition command
8. Record: task_id, condition, success, tokens, time, tool_calls
9. Reset repo: git checkout . && git clean -fd
10. Run paired condition (same task, other condition)
11. Record second run
```

## 5.3 Agent Configuration

**Control condition prompt prefix:**
```
You are working on a coding task. Use your standard tools
(terminal, file read/write, search) to complete it.
```

**Treatment condition prompt prefix:**
```
You are working on a coding task. You have access to Borg,
a reasoning cache with proven approaches. Before starting,
call borg_search with a description of your task to get
structured guidance. Use your standard tools plus borg
tools (borg_search, borg_observe, borg_suggest) to complete it.
```

**Everything else identical:** Same model, same temperature, same system prompt,
same tools (except borg), same timeout.

## 5.4 Where to Run

| Machine | Tasks | Rationale |
|---------|-------|-----------|
| Local | 10 tasks (4 debug, 2 test, 1 review, 1 refactor, 2 control) | Primary |
| VPS3 | 8 tasks (2 debug, 1 test, 1 review, 1 refactor, 1 deploy, 2 control) | Cross-validate |
| VPS4 | 7 tasks (2 debug, 1 test, 1 review, 1 refactor, 1 deploy, 1 control) | Cross-validate |

VPS1 + VPS2 held in reserve for reruns if needed.

---

# 6. TASK CREATION SPEC

Each task repo follows this template:

```
experiment_repos/TASK-ID/
├── README.md          # Task description (for humans)
├── setup.sh           # Creates starting state
├── check.sh           # Pass condition (exit 0 = pass, 1 = fail)
├── solution.md        # Known correct fix (for verification only)
├── src/               # Source code with seeded bug
└── tests/             # Tests that should pass after fix
```

### Example: DEBUG-001 (Flask HTTP Status Bug)

**setup.sh:**
```bash
#!/bin/bash
pip install flask pytest -q
# Repo already contains the buggy code
```

**check.sh:**
```bash
#!/bin/bash
cd "$(dirname "$0")"
python -m pytest tests/ -q 2>&1
```

**src/app.py** (buggy):
```python
@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    user = db.get(user_id)
    return jsonify(user)  # BUG: returns 200 with null when not found
```

**solution.md:**
```
Add null check: if not user: abort(404)
Add try/except for JSON parsing: except ValueError: abort(400)
```

---

# 7. SUCCESS CRITERIA

| ID | Criterion | Target | Measurement |
|----|-----------|--------|-------------|
| E1 | Token reduction (treatment vs control) | p < 0.025 (one-sided) | Wilcoxon signed-rank on 20 paired tasks |
| E2 | Mean token reduction | >= 30% | (mean_control - mean_treatment) / mean_control |
| E3 | Control tasks show no improvement | p > 0.10 | Same test on 5 control task pairs |
| E4 | Agent voluntarily uses borg | >= 15/20 treatment tasks | Count borg_search calls > 0 |
| E5 | No success rate regression | treatment_success >= control_success | McNemar's test |

## Go/No-Go from Experiment

```
E1 PASS + E2 PASS + E3 PASS → BORG WORKS (proceed to learning loop)
E1 FAIL                     → BORG DOESN'T WORK (redesign or kill)
E3 FAIL                     → EXPERIMENT INVALID (redesign experiment)
E4 FAIL                     → AGENT DOESN'T USE BORG (fix UX/prompting)
E5 FAIL                     → BORG MAKES THINGS WORSE (kill immediately)
```

---

# 8. FAILURE MODES

| # | Failure Mode | How We Detect | Mitigation |
|---|-------------|---------------|------------|
| 1 | Task too easy (both solve instantly) | Both runs < 2 min | Exclude from analysis, replace with harder task |
| 2 | Task too hard (neither solves) | Both runs timeout | Exclude from analysis, replace with easier task |
| 3 | Order effect (first run always better) | Counterbalancing analysis | 50/50 randomized order |
| 4 | Model stochasticity swamps signal | High variance in paired diffs | Bootstrap CI, increase N |
| 5 | Agent ignores borg even when available | borg_search call count = 0 | Stronger prompt, E4 criterion |
| 6 | Borg recommends wrong pack | Agent uses irrelevant pack | Track which pack was selected |
| 7 | Treatment prompt itself helps (not borg) | Control tasks show improvement | E3 criterion — control tasks must be flat |
| 8 | Repo setup fails on some machines | check.sh fails before agent starts | Pre-verify all repos on all machines |

---

# 9. IMPLEMENTATION FILES

```
dogfood/
├── experiment_tasks.json         # 25 task definitions (DONE)
├── analyze_experiment.py         # Statistical analysis (DONE)
├── experiment_repos/             # 25 git repos with seeded bugs (TO BUILD)
│   ├── DEBUG-001/
│   │   ├── setup.sh
│   │   ├── check.sh
│   │   ├── solution.md
│   │   └── src/
│   ├── DEBUG-002/
│   └── ...
├── run_experiment.py             # Experiment runner (TO BUILD)
│   # For each task:
│   # 1. Clone repo to /tmp
│   # 2. Run setup.sh
│   # 3. Verify check.sh fails (starting state)
│   # 4. Launch agent with control/treatment config
│   # 5. Measure tokens, time, success
│   # 6. Record to results.json
│   # 7. Reset and run paired condition
├── results.json                  # Raw results (GENERATED)
└── experiment_report.md          # Final analysis (GENERATED)
```

---

# 10. TIMELINE

```
Day 1: Build 10 highest-priority task repos
        (4 debug, 2 test, 2 refactor, 2 control)
        Verify all setup.sh + check.sh work
        Build run_experiment.py

Day 2: Dry run — 2 tasks end-to-end
        Fix any protocol issues
        Build remaining 15 task repos

Day 3-4: Run all 25 tasks (50 agent runs)
          ~2 runs per hour = ~25 hours total
          Split across Local + VPS3 + VPS4

Day 5: Run analyze_experiment.py
        Write experiment_report.md
        Go/No-Go decision
```

---

# 11. WHAT HAPPENS AFTER

## If Borg Helps (E1-E5 pass):
1. Quantify exactly HOW MUCH it helps (effect size)
2. Identify WHICH task categories benefit most
3. Activate the learning loop from the V3 spec
4. Replace fake fleet data with real experiment outcomes
5. Update marketing with REAL numbers
6. Ship V3 to PyPI

## If Borg Doesn't Help:
1. Analyze WHY — which packs failed? Where did agents ignore guidance?
2. Consider: is it the packs that are wrong, or the delivery mechanism?
3. If packs are wrong → rewrite packs based on what agents actually needed
4. If delivery is wrong → change how borg_search presents information
5. If fundamental → kill the product, archive learnings

## If Experiment Is Inconclusive:
1. Run 25 more tasks (increase power)
2. Focus on the category with the strongest signal
3. If still inconclusive after 100 runs → probably no meaningful effect

---

*This experiment is the single most important thing we can do.*
*Everything else is theatre until this question is answered.*
*Does borg actually help?*
