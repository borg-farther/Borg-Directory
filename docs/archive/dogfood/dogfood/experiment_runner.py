#!/usr/bin/env python3
"""
Experiment Runner for HARD Benchmark Experiment
Executes the primary experiment with 3 conditions across 10 validated hard tasks.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
HARD_TASKS_DIR = Path("/root/hermes-workspace/borg/dogfood/hard_tasks")
RESULTS_FILE = Path("/root/hermes-workspace/borg/dogfood/experiment_results.json")
TASK_IDS = [
    "HARD-001", "HARD-002", "HARD-003", "HARD-004", "HARD-005",
    "HARD-006", "HARD-007", "HARD-013", "HARD-014", "HARD-015"
]
CONDITIONS = ["A", "B", "C"]  # A=no cache, B=correct trace, C=wrong-task trace
RUNS_PER_CONDITION = 2

# Counterbalancing: odd tasks (1,3,5,7,9) run B first; even tasks (2,4,6,8,10) run A first
COUNTERBALANCE = {
    "HARD-001": ["B", "A", "C"],
    "HARD-002": ["A", "B", "C"],
    "HARD-003": ["B", "A", "C"],
    "HARD-004": ["A", "B", "C"],
    "HARD-005": ["B", "A", "C"],
    "HARD-006": ["A", "B", "C"],
    "HARD-007": ["B", "A", "C"],
    "HARD-013": ["A", "B", "C"],  # Position 8 in our list
    "HARD-014": ["B", "A", "C"],  # Position 9
    "HARD-015": ["A", "B", "C"],  # Position 10
}

# Wrong-task trace rotation mapping (N gets trace from N+2, wrapping within our task set)
WRONG_TRACE_MAP = {
    "HARD-001": "HARD-003",
    "HARD-002": "HARD-004",
    "HARD-003": "HARD-005",
    "HARD-004": "HARD-006",
    "HARD-005": "HARD-007",
    "HARD-006": "HARD-013",
    "HARD-007": "HARD-014",
    "HARD-013": "HARD-015",
    "HARD-014": "HARD-001",
    "HARD-015": "HARD-002",
}


def load_json(filepath: Path) -> dict:
    """Load JSON from file, handling trailing garbage."""
    with open(filepath) as f:
        content = f.read()
    # Handle files with trailing data after valid JSON (e.g., shell wrapper artifacts)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find the last valid closing brace and parse only that portion
        last_brace = content.rfind('}')
        if last_brace > 0:
            clean_content = content[:last_brace+1]
            return json.loads(clean_content)
        raise


def save_json(filepath: Path, data: Any) -> None:
    """Save JSON to file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_results() -> dict:
    """Load existing results or create new structure."""
    if RESULTS_FILE.exists():
        return load_json(RESULTS_FILE)
    return {
        "experiment_start": datetime.now().isoformat(),
        "tasks": {},
        "completed_runs": [],
        "failed_runs": []
    }


def save_results(results: dict) -> None:
    """Save results to file."""
    save_json(RESULTS_FILE, results)


def get_task_dir(task_id: str) -> Path:
    """Get directory for a task."""
    return HARD_TASKS_DIR / task_id


def load_readme(task_id: str) -> str:
    """Load README.md content for a task."""
    readme_path = get_task_dir(task_id) / "README.md"
    if not readme_path.exists():
        return f"Task {task_id}: No README.md found."
    with open(readme_path) as f:
        return f.read()


def load_reasoning_trace(task_id: str) -> str:
    """Load reasoning_trace.json content for a task."""
    trace_path = get_task_dir(task_id) / "reasoning_trace.json"
    if not trace_path.exists():
        return ""
    data = load_json(trace_path)
    return json.dumps(data, indent=2)


def generate_prompt(task_id: str, condition: str) -> str:
    """
    Generate the prompt for a task and condition.
    
    Condition A (no cache): Just the README.md task description
    Condition B (correct trace): README.md + reasoning_trace.json with "MAY use" framing
    Condition C (wrong-task trace): README.md + trace from different task
    """
    readme = load_readme(task_id)
    
    if condition == "A":
        return readme
    
    elif condition == "B":
        # Correct trace - from the same task
        trace = load_reasoning_trace(task_id)
        return f"{readme}\n\nA previous agent worked on a similar problem. Here is their reasoning trace:\n\n{trace}\n\nYou MAY use this information if you find it helpful, but you are not required to follow their approach."
    
    elif condition == "C":
        # Wrong-task trace - from a different task (rotated)
        wrong_task_id = WRONG_TRACE_MAP[task_id]
        trace = load_reasoning_trace(wrong_task_id)
        return f"{readme}\n\nA previous agent worked on a similar problem. Here is their reasoning trace:\n\n{trace}\n\nYou MAY use this information if you find it helpful, but you are not required to follow their approach."
    
    raise ValueError(f"Unknown condition: {condition}")


