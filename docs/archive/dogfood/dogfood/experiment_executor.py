#!/usr/bin/env python3
"""
Borg SWE-bench Experiment Executor

Runs A/B experiment on SWE-bench tasks using Docker containers + delegate_task.

The key insight from adversarial review: delegate_task agents can't work INSIDE 
Docker. Instead, we:
1. Start a Docker container
2. Give the agent docker exec commands to run inside it
3. The agent's prompt tells it to use "docker exec CONTAINER_NAME bash -c '...'"
4. After the agent finishes, we run tests in the container

Actually simpler approach: start container, exec agent commands via subprocess 
directly (no delegate_task Docker interaction needed). The agent works on the 
host but targets files in the container via docker exec/cp.

SIMPLEST approach (what we'll use):
1. Start container 
2. Create a workspace script that the agent can edit
3. Apply the agent's patch via docker cp
4. Run tests

But for actual A/B experiment with delegate_task:
- Agent needs terminal access
- Terminal commands get docker exec'd into the container
- This requires a wrapper/proxy approach
"""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import json
import os
import subprocess
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

DATA_DIR = Path("/root/hermes-workspace/borg/dogfood/v2_data")
RESULTS_DIR = DATA_DIR / "swebench_results"
EXPERIMENT_DIR = Path("/root/hermes-workspace/borg/dogfood/swebench_experiment")


def get_container_name(task_id, condition, run):
    """Generate unique container name."""
    return f"borg_{task_id.replace('/', '_')}_{condition}_{run}_{int(time.time())}"


def start_container(image_key):
    """Start a Docker container and return its name."""
    name = f"borg_exp_{int(time.time())}"
    result = subprocess.run(
        ["docker", "run", "-d", "--name", name,
         "--memory", "4g", "--cpus", "2",
         image_key, "tail", "-f", "/dev/null"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"Container start failed: {result.stderr[:200]}")
    return name


def docker_exec(container, cmd, timeout=300):
    """Execute command in container."""
    full_cmd = f"source /opt/miniconda3/bin/activate testbed && {cmd}"
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c", full_cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def verify_tests_fail(container, fail_to_pass):
    """Verify that the specified tests fail before any fix."""
    # Use Django's test runner
    test_modules = set()
    for test in fail_to_pass:
        # Parse "test_name (module.Class)" format
        if '(' in test:
            parts = test.split('(')[1].rstrip(')')
            module = '.'.join(parts.split('.')[:-1])
            test_modules.add(module)
        else:
            test_modules.add(test)
    
    test_arg = ' '.join(test_modules)
    code, stdout, stderr = docker_exec(
        container, f"cd /testbed && python tests/runtests.py {test_arg} --verbosity 0", timeout=120
    )
    
    # Tests should FAIL
    output = stdout + stderr
    return code != 0, output


def run_tests(container, fail_to_pass):
    """Run the failing tests and return pass/fail."""
    test_modules = set()
    for test in fail_to_pass:
        if '(' in test:
            parts = test.split('(')[1].rstrip(')')
            module = '.'.join(parts.split('.')[:-1])
            test_modules.add(module)
        else:
            test_modules.add(test)
    
    test_arg = ' '.join(test_modules)
    code, stdout, stderr = docker_exec(
        container, f"cd /testbed && python tests/runtests.py {test_arg} --verbosity 2", timeout=180
    )
    
    output = stdout + stderr
    
    # Check if all fail_to_pass tests now pass
    all_pass = code == 0 and "FAILED" not in output
    return all_pass, output


def cleanup_container(name):
    """Remove container."""
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=30)


def get_counterbalance(task_id):
    """Deterministic A-first or B-first."""
    h = hashlib.sha256(f"{task_id}-borg-swebench-v1".encode()).hexdigest()
    return "A" if int(h[:2], 16) % 2 == 0 else "B"


