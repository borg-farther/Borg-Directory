#!/usr/bin/env python3
"""
Run calibration: 15 tasks × 3 runs each = 45 runs (Condition A only).
Each run spawns a delegate_task agent to fix a real Django bug.

Usage:
    python3 run_calibration.py                    # Run all
    python3 run_calibration.py --task django__django-16631  # Single task
    python3 run_calibration.py --status           # Show progress
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
RESULTS_FILE = DATA_DIR / "swebench_results" / "calibration.json"


def load_calibration():
    """Load existing calibration data."""
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return {"experiment": "borg-swebench-v1", "runs": []}


def save_calibration(data):
    """Save calibration data."""
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(data, indent=2))


def docker_exec(container, cmd, timeout=300):
    """Execute command in container with conda env."""
    full_cmd = f"source /opt/miniconda3/bin/activate testbed && {cmd}"
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c", full_cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def setup_task_container(task_record):
    """Start container, apply test patch, verify tests fail."""
    spec = make_test_spec(task_record)
    image = spec.instance_image_key
    
    # Check image exists
    check = subprocess.run(["docker", "image", "inspect", image],
                          capture_output=True, timeout=10)
    if check.returncode != 0:
        return None, None, f"Image {image} not found"
    
    # Start container
    container = f"borg_cal_{task_record['instance_id'].replace('/', '_')}_{int(time.time())}"
    result = subprocess.run(
        ["docker", "run", "-d", "--name", container,
         "--memory", "4g", "--cpus", "2",
         image, "tail", "-f", "/dev/null"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        return None, container, f"Container start failed: {result.stderr[:200]}"
    
    # Apply test patch
    test_patch = task_record.get("test_patch", "")
    if test_patch:
        patch_file = f"/tmp/test_patch_{container}.diff"
        with open(patch_file, "w") as f:
            f.write(test_patch)
        subprocess.run(["docker", "cp", patch_file, f"{container}:/tmp/test_patch.diff"],
                      capture_output=True, timeout=10)
        code, stdout, stderr = docker_exec(container, "cd /testbed && git apply /tmp/test_patch.diff")
        if code != 0:
            return None, container, f"Test patch apply failed: {stderr[:200]}"
        os.remove(patch_file)
    
    # Parse FAIL_TO_PASS
    ftp = task_record["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)
    
    # Extract test module paths for Django's test runner
    test_args = set()
    for test in ftp:
        if '(' in test:
            # Format: "test_name (module.Class)"
            module_class = test.split('(')[1].rstrip(')')
            parts = module_class.split('.')
            # Use module.Class format for runtests.py
            test_args.add(module_class)
        else:
            test_args.add(test)
    
    # Verify tests fail
    test_cmd = f"cd /testbed && python tests/runtests.py {' '.join(test_args)} --verbosity 0"
    code, stdout, stderr = docker_exec(container, test_cmd, timeout=120)
    output = stdout + stderr
    
    if code == 0 and "FAILED" not in output:
        return None, container, f"Tests pass before fix (should fail)"
    
    return ftp, container, None


def build_prompt(task_record, container, fail_to_pass, condition="A"):
    """Build the agent prompt."""
    problem = task_record["problem_statement"]
    
    # Build test command
    test_args = set()
    for test in fail_to_pass:
        if '(' in test:
            test_args.add(test.split('(')[1].rstrip(')'))
        else:
            test_args.add(test)
    test_cmd = f"python tests/runtests.py {' '.join(test_args)} --verbosity 2"
    
    prompt = f"""You are an expert Django developer. Fix the bug described below.

The Django codebase is inside Docker container "{container}".
Run commands with: docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && COMMAND"

Examples:
  docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && cat /testbed/django/path/to/file.py"
  docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && grep -rn 'search_term' django/"

To edit files: write to a temp file on host, then docker cp it in:
  1. Write the fixed file to /tmp/some_file.py
  2. Run: docker cp /tmp/some_file.py {container}:/testbed/django/path/to/file.py

ISSUE:
{problem}

TESTS THAT MUST PASS:
{json.dumps(fail_to_pass, indent=2)}

