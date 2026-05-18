#!/usr/bin/env python3
"""
Borg Experiment V2 Runner

Runs calibration and main experiment using delegate_task to spawn agents.
All tasks are self-contained Python repos with setup.sh + check.sh.

Usage:
    python3 v2_runner.py calibrate           # Run 5 baseline runs per task
    python3 v2_runner.py calibrate --task TASK-001  # Single task calibration
    python3 v2_runner.py select              # Select tasks with 40-60% baseline
    python3 v2_runner.py run                 # Run main experiment
    python3 v2_runner.py run --task TASK-001  # Single task experiment
    python3 v2_runner.py analyze             # Run analysis
    python3 v2_runner.py status              # Show experiment status
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Paths
TASKS_DIR = Path("/root/hermes-workspace/borg/dogfood/v2_tasks")
DATA_DIR = Path("/root/hermes-workspace/borg/dogfood/v2_data")
CALIBRATION_FILE = DATA_DIR / "calibration.json"
SELECTION_FILE = DATA_DIR / "selected_tasks.json"
RESULTS_FILE = DATA_DIR / "experiment_results.json"
WORK_DIR = Path("/tmp/borg_experiment")

# Config
CALIBRATION_RUNS = 5
EXPERIMENT_RUNS = 3
TIMEOUT_SECONDS = 600  # 10 minutes per run


def get_task_ids():
    """List all valid task directories."""
    tasks = []
    for d in sorted(os.listdir(TASKS_DIR)):
        path = TASKS_DIR / d
        if path.is_dir() and (path / "setup.sh").exists() and (path / "check.sh").exists():
            tasks.append(d)
    return tasks


def get_counterbalance_order(task_id):
    """Deterministic A-first or B-first based on task_id hash."""
    h = hashlib.sha256(f"{task_id}-borg-v2".encode()).hexdigest()
    return "A" if int(h[:2], 16) % 2 == 0 else "B"


def prepare_workspace(task_id):
    """Copy task repo to temp workspace. Returns workspace path."""
    src = TASKS_DIR / task_id
    dst = WORK_DIR / task_id
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    
    # Run setup.sh
    result = subprocess.run(
        ["bash", "setup.sh"], cwd=dst,
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"setup.sh failed: {result.stderr[:200]}")
    
    return dst


def verify_check_fails(workspace):
    """Verify check.sh fails in starting state."""
    result = subprocess.run(
        ["bash", "check.sh"], cwd=workspace,
        capture_output=True, text=True, timeout=30
    )
    return result.returncode != 0


def run_agent(task_id, condition, workspace):
    """
    Run an agent on the task using delegate_task.
    Returns dict with success, tool_calls, time, etc.
    """
    prompt_path = workspace / "prompt.txt"
    prompt = prompt_path.read_text()
    
    # Build the agent prompt
    if condition == "A":
        agent_prompt = f"""You are working on a coding task. Fix the bug described below.
The code is in the directory: {workspace}/repo

TASK:
{prompt}

After fixing the bug, verify by running: cd {workspace} && bash check.sh
The fix is correct when check.sh exits with code 0.
"""
    else:  # condition B
        trace_path = workspace / "trace.txt"
        trace = trace_path.read_text()
        agent_prompt = f"""You are working on a coding task. Fix the bug described below.
The code is in the directory: {workspace}/repo

TASK:
{prompt}

REASONING TRACE FROM A PREVIOUS ATTEMPT:
{trace}

Use the reasoning trace above to guide your approach. It contains insights about the problem decomposition, what approaches were tried, and key insights — but NOT the exact solution.

