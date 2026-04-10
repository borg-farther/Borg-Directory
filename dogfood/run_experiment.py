#!/usr/bin/env python3
"""
Borg A/B Experiment Runner

Orchestrates the controlled experiment comparing AI agent performance
with and without Borg reasoning cache tool.

Usage:
    python3 run_experiment.py                    # Run all tasks
    python3 run_experiment.py --dry-run         # Show what would run
    python3 run_experiment.py --verify          # Verify all repos
    python3 run_experiment.py --run-task DEBUG-001  # Run single task
    python3 run_experiment.py --list-tasks        # List all tasks
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
from typing import Any, Dict, List, Optional, Tuple

# Constants
EXPERIMENT_ID = "borg-ab-001"
TASKS_FILE = "/root/hermes-workspace/borg/dogfood/experiment_tasks.json"
RESULTS_FILE = "/root/hermes-workspace/borg/dogfood/results.json"
REPOS_BASE = "/root/hermes-workspace/borg/dogfood/experiment_repos"
WORK_DIR = "/tmp/experiment"
TIMEOUT_SECONDS = 1800  # 30 minutes

# Prompt templates
CONTROL_PROMPT_TEMPLATE = """You are working on a coding task. Use your standard tools
(terminal, file read/write, search) to complete it.

{prompt}
"""

TREATMENT_PROMPT_TEMPLATE = """You are working on a coding task. You have access to Borg,
a reasoning cache with proven approaches. Before starting,
call borg_search with a description of your task to get
structured guidance. Use your standard tools plus borg
tools (borg_search, borg_observe, borg_suggest) to complete it.

{prompt}
"""


class ExperimentError(Exception):
    """Custom exception for experiment errors."""
    pass


def load_tasks() -> List[Dict[str, Any]]:
    """Load tasks from experiment_tasks.json."""
    with open(TASKS_FILE, 'r') as f:
        data = json.load(f)
    return data.get('tasks', [])


def get_task_repo_path(task_id: str) -> Path:
    """Get the path to a task's repository."""
    return Path(REPOS_BASE) / task_id


def get_counterbalance_order(task_id: str) -> Tuple[str, str]:
    """
    Determine counterbalance order using deterministic hash of task_id.
    Returns (first_condition, second_condition) as ('control', 'treatment') or vice versa.
    """
    hash_input = f"{task_id}-{EXPERIMENT_ID}".encode()
    hash_value = hashlib.sha256(hash_input).hexdigest()
    # Use first byte to decide: even = control first, odd = treatment first
    first_byte = int(hash_value[:2], 16)
    if first_byte % 2 == 0:
        return ('control', 'treatment')
    else:
        return ('treatment', 'control')


def generate_prompt(task: Dict[str, Any], condition: str) -> str:
    """Generate the prompt for a given task and condition."""
    base_prompt = task.get('prompt', '')
    
    if condition == 'control':
        return CONTROL_PROMPT_TEMPLATE.format(prompt=base_prompt)
    else:  # treatment
        return TREATMENT_PROMPT_TEMPLATE.format(prompt=base_prompt)


def copy_repo_to_tmp(task_id: str) -> Path:
    """
    Copy task repository to /tmp for experiment.
    Returns the path to the copied repo.
    """
    src = get_task_repo_path(task_id)
    dst = Path(WORK_DIR) / task_id
    
    if dst.exists():
        shutil.rmtree(dst)
    
    if not src.exists():
        raise ExperimentError(f"Task repo not found: {src}")
    
    shutil.copytree(src, dst)
    return dst