Verify your fix:
  docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && {test_cmd}"

Do NOT modify test files. Only fix source code in /testbed/django/."""

    if condition == "B":
        hints = task_record.get("hints_text", "")
        prompt += f"""

REASONING TRACE FROM PRIOR INVESTIGATION:
{hints}

Use these notes to guide your debugging approach."""

    return prompt


def check_result(container, fail_to_pass):
    """Check if the agent's fix works."""
    test_args = set()
    for test in fail_to_pass:
        if '(' in test:
            test_args.add(test.split('(')[1].rstrip(')'))
        else:
            test_args.add(test)
    
    test_cmd = f"cd /testbed && python tests/runtests.py {' '.join(test_args)} --verbosity 2"
    code, stdout, stderr = docker_exec(container, test_cmd, timeout=180)
    output = stdout + stderr
    
    success = code == 0 and "FAILED" not in output
    return success, output


def run_single_calibration(task_id, run_num, task_record):
    """Run a single calibration trial."""
    print(f"\n{'='*60}")
    print(f"[{task_id}] Calibration Run {run_num}")
    print(f"{'='*60}")
    
    result = {
        "task_id": task_id,
        "condition": "A",
        "run": run_num,
        "success": None,
        "error": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Setup
    print("  Setting up container...")
    fail_to_pass, container, error = setup_task_container(task_record)
    
    if error:
        result["error"] = error
        print(f"  ERROR: {error}")
        if container:
            subprocess.run(["docker", "rm", "-f", container], capture_output=True)
        return result
    
    result["container"] = container
    print(f"  Container: {container}")
    print(f"  Tests correctly fail in starting state ✓")
    
    # Build prompt
    prompt = build_prompt(task_record, container, fail_to_pass, condition="A")
    result["prompt_length"] = len(prompt)
    
    # Save prompt for delegate_task
    prompt_file = f"/tmp/cal_prompt_{task_id}_{run_num}.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)
    
    print(f"  Prompt saved ({len(prompt)} chars)")
    print(f"  Prompt file: {prompt_file}")
    print(f"  Container: {container}")
    
    # NOTE: In automated mode, we'd call delegate_task here.
    # For now, output the info needed for manual or scripted execution.
    result["prompt_file"] = prompt_file
    result["needs_execution"] = True
    
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=None)
    parser.add_argument("--run", type=int, default=None)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--check", help="Check result for a container")
    args = parser.parse_args()
    
    if args.status:
        cal = load_calibration()
        runs = cal.get("runs", [])
        completed = [r for r in runs if r.get("success") is not None]
        pending = [r for r in runs if r.get("needs_execution")]
        errors = [r for r in runs if r.get("error")]
        print(f"Total runs: {len(runs)}")
        print(f"  Completed: {len(completed)} ({sum(1 for r in completed if r['success'])} pass, {sum(1 for r in completed if not r['success'])} fail)")
        print(f"  Pending execution: {len(pending)}")
        print(f"  Errors: {len(errors)}")
        return
    
    # Load tasks
    with open(DATA_DIR / "final_task_selection.json") as f:
        task_ids = json.load(f)["tasks"]
    
    if args.task:
        task_ids = [args.task]
    
    # Load dataset
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    task_map = {t["instance_id"]: dict(t) for t in ds}
    
    cal = load_calibration()
    
    for task_id in task_ids:
        if task_id not in task_map:
            print(f"SKIP {task_id}: not in dataset")
            continue
        
        runs_to_do = [args.run] if args.run else [1, 2, 3]
        
        for run_num in runs_to_do:
            # Skip if already done
            existing = [r for r in cal["runs"] 
                       if r["task_id"] == task_id and r["run"] == run_num
                       and r.get("success") is not None]
            if existing:
                print(f"[{task_id}] Run {run_num}: already done (success={existing[0]['success']})")
                continue
            
            result = run_single_calibration(task_id, run_num, task_map[task_id])
            cal["runs"].append(result)
            save_calibration(cal)
    
    print(f"\nCalibration data saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()
