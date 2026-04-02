# ADVERSARIAL REVIEW: SWE-bench Experiment Design
**Reviewer: Google L7 Staff Engineer (Controlled Experiments)**
**Date: 2026-04-01**
**Status: BLOCKING ISSUES FOUND**

---

## EXECUTIVE SUMMARY

This experiment has **6 critical blocking issues** that will cause it to fail in execution. Issues range from fundamental architectural mismatches (delegate_task cannot work inside Docker containers) to statistical inadequacy (10 tasks cannot power a McNemar's test for the intended effect size). The experiment design conflates synthetic "HARD" tasks with real SWE-bench Django tasks, and the `hints_text` field does not contain "reasoning traces" as the design claims.

**Recommendation: DO NOT RUN — redesign from scratch**

---

## ISSUE 1: delegate_task Cannot Work Inside Docker Containers

### Problem
The experiment design requires the agent to work INSIDE Docker containers (Section 7: "per-run execution... Agent works via delegate_task (terminal + file tools inside container)"). But `delegate_task` spawns subagents with terminal and file access on the **host system** or a **different execution context** — not inside a running Docker container.

### Evidence
From `experiment_runner.py` lines 145-154:
```python
def copy_task_to_tmp(task_id: str, condition: str, run_number: int) -> Path:
    """Copy task repo to temp directory for experiment run."""
    src_dir = get_task_dir(task_id)
    dst_dir = Path(f"/tmp/exp_{task_id}_{condition}_run{run_number}")
    shutil.copytree(src_dir, dst_dir)
    return dst_dir
```

The runner copies tasks to `/tmp` on the **host**, not inside any Docker container. The `delegate_params` (lines 214-219) show:
```python
return {
    "goal": f"Fix the bug in task {task_id}...",
    "context": prompt,
    "toolsets": ["file_reader", "code_writer", "bash_runner"],
    "max_iterations": 50
}
```

This is designed to work on files in `/tmp` on the host — **not** inside a Docker container filesystem.

### Practical Failure Mode
1. You start a Docker container for a Django SWE-bench task
2. The container has its own filesystem at `/workspace/django`
3. `delegate_task` agent runs on the HOST with access to `/tmp/exp_HARD-001_A_run1/`
4. Agent modifies files in `/tmp/exp_HARD-001_A_run1/src/`
5. Docker container's `/workspace/django/` is NEVER modified
6. When you run `check.sh` inside the Docker container, tests still fail because the original buggy code is still there

### Fix
**Option A**: Use SWE-bench's built-in agent evaluation harness (`swebench.harness.run_evaluation`) which is designed to work with Docker containers. Do NOT use `delegate_task` — use SWE-agent or the harness's own agent interface.

**Option B**: If you must use delegate_task, you must bind-mount the agent's workspace INTO the Docker container at runtime, so edits on the host appear inside the container. But this requires significant infrastructure work and is not what the current design does.

---

## ISSUE 2: hints_text Does NOT Contain "Reasoning Traces"

### Problem
The design claims `hints_text` is "exactly what Borg would provide: reasoning context from prior investigation" and "it's NOT the answer: hints discuss approach, not provide patches" (Section 4). This is **false**.

### Evidence from actual data
From `final_analysis.py` lines 72-91:
```
KEY CONFOUND:
  hints_text is developer-insider knowledge + sometimes solutions
  NOT a reasoning trace from an agent that previously attempted the task
```

The analysis explicitly categorizes hints_text content:
- "Sometimes: actual diffs/patches" 
- "Sometimes: StackOverflow solutions"
- "Sometimes: 'Thanks for the report'"
- Variable quality: **3 chars to 13,753 chars**

From `analyze_hints.py`, hints_text content patterns include:
- `suggests_fix`: Suggests approach/fix
- `contains_patch`: Contains diff/patch content
- `contains_so`: Contains StackOverflow references
- `HAS_CODE`: Contains `#`, `//`, `def `, `class `

### Example of problematic hints_text
From `django__django-14725` (`swebench_tasks/django__django-14725/task_data.json`), hints_text is 6,700+ characters of developer discussion. While it may not contain a literal patch, it discusses the issue in detail including potential approaches, code references, and discussion of what should and shouldn't happen.

### Why This Breaks the Experiment
1. **Confound**: Some tasks' hints_text effectively provide the answer (detailed approach + code references). The treatment condition B gets a shortcut on these tasks that has nothing to do with "reasoning traces" as Borg conceptualizes them.
2. **Validity**: You cannot claim Borg's reasoning trace injection "works on real tasks" if you're actually testing whether developer discussion + StackOverflow hints help (which is trivially obvious).
3. **Selection bias**: The 10 selected tasks will likely be those with "good" hints_text, which are not representative of the full distribution.

### Fix
1. **Audit every hints_text** before experiment: Check for patch content (`diff --git`, `--- a/`, `+++ b/`, `@@ -`), code snippets that implement the fix, or explicit solution statements. Exclude contaminated tasks.
2. **Consider using only minimal/empty hints_text tasks** as your selection pool, to be more representative of the "no useful prior knowledge" scenario.
3. **Be honest in the framing**: Don't call hints_text a "reasoning trace" — it's developer discussion from the bug report, which is a different construct entirely.

---

## ISSUE 3: Statistical Power is Insufficient (n=10, McNemar's)

### Problem
With only 10 tasks and McNemar's exact test, the experiment cannot detect practically meaningful effect sizes.

### Statistical Reality
For McNemar's test with n=10 (5 discordant pairs at best, realistically fewer):
- **Minimum detectable effect**: ~40-50% absolute improvement in success rate
- **Actual target**: The design aims to detect a "≥20 percentage point improvement" (GO criterion)
- **Problem**: 20 percentage points with 10 tasks is at or below the noise floor

The contingency table:
```
              B-fail    B-success
A-fail          a          b       (b = traces helped)
A-success       c          d       (c = traces hurt)
```

With only 10 tasks, even if traces helped on 3 tasks (b=3) and hurt on 1 (c=1):
- McNemar chi-sq = (3-1)² / (3+1) = 4/4 = 1.0
- p-value = 0.317 (NOT significant at 0.05)

### Evidence from calibration data
From `calibration_run2.json`: Only 1 of 5 "hard" calibration tasks fully passed. If this holds for real SWE-bench Django tasks, your baseline success rate will be ~20%, meaning 8/10 tasks fail in BOTH conditions. You won't have enough discordant pairs to compute a meaningful test.

### Fix
1. **Increase to 25-30 tasks minimum** for adequate power (this is what the "CONDITIONAL GO" criterion acknowledges by suggesting expansion to 25 tasks)
2. **Use continuous outcomes** (time to fix, tool calls) rather than binary success, which gives more statistical power with small n
3. **Or acknowledge** this is a pilot study with n=10 that provides suggestive but not conclusive evidence

---

## ISSUE 4: 15 Minute Timeout is Likely Insufficient

### Problem
The design sets 15 minutes per run (Section 7: "Timeout: 15 minutes per run (SWE-bench standard)"). But the task selection targets "1-4 hours" difficulty tasks.

### Evidence
From the experiment design Section 3: "Select all 42 '1-4 hours' difficulty tasks"

But SWE-bench's own documentation states:
- "1-4 hours" difficulty = tasks taking 1-4 hours for a human developer
- This is NOT the same as 15 minutes

From `calibration_run2.json`, even the synthetic HARD tasks (which are simpler than real Django bugs) show:
- HARD-004: "partially_fixed" — agent couldn't fully fix it
- HARD-006: "partially_fixed" — 1 test still failing after 15+ minutes of work
- HARD-014: "conflicting_tests" — test design issue, not fixable

### Real Django Bug Complexity
Real Django bugs involve:
- Understanding Django's codebase architecture (forms, ORM, templates, middleware)
- Finding the right file among thousands in the Django source
- Understanding the interaction between multiple subsystems
- Writing a fix that doesn't break other tests (PASS_TO_PASS tests)
- 15 minutes is barely enough to read the problem statement and locate the relevant code

### Fix
1. **Increase timeout to 45-60 minutes** for hard tasks
2. **Or select only "15 min - 1 hour" difficulty tasks** if you must keep 15 minute timeout
3. **Or measure time-to-fix as a secondary outcome** and allow longer timeouts with a grace period

---

## ISSUE 5: Django SWE-bench Docker Infrastructure Has Known Failure Modes

### Problem
Building and running 10 Django SWE-bench Docker containers is not trivial. The infrastructure has multiple known failure points.

### Known Issues from existing code
From `calibration_run2.json`:
- "test design issues" — some tests have contradictory assertions
- "conflicting_tests" — tests expect contradictory behaviors
- "shared global emitter state" — tests interfere with each other
- "incorrect assertion" — tests themselves are buggy

### Practical Docker Failures
1. **Image build failures**: Django version + commit combinations may have missing system dependencies
2. **test_patch application failures**: The patch format may not apply cleanly to all Django versions
3. **Flaky tests**: Some Django tests are timing-sensitive or depend on external state
4. **Disk space**: 10 Docker images × ~2GB each = ~20GB required
5. **Version conflicts**: SWE-bench 4.1.0 may not support all Django versions

### Evidence
The `swebench_setup.py` file suggests custom setup is needed. The existing `swebench_tasks/` directory only has **15 tasks** after months of work, suggesting the Docker setup pipeline is slow and failure-prone.

### Fix
1. **Budget 2-3 days** for Docker infrastructure setup and testing (not 2-3 hours as in the budget)
2. **Pre-verify each of the 10 tasks** by running the full Docker build + test cycle before experiment
3. **Have backup tasks** — if 2-3 tasks fail Docker setup, you need alternatives
4. **Use SWE-bench's own Docker validation** (`--verify` flag) before treating a task as valid

---

## ISSUE 6: The Design Conflates Synthetic HARD Tasks with Real SWE-bench Tasks

### Problem
The experiment design mentions "HARD-001" through "HARD-015" in the `experiment_runner.py` (lines 20-23), and these tasks exist in `hard_tasks/` directory. But the design document (SWBENCH_EXPERIMENT_DESIGN.md) says the experiment uses "SWE-bench Verified dataset, django/django repo only."

### Evidence of mismatch
1. `experiment_runner.py` TASK_IDS = ["HARD-001", "HARD-002", ..., "HARD-015"] — these are synthetic tasks
2. `hard_tasks/HARD-001/README.md` describes a Flask API bug, NOT a Django bug
3. `hard_tasks/HARD-001/solution.md` contains the actual solution code (lines 17-23)
4. The design document says "Django repo only" but HARD tasks are NOT Django tasks

### What this means
The existing dogfood infrastructure (experiment_runner.py, hard_tasks/) is designed for synthetic tasks, NOT real SWE-bench Django tasks. The SWE-bench experiment design document describes a DIFFERENT experiment than what's implemented in the existing code.

### Fix
1. **Decide**: Are you running on synthetic HARD tasks or real SWE-bench Django tasks? The design and implementation must match.
2. **If Django**: Throw out `experiment_runner.py` and `hard_tasks/` entirely. Build a new runner using SWE-bench's harness.
3. **If HARD tasks**: Update the design document to accurately describe using synthetic tasks, and acknowledge the reduced external validity.

---

## ADDITIONAL CONCERNS (Less Critical but Notable)

### A. Counterbalancing implementation
The hash-based counterbalancing ("hash-deterministic per task") in Section 5 is not implemented in the existing `experiment_runner.py`. The COUNTERBALANCE dict (lines 28-39) is manually specified, not computed. This is fine but the design should match implementation.

### B. Within-subject design concern
With only 3 runs per condition per task, and within-subject design, there's a risk of **learning effects**: the agent might "remember" the task from Condition A when doing Condition B, inflating the B>A effect. This is acknowledged in the design (Section 9 "Order effects: Hash-based counterbalancing") but the mitigation only partially addresses it.

### C. PASS_TO_PASS regression checking
The design says "Also run PASS_TO_PASS tests (check for regressions)" (Section 7) but the aggregation only considers FAIL_TO_PASS success. An agent could "fix" a bug by deleting the failing code entirely (making all tests pass trivially). The PASS_TO_PASS check is not aggregated, so this failure mode is invisible.

---

## SUMMARY TABLE

| Issue | Severity | Impact | Fix Complexity |
|-------|----------|--------|----------------|
| delegate_task can't work in Docker | **CRITICAL** | Experiment produces no valid data | High (redesign harness) |
| hints_text contamination | **CRITICAL** | Invalidates treatment condition | Medium (audit + exclude) |
| n=10 underpowers McNemar's | **CRITICAL** | Cannot detect real effect | Low (increase n) |
| 15 min timeout insufficient | **HIGH** | High false failure rate | Low (increase timeout) |
| Docker infrastructure fragile | **HIGH** | Setup phase overruns | Medium (pre-verify) |
| Synthetic vs real task mismatch | **HIGH** | Wrong external validity | Medium (clarify scope) |

---

## RECOMMENDATIONS

**DO NOT RUN THIS EXPERIMENT AS DESIGNED.**

Priority actions if you want a valid experiment:

1. **First**: Decide and document whether you're using real SWE-bench Django tasks or synthetic HARD tasks. Current design/implementation mismatch is fundamental.

2. **Second**: If Django: rebuild the experiment harness using SWE-bench's native Docker evaluation. Do NOT use delegate_task for containerized tasks.

3. **Third**: Audit all hints_text for contamination before selecting tasks.

4. **Fourth**: Increase to 25+ tasks OR switch to continuous outcomes.

5. **Fifth**: Increase timeout to 45-60 min OR select easier tasks.

6. **Budget realistic time**: 2-3 days for Docker setup + verification, not 2-3 hours.

---

*This review is based on analysis of:*
- *`SWBENCH_EXPERIMENT_DESIGN.md` (the experiment design under review)*
- *`dogfood/experiment_runner.py` (existing runner code)*
- *`dogfood/calibration_run2.json` (calibration data showing failure modes)*
- *`dogfood/final_analysis.py` (analysis of hints_text content)*
- *`dogfood/analyze_hints.py` (hints_text quality analysis)*
- *Actual SWE-bench task data in `swebench_tasks/` and `hard_tasks/`*