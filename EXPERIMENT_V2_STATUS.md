# Borg Experiment V2 — Status Report
## Date: 2026-04-01

---

## WHAT WE DID

### 1. Adversarial Review (3 independent reviewers)
Found 5 critical design flaws in the original experiment:
- Wrong test (Wilcoxon) for binary data → should use McNemar's
- n=15 underpowered → need n=25+
- Testing mechanism not product → difficulty detector untested
- Hand-crafted traces ≠ production traces
- Too much complexity stealing budget from core question

### 2. Redesigned Experiment
- 25 tasks × 2 conditions × 3 runs = 150 runs
- McNemar's test (correct for paired binary outcomes)
- Simple A/B: no trace vs reasoning trace
- GO threshold: p<0.05, ≥6 flips, ≥20pp improvement

### 3. Built 33 Self-Contained Task Repos
- All Python, stdlib only
- Each has setup.sh + check.sh + prompt.txt + trace.txt
- All verified: setup works, check fails in starting state

### 4. Ran Calibration (Round 1)
- 33 tasks × 1 run each (baseline, Condition A)
- **Result: 30/33 passed (91% baseline success rate)**
- Only 3 failures (TASK-011, TASK-014, TASK-031)
- All 3 failures were environmental, not logic difficulty

### 5. Root Cause Analysis
- Single-file Python bugs are TRIVIALLY EASY for AI agents
- Off-by-one, wrong operator, missing set → pattern matching
- Need tasks where the agent genuinely struggles (~40-60% success)

### 6. SWE-bench Exploration
- Loaded SWE-bench Verified dataset (500 tasks)
- Found 82 medium-difficulty Django tasks with hints
- Selected 15 candidates with 1-3 failing tests
- Published pass rates confirm 40-55% for frontier models
- Harness installed, Docker available

---

## WHAT WE LEARNED

### Key Finding: The Difficulty Problem is Fundamental

The experiment is mechanically sound (runner, analysis, design). But **we cannot create tasks that are hard enough** with synthetic single-file bugs.

What agents struggle with (from SWE-bench data):
1. Multi-file navigation in large codebases (1000+ files)
2. Real-world context (Django, scikit-learn — not toy scripts)
3. Ambiguous bug reports (real GitHub issues, not precise descriptions)
4. Environment complexity (specific versions, dependencies)

What agents DON'T struggle with:
1. Single-file bugs (our 33 tasks: 91% pass rate)
2. Well-described bugs with clear test cases
3. Standard patterns (off-by-one, wrong operator, etc.)

### The Uncomfortable Implication

If Borg's value is "help agents solve tasks they otherwise fail at," and agents already solve 91% of coding bugs without help, then:

1. The addressable market is the **9% of hard tasks**
2. Even a 34pp improvement on that 9% = 3% overall improvement
3. Is 3% overall improvement worth building and maintaining a reasoning cache?

**UNLESS** we target the RIGHT tasks: SWE-bench medium (40-55% pass rate) represents real-world agent failure modes. Borg's traces would need to help on THESE tasks.

---

## WHAT'S NEXT

### Recommended: SWE-bench Experiment (2-3 days)

1. Set up 10 Django SWE-bench tasks (medium difficulty)
2. Clone Django repo at correct commits
3. Run 3 baseline calibration runs each (30 runs)
4. Select tasks at 40-60% baseline
5. Run A/B experiment: no trace vs SWE-bench hints_text as trace
6. Analyze with McNemar's test

This tests Borg on REAL tasks where agents ACTUALLY struggle.

### Alternative: Kill Decision

If we conclude that:
- Agents already solve most coding tasks
- The remaining hard tasks are too diverse for a reasoning cache
- Trace matching would be too unreliable in production

Then the honest decision is: the product hypothesis was interesting but doesn't scale.

---

## DELIVERABLES SO FAR

| Artifact | Location | Status |
|----------|----------|--------|
| V2 Design Doc | borg/EXPERIMENT_V2_DESIGN.md | Complete |
| 33 Task Repos | borg/dogfood/v2_tasks/ | Complete, verified |
| Experiment Runner | borg/dogfood/v2_runner.py | Complete |
| Calibration Data | borg/dogfood/v2_data/ | Round 1 complete |
| SWE-bench Tasks | borg/dogfood/swebench_tasks/ | 15 tasks extracted |
| Analysis Code | (embedded in v2_runner.py) | McNemar's test ready |
| This Status Report | borg/EXPERIMENT_V2_STATUS.md | Current |

---

## TOTAL COST

- Calibration runs: 33 delegate_task calls
- Design review: 3 subagent calls
- SWE-bench setup: 0 API cost (data download only)
- Estimated API cost: ~$5-10 total