def build_agent_prompt(task_data, condition, container_name):
    """Build the prompt for the delegate_task agent."""
    task_id = task_data["instance_id"]
    problem = task_data["problem_statement"]
    hints = task_data.get("hints_text", "")
    
    fail_to_pass = task_data["FAIL_TO_PASS"]
    if isinstance(fail_to_pass, str):
        fail_to_pass = json.loads(fail_to_pass)
    
    # Build test command
    test_modules = set()
    for test in fail_to_pass:
        if '(' in test:
            parts = test.split('(')[1].rstrip(')')
            module = '.'.join(parts.split('.')[:-1])
            test_modules.add(module)
        else:
            test_modules.add(test)
    test_arg = ' '.join(test_modules)
    
    prompt = f"""You are an expert Django developer. Fix the bug described below.

The Django codebase is inside a Docker container named {container_name}.
To run commands inside the container, use:
  docker exec {container_name} bash -c "source /opt/miniconda3/bin/activate testbed && YOUR_COMMAND"

To read files:
  docker exec {container_name} cat /testbed/path/to/file.py

To edit files, write the content to a temp file then copy it in:
  # Write to temp file on host, then:
  docker cp /tmp/fixed_file.py {container_name}:/testbed/path/to/file.py

ISSUE:
{problem}

TESTS THAT MUST PASS:
{json.dumps(fail_to_pass, indent=2)}

To run the tests:
  docker exec {container_name} bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py {test_arg} --verbosity 2"

The fix is correct when all specified tests pass.
Do NOT modify the test files — only fix the source code in /testbed/django/."""

    if condition == "B":
        prompt += f"""

REASONING TRACE FROM PRIOR INVESTIGATION:
The following notes are from developers who investigated this bug.
They contain observations about the root cause and potential approaches.

{hints}

Use these notes to guide your debugging approach."""

    return prompt


def run_calibration(task_ids, num_runs=3):
    """Run calibration: baseline (Condition A) only."""
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    task_map = {t["instance_id"]: dict(t) for t in ds}
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cal_file = RESULTS_DIR / "calibration.json"
    cal_data = json.loads(cal_file.read_text()) if cal_file.exists() else {"runs": []}
    
    for task_id in task_ids:
        task = task_map.get(task_id)
        if not task:
            print(f"SKIP {task_id}: not found in dataset")
            continue
        
        spec = make_test_spec(task)
        
        for run in range(1, num_runs + 1):
            # Check if already done
            existing = [r for r in cal_data["runs"] 
                       if r["task_id"] == task_id and r["run"] == run]
            if existing:
                print(f"[{task_id}] Run {run}: already done (success={existing[0].get('success')})")
                continue
            
            print(f"\n[{task_id}] Run {run}/{num_runs}")
            
            run_result = {
                "task_id": task_id,
                "condition": "A",
                "run": run,
                "success": None,
                "error": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            
            try:
                # Start container
                container = start_container(spec.instance_image_key)
                run_result["container"] = container
                print(f"  Container: {container}")
                
                # Verify tests fail
                tests_fail, pre_output = verify_tests_fail(
                    container, 
                    json.loads(task["FAIL_TO_PASS"]) if isinstance(task["FAIL_TO_PASS"], str) else task["FAIL_TO_PASS"]
                )
                if not tests_fail:
                    run_result["error"] = "Tests pass before fix"
                    print(f"  ERROR: Tests pass before fix")
                    cleanup_container(container)
                    cal_data["runs"].append(run_result)
                    continue
                
                print(f"  Tests correctly fail in starting state")
                
                # Build prompt
                prompt = build_agent_prompt(task, "A", container)
                run_result["prompt"] = prompt
                run_result["prompt_length"] = len(prompt)
                
                # This is where delegate_task would be called
                # For now, we record the prompt and container
                print(f"  Ready for agent (prompt: {len(prompt)} chars)")
                print(f"  Container: {container}")
                print(f"  To run manually: delegate_task with prompt above")
                
                # After agent runs, check tests:
                # success, output = run_tests(container, fail_to_pass)
                # run_result["success"] = success
                
            except Exception as e:
                run_result["error"] = str(e)
                print(f"  ERROR: {e}")
            
            cal_data["runs"].append(run_result)
            
            # Save after each run
            cal_file.write_text(json.dumps(cal_data, indent=2))
    
    print(f"\nCalibration data saved to {cal_file}")
    return cal_data


def run_experiment(task_ids, num_runs=3):
    """Run full A/B experiment."""
    # Similar to calibration but runs both conditions
    pass  # Will implement after calibration validates the pipeline


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["calibrate", "run", "status"])
    parser.add_argument("--task", default=None)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    
    # Load task selection
    with open(DATA_DIR / "final_task_selection.json") as f:
        task_ids = json.load(f)["tasks"]
    
    if args.task:
        task_ids = [args.task]
    
    if args.command == "calibrate":
        run_calibration(task_ids, num_runs=args.runs)
    elif args.command == "status":
        cal_file = RESULTS_DIR / "calibration.json"
        if cal_file.exists():
            data = json.loads(cal_file.read_text())
            completed = [r for r in data["runs"] if r.get("success") is not None]
            pending = [r for r in data["runs"] if r.get("success") is None]
            print(f"Calibration: {len(completed)} completed, {len(pending)} pending")
        else:
            print("No calibration data yet")
    else:
        print("Not yet implemented")
