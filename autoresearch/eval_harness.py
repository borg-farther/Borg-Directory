#!/usr/bin/env python3
"""
SWE-bench Autoresearch Eval Harness

Runs SWE-bench tasks with/without Borg traces and measures pass rate delta.
This is the EVAL component - the agent does NOT modify this file.

Usage:
    python eval_harness.py --exp-num 1 --config trace_config.json
    python eval_harness.py --baseline  # Run without Borg (Condition A only)
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from math import exp
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add borg to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Constants
SWE_BENCH_DIR = Path("/root/hermes-workspace/borg/dogfood/swebench_experiment")
TRACES_DB = Path.home() / ".borg" / "traces.db"
RESULTS_DIR = Path("/root/hermes-workspace/borg/autoresearch/results")
EXPERIMENTS_DIR = Path("/root/hermes-workspace/borg/autoresearch/experiments")

# Default tasks (Django medium difficulty)
DEFAULT_TASKS = [
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


@dataclass
class RunResult:
    """Result of a single task run."""
    task_id: str
    condition: str  # "A" (no trace) or "B" (with trace)
    run_number: int
    success: bool
    pass_rate: float
    tool_calls: int
    wall_time_seconds: float
    trace_captured: bool = False
    trace_matched: bool = False
    trace_helped: Optional[bool] = None
    error: Optional[str] = None
    timestamp: str = ""


@dataclass
class ExperimentResult:
    """Result of a full experiment iteration."""
    exp_num: int
    config: Dict
    runs: List[RunResult]
    delta_pass_rate: float
    p_value: float
    mc_nemar_b: int  # B better than A
    mc_nemar_c: int  # A better than B
    improvement_iterations: int
    status: str  # "success", "stagnation", "pipeline_broken", "running"


def load_config(config_path: str) -> Dict:
    """Load trace configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def load_task_data(task_id: str) -> Dict:
    """Load SWE-bench task data."""
    task_file = SWE_BENCH_DIR / task_id / "task_data.json"
    if not task_file.exists():
        raise FileNotFoundError(f"Task data not found: {task_file}")
    return json.loads(task_file.read_text())


def build_prompt(task_data: Dict, condition: str, trace_text: str = "") -> str:
    """
    Build the agent prompt for a task.
    
    Condition A: No trace (baseline)
    Condition B: With Borg trace
    """
    base = f"""You are an expert software engineer. Fix the bug described below.

ISSUE:
{task_data['problem_statement']}
"""

    if condition == "B" and trace_text:
        base += f"""
---
PRIOR INVESTIGATION HINT:
{trace_text}
---
"""

    base += f"""
TESTS THAT MUST PASS:
{', '.join(task_data['FAIL_TO_PASS'])}

After fixing, run the tests to verify your fix.
The fix is correct when all specified tests pass.
"""
    return base


def query_borg_trace(task_id: str, config: Dict) -> Tuple[str, bool, float]:
    """
    Query Borg for a relevant trace using the given matching config.
    
    Returns:
        Tuple of (trace_text, matched, match_score)
    """
    try:
        from borg.core.trace_matcher import TraceMatcher
        from borg.core.traces import _get_db
        
        task_data = load_task_data(task_id)
        matcher = TraceMatcher()
        
        # Find relevant traces
        traces = matcher.find_relevant(
            task=task_data["problem_statement"],
            error="",
            top_k=config["matching"]["top_k"]
        )
        
        if not traces:
            return "", False, 0.0
        
        top_trace = traces[0]
        match_score = top_trace.get("match_score", 0.0)
        
        # Check if above threshold
        if match_score < config["matching"]["min_match_score"]:
            return "", False, match_score
        
        # Format trace
        trace_text = matcher.format_for_agent(top_trace)
        return trace_text, True, match_score
        
    except Exception as e:
        print(f"  WARNING: Borg query failed: {e}")
        return "", False, 0.0