def copy_task_to_tmp(task_id: str, condition: str, run_number: int) -> Path:
    """Copy task repo to temp directory for experiment run."""
    src_dir = get_task_dir(task_id)
    dst_dir = Path(f"/tmp/exp_{task_id}_{condition}_run{run_number}")
    
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    
    shutil.copytree(src_dir, dst_dir)
    return dst_dir


def run_setup(dst_dir: Path) -> bool:
    """Run setup.sh in the destination directory."""
    setup_script = dst_dir / "setup.sh"
    if not setup_script.exists():
        print(f"  WARNING: No setup.sh found in {dst_dir}")
        return False
    
    result = subprocess.run(
        ["bash", str(setup_script)],
        cwd=dst_dir,
        capture_output=True,
        text=True,
        timeout=120
    )
    return result.returncode == 0


def verify_check_fails(dst_dir: Path) -> bool:
    """Verify that check.sh initially fails (starting state is broken)."""
    check_script = dst_dir / "check.sh"
    if not check_script.exists():
        print(f"  WARNING: No check.sh found in {dst_dir}")
        return False
    
    result = subprocess.run(
        ["bash", str(check_script)],
        cwd=dst_dir,
        capture_output=True,
        text=True,
        timeout=120
    )
    # We expect this to fail (returncode != 0) for a valid starting state
    return result.returncode != 0


def run_check(dst_dir: Path) -> tuple[bool, str]:
    """Run check.sh and return success status and output."""
    check_script = dst_dir / "check.sh"
    if not check_script.exists():
        return False, "No check.sh found"
    
    result = subprocess.run(
        ["bash", str(check_script)],
        cwd=dst_dir,
        capture_output=True,
        text=True,
        timeout=120
    )
    return result.returncode == 0, result.stdout + result.stderr


def get_delegate_task_params(task_id: str, condition: str, prompt: str) -> dict:
    """
    Return the EXACT delegate_task parameters for the orchestrator.
    
    These are the parameters that would be passed to delegate_task.
    """
    return {
        "goal": f"Fix the bug in task {task_id}. Your task is described in the prompt below.",
        "context": prompt,
        "toolsets": ["file_reader", "code_writer", "bash_runner"],
        "max_iterations": 50
    }


def run_single_task(task_id: str, verbose: bool = False) -> list[dict]:
    """Run all 3 conditions for a single task."""
    results = []
    order = COUNTERBALANCE[task_id]
    
    print(f"\n{'='*60}")
    print(f"Running task: {task_id}")
    print(f"Condition order: {order}")
    print(f"{'='*60}")
    
    for run_num in range(1, RUNS_PER_CONDITION + 1):
        for cond in order:
            run_id = f"{task_id}_{cond}_run{run_num}"
            print(f"\n--- {run_id} ---")
            
            # Generate prompt
            prompt = generate_prompt(task_id, cond)
            
            if verbose:
                print(f"\nPROMPT:\n{prompt[:500]}..." if len(prompt) > 500 else f"\nPROMPT:\n{prompt}")
            
            # Copy task to temp
            dst_dir = copy_task_to_tmp(task_id, cond, run_num)
            print(f"  Copied to: {dst_dir}")
            
            # Run setup
            setup_ok = run_setup(dst_dir)
            print(f"  Setup: {'OK' if setup_ok else 'FAILED'}")
            
            # Verify starting state is broken
            start_broken = verify_check_fails(dst_dir)
            print(f"  Starting state broken: {start_broken}")
            
            # Get delegate_task params (for reference/print)
            delegate_params = get_delegate_task_params(task_id, cond, prompt)
            print(f"\n  DELEGATE_TASK PARAMETERS:")
            print(f"    goal: {delegate_params['goal']}")
            print(f"    context: (length={len(delegate_params['context'])})")
            print(f"    toolsets: {delegate_params['toolsets']}")
            print(f"    max_iterations: {delegate_params['max_iterations']}")
            
            # NOTE: The actual agent execution happens externally via delegate_task
            # The runner prints the exact parameters the orchestrator should use
            
            # For dry-run / status, we don't actually execute
            # After external execution, results would be recorded here
            
            results.append({
                "task_id": task_id,
                "condition": cond,
                "run_number": run_num,
                "run_id": run_id,
                "prompt_length": len(prompt),
                "delegate_params": delegate_params,
                "setup_ok": setup_ok,
                "start_broken": start_broken,
                "success": None,  # Set after external execution
                "duration_seconds": None,  # Set after external execution
                "tokens": None,  # Set from metadata after external execution
            })
            
            # Cleanup
            if dst_dir.exists():
                shutil.rmtree(dst_dir)
    
    return results


