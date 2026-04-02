#!/usr/bin/env python3
"""Set up a batch of 3 calibration workspaces."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
import subprocess, json, os, shutil, time
from pathlib import Path
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

WORKSPACE_BASE = Path("/tmp/borg_workspaces")

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task_map = {t["instance_id"]: dict(t) for t in ds}

# Which tasks to set up (from argv or default batch)
tasks = sys.argv[1:] if len(sys.argv) > 1 else [
    "django__django-10554",
    "django__django-11138",
    "django__django-13344",
]

for tid in tasks:
    print(f"\n{'='*50}")
    print(f"Setting up {tid}")
    task = task_map[tid]
    spec = make_test_spec(task)
    image = spec.instance_image_key
    
    workspace = WORKSPACE_BASE / tid.replace("/", "_")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    
    # Extract source
    temp = f"borg_ext_{int(time.time())}"
    subprocess.run(["docker", "run", "-d", "--name", temp, image, "tail", "-f", "/dev/null"],
                  capture_output=True, timeout=30)
    subprocess.run(["docker", "cp", f"{temp}:/testbed", str(workspace / "testbed")],
                  capture_output=True, timeout=120)
    
    # Apply test patch
    tp = task.get("test_patch", "")
    if tp:
        (workspace / "test_patch.diff").write_text(tp)
        r = subprocess.run(["git", "apply", str(workspace / "test_patch.diff")],
                      cwd=workspace / "testbed", capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print(f"  Test patch warning: {r.stderr[:100]}")
    
    subprocess.run(["docker", "rm", "-f", temp], capture_output=True, timeout=10)
    
    # Start container with mount
    container = f"borg_ws_{tid.replace('/', '_')}_{int(time.time())}"
    testbed_path = str(workspace / "testbed")
    subprocess.run(
        ["docker", "run", "-d", "--name", container, "--memory", "4g", "--cpus", "2",
         "-v", f"{testbed_path}:/testbed", image, "tail", "-f", "/dev/null"],
        capture_output=True, timeout=30)
    
    # Parse tests
    ftp = task["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)
    
    test_args = set()
    for test in ftp:
        if '(' in test:
            test_args.add(test.split('(')[1].rstrip(')'))
        else:
            test_args.add(test)
    test_cmd = f"python tests/runtests.py {' '.join(test_args)} --verbosity 2"
    
    # Verify tests fail
    r = subprocess.run(
        ["docker", "exec", container, "bash", "-c",
         f"source /opt/miniconda3/bin/activate testbed && cd /testbed && {test_cmd}"],
        capture_output=True, text=True, timeout=120)
    tests_fail = r.returncode != 0 or "FAILED" in r.stdout + r.stderr
    
    # Build prompt
    problem = task["problem_statement"]
    prompt = f"""You are an expert Django developer. Fix the bug described below.

The Django source code is at {testbed_path}/django/ — edit files directly.

To run tests:
  docker exec {container} bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && {test_cmd}"

ISSUE:
{problem}

TESTS THAT MUST PASS:
{json.dumps(ftp, indent=2)}

Only fix source code in {testbed_path}/django/. Do NOT modify test files."""
    
    prompt_file = f"/tmp/cal_v2_{tid}_1.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)
    
    print(f"  Container: {container}")
    print(f"  Tests fail: {tests_fail}")
    print(f"  Prompt: {prompt_file} ({len(prompt)} chars)")
    print(f"  Workspace: {workspace}")

print(f"\n{'='*50}")
print("All workspaces ready. Run agents now.")
