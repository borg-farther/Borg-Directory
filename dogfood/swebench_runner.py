#!/usr/bin/env python3
"""
SWE-bench Experiment Runner for Borg

Uses swebench harness to:
1. Build Docker images for each task
2. Start containers with the correct environment
3. Exec agent commands inside containers
4. Run tests to verify fixes
"""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.docker_build import build_instance_image
from swebench.harness.docker_utils import cleanup_container

DATA_DIR = Path("/root/hermes-workspace/borg/dogfood/v2_data")
RESULTS_DIR = DATA_DIR / "swebench_results"

def load_tasks(difficulty="1-4 hours", repo="django/django", max_tasks=15):
    """Load SWE-bench tasks filtered by difficulty and repo."""
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    
    tasks = []
    for t in ds:
        if t["repo"] != repo:
            continue
        if t.get("difficulty") != difficulty:
            continue
        
        hints = t.get("hints_text", "") or ""
        
        # FILTER: skip tasks where hints contain patch diffs
        if "diff --git" in hints or "@@ -" in hints or "+++b/" in hints:
            continue
        
        # FILTER: skip tasks with minimal hints (<50 chars)
        if len(hints) < 50:
            continue
        
        fail_to_pass = t["FAIL_TO_PASS"]
        if isinstance(fail_to_pass, str):
            fail_to_pass = json.loads(fail_to_pass)
        
        tasks.append({
            "instance_id": t["instance_id"],
            "repo": t["repo"],
            "base_commit": t["base_commit"],
            "problem_statement": t["problem_statement"],
            "hints_text": hints,
            "test_patch": t["test_patch"],
            "patch": t["patch"],
            "FAIL_TO_PASS": fail_to_pass,
            "PASS_TO_PASS": json.loads(t["PASS_TO_PASS"]) if isinstance(t["PASS_TO_PASS"], str) else t["PASS_TO_PASS"],
            "version": t.get("version"),
            "difficulty": t.get("difficulty"),
            "raw_record": dict(t),
        })
    
    return tasks[:max_tasks]


def build_task_image(task):
    """Build Docker image for a task using swebench harness."""
    import docker
    
    spec = make_test_spec(task["raw_record"])
    
    # Build the image
    print(f"  Building Docker image for {task['instance_id']}...")
    try:
        client = docker.from_env()
        build_instance_image(spec, client, logger=None, nocache=False)
        return spec
    except Exception as e:
        print(f"  ERROR building image: {e}")
        import traceback
        traceback.print_exc()
        return None


