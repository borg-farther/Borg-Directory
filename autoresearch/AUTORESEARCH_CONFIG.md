# Borg Autoresearch Config: Trace Format Optimization
## Does the trace format/matching algorithm affect agent success rate?

**Date:** 2026-04-02  
**Status:** HONEST ASSESSMENT FIRST — is this worth doing?

---

# VERDICT: PREMATURE OPTIMIZATION — FIX THE BROKEN PIPELINE FIRST

## Why Autoresearch on Trace Format is Premature

### The Core Problem: 50% Trace Capture Rate

The stated problem is "only 50% of traces are effective." This is NOT a trace FORMAT problem — it's a **pipeline integration problem**:

1. **Trace capture isn't wired into the agent loop** — `TraceCapture` exists but isn't called from the MCP server's `call_tool` flow
2. **The SWE-bench results (40%→90%) used hints_text** — manually-written reasoning traces from GitHub issue discussions, NOT auto-captured traces
3. **The gap between hints_text and auto-trace is enormous:**
   - hints_text: Written by developers who UNDERSTAND the bug
   - auto-trace: Extracted from agent tool calls (file reads, errors) with no semantic understanding

### What This Means

```
Manually-written hints (SWE-bench):  40% → 90% (+50pp)
Auto-captured traces (current Borg): ??% → ??% (unknown, likely much smaller)
```

If auto-captured traces are 50% effective, that could mean:
- 50% of sessions produce no useful trace (capture not triggered)
- 50% of captured traces don't match well (matching algorithm)
- 50% of matched traces don't help (trace content quality)

**Autoresearch on trace format optimizes the WRONG thing until the pipeline is fixed.**

---

# ONLY IF YOU IGNORE THE WARNING ABOVE

If you still want to proceed with autoresearch on trace format (polishing a broken product), here's the config:

---

## 1. Is Autoresearch the Right Pattern?

**YES — but only for trace FORMAT and MATCHING, not for the overall approach.**

Autoresearch works when:
- ✅ Measurable metric exists (SWE-bench pass rate)
- ✅ Eval is fast enough (15 min/task × 10 tasks = 150 min per iteration)
- ✅ LLM can reason about WHY changes help

