#!/usr/bin/env python3
"""
Calibration v2: Mount Django source on host so agents can edit directly.

Instead of docker exec + docker cp, we:
1. Copy Django source from container to host
2. Mount it back into a new container  
3. Agent edits files on host (normal file operations)
4. Changes are instantly visible inside container
5. Run tests inside container
"""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import json
import os
import subprocess
import time
import shutil
from datetime import datetime, timezone
from pathlib import Path
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

DATA_DIR = Path("/root/hermes-workspace/borg/dogfood/v2_data")
RESULTS_FILE = DATA_DIR / "swebench_results" / "calibration_v2.json"
WORKSPACE_BASE = Path("/tmp/borg_workspaces")


def setup_workspace(task_record):
    """Create a workspace: extract Django source from image, mount it back."""
    spec = make_test_spec(task_record)
    image = spec.instance_image_key
    tid = task_record["instance_id"]
    
    workspace = WORKSPACE_BASE / tid.replace("/", "_")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    
    # Step 1: Start temp container to extract source
    temp_container = f"borg_extract_{int(time.time())}"
    subprocess.run(
        ["docker", "run", "-d", "--name", temp_container, image, "tail", "-f", "/dev/null"],
        capture_output=True, timeout=30
    )
    
    # Step 2: Copy /testbed from container to host
    subprocess.run(
        ["docker", "cp", f"{temp_container}:/testbed", str(workspace / "testbed")],
        capture_output=True, timeout=120
    )
    
    # Step 3: Apply test patch on host
    test_patch = task_record.get("test_patch", "")
    if test_patch:
        patch_file = workspace / "test_patch.diff"
        patch_file.write_text(test_patch)
        result = subprocess.run(
            ["git", "apply", str(patch_file)],
            cwd=workspace / "testbed",
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"  Test patch warning: {result.stderr[:200]}")
    
    # Step 4: Stop temp container
    subprocess.run(["docker", "rm", "-f", temp_container], capture_output=True, timeout=10)
    
    # Step 5: Start new container with mounted workspace
    container = f"borg_ws_{tid.replace('/', '_')}_{int(time.time())}"
    testbed_path = str(workspace / "testbed")
    result = subprocess.run(
        ["docker", "run", "-d", "--name", container,
         "--memory", "4g", "--cpus", "2",
         "-v", f"{testbed_path}:/testbed",
         image, "tail", "-f", "/dev/null"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None, None, None, f"Container start failed: {result.stderr[:200]}"
    
    # Step 6: Verify tests fail
    full_cmd = "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py --help > /dev/null 2>&1 && echo OK"
    check = subprocess.run(
        ["docker", "exec", container, "bash", "-c", full_cmd],
        capture_output=True, text=True, timeout=30
    )
    
    return workspace, container, spec, None


def run_test(container, fail_to_pass):
    """Run tests inside container (source is mounted from host)."""
    test_args = set()
    for test in fail_to_pass:
        if '(' in test:
            test_args.add(test.split('(')[1].rstrip(')'))
        else:
            test_args.add(test)
    
    test_cmd = f"source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py {' '.join(test_args)} --verbosity 2"
    result = subprocess.run(
        ["docker", "exec", container, "bash", "-c", test_cmd],
        capture_output=True, text=True, timeout=300
    )
    output = result.stdout + result.stderr
    success = result.returncode == 0 and "FAILED" not in output
    return success, output


def build_prompt_v2(task_record, workspace, container, fail_to_pass, condition="A"):
    """Build prompt where agent edits files on HOST filesystem."""
    problem = task_record["problem_statement"]
    testbed = workspace / "testbed"
    
    # Build test command
    test_args = set()
    for test in fail_to_pass:
        if '(' in test:
            test_args.add(test.split('(')[1].rstrip(')'))
        else:
            test_args.add(test)
    test_cmd = f"python tests/runtests.py {' '.join(test_args)} --verbosity 2"
    
    prompt = f"""You are an expert Django developer. Fix the bug described below.

The Django source code is at {testbed}/django/ — edit these files directly 
using normal file operations (read_file, patch, write_file). Your edits 
are automatically visible inside the test container.

To run tests, use:
  docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && {test_cmd}"

ISSUE:
{problem}

TESTS THAT MUST PASS:
{json.dumps(fail_to_pass, indent=2)}

Do NOT modify test files in {testbed}/tests/. Only fix source code in {testbed}/django/."""

    if condition == "B":
        hints = task_record.get("hints_text", "")
        prompt += f"""

REASONING TRACE FROM PRIOR INVESTIGATION:
{hints}

Use these notes to guide your debugging approach."""

    return prompt


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--run", type=int, default=1)
    args = parser.parse_args()
    
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    task_map = {t["instance_id"]: dict(t) for t in ds}
    
    task = task_map.get(args.task)
    if not task:
        print(f"Task {args.task} not found")
        sys.exit(1)
    
    print(f"Setting up workspace for {args.task}...")
    workspace, container, spec, error = setup_workspace(task)
    if error:
        print(f"ERROR: {error}")
        sys.exit(1)
    
    ftp = task["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)
    
    # Verify tests fail
    print("Verifying tests fail in starting state...")
    success, output = run_test(container, ftp)
    if success:
        print("ERROR: Tests pass before fix!")
        print(output[-500:])
        sys.exit(1)
    print("Tests correctly fail ✓")
    
    # Build prompt
    prompt = build_prompt_v2(task, workspace, container, ftp, condition="A")
    
    prompt_file = f"/tmp/cal_v2_{args.task}_{args.run}.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)
    
    print(f"\nWorkspace: {workspace}")
    print(f"Container: {container}")
    print(f"Prompt: {prompt_file} ({len(prompt)} chars)")
    print(f"\nAgent can edit files directly at: {workspace}/testbed/django/")
    print(f"Test with: docker exec {container} bash -c \"source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py ...\"")