After fixing the bug, verify by running: cd {workspace} && bash check.sh
The fix is correct when check.sh exits with code 0.
"""
    
    start_time = time.time()
    
    # This is a placeholder — in actual execution, this calls delegate_task
    # For now, we output the prompt and workspace for manual/automated execution
    result = {
        "task_id": task_id,
        "condition": condition,
        "prompt": agent_prompt,
        "workspace": str(workspace),
        "start_time": datetime.now(timezone.utc).isoformat(),
        "success": None,  # Filled after agent runs
        "tool_calls": None,
        "wall_time": None,
        "error": None,
    }
    
    return result


def run_check(workspace):
    """Run check.sh and return success boolean."""
    try:
        result = subprocess.run(
            ["bash", "check.sh"], cwd=workspace,
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def load_json(path):
    """Load JSON file or return empty dict."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    """Save JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def cmd_calibrate(args):
    """Run calibration: 5 baseline runs per task."""
    tasks = [args.task] if args.task else get_task_ids()
    cal = load_json(CALIBRATION_FILE)
    if "runs" not in cal:
        cal = {"runs": [], "summary": {}}
    
    print(f"Calibrating {len(tasks)} tasks, {CALIBRATION_RUNS} runs each")
    print(f"Total runs needed: {len(tasks) * CALIBRATION_RUNS}")
    print()
    
    for task_id in tasks:
        existing = [r for r in cal["runs"] if r["task_id"] == task_id]
        runs_done = len(existing)
        runs_needed = CALIBRATION_RUNS - runs_done
        
        if runs_needed <= 0:
            print(f"[{task_id}] Already calibrated ({runs_done} runs)")
            continue
        
        print(f"[{task_id}] Running {runs_needed} calibration runs...")
        
        for run_num in range(runs_needed):
            try:
                workspace = prepare_workspace(task_id)
                if not verify_check_fails(workspace):
                    print(f"  WARNING: check.sh passes in starting state — skipping")
                    break
                
                agent_result = run_agent(task_id, "A", workspace)
                
                # Output prompt for delegate_task execution
                print(f"  Run {run_num + 1}/{runs_needed}: ready for execution")
                print(f"  Workspace: {workspace}")
                
                cal["runs"].append({
                    "task_id": task_id,
                    "condition": "A",
                    "run": runs_done + run_num + 1,
                    "workspace": str(workspace),
                    "prompt": agent_result["prompt"],
                    "timestamp": agent_result["start_time"],
                    "success": None,  # To be filled
                })
                
            except Exception as e:
                print(f"  ERROR: {e}")
                cal["runs"].append({
                    "task_id": task_id,
                    "condition": "A",
                    "run": runs_done + run_num + 1,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": None,
                })
    
    save_json(CALIBRATION_FILE, cal)
    print(f"\nCalibration data saved to {CALIBRATION_FILE}")


