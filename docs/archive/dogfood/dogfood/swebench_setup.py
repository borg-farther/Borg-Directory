#!/usr/bin/env python3
"""
Set up SWE-bench tasks for the Borg experiment.
Picks 10 medium-difficulty Django tasks and creates self-contained task dirs.
"""

from datasets import load_dataset
import json
import os
import subprocess

DATA_DIR = "/root/hermes-workspace/borg/dogfood/v2_data"
TASKS_DIR = "/root/hermes-workspace/borg/dogfood/swebench_tasks"

def setup():
    print("Loading SWE-bench Verified...")
    ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
    
    # Filter: Django, medium difficulty (15 min - 1 hour), has hints
    candidates = []
    for t in ds:
        if (t["repo"] == "django/django" and 
            t.get("difficulty") == "15 min - 1 hour" and
            t.get("hints_text")):
            
            fail_to_pass = t["FAIL_TO_PASS"]
            if isinstance(fail_to_pass, str):
                fail_to_pass = json.loads(fail_to_pass)
            
            # Prefer tasks with 1-3 failing tests (more tractable)
            if 1 <= len(fail_to_pass) <= 3:
                candidates.append({
                    "instance_id": t["instance_id"],
                    "repo": t["repo"],
                    "base_commit": t["base_commit"],
                    "problem_statement": t["problem_statement"],
                    "hints_text": t["hints_text"],
                    "test_patch": t["test_patch"],
                    "patch": t["patch"],  # the gold solution
                    "FAIL_TO_PASS": fail_to_pass,
                    "PASS_TO_PASS": json.loads(t["PASS_TO_PASS"]) if isinstance(t["PASS_TO_PASS"], str) else t["PASS_TO_PASS"],
                    "version": t.get("version"),
                    "environment_setup_commit": t.get("environment_setup_commit"),
                    "difficulty": t.get("difficulty"),
                    "problem_length": len(t["problem_statement"]),
                })
    
    print(f"Found {len(candidates)} Django medium-difficulty candidates with hints")
    
    # Sort by problem statement length (shorter = more focused)
    candidates.sort(key=lambda x: x["problem_length"])
    
    # Take first 15 (will calibrate down to 10)
    selected = candidates[:15]
    
    print(f"\nSelected {len(selected)} tasks:")
    for t in selected:
        print(f"  {t['instance_id']} ({len(t['FAIL_TO_PASS'])} tests, {t['problem_length']} chars)")
    
    # Create task directories
    os.makedirs(TASKS_DIR, exist_ok=True)
    
    for task in selected:
        task_id = task["instance_id"].replace("/", "__")
        task_dir = os.path.join(TASKS_DIR, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Save full task data
        with open(os.path.join(task_dir, "task_data.json"), "w") as f:
            json.dump(task, f, indent=2)
        
        # Create prompt.txt from problem_statement
        with open(os.path.join(task_dir, "prompt.txt"), "w") as f:
            f.write(f"""Fix the following Django bug. The code is in the repo at /workspace/django.

BUG REPORT:
{task['problem_statement']}

The fix should make these tests pass:
{json.dumps(task['FAIL_TO_PASS'], indent=2)}

After fixing, verify with: cd /workspace && python -m pytest {' '.join(task['FAIL_TO_PASS'])} --no-header -q
""")
        
        # Create trace.txt from hints_text (this is the reasoning trace)
        with open(os.path.join(task_dir, "trace.txt"), "w") as f:
            f.write(f"""REASONING TRACE FOR: {task['instance_id']}

HINTS FROM BUG DISCUSSION:
{task['hints_text']}

Note: These hints are from the original bug discussion and may contain 
insights about the root cause, proposed approaches, and potential pitfalls.
""")
        
        # Create setup.sh that uses SWE-bench's Docker infrastructure
        with open(os.path.join(task_dir, "setup.sh"), "w") as f:
            f.write(f"""#!/bin/bash
# Setup for {task['instance_id']}
# This task requires a Django checkout at commit {task['base_commit']}
cd "$(dirname "$0")"

# Check if workspace already exists
if [ -d "/workspace/django" ]; then
    echo "Workspace exists"
    exit 0
fi

# Clone Django at the right commit
mkdir -p /workspace
cd /workspace
git clone --depth 100 https://github.com/{task['repo']}.git django 2>/dev/null || true
cd django
git checkout {task['base_commit']} 2>/dev/null

# Apply test patch (adds the failing test)
cat > /tmp/test_patch.diff << 'PATCHEOF'
{task['test_patch']}
PATCHEOF
git apply /tmp/test_patch.diff 2>/dev/null || true

# Install Django in dev mode
pip install -e . -q 2>/dev/null || true

echo "Setup complete for {task['instance_id']}"
""")
        
        # Create check.sh
        test_cmds = " ".join(task["FAIL_TO_PASS"])
        with open(os.path.join(task_dir, "check.sh"), "w") as f:
            f.write(f"""#!/bin/bash
# Verify fix for {task['instance_id']}
cd /workspace/django
python -m pytest {test_cmds} --no-header -q 2>&1
exit $?
""")
        
        # Make executable
        os.chmod(os.path.join(task_dir, "setup.sh"), 0o755)
        os.chmod(os.path.join(task_dir, "check.sh"), 0o755)
        
        print(f"  Created: {task_dir}")
    
    # Save selection metadata
    with open(os.path.join(DATA_DIR, "swebench_selected.json"), "w") as f:
        json.dump({
            "total_candidates": len(candidates),
            "selected": len(selected),
            "tasks": [{"instance_id": t["instance_id"], "difficulty": t["difficulty"], 
                       "tests": len(t["FAIL_TO_PASS"]), "problem_length": t["problem_length"]}
                      for t in selected]
        }, f, indent=2)
    
    print(f"\nDone. {len(selected)} SWE-bench tasks ready in {TASKS_DIR}")
    print("Next: run calibration with delegate_task (Condition A, no traces)")


if __name__ == "__main__":
    setup()
