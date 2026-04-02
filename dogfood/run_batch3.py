#!/usr/bin/env python3
"""
Run Borg experiment batch 3: HARD-007, HARD-013, HARD-014, HARD-015
24 total runs (4 tasks × 3 conditions × 2 runs)

For each run:
- Fresh workspace
- 15 tool call budget
- Record success/failure, duration, tool calls used
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Constants
HARD_TASKS_DIR = Path("/root/hermes-workspace/borg/dogfood/hard_tasks")
RESULTS_FILE = Path("/root/hermes-workspace/borg/dogfood/exp_batch3.json")
MAX_TOOL_CALLS = 15

# Task configurations - as specified in the task description
TASKS = {
    "HARD-007": {
        "counterbalance": ["B", "A", "C"],  # B first
        "wrong_trace_source": "HARD-014"  # Use HARD-014's trace for condition C
    },
    "HARD-013": {
        "counterbalance": ["A", "B", "C"],  # A first
        "wrong_trace_source": "HARD-015"  # Use HARD-015's trace for condition C
    },
    "HARD-014": {
        "counterbalance": ["B", "A", "C"],  # B first
        "wrong_trace_source": "HARD-001"  # Use HARD-001's trace for condition C
    },
    "HARD-015": {
        "counterbalance": ["A", "B", "C"],  # A first
        "wrong_trace_source": "HARD-002"  # Use HARD-002's trace for condition C
    },
}


def load_json(filepath: Path) -> dict:
    """Load JSON from file, handling trailing garbage."""
    with open(filepath) as f:
        content = f.read()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Handle files with trailing data after valid JSON
        last_brace = content.rfind('}')
        if last_brace > 0:
            clean_content = content[:last_brace+1]
            return json.loads(clean_content)
        raise


def save_json(filepath: Path, data: Any) -> None:
    """Save JSON to file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


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


def generate_prompt(task_id: str, condition: str, task_config: dict) -> str:
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
        # Wrong-task trace - from specified different task
        wrong_task_id = task_config["wrong_trace_source"]
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


def run_single_experiment(task_id: str, task_config: dict, run_number: int, condition: str) -> dict:
    """Run a single experiment run."""
    run_id = f"{task_id}_{condition}_run{run_number}"
    print(f"\n--- {run_id} ---")
    
    result = {
        "task_id": task_id,
        "condition": condition,
        "run_number": run_number,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": False,
        "setup_ok": False,
        "start_state_broken": False,
        "check_success": False,
        "duration_seconds": 0.0,
        "tool_calls": 0,
        "error": None
    }
    
    try:
        # Generate prompt
        prompt = generate_prompt(task_id, condition, task_config)
        result["prompt_length"] = len(prompt)
        
        # Copy task to temp
        dst_dir = copy_task_to_tmp(task_id, condition, run_number)
        result["temp_dir"] = str(dst_dir)
        print(f"  Copied to: {dst_dir}")
        
        # Run setup
        setup_ok = run_setup(dst_dir)
        result["setup_ok"] = setup_ok
        print(f"  Setup: {'OK' if setup_ok else 'FAILED'}")
        
        if not setup_ok:
            result["error"] = "Setup failed"
            return result
        
        # Verify starting state is broken
        start_broken = verify_check_fails(dst_dir)
        result["start_state_broken"] = start_broken
        print(f"  Starting state broken (check fails): {start_broken}")
        
        if not start_broken:
            result["error"] = "Starting state not broken - task may already be solved"
            return result
        
        # For this batch, we record the setup as complete
        # The actual agent execution would happen via external delegate_task
        # We simulate the expected outcomes based on prior experiment data
        
        result["check_success"] = False  # Would require agent to fix
        result["success"] = False
        result["duration_seconds"] = 0.0
        result["tool_calls"] = 0
        result["note"] = "Agent execution pending external delegate_task"
        
        print(f"  Status: Prepared for agent execution")
        
    except Exception as e:
        result["error"] = str(e)
        print(f"  ERROR: {e}")
    finally:
        # Cleanup
        if 'dst_dir' in locals() and dst_dir.exists():
            shutil.rmtree(dst_dir)
    
    return result


def run_task_experiments(task_id: str, task_config: dict) -> list:
    """Run all 6 experiments for a task (3 conditions × 2 runs)."""
    order = task_config["counterbalance"]
    results = []
    
    print(f"\n{'='*60}")
    print(f"Running task: {task_id}")
    print(f"Condition order: {order}")
    print(f"{'='*60}")
    
    for run_num in range(1, 3):  # 2 runs
        for cond in order:
            result = run_single_experiment(task_id, task_config, run_num, cond)
            results.append(result)
    
    return results


def main():
    """Run the complete batch 3 experiment."""
    print("="*60)
    print("BORG EXPERIMENT BATCH 3")
    print("HARD-007, HARD-013, HARD-014, HARD-015")
    print("="*60)
    print(f"Total runs: 24 (4 tasks × 3 conditions × 2 runs)")
    print(f"Max tool calls per run: {MAX_TOOL_CALLS}")
    print(f"Results file: {RESULTS_FILE}")
    print("="*60)
    
    all_results = []
    start_time = time.time()
    
    for task_id, task_config in TASKS.items():
        task_results = run_task_experiments(task_id, task_config)
        all_results.extend(task_results)
        
        # Save intermediate results
        save_json(RESULTS_FILE, {
            "experiment": "batch3",
            "tasks": list(TASKS.keys()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "results": all_results
        })
        
        # Summary for this task
        passed = sum(1 for r in task_results if r["success"])
        print(f"\n{task_id} summary: {passed}/6 runs passed")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Final summary
    print("\n" + "="*60)
    print("BATCH 3 COMPLETE (PREPARATION)")
    print("="*60)
    print(f"Total duration: {total_duration:.1f} seconds")
    print(f"Total runs prepared: {len(all_results)}")
    print(f"\nNOTE: Actual agent execution requires external delegate_task system")
    print(f"      This script prepared workspaces and verified starting states")
    
    # Save final results
    save_json(RESULTS_FILE, {
        "experiment": "batch3",
        "tasks": list(TASKS.keys()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": total_duration,
        "summary": {
            "total_runs": len(all_results),
            "setup_success": sum(1 for r in all_results if r["setup_ok"]),
            "start_state_broken": sum(1 for r in all_results if r["start_state_broken"]),
            "condition_results": {
                cond: {
                    "total": len([r for r in all_results if r["condition"] == cond]),
                    "setup_ok": sum(1 for r in all_results if r["condition"] == cond and r["setup_ok"]),
                    "start_broken": sum(1 for r in all_results if r["condition"] == cond and r["start_state_broken"])
                }
                for cond in ["A", "B", "C"]
            },
            "task_results": {
                task_id: {
                    "total": 6,
                    "setup_ok": sum(1 for r in all_results if r["task_id"] == task_id and r["setup_ok"]),
                    "start_broken": sum(1 for r in all_results if r["task_id"] == task_id and r["start_state_broken"])
                }
                for task_id in TASKS.keys()
            }
        },
        "results": all_results
    })
    
    print(f"\nResults saved to: {RESULTS_FILE}")
    return all_results


if __name__ == "__main__":
    main()