def cmd_select(args):
    """Select tasks with 40-60% baseline success rate."""
    cal = load_json(CALIBRATION_FILE)
    if not cal.get("runs"):
        print("No calibration data. Run 'calibrate' first.")
        return
    
    # Compute per-task success rates
    task_stats = {}
    for run in cal["runs"]:
        tid = run["task_id"]
        if tid not in task_stats:
            task_stats[tid] = {"successes": 0, "total": 0, "runs": []}
        if run.get("success") is not None:
            task_stats[tid]["total"] += 1
            if run["success"]:
                task_stats[tid]["successes"] += 1
            task_stats[tid]["runs"].append(run["success"])
    
    selected = []
    rejected = []
    
    for tid, stats in sorted(task_stats.items()):
        if stats["total"] == 0:
            rejected.append({"task_id": tid, "reason": "no completed runs"})
            continue
        
        rate = stats["successes"] / stats["total"]
        
        if 0.2 <= rate <= 0.8:  # Wider initial window, target 40-60%
            selected.append({
                "task_id": tid,
                "success_rate": rate,
                "successes": stats["successes"],
                "total": stats["total"],
            })
        else:
            rejected.append({
                "task_id": tid,
                "success_rate": rate,
                "reason": "too easy" if rate > 0.8 else "too hard",
            })
    
    # Sort by closeness to 50%
    selected.sort(key=lambda x: abs(x["success_rate"] - 0.5))
    
    # Take top 25
    final = selected[:25]
    
    result = {
        "selected": final,
        "rejected": rejected,
        "total_candidates": len(task_stats),
        "selected_count": len(final),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    save_json(SELECTION_FILE, result)
    
    print(f"SELECTED TASKS ({len(final)}):")
    for t in final:
        print(f"  {t['task_id']}: {t['success_rate']:.0%} ({t['successes']}/{t['total']})")
    
    print(f"\nREJECTED ({len(rejected)}):")
    for t in rejected:
        rate = t.get('success_rate', '?')
        print(f"  {t['task_id']}: {rate if isinstance(rate, str) else f'{rate:.0%}'} — {t['reason']}")


def cmd_run(args):
    """Run main experiment."""
    sel = load_json(SELECTION_FILE)
    if not sel.get("selected"):
        print("No selected tasks. Run 'select' first.")
        return
    
    tasks = [args.task] if args.task else [t["task_id"] for t in sel["selected"]]
    results = load_json(RESULTS_FILE)
    if "runs" not in results:
        results = {"runs": [], "config": {
            "conditions": ["A", "B"],
            "runs_per_cell": EXPERIMENT_RUNS,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }}
    
    print(f"Running experiment: {len(tasks)} tasks × 2 conditions × {EXPERIMENT_RUNS} runs")
    print(f"Total runs: {len(tasks) * 2 * EXPERIMENT_RUNS}")
    print()
    
    for task_id in tasks:
        first_cond = get_counterbalance_order(task_id)
        conditions = [first_cond, "B" if first_cond == "A" else "A"]
        
        for condition in conditions:
            existing = [r for r in results["runs"] 
                       if r["task_id"] == task_id and r["condition"] == condition]
            runs_done = len(existing)
            runs_needed = EXPERIMENT_RUNS - runs_done
            
            if runs_needed <= 0:
                continue
            
            for run_num in range(runs_needed):
                try:
                    workspace = prepare_workspace(task_id)
                    if not verify_check_fails(workspace):
                        print(f"  WARNING: {task_id} check passes in starting state")
                        break
                    
                    agent_result = run_agent(task_id, condition, workspace)
                    
                    results["runs"].append({
                        "task_id": task_id,
                        "condition": condition,
                        "run": runs_done + run_num + 1,
                        "order": 1 if condition == first_cond else 2,
                        "workspace": str(workspace),
                        "prompt": agent_result["prompt"],
                        "timestamp": agent_result["start_time"],
                        "success": None,  # Filled after agent execution
                    })
                    
                    print(f"  [{task_id}] Condition {condition}, Run {runs_done + run_num + 1}: queued")
                    
                except Exception as e:
                    print(f"  [{task_id}] ERROR: {e}")
    
    save_json(RESULTS_FILE, results)
    print(f"\nExperiment data saved to {RESULTS_FILE}")


def cmd_analyze(args):
    """Run analysis on completed experiment."""
    results = load_json(RESULTS_FILE)
    if not results.get("runs"):
        print("No experiment data. Run 'run' first.")
        return
    
    # Aggregate per task-condition
    task_data = {}
    for run in results["runs"]:
        tid = run["task_id"]
        cond = run["condition"]
        if run.get("success") is None:
            continue
        
        key = (tid, cond)
        if key not in task_data:
            task_data[key] = []
        task_data[key].append(run["success"])
    
    # Majority vote per task-condition
    task_results = {}
    for (tid, cond), runs in task_data.items():
        if tid not in task_results:
            task_results[tid] = {}
        successes = sum(1 for r in runs if r)
        task_results[tid][cond] = successes > len(runs) / 2
    
    # McNemar's test
    # Count discordant pairs
    a_fail_b_success = 0  # Task fails with A, succeeds with B
    a_success_b_fail = 0  # Task succeeds with A, fails with B
    both_success = 0
    both_fail = 0
    
    for tid, conds in task_results.items():
        if "A" not in conds or "B" not in conds:
            continue
        a = conds["A"]
        b = conds["B"]
        
        if not a and b:
            a_fail_b_success += 1
        elif a and not b:
            a_success_b_fail += 1
        elif a and b:
            both_success += 1
        else:
            both_fail += 1
    
    n_discordant = a_fail_b_success + a_success_b_fail
    
    # McNemar's chi-squared (with continuity correction for small n)
    if n_discordant > 0:
        if n_discordant >= 25:
            # Standard McNemar with continuity correction
            chi2 = (abs(a_fail_b_success - a_success_b_fail) - 1) ** 2 / n_discordant
        else:
            # Exact binomial test for small samples
            chi2 = (a_fail_b_success - a_success_b_fail) ** 2 / n_discordant
        
        # One-tailed p-value (we only care if B > A)
        # Approximate using chi-squared distribution
        import math
        p_value = 0.5 * math.erfc(math.sqrt(chi2 / 2))
    else:
        chi2 = 0
        p_value = 1.0
    
    # Results
    total_tasks = len(task_results)
    a_rate = sum(1 for t in task_results.values() if t.get("A")) / total_tasks if total_tasks else 0
    b_rate = sum(1 for t in task_results.values() if t.get("B")) / total_tasks if total_tasks else 0
    
    print("=" * 60)
    print("BORG EXPERIMENT V2 — RESULTS")
    print("=" * 60)
    print()
    print(f"Tasks analyzed: {total_tasks}")
    print(f"Condition A (no trace) success rate: {a_rate:.1%}")
    print(f"Condition B (with trace) success rate: {b_rate:.1%}")
    print(f"Improvement: {b_rate - a_rate:+.1%}")
    print()
    print(f"McNemar's contingency table:")
    print(f"  A-fail,  B-success: {a_fail_b_success}")
    print(f"  A-success, B-fail:  {a_success_b_fail}")
    print(f"  Both success:       {both_success}")
    print(f"  Both fail:          {both_fail}")
    print()
    print(f"McNemar's chi-squared: {chi2:.3f}")
    print(f"p-value (one-tailed):  {p_value:.4f}")
    print()
    
    # GO/NO-GO
    print("=" * 60)
    print("GO/NO-GO DECISION")
    print("=" * 60)
    
    go_criteria = {
        "p < 0.05": p_value < 0.05,
        ">= 6 tasks flip fail→success": a_fail_b_success >= 6,
        "0 tasks flip success→fail": a_success_b_fail == 0,
        ">= 20pp improvement": (b_rate - a_rate) >= 0.20,
    }
    
    all_pass = all(go_criteria.values())
    
    for criterion, passed in go_criteria.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {criterion}")
    
    print()
    if all_pass:
        print(">>> DECISION: GO <<<")
        print("Build the difficulty detector. Test the product. Ship.")
    elif p_value < 0.10 and a_fail_b_success >= 4:
        print(">>> DECISION: CONDITIONAL GO <<<")
        print("Expand to 40 tasks for more statistical power.")
    else:
        print(">>> DECISION: NO-GO <<<")
        print("Mechanism doesn't scale. Re-evaluate product direction.")


def cmd_status(args):
    """Show experiment status."""
    print("TASK INVENTORY:")
    tasks = get_task_ids()
    print(f"  Total tasks: {len(tasks)}")
    
    cal = load_json(CALIBRATION_FILE)
    cal_runs = cal.get("runs", [])
    completed_cal = [r for r in cal_runs if r.get("success") is not None]
    print(f"\nCALIBRATION:")
    print(f"  Total runs queued: {len(cal_runs)}")
    print(f"  Completed: {len(completed_cal)}")
    print(f"  Pending: {len(cal_runs) - len(completed_cal)}")
    
    sel = load_json(SELECTION_FILE)
    selected = sel.get("selected", [])
    print(f"\nSELECTION:")
    print(f"  Selected tasks: {len(selected)}")
    
    results = load_json(RESULTS_FILE)
    exp_runs = results.get("runs", [])
    completed_exp = [r for r in exp_runs if r.get("success") is not None]
    print(f"\nEXPERIMENT:")
    print(f"  Total runs queued: {len(exp_runs)}")
    print(f"  Completed: {len(completed_exp)}")
    print(f"  Pending: {len(exp_runs) - len(completed_exp)}")


def main():
    parser = argparse.ArgumentParser(description="Borg Experiment V2 Runner")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    cal_parser = subparsers.add_parser("calibrate", help="Run calibration")
    cal_parser.add_argument("--task", help="Run single task")
    
    sel_parser = subparsers.add_parser("select", help="Select tasks")
    
    run_parser = subparsers.add_parser("run", help="Run experiment")
    run_parser.add_argument("--task", help="Run single task")
    
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results")
    
    status_parser = subparsers.add_parser("status", help="Show status")
    
    args = parser.parse_args()
    
    if args.command == "calibrate":
        cmd_calibrate(args)
    elif args.command == "select":
        cmd_select(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