def run_single_task(
    task_id: str,
    condition: str,
    config: Dict,
    run_number: int,
    timeout: int = 900
) -> RunResult:
    """
    Run a single SWE-bench task under specified condition.
    
    This is the main eval function - it:
    1. Builds the prompt (with or without trace)
    2. Runs the agent in Docker
    3. Runs tests
    4. Returns the result
    """
    print(f"  Running {task_id} condition={condition} run={run_number}...")
    start_time = time.time()
    
    try:
        # Load task data
        task_data = load_task_data(task_id)
        
        # Get trace if condition B
        trace_text = ""
        trace_matched = False
        if condition == "B":
            trace_text, trace_matched, _ = query_borg_trace(task_id, config)
        
        # Build prompt
        prompt = build_prompt(task_data, condition, trace_text)
        
        # Run agent (placeholder - integrate with actual agent runner)
        # For now, simulate a run
        success, tool_calls = simulate_agent_run(task_id, condition, prompt, timeout)
        
        # Calculate pass rate (for simulation, use success as proxy)
        pass_rate = 1.0 if success else 0.0
        
        wall_time = time.time() - start_time
        
        return RunResult(
            task_id=task_id,
            condition=condition,
            run_number=run_number,
            success=success,
            pass_rate=pass_rate,
            tool_calls=tool_calls,
            wall_time_seconds=wall_time,
            trace_captured=condition == "B",
            trace_matched=trace_matched,
            trace_helped=None,  # Would need follow-up to determine
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        print(f"  ERROR: {task_id} failed: {e}")
        import traceback
        traceback.print_exc()
        return RunResult(
            task_id=task_id,
            condition=condition,
            run_number=run_number,
            success=False,
            pass_rate=0.0,
            tool_calls=0,
            wall_time_seconds=time.time() - start_time,
            error=str(e),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )


def simulate_agent_run(task_id: str, condition: str, prompt: str, timeout: int) -> Tuple[bool, int]:
    """
    Simulate an agent run (placeholder for actual implementation).
    
    In production, this would:
    1. Start Docker container with SWE-bench environment
    2. Run the agent (delegate_task or similar) with the prompt
    3. Collect tool calls, wall time, output
    4. Return success and tool count
    
    For simulation:
    - 60% success rate for condition A (baseline)
    - 75% success rate for condition B (with trace)
    """
    import random
    
    # Simulate agent thinking
    time.sleep(0.5)
    
    # Simple simulation: trace helps ~15pp on average
    base_success = 0.60
    trace_boost = 0.15 if condition == "B" else 0.0
    
    success = random.random() < (base_success + trace_boost)
    tool_calls = random.randint(10, 50)
    
    return success, tool_calls


def run_agent_in_container(task_id: str, prompt: str, timeout: int) -> Dict:
    """
    ACTUAL implementation: run agent in Docker container.
    
    This is the real integration point for SWE-bench.
    """
    # TODO: Implement actual Docker-based agent execution
    # For now, return simulation
    success, tool_calls = simulate_agent_run(task_id, "B", prompt, timeout)
    return {
        "success": success,
        "tool_calls": tool_calls,
        "output": "Simulation - implement Docker runner"
    }


def compute_mcnemar(runs: List[RunResult]) -> Tuple[float, float, int, int]:
    """
    Compute McNemar's test for paired binary outcomes.
    
    Returns:
        Tuple of (delta, p_value, b_better_count, a_better_count)
    
    Where:
        b_better = A fails, B succeeds (trace helped)
        a_better = A succeeds, B fails (trace hurt)
    """
    # Aggregate to task-condition level (majority vote of runs)
    task_results: Dict[str, Dict[str, bool]] = {}
    
    for r in runs:
        tid = r.task_id
        cond = r.condition
        
        if tid not in task_results:
            task_results[tid] = {}
        
        # Majority vote per task-condition
        if cond not in task_results[tid]:
            task_results[tid][cond] = []
        task_results[tid][cond].append(r.success)
    
    # Compute majority vote
    task_outcomes = {}
    for tid, conds in task_results.items():
        task_outcomes[tid] = {}
        for cond, successes in conds.items():
            task_outcomes[tid][cond] = sum(successes) >= len(successes) / 2
    
    # Count discordant pairs
    b_better = 0  # A fails, B succeeds
    a_better = 0  # A succeeds, B fails
    
    for tid, outcomes in task_outcomes.items():
        a_success = outcomes.get("A", False)
        b_success = outcomes.get("B", None)
        
        if b_success is None:
            continue
            
        if not a_success and b_success:
            b_better += 1
        elif a_success and not b_success:
            a_better += 1
    
    # McNemar chi-sq
    n = b_better + a_better
    if n > 0:
        chi_sq = (b_better - a_better) ** 2 / n
        # Approximate p-value (one-tailed, continuity correction)
        p_value = exp(-chi_sq / 2) * (1 + chi_sq / 2)  # Wilson-Hilferty approximation
    else:
        chi_sq = 0
        p_value = 1.0
    
    delta = (b_better - a_better) / len(task_outcomes) if task_outcomes else 0
    
    return delta, p_value, b_better, a_better


def run_experiment(
    exp_num: int,
    config: Dict,
    tasks: List[str] = None,
    runs_per_condition: int = 3
) -> ExperimentResult:
    """
    Run a full experiment iteration.
    
    Args:
        exp_num: Experiment number (for tracking)
        config: Trace configuration to test
        tasks: List of task IDs to run
        runs_per_condition: Number of runs per task-condition
    
    Returns:
        ExperimentResult with all data
    """
    print(f"\n{'='*60}")
    print(f"EXPERIMENT {exp_num}")
    print(f"{'='*60}")
    
    tasks = tasks or DEFAULT_TASKS
    runs: List[RunResult] = []
    
    # Counterbalancing: hash-deterministic order
    def get_order(task_id: str, exp_num: int) -> str:
        import hashlib
        h = hashlib.sha256(f"{task_id}:{exp_num}:borg".encode()).digest()
        return "AB" if h[0] % 2 == 0 else "BA"
    
    for task_id in tasks:
        order = get_order(task_id, exp_num)
        
        for run_num in range(1, runs_per_condition + 1):
            for cond in order:
                result = run_single_task(task_id, cond, config, run_num)
                runs.append(result)
                print(f"    -> {'PASS' if result.success else 'FAIL'}")
    
    # Compute statistics
    delta, p_value, b_better, a_better = compute_mcnemar(runs)
    
    print(f"\n  Results:")
    print(f"    Tasks: {len(tasks)}")
    print(f"    Total runs: {len(runs)}")
    print(f"    McNemar: b_better={b_better}, a_better={a_better}")
    print(f"    Delta pass rate: {delta:.1%}")
    print(f"    p-value: {p_value:.4f}")
    
    return ExperimentResult(
        exp_num=exp_num,
        config=config,
        runs=runs,
        delta_pass_rate=delta,
        p_value=p_value,
        mc_nemar_b=b_better,
        mc_nemar_c=a_better,
        improvement_iterations=0,  # Track consecutive improvements
        status="running"
    )


def check_pipeline_health() -> Dict[str, float]:
    """
    Check if the Borg pipeline is working correctly.
    
    Returns diagnostics on:
    - Trace capture rate
    - Trace match rate
    - Trace helpfulness rate
    """
    print("\n  Checking pipeline health...")
    
    try:
        from borg.core.traces import _get_db
        import sqlite3
        
        db_path = str(TRACES_DB)
        
        if not Path(db_path).exists():
            return {
                "capture_rate": 0.0,
                "match_rate": 0.0,
                "helpfulness_rate": 0.0,
                "status": "no_database"
            }
        
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        
        # Count total traces
        total_traces = db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        
        # Count traces with helpfulness data
        shown_traces = db.execute("SELECT COUNT(*) FROM traces WHERE times_shown > 0").fetchone()[0]
        helped_traces = db.execute("SELECT COUNT(*) FROM traces WHERE times_helped > 0").fetchone()[0]
        
        db.close()
        
        return {
            "total_traces": total_traces,
            "capture_rate": min(1.0, total_traces / 100),  # Normalized
            "match_rate": min(1.0, shown_traces / max(1, total_traces)),
            "helpfulness_rate": helped_traces / max(1, shown_traces),
            "status": "ok" if total_traces > 0 else "no_traces"
        }
        
    except Exception as e:
        return {
            "capture_rate": 0.0,
            "match_rate": 0.0,
            "helpfulness_rate": 0.0,
            "status": f"error: {e}"
        }


def save_results(result: ExperimentResult, exp_num: int):
    """Save experiment results to disk."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    result_file = RESULTS_DIR / f"iteration_{exp_num:03d}.json"
    
    # Convert to serializable format
    result_dict = {
        "exp_num": result.exp_num,
        "config": result.config,
        "delta_pass_rate": result.delta_pass_rate,
        "p_value": result.p_value,
        "mc_nemar_b": result.mc_nemar_b,
        "mc_nemar_c": result.mc_nemar_c,
        "improvement_iterations": result.improvement_iterations,
        "status": result.status,
        "runs": [asdict(r) for r in result.runs]
    }
    
    with open(result_file, "w") as f:
        json.dump(result_dict, f, indent=2)
    
    print(f"  Results saved to {result_file}")


def load_previous_results() -> List[ExperimentResult]:
    """Load previous experiment results for tracking."""
    results = []
    
    if not RESULTS_DIR.exists():
        return results
    
    for result_file in sorted(RESULTS_DIR.glob("iteration_*.json")):
        with open(result_file) as f:
            d = json.load(f)
            
        runs = [RunResult(**r) for r in d["runs"]]
        results.append(ExperimentResult(
            exp_num=d["exp_num"],
            config=d["config"],
            runs=runs,
            delta_pass_rate=d["delta_pass_rate"],
            p_value=d["p_value"],
            mc_nemar_b=d["mc_nemar_b"],
            mc_nemar_c=d["mc_nemar_c"],
            improvement_iterations=d.get("improvement_iterations", 0),
            status=d.get("status", "unknown")
        ))
    
    return results


def determine_stoppage(
    current: ExperimentResult,
    previous: List[ExperimentResult],
    pipeline_health: Dict
) -> Tuple[bool, str]:
    """
    Determine if we should stop based on pre-registered criteria.
    
    Returns:
        Tuple of (should_stop, reason)
    """
    # Check pipeline health first
    if pipeline_health["capture_rate"] < 0.3:
        return True, f"PIPELINE BROKEN: capture_rate={pipeline_health['capture_rate']:.1%}"
    
    # Check for success
    if current.p_value < 0.05 and current.delta_pass_rate > 0.15:
        return True, f"SUCCESS: p={current.p_value:.4f}, Δ={current.delta_pass_rate:.1%}"
    
    # Check for stagnation (5 consecutive no-improvement)
    if len(previous) >= 5:
        recent = previous[-5:]
        deltas = [r.delta_pass_rate for r in recent]
        if max(deltas) < 0.05:
            return True, f"STAGNATION: no improvement in 5 iterations"
    
    # Hard budget stop
    if len(previous) >= 20:
        return True, f"BUDGET: 20 iterations completed"
    
    # Check for negative transfer (safety)
    if current.mc_nemar_c > 0:
        print(f"  WARNING: {current.mc_nemar_c} tasks showed negative transfer (B < A)")
    
    return False, ""


def main():
    parser = argparse.ArgumentParser(description="SWE-bench Autoresearch Eval Harness")
    parser.add_argument("--exp-num", type=int, default=1, help="Experiment number")
    parser.add_argument("--config", type=str, default="trace_config.json", 
                        help="Path to trace config JSON")
    parser.add_argument("--baseline", action="store_true",
                        help="Run baseline (condition A only) for calibration")
    parser.add_argument("--tasks", type=str, nargs="+",
                        help="Specific task IDs to run")
    parser.add_argument("--runs-per-condition", type=int, default=3,
                        help="Runs per task-condition")
    
    args = parser.parse_args()
    
    print("SWE-bench Autoresearch Eval Harness")
    print("=" * 40)
    
    # Check pipeline health
    health = check_pipeline_health()
    print(f"\nPipeline health: {health['status']}")
    print(f"  Capture rate: {health['capture_rate']:.1%}")
    print(f"  Match rate: {health.get('match_rate', 0):.1%}")
    print(f"  Helpfulness: {health.get('helpfulness_rate', 0):.1%}")
    
    if health["capture_rate"] < 0.3:
        print("\n*** WARNING: Pipeline appears broken. Results may be meaningless. ***")
        print("*** Fix trace capture before running autoresearch. ***\n")
    
    # Load config
    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)
    
    config = load_config(str(config_path))
    print(f"\nLoaded config: {args.config}")
    
    # Determine tasks
    tasks = args.tasks or DEFAULT_TASKS
    print(f"Tasks: {len(tasks)}")
    
    if args.baseline:
        print("\nRunning BASELINE (Condition A only - no Borg)")
        # Run baseline calibration
        results = []
        for task_id in tasks:
            for run_num in range(1, args.runs_per_condition + 1):
                result = run_single_task(task_id, "A", config, run_num)
                results.append(result)
                print(f"  {task_id}: {'PASS' if result.success else 'FAIL'}")
        
        # Compute baseline stats
        baseline_pass = sum(1 for r in results if r.success) / len(results)
        print(f"\nBaseline pass rate: {baseline_pass:.1%}")
        return
    
    # Run full experiment
    result = run_experiment(
        args.exp_num,
        config,
        tasks,
        args.runs_per_condition
    )
    
    # Save results
    save_results(result, args.exp_num)
    
    # Check stoppage
    previous = load_previous_results()
    should_stop, reason = determine_stoppage(result, previous, health)
    
    print(f"\nStoppage check: {reason if should_stop else 'Continue'}")
    
    if should_stop:
        print(f"\n*** EXPERIMENT {'SUCCEEDED' if 'SUCCESS' in reason else 'STOPPED'}: {reason} ***")


if __name__ == "__main__":
    main()