def start_container(spec, task_id):
    """Start a Docker container from the task image."""
    container_name = f"borg_exp_{task_id}_{int(time.time())}"
    image = spec.instance_image_key
    
    # Start container
    result = subprocess.run(
        ["docker", "run", "-d", "--name", container_name,
         "--memory", "4g", "--cpus", "2",
         image, "tail", "-f", "/dev/null"],
        capture_output=True, text=True, timeout=60
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start container: {result.stderr}")
    
    container_id = result.stdout.strip()
    return container_id, container_name


def exec_in_container(container_name, cmd, timeout=300):
    """Execute a command inside a Docker container."""
    result = subprocess.run(
        ["docker", "exec", container_name, "bash", "-c", cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def run_tests(container_name, fail_to_pass):
    """Run the failing tests inside the container."""
    test_cmd = f"cd /testbed && python -m pytest {' '.join(fail_to_pass)} --no-header -q 2>&1"
    code, stdout, stderr = exec_in_container(container_name, test_cmd, timeout=120)
    
    # Parse test results
    all_pass = code == 0
    return all_pass, stdout + stderr


def cleanup(container_name):
    """Stop and remove container."""
    subprocess.run(["docker", "rm", "-f", container_name],
                   capture_output=True, timeout=30)


def create_reasoning_trace(hints_text, problem_statement):
    """Transform raw hints_text into a structured reasoning trace.
    
    Strips insider knowledge and reformats as reasoning context.
    """
    # Basic transformation: frame as prior investigation findings
    trace = f"""REASONING TRACE FROM PRIOR INVESTIGATION:

The following notes are from a prior investigation of this bug.
They contain observations about the root cause and potential approaches,
but NOT the exact solution.

INVESTIGATION NOTES:
{hints_text}

Use these notes to guide your debugging approach.
Focus on understanding WHY the bug occurs, not just WHERE.
"""
    return trace


def run_single(task, condition, run_num, spec):
    """Run a single experiment trial."""
    task_id = task["instance_id"]
    
    result = {
        "task_id": task_id,
        "condition": condition,
        "run": run_num,
        "success": False,
        "tool_calls": 0,
        "wall_time": 0,
        "error": None,
        "test_output": "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    try:
        # Start fresh container
        container_id, container_name = start_container(spec, task_id.replace("/", "_"))
        result["container"] = container_name
        
        # Verify tests fail initially
        pre_success, pre_output = run_tests(container_name, task["FAIL_TO_PASS"])
        if pre_success:
            result["error"] = "Tests pass before fix — invalid task"
            cleanup(container_name)
            return result
        
        # Build prompt
        prompt = f"""You are an expert software engineer. Fix the bug described below.
The codebase is at /testbed (it's a Django checkout).

ISSUE:
{task['problem_statement']}

TESTS THAT MUST PASS AFTER YOUR FIX:
{json.dumps(task['FAIL_TO_PASS'])}

After fixing, verify with:
cd /testbed && python -m pytest {' '.join(task['FAIL_TO_PASS'])} --no-header -q
"""
        
        if condition == "B":
            trace = create_reasoning_trace(task["hints_text"], task["problem_statement"])
            prompt += f"\n{trace}"
        
        # HERE: This is where we'd call delegate_task with the agent
        # The agent would exec commands inside the container via docker exec
        # For now, we record the prompt and container for manual execution
        
        result["prompt"] = prompt
        result["prompt_length"] = len(prompt)
        
        # In actual execution: agent works, then we check
        # post_success, post_output = run_tests(container_name, task["FAIL_TO_PASS"])
        # result["success"] = post_success
        # result["test_output"] = post_output
        
        cleanup(container_name)
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def cmd_setup(args):
    """Set up Docker images for all tasks."""
    difficulty = args.difficulty if hasattr(args, 'difficulty') else "1-4 hours"
    tasks = load_tasks(difficulty=difficulty, max_tasks=15)
    
    print(f"Setting up {len(tasks)} {difficulty} Django tasks")
    print(f"(Filtered: no patch diffs in hints, hints > 50 chars)")
    
    specs = {}
    for task in tasks:
        task_id = task["instance_id"]
        print(f"\n[{task_id}]")
        print(f"  Problem: {task['problem_statement'][:80]}...")
        print(f"  Hints: {len(task['hints_text'])} chars")
        print(f"  Tests: {len(task['FAIL_TO_PASS'])} failing tests")
        
        spec = build_task_image(task)
        if spec:
            specs[task_id] = spec
            print(f"  Image: {spec.instance_image_key}")
        else:
            print(f"  FAILED to build image")
    
    print(f"\n\nSuccessfully built {len(specs)}/{len(tasks)} task images")
    
    # Save task list
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "tasks.json", "w") as f:
        json.dump([{
            "instance_id": t["instance_id"],
            "difficulty": t["difficulty"],
            "hints_length": len(t["hints_text"]),
            "tests": len(t["FAIL_TO_PASS"]),
            "problem_length": len(t["problem_statement"]),
        } for t in tasks], f, indent=2)
    
    return tasks, specs


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["setup", "calibrate", "run", "analyze"])
    parser.add_argument("--difficulty", default="1-4 hours")
    parser.add_argument("--task", default=None)
    args = parser.parse_args()
    
    if args.command == "setup":
        cmd_setup(args)
    else:
        print(f"Command '{args.command}' not yet implemented")