def show_status() -> None:
    """Show current experiment progress."""
    results = load_results()
    completed = results.get("completed_runs", [])
    failed = results.get("failed_runs", [])
    
    print(f"\n{'='*60}")
    print("EXPERIMENT STATUS")
    print(f"{'='*60}")
    print(f"Total tasks: {len(TASK_IDS)}")
    print(f"Runs per condition: {RUNS_PER_CONDITION}")
    print(f"Conditions per task: {len(CONDITIONS)}")
    print(f"Total runs: {len(TASK_IDS) * len(CONDITIONS) * RUNS_PER_CONDITION}")
    print(f"\nCompleted runs: {len(completed)}")
    print(f"Failed runs: {len(failed)}")
    
    # Per-task status
    print(f"\nPer-task status:")
    for task_id in TASK_IDS:
        task_results = [r for r in completed if r.get("task_id") == task_id]
        status = f"{len(task_results)}/{len(CONDITIONS) * RUNS_PER_CONDITION}"
        print(f"  {task_id}: {status} runs completed")


def dry_run() -> None:
    """Print all prompts and execution order without running."""
    print("\n" + "="*60)
    print("DRY RUN - All Prompts and Execution Order")
    print("="*60)
    
    for task_id in TASK_IDS:
        order = COUNTERBALANCE[task_id]
        print(f"\n{'='*60}")
        print(f"TASK: {task_id}")
        print(f"Condition order: {order}")
        print(f"{'='*60}")
        
        for run_num in range(1, RUNS_PER_CONDITION + 1):
            for cond in order:
                print(f"\n--- {task_id} | Condition {cond} | Run {run_num} ---")
                
                # Show which trace would be used
                if cond == "A":
                    print(f"Trace: NONE (no cache)")
                elif cond == "B":
                    print(f"Trace: {task_id} (correct task)")
                elif cond == "C":
                    wrong_task = WRONG_TRACE_MAP[task_id]
                    print(f"Trace: {wrong_task} (wrong-task trace)")
                
                # Generate and show prompt
                prompt = generate_prompt(task_id, cond)
                print(f"\nPROMPT (first 800 chars):\n{prompt[:800]}")
                if len(prompt) > 800:
                    print(f"\n... [{len(prompt) - 800} more characters]")
                
                # Show delegate params
                delegate_params = get_delegate_task_params(task_id, cond, prompt)
                print(f"\nDelegate params:")
                print(f"  goal: {delegate_params['goal']}")
                print(f"  context length: {len(delegate_params['context'])} chars")
                print(f"  toolsets: {delegate_params['toolsets']}")
                print(f"  max_iterations: {delegate_params['max_iterations']}")
                
                # Temp directory that would be used
                print(f"  temp dir: /tmp/exp_{task_id}_{cond}_run{run_num}/")


def run_all() -> None:
    """Run the complete experiment."""
    print("\n" + "="*60)
    print("STARTING FULL EXPERIMENT")
    print("="*60)
    print(f"Tasks: {TASK_IDS}")
    print(f"Total runs: {len(TASK_IDS) * len(CONDITIONS) * RUNS_PER_CONDITION}")
    
    all_results = []
    start_time = datetime.now()
    
    for task_id in TASK_IDS:
        task_results = run_single_task(task_id, verbose=False)
        all_results.extend(task_results)
        
        # Save intermediate results
        results = load_results()
        results["completed_runs"].extend([{
            "task_id": r["task_id"],
            "condition": r["condition"],
            "run_number": r["run_number"],
            "run_id": r["run_id"],
            "prompt_length": r["prompt_length"]
        } for r in task_results])
        save_results(results)
        
        print(f"\nCompleted {task_id}. Total runs so far: {len(results['completed_runs'])}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("EXPERIMENT COMPLETE")
    print(f"Total duration: {duration:.2f} seconds")
    print(f"Note: This shows the runner setup. Actual agent execution")
    print(f"      happens externally via delegate_task.")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Experiment Runner for HARD Benchmark"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Print all prompts and order without running"
    )
    group.add_argument(
        "--task",
        type=str,
        metavar="TASK-ID",
        help="Run single task (e.g., HARD-001), all 3 conditions"
    )
    group.add_argument(
        "--run-all",
        action="store_true",
        help="Run complete experiment"
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Show experiment progress"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        dry_run()
    elif args.task:
        if args.task not in TASK_IDS:
            print(f"Error: Unknown task '{args.task}'")
            print(f"Valid tasks: {TASK_IDS}")
            sys.exit(1)
        results = run_single_task(args.task, verbose=args.verbose)
        # Save results after task completion
        existing = load_results()
        existing["completed_runs"].extend([{
            "task_id": r["task_id"],
            "condition": r["condition"],
            "run_number": r["run_number"],
            "run_id": r["run_id"],
            "prompt_length": r["prompt_length"]
        } for r in results])
        save_results(existing)
        print(f"\nResults saved for {args.task}")
    elif args.run_all:
        run_all()
    elif args.status:
        show_status()


if __name__ == "__main__":
    main()