Autoresearch fails when:
- ❌ Product doesn't work end-to-end (current state: broken trace capture)
- ❌ Metric is unclear (we don't know WHY traces are only 50% effective)
- ❌ Eval is too slow (15 min is borderline for fast iteration)

**Honest recommendation:** Fix trace capture wiring first (get to 80%+ capture rate), then use autoresearch to optimize format.

---

## 2. Measurable Metric

### Primary Metric: Pass Rate Delta (ΔPASS)

```
ΔPASS = PASS_RATE_WITH_BORG - PASS_RATE_WITHOUT_BORG
```

- **Higher = better**
- **Target:** ΔPASS > 20 percentage points on hard tasks (40-60% baseline)
- **Measurement:** McNemar's exact test, one-tailed, α=0.05

### Secondary Metrics

| Metric | Why It Matters |
|--------|----------------|
| **Trace capture rate** | % of agent sessions producing traces >5 tool calls |
| **Match precision** | % of shown traces that are relevant (manual review) |
| **Token overhead** | Extra tokens from trace injection (should be <10%) |
| **Time to solve** | Median tool calls with vs without trace |

### What to Track Per Run

```json
{
  "task_id": "django__django-15503",
  "condition": "A|B",  // A = no trace, B = borg trace
  "success": true,
  "pass_rate": 0.9,
  "tool_calls": 45,
  "trace_captured": true,
  "trace_matched": true,
  "trace_helped": true,
  "timestamp": "2026-04-02T10:00:00Z"
}
```

---

## 3. The Model File (What the Agent Iterates On)

### Model File: `trace_config.json`

This is the configuration file the autoresearch agent modifies:

```json
{
  "trace_format": {
    "capture_threshold": 5,
    "max_files_tracked": 20,
    "max_errors_tracked": 10,
    "include_dead_ends": true,
    "include_tool_sequence": false,
    "min_session_duration_seconds": 30
  },
  "matching": {
    "top_k": 3,
    "min_match_score": 1.0,
    "signals": {
      "fts_weight": 1.0,
      "error_type_weight": 5.0,
      "file_overlap_weight": 3.0,
      "technology_match_weight": 2.0,
      "helpfulness_multiplier": true
    },
    "filters": {
      "min_trace_quality": 0.3,
      "decay_old_traces": true,
      "decay_days": 30
    }
  },
  "injection": {
    "trigger": "after_n_failures",
    "n_failures": 2,
    "format": "concise",  // "concise" | "verbose" | "structured"
    "include_key_files": true,
    "include_root_cause": true,
    "include_dead_ends": true
  },
  "pack_structure": {
    "enabled": false,  // Packs vs traces - explore which works better
    "pack_template": "phase_based"  // "phase_based" | "entity_based" | "timeline_based"
  }
}
```

### Dimensions to Explore

| Dimension | Options | Hypothesis |
|-----------|---------|------------|
| Capture threshold | 3, 5, 10 tool calls | Lower = more traces, but noise |
| Match top_k | 1, 3, 5 | More = more chance of help, but dilution |
| Min match score | 0.5, 1.0, 2.0 | Higher = precision, lower = recall |
| Injection trigger | "immediate", "after_1_failure", "after_2_failures" | Later = less noise |
| Trace format | "concise", "verbose", "structured" | Structured helps on hard tasks |
| Packs vs Traces | boolean | Packs for workflow, traces for specific bugs |

---

## 4. Eval Harness

### How to Run SWE-bench Tasks Programmatically

```python
#!/usr/bin/env python3
"""
SWE-bench Autoresearch Eval Harness
Runs SWE-bench tasks with/without Borg traces and measures pass rate.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
import docker

# Paths
SWE_BENCH_DIR = Path("/root/hermes-workspace/borg/dogfood/swebench_experiment")
TRACES_DIR = Path("/root/hermes-workspace/borg/dogfood/swebench_traces")
RESULTS_DIR = Path("/root/hermes-workspace/borg/autoresearch/results")

# SWE-bench tasks (Django, medium difficulty)
TASKS = [
    "django__django-10554",
    "django__django-11138", 
    "django__django-11400",
    "django__django-12708",
    "django__django-12754",
    "django__django-13212",
    "django__django-13344",
    "django__django-14631",
    "django__django-15128",
    "django__django-15252",
]

def run_task(task_id: str, condition: str, trace_config: dict) -> Dict:
    """
    Run a single SWE-bench task under specified condition.
    
    Args:
        task_id: e.g., "django__django-15503"
        condition: "A" (no trace) or "B" (with borg trace)
        trace_config: The trace format/matching config to test
    
    Returns:
        Dict with success, tool_calls, pass_rate, etc.
    """
    # Build the prompt based on condition
    task_dir = SWE_BENCH_DIR / task_id
    task_data = json.loads((task_dir / "task_data.json").read_text())
    
    if condition == "A":
        prompt = build_condition_a_prompt(task_data)
        trace_to_inject = None
    else:
        prompt = build_condition_b_prompt(task_data, trace_config)
        trace_to_inject = get_borg_trace_for_task(task_id, trace_config)
    
    # Start Docker container
    container = start_container(task_id)
    
    try:
        # Run agent with prompt
        result = run_agent_in_container(
            container,
            prompt,
            trace_to_inject,
            timeout=900  # 15 minutes
        )
        
        # Run tests
        test_result = run_tests(container, task_data["FAIL_TO_PASS"])
        
        return {
            "task_id": task_id,
            "condition": condition,
            "success": test_result["all_passed"],
            "pass_rate": test_result["pass_rate"],
            "tool_calls": result["tool_calls"],
            "wall_time": result["wall_time"],
            "trace_captured": trace_to_inject is not None,
        }
    finally:
        cleanup_container(container)

def build_condition_a_prompt(task_data: Dict) -> str:
    """Build prompt WITHOUT trace (baseline condition)."""
    return f"""You are an expert software engineer. Fix the bug described below.

ISSUE:
{task_data['problem_statement']}

TESTS THAT MUST PASS:
{', '.join(task_data['FAIL_TO_PASS'])}

After fixing, run the tests to verify.
The fix is correct when all specified tests pass.
"""

def build_condition_b_prompt(task_data: Dict, trace_config: dict) -> str:
    """Build prompt WITH borg trace injection."""
    # Get relevant trace (using the trace_config's matching settings)
    trace = get_borg_trace_for_task(task_data["instance_id"], trace_config)
    
    trace_text = ""
    if trace:
        trace_text = format_trace_for_prompt(trace, trace_config["injection"]["format"])
    
    return f"""You are an expert software engineer. Fix the bug described below.

ISSUE:
{task_data['problem_statement']}

{trace_text}

TESTS THAT MUST PASS:
{', '.join(task_data['FAIL_TO_PASS'])}

After fixing, run the tests to verify.
The fix is correct when all specified tests pass.
"""

def get_borg_trace_for_task(task_id: str, trace_config: dict) -> str:
    """
    Query Borg for a relevant trace using the given matching config.
    This is where trace_format and matching algorithm are tested.
    """
    from borg.core.trace_matcher import TraceMatcher
    from borg.core.traces import _get_db
    
    db = _get_db()
    matcher = TraceMatcher()
    
    # Load task details
    task_data = json.loads((SWE_BENCH_DIR / task_id / "task_data.json").read_text())
    
    # Find relevant traces using the configured matching
    traces = matcher.find_relevant(
        task=task_data["problem_statement"],
        error="",  # No specific error in SWE-bench
        top_k=trace_config["matching"]["top_k"]
    )
    
    if not traces or traces[0]["match_score"] < trace_config["matching"]["min_match_score"]:
        return ""  # No good match
    
    return matcher.format_for_agent(traces[0])

def run_agent_in_container(container, prompt: str, trace: str, timeout: int) -> Dict:
    """Run the agent command in Docker container."""
    # Implementation uses delegate_task or similar
    # Returns {"tool_calls": int, "wall_time": float, "output": str}
    pass

def run_tests(container, test_names: List[str]) -> Dict:
    """Run the FAIL_TO_PASS tests in the container."""
    # Returns {"all_passed": bool, "pass_rate": float, "results": list}
    pass

def compute_delta(results: List[Dict]) -> Tuple[float, float]:
    """Compute pass rate delta with statistical test."""
    # Filter to tasks that ran in both conditions
    task_results = {}
    for r in results:
        tid = r["task_id"]
        if tid not in task_results:
            task_results[tid] = {}
        task_results[tid][r["condition"]] = r["success"]
    
    # McNemar's test
    b_better = sum(
        1 for tid, res in task_results.items()
        if res.get("A") == False and res.get("B") == True
    )
    a_better = sum(
        1 for tid, res in task_results.items()
        if res.get("A") == True and res.get("B") == False
    )
    
    # McNemar chi-sq = (b-c)^2 / (b+c)
    from math import sqrt
    if b_better + a_better > 0:
        chi_sq = (b_better - a_better) ** 2 / (b_better + a_better)
        # Approximate p-value
        p_value = exp(-chi_sq / 2)  # rough approximation
    else:
        chi_sq = 0
        p_value = 1.0
    
    delta = (b_better - a_better) / len(task_results) if task_results else 0
    
    return delta, p_value
```

---

## 5. Stopping Criteria

### Pre-registered Thresholds

| Criterion | Threshold | Action |
|-----------|-----------|--------|
| **Primary: McNemar p-value** | p < 0.05 (one-tailed) | SUCCESS — publish result |
| **Secondary: Pass rate delta** | ΔPASS > 15pp | Continue if p < 0.10 |
| **Safety: Negative transfer** | 0 tasks flip success→fail | If >0, investigate |
| **Stagnation** | No improvement for 5 consecutive iterations | STOP — try different approach |
| **Budget** | 20 total iterations | HARD STOP |
| **Capture rate** | If capture_rate < 30% | STOP — fix pipeline first |

### Diagnostic Checkpoints

Every 5 iterations, check:

1. **Trace capture rate** — is the harness capturing traces?
2. **Match rate** — are traces matching to tasks?
3. **Helpfulness rate** — do matched traces actually help?

If any rate is <50%, the problem is NOT the trace format — it's the pipeline.

---

## 6. Expected Iteration Time Per Cycle

| Phase | Time | Notes |
|-------|------|-------|
| Task setup (Docker) | 2-5 min/task | Cached after first run |
| Agent run | 5-15 min/task | 15 min timeout |
| Test verification | 1-2 min/task | |
| Analysis | 1 min | McNemar test |

**Total per iteration:** ~3 hours for 10 tasks × 2 conditions  
**If parallelized (3 workers):** ~1 hour per iteration

**Realistic throughput:** 2-3 iterations per day

---

## 7. Parameters/Structure to Explore

### Enumerate Known Variants First (Hybrid Approach)

Before LLM proposes novel variants, exhaustively test these known variants:

#### Trace Format Variants

| Variant | Description | When it helps |
|---------|-------------|---------------|
| **Minimal** | Only key_files + outcome | Low noise, misses context |
| **Full** | All files_read + errors + dead_ends + approach | High noise, complete context |
| **Selective** | key_files + approach_summary + root_cause | Balanced |
| **Error-focused** | errors + error_patterns + key_files | When errors are the signal |

#### Matching Algorithm Variants

| Variant | Description |
|---------|-------------|
| **FTS-only** | Pure text match via FTS5 |
| **Multi-signal** | FTS + error types + file overlap + helpfulness |
| **Helpfulness-boosted** | Heavy weight on helpfulness_score |
| **Recency-boosted** | Prefer newer traces |

#### Injection Timing Variants

| Variant | Description | Hypothesis |
|---------|-------------|------------|
| **Immediate** | Show trace at start | Helps agents avoid rabbit holes |
| **After failure** | Show after 1 failed attempt | Lower noise, only when needed |
| **After 2 failures** | Show after 2 failed attempts | Even lower noise |

#### Exploration Order

```
1. Exhaustive: (trace_format × injection_timing) = 4 × 3 = 12 combinations
2. If stagnation: LLM proposes novel variants based on failure analysis
3. Final: Best config validated on 20 tasks
```

---

## 8. How Many Cycles to Converge

### Theoretical Minimum

For McNemar's test with α=0.05, 80% power, detecting ΔPASS=20pp:
- Need ~30 tasks with discordant pairs
- At 10 tasks/iteration: 3 iterations for signal

### Practical Estimate

| Phase | Iterations | Tasks | Time | Purpose |
|-------|------------|-------|------|---------|
| Exploration | 3-5 | 10 | 1-2 days | Find best variant |
| Validation | 2-3 | 20 | 1 day | Confirm result |
| **Total** | **5-8** | **10-20** | **2-3 days** | **Working answer** |

### Early Stopping Triggers

- If ΔPASS < 5pp after 3 iterations → likely no effect, STOP
- If capture_rate < 30% → pipeline broken, STOP
- If match_rate < 20% → matching broken, STOP

---

## 9. Files to Create

```
borg/autoresearch/
├── AUTORESEARCH_CONFIG.md     # This file
├── trace_config.json           # Model file (what agent modifies)
├── eval_harness.py             # The eval runner
├── results/
│   ├── iteration_001.json
│   ├── iteration_002.json
│   └── ...
└── experiments/
    ├── exp_001/
    │   ├── hypothesis.md
    │   ├── config.json
    │   └── results.json
    └── ...
```

---

## 10. Honest Assessment Summary

| Question | Answer |
|----------|--------|
| Is autoresearch right here? | **Maybe** — if the pipeline is fixed first |
| What's the measurable metric? | **Pass rate delta** (McNemar p < 0.05) |
| What's the model file? | **trace_config.json** — trace format + matching + injection |
| What's the eval harness? | **SWE-bench via Docker** — 10 Django tasks |
| Stopping criteria? | p < 0.05 OR stagnation (5 no-improvement iterations) OR capture_rate < 30% |
| Iteration time? | **1-3 hours per cycle** (parallelized) |
| Parameters to explore? | **12 exhaustive variants** then LLM proposals |
| Cycles to converge? | **5-8 cycles** for working answer |

### The Uncomfortable Truth

**Autoresearch on trace format is polishing a broken product.**

The 50% effective trace rate is NOT because the trace format is suboptimal. It's because:

1. Trace capture isn't wired into the agent loop (50% never captured)
2. Auto-captured traces lack the semantic depth of manually-written hints
3. The matching algorithm can't infer intent from file access patterns

**Recommended action:** Fix the trace capture pipeline first. Get to 80%+ capture rate. Then use this autoresearch config to optimize format.

If you proceed anyway: acknowledge that you're optimizing the WRONG thing and will likely see underwhelming results.