def reset_repo(repo_path: Path) -> None:
    """Reset repo to clean state using git."""
    if not (repo_path / '.git').exists():
        return  # Not a git repo, skip reset
    
    try:
        subprocess.run(
            ['git', 'checkout', '.'],
            cwd=repo_path,
            capture_output=True,
            timeout=30
        )
        subprocess.run(
            ['git', 'clean', '-fd'],
            cwd=repo_path,
            capture_output=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        print(f"Warning: Git reset timed out for {repo_path}")
    except Exception as e:
        print(f"Warning: Git reset failed for {repo_path}: {e}")


def run_setup(repo_path: Path) -> bool:
    """
    Run setup.sh in the repository.
    Returns True if setup succeeds.
    """
    setup_script = repo_path / 'setup.sh'
    if not setup_script.exists():
        print(f"Warning: No setup.sh found in {repo_path}")
        return True  # No setup needed
    
    try:
        result = subprocess.run(
            ['bash', str(setup_script)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout for setup
        )
        if result.returncode != 0:
            print(f"Setup failed: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"Setup timed out for {repo_path}")
        return False
    except Exception as e:
        print(f"Setup error: {e}")
        return False


def run_check(repo_path: Path) -> Tuple[bool, str]:
    """
    Run check.sh to verify task completion.
    Returns (success, output).
    """
    check_script = repo_path / 'check.sh'
    if not check_script.exists():
        return False, "No check.sh found"
    
    try:
        result = subprocess.run(
            ['bash', str(check_script)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Check timed out"
    except Exception as e:
        return False, str(e)


def verify_starting_state(repo_path: Path) -> Tuple[bool, str]:
    """
    Verify that check.sh FAILS in the starting state (before agent works).
    Returns (is_correct, message).
    """
    success, output = run_check(repo_path)
    if success:
        return False, "Task already passes in starting state - should fail"
    return True, "Starting state verified (check.sh fails)"


def prepare_task(task_id: str, condition: str) -> Dict[str, Any]:
    """
    Prepare a task for running: copy repo, run setup, verify starting state.
    Returns preparation result dict.
    """
    result = {
        'task_id': task_id,
        'condition': condition,
        'success': False,
        'tokens_used': 0,
        'time_seconds': 0.0,
        'tool_calls': 0,
        'borg_searches': 0,
        'error': None,
        'prepared_at': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Copy repo to /tmp
        repo_path = copy_repo_to_tmp(task_id)
        result['repo_path'] = str(repo_path)
        
        # Run setup
        if not run_setup(repo_path):
            result['error'] = 'Setup failed'
            return result
        
        # Verify starting state fails
        is_correct, msg = verify_starting_state(repo_path)
        if not is_correct:
            result['error'] = f"Starting state incorrect: {msg}"
            return result
        
        result['prepared'] = True
        result['prompt'] = None  # Will be set by caller
        
    except ExperimentError as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = f"Preparation error: {e}"
    
    return result


def simulate_agent_run(task: Dict[str, Any], condition: str, 
                       prep_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate an agent run for a task.
    
    Since we can't actually spawn AI agents, this function:
    1. Generates the exact prompt that would be used
    2. Simulates measurement metrics
    3. Provides guidance on how to run manually
    
    In a real implementation, this would spawn an AI agent process.
    """
    result = {
        'task_id': task['id'],
        'condition': condition,
        'order': 1 if condition == 'control' else 2,
        'success': False,
        'tokens_used': 0,
        'time_seconds': 0.0,
        'tool_calls': 0,
        'borg_searches': 0 if condition == 'control' else -1,  # Unknown until actual run
        'error': None,
        'prompt': generate_prompt(task, condition),
        'repo_path': prep_result.get('repo_path'),
        'manual_command': f"cd {prep_result.get('repo_path', '/tmp/experiment/' + task['id'])} && bash check.sh"
    }
    
    return result


def record_result(result: Dict[str, Any], results_path: Path = None) -> None:
    """Record a result to results.json."""
    if results_path is None:
        results_path = Path(RESULTS_FILE)
    
    # Load existing results or create new structure
    if results_path.exists():
        with open(results_path, 'r') as f:
            data = json.load(f)
    else:
        data = {
            'experiment_id': EXPERIMENT_ID,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'results': []
        }
    
    # Add new result
    data['results'].append(result)
    
    # Save
    with open(results_path, 'w') as f:
        json.dump(data, f, indent=2)


def dry_run_all(tasks: List[Dict[str, Any]]) -> None:
    """Show what would run without executing."""
    print("=" * 70)
    print("DRY RUN - No actual execution")
    print("=" * 70)
    print()
    
    for task in tasks:
        task_id = task['id']
        repo_path = get_task_repo_path(task_id)
        first_cond, second_cond = get_counterbalance_order(task_id)
        
        print(f"Task: {task_id} ({task.get('category', 'unknown')})")
        print(f"  Repo: {repo_path}")
        print(f"  Order: {first_cond} → {second_cond}")
        print(f"  Condition 1 ({first_cond}):")
        print(f"    Prompt: {task.get('prompt', '')[:80]}...")
        print(f"    Command: cd {WORK_DIR}/{task_id} && <agent_run> && bash check.sh")
        print(f"  Condition 2 ({second_cond}):")
        print(f"    Prompt: {task.get('prompt', '')[:80]}...")
        print(f"    + borg_search instruction")
        print()
    
    print(f"Total: {len(tasks)} tasks × 2 conditions = {len(tasks) * 2} runs")


def verify_all_repos(tasks: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
    """
    Verify all task repositories.
    Tests: setup.sh works, check.sh fails in starting state.
    Returns (passed, failed, error_messages).
    """
    passed = 0
    failed = 0
    errors = []
    
    print("Verifying all task repositories...")
    print("=" * 70)
    
    for task in tasks:
        task_id = task['id']
        repo_path = get_task_repo_path(task_id)
        
        print(f"\n[{task_id}] ", end="", flush=True)
        
        if not repo_path.exists():
            print(f"FAIL - Repo not found: {repo_path}")
            failed += 1
            errors.append(f"{task_id}: Repo not found at {repo_path}")
            continue
        
        # Check required files
        setup_script = repo_path / 'setup.sh'
        check_script = repo_path / 'check.sh'
        
        if not setup_script.exists():
            print(f"FAIL - setup.sh missing")
            failed += 1
            errors.append(f"{task_id}: setup.sh missing")
            continue
        
        if not check_script.exists():
            print(f"FAIL - check.sh missing")
            failed += 1
            errors.append(f"{task_id}: check.sh missing")
            continue
        
        # Test 1: Run setup.sh
        print(f"\n  Running setup.sh... ", end="", flush=True)
        try:
            setup_result = subprocess.run(
                ['bash', str(setup_script)],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            if setup_result.returncode != 0:
                print(f"FAIL (exit {setup_result.returncode})")
                failed += 1
                errors.append(f"{task_id}: setup.sh failed with exit {setup_result.returncode}")
                errors.append(f"  stderr: {setup_result.stderr[:200]}")
                continue
            print("OK")
        except subprocess.TimeoutExpired:
            print(f"FAIL - Timeout (>5 min)")
            failed += 1
            errors.append(f"{task_id}: setup.sh timed out")
            continue
        except Exception as e:
            print(f"FAIL - {e}")
            failed += 1
            errors.append(f"{task_id}: setup.sh error: {e}")
            continue
        
        # Test 2: Verify check.sh fails in starting state
        print(f"  Verifying check.sh fails... ", end="", flush=True)
        try:
            check_result = subprocess.run(
                ['bash', str(check_script)],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            if check_result.returncode == 0:
                print(f"FAIL (check.sh passes in starting state - should fail)")
                failed += 1
                errors.append(f"{task_id}: check.sh passes in starting state (should fail)")
                # Reset the repo state for next test
                reset_repo(repo_path)
                continue
            print("OK (correctly fails)")
        except subprocess.TimeoutExpired:
            print(f"FAIL - Timeout")
            failed += 1
            errors.append(f"{task_id}: check.sh timed out")
            continue
        except Exception as e:
            print(f"FAIL - {e}")
            failed += 1
            errors.append(f"{task_id}: check.sh error: {e}")
            continue
        
        # Reset repo to clean state after verification
        reset_repo(repo_path)
        passed += 1
        print(f"  ✓ VERIFIED")
    
    print("\n" + "=" * 70)
    print(f"Verification complete: {passed} passed, {failed} failed")
    
    return passed, failed, errors


def run_single_task(task_id: str, tasks: List[Dict[str, Any]]) -> None:
    """Run a single task manually with guidance."""
    task = None
    for t in tasks:
        if t['id'] == task_id:
            task = t
            break
    
    if task is None:
        print(f"Error: Task {task_id} not found")
        sys.exit(1)
    
    repo_path = get_task_repo_path(task_id)
    
    if not repo_path.exists():
        print(f"Error: Repo not found: {repo_path}")
        sys.exit(1)
    
    print("=" * 70)
    print(f"SINGLE TASK RUN: {task_id}")
    print("=" * 70)
    print()
    print(f"Category: {task.get('category')}")
    print(f"Difficulty: {task.get('difficulty')}")
    print(f"Expected time: {task.get('expected_time_minutes')} minutes")
    print(f"Repo path: {repo_path}")
    print(f"Borg pack: {task.get('borg_pack', 'none (control task)')}")
    print()
    
    first_cond, second_cond = get_counterbalance_order(task_id)
    print(f"Counterbalance order: {first_cond} → {second_cond}")
    print()
    
    # Show control prompt
    print("-" * 70)
    print("CONTROL PROMPT:")
    print("-" * 70)
    print(generate_prompt(task, 'control'))
    print()
    
    # Show treatment prompt
    print("-" * 70)
    print("TREATMENT PROMPT:")
    print("-" * 70)
    print(generate_prompt(task, 'treatment'))
    print()
    
    # Show pass condition
    print("-" * 70)
    print("PASS CONDITION (check.sh):")
    print("-" * 70)
    print(task.get('pass_condition', 'Not specified'))
    print()
    
    # Prepare task and show commands
    print("-" * 70)
    print("TO RUN MANUALLY:")
    print("-" * 70)
    work_path = Path(WORK_DIR) / task_id
    
    print(f"""
# 1. Copy repo to /tmp:
mkdir -p {WORK_DIR}
rm -rf {work_path}
cp -r {repo_path} {work_path}

# 2. Run setup:
cd {work_path} && bash setup.sh

# 3. For CONTROL run:
# Give agent the CONTROL PROMPT above
# Agent works...
# Then verify: cd {work_path} && bash check.sh

# 4. Reset repo:
cd {work_path} && git checkout . && git clean -fd

# 5. For TREATMENT run:
# Give agent the TREATMENT PROMPT above
# Agent works...
# Then verify: cd {work_path} && bash check.sh

# 6. Record results:
python3 record_result.py {task_id} control <success> <tokens> <time_seconds> <tool_calls>
python3 record_result.py {task_id} treatment <success> <tokens> <time_seconds> <tool_calls>
""")


def list_tasks(tasks: List[Dict[str, Any]]) -> None:
    """List all tasks in a table format."""
    print(f"{'ID':<15} {'Category':<15} {'Difficulty':<10} {'Borg Pack':<25} {'Expected (min)'}")
    print("-" * 90)
    
    for task in tasks:
        task_id = task['id']
        category = task.get('category', 'unknown')
        difficulty = task.get('difficulty', '?')
        borg_pack = task.get('borg_pack', '-')
        expected = task.get('expected_time_minutes', '?')
        borg_pack = task.get('borg_pack', '-') or '-'
        print(f"{task_id:<15} {category:<15} {difficulty:<10} {borg_pack:<25} {expected}")


def main():
    parser = argparse.ArgumentParser(
        description='Borg A/B Experiment Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_experiment.py --dry-run           Show what would run
  python3 run_experiment.py --verify            Verify all repos
  python3 run_experiment.py --list-tasks        List all tasks
  python3 run_experiment.py --run-task DEBUG-001  Run single task manually
        """
    )
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would run without executing')
    parser.add_argument('--verify', action='store_true',
                       help='Verify all task repositories')
    parser.add_argument('--list-tasks', action='store_true',
                       help='List all available tasks')
    parser.add_argument('--run-task', type=str, metavar='TASK_ID',
                       help='Show details for running a single task')
    parser.add_argument('--results-file', type=str, default=RESULTS_FILE,
                       help=f'Path to results file (default: {RESULTS_FILE})')
    
    args = parser.parse_args()
    
    # Load tasks
    try:
        tasks = load_tasks()
    except FileNotFoundError:
        print(f"Error: Tasks file not found: {TASKS_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in tasks file: {e}")
        sys.exit(1)
    
    # Handle commands
    if args.dry_run:
        dry_run_all(tasks)
        return
    
    if args.verify:
        passed, failed, errors = verify_all_repos(tasks)
        if failed > 0:
            print("\nErrors:")
            for err in errors:
                print(f"  - {err}")
        sys.exit(1 if failed > 0 else 0)
    
    if args.list_tasks:
        list_tasks(tasks)
        return
    
    if args.run_task:
        run_single_task(args.run_task, tasks)
        return
    
    # Default: show help
    parser.print_help()
    print("\nNote: Use --dry-run, --verify, --list-tasks, or --run-task to do something.")


if __name__ == '__main__':
    main()
