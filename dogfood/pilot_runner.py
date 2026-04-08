#!/usr/bin/env python3
"""Pilot A/B runner — 3 tasks x 2 conditions = 6 trials.

Runs agents as delegate_task subagents (from the orchestrator).
Condition A: baseline (no borg)
Condition B: with borg tools mentioned + traces seeded
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

TASKS = [
    {
        "id": "pydata__xarray-2905",
        "difficulty": "easy",
        "testbed": "/tmp/borg_workspaces/pydata__xarray-2905/testbed",
        "test_cmd": "python -m pytest xarray/tests/test_variable.py::TestAsCompatibleData::test_unsupported_type -xvs",
        "docker_image": "swebench/sweb.eval.x86_64.pydata_1776_xarray-2905:latest",
        "file_to_fix": "xarray/core/variable.py",
        "bug_description": "xarray's as_compatible_data unconditionally extracts .values from objects that have it. Custom objects with a .values attribute get incorrectly converted. The fix should restrict the getattr(data, 'values', data) call to only pd.Series, pd.Index, and pd.DataFrame.",
        "fail_to_pass": ["xarray/tests/test_variable.py::TestAsCompatibleData::test_unsupported_type"],
    },
    {
        "id": "scikit-learn__scikit-learn-13142",
        "difficulty": "medium",
        "testbed": "/tmp/borg_workspaces/scikit-learn__scikit-learn-13142/testbed",
        "test_cmd": "python -m pytest sklearn/mixture/tests/test_gaussian_mixture.py::test_gaussian_mixture_fit_predict_n_init sklearn/mixture/tests/test_bayesian_mixture.py::test_bayesian_mixture_fit_predict_n_init -x -v",
        "docker_image": "sweb.eval.x86_64.scikit-learn__scikit-learn-13142:latest",
        "file_to_fix": "sklearn/mixture/base.py",
        "bug_description": "GaussianMixture.fit_predict gives different results than fit().predict() when n_init > 1. In base.py, the final e-step happens BEFORE restoring best parameters when n_init > 1, so labels come from wrong model. The e-step should happen AFTER restoring best params.",
        "fail_to_pass": [
            "sklearn/mixture/tests/test_bayesian_mixture.py::test_bayesian_mixture_fit_predict_n_init",
            "sklearn/mixture/tests/test_gaussian_mixture.py::test_gaussian_mixture_fit_predict_n_init",
        ],
    },
    {
        "id": "django__django-10973",
        "difficulty": "hard",
        "testbed": "/tmp/borg_workspaces/django__django-10973/testbed",
        "test_cmd": "python tests/runtests.py dbshell.test_postgresql --verbosity 2",
        "docker_image": "sweb.eval.x86_64.django__django-10973:latest",
        "file_to_fix": "django/db/backends/postgresql/client.py",
        "bug_description": "PostgreSQL dbshell should use PGPASSWORD env var instead of .pgpass file, and subprocess.run instead of subprocess.check_call. Tests mock subprocess.run so the implementation must use that.",
        "fail_to_pass": [
            "dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase.test_accent",
            "dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase.test_basic",
            "dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase.test_column",
            "dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase.test_nopass",
            "dbshell.test_postgresql.PostgreSqlDbshellCommandTestCase.test_sigint_handler",
        ],
    },
]


def build_prompt_a(task):
    """Condition A: baseline — no borg, just the bug report."""
    return f"""You are a software engineer fixing a bug in an open-source project.

BUG REPORT:
{task['bug_description']}

WORKSPACE: {task['testbed']}
The repository is checked out at the workspace path. Edit files directly there.

FILE TO INVESTIGATE: {task['file_to_fix']}

TO VERIFY YOUR FIX, run this test command inside Docker:
docker run --rm -v {task['testbed']}:/testbed -w /testbed {task['docker_image']} bash -c "source /opt/miniconda3/bin/activate testbed && {task['test_cmd']}"

FAILING TESTS: {', '.join(task['fail_to_pass'])}

Your goal: modify the source code to make the failing tests pass.
Do NOT modify the test files.
After making your fix, run the test command to verify."""


def build_prompt_b(task):
    """Condition B: with borg — agent gets borg search/observe instructions."""
    return f"""You are a software engineer fixing a bug in an open-source project.
You have access to Borg, a knowledge system with traces from prior successful bug fixes.

BEFORE YOU START: Use borg to search for relevant guidance:
1. Run: borg search "{task['difficulty']} bug fix"
2. Run: borg debug "{task['bug_description'][:100]}"
These may return useful patterns from prior successful fixes.

BUG REPORT:
{task['bug_description']}

WORKSPACE: {task['testbed']}
The repository is checked out at the workspace path. Edit files directly there.

FILE TO INVESTIGATE: {task['file_to_fix']}

TO VERIFY YOUR FIX, run this test command inside Docker:
docker run --rm -v {task['testbed']}:/testbed -w /testbed {task['docker_image']} bash -c "source /opt/miniconda3/bin/activate testbed && {task['test_cmd']}"

FAILING TESTS: {', '.join(task['fail_to_pass'])}

Your goal: modify the source code to make the failing tests pass.
Do NOT modify the test files.
After making your fix, run the test command to verify.
After fixing (or failing), run: borg feedback-v3 --problem-class debugging --success yes/no"""


def run_test(task):
    """Run the FAIL_TO_PASS tests and return True if they pass."""
    cmd = (
        f"docker run --rm -v {task['testbed']}:/testbed -w /testbed "
        f"{task['docker_image']} bash -c "
        f"'source /opt/miniconda3/bin/activate testbed && {task['test_cmd']}'"
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    return result.returncode == 0, result.stdout[-500:] if result.stdout else "", result.stderr[-500:] if result.stderr else ""


def reset_workspace(task):
    """Reset workspace to pre-fix state using git."""
    testbed = task['testbed']
    subprocess.run(f"cd {testbed} && git checkout -- .", shell=True, capture_output=True)


def main():
    results = []
    
    # Counterbalanced: task 0 = A first, task 1 = B first, task 2 = A first
    order = [("A", "B"), ("B", "A"), ("A", "B")]
    
    for i, task in enumerate(TASKS):
        first_cond, second_cond = order[i]
        
        for cond in [first_cond, second_cond]:
            print(f"\n{'='*60}")
            print(f"TRIAL: {task['id']} | Condition {cond} | Difficulty: {task['difficulty']}")
            print(f"{'='*60}")
            
            # Reset workspace
            reset_workspace(task)
            
            # Build prompt
            if cond == "A":
                prompt = build_prompt_a(task)
            else:
                prompt = build_prompt_b(task)
            
            # Save prompt for audit trail
            prompt_file = f"/tmp/borg_workspaces/prompts/{task['id']}_{cond}.txt"
            os.makedirs(os.path.dirname(prompt_file), exist_ok=True)
            Path(prompt_file).write_text(prompt)
            
            start_time = time.time()
            
            # Print prompt (for manual agent dispatch)
            print(f"\nPrompt saved to: {prompt_file}")
            print(f"Prompt length: {len(prompt)} chars")
            print(f"\nTo run manually: delegate_task with this prompt")
            
            # Run test to check if it passes (pre-check should fail)
            pre_pass, _, _ = run_test(task)
            print(f"Pre-fix test: {'PASS (unexpected!)' if pre_pass else 'FAIL (expected)'}")
            
            elapsed = time.time() - start_time
            
            result = {
                "task_id": task["id"],
                "difficulty": task["difficulty"],
                "condition": cond,
                "order": f"{first_cond}-first",
                "prompt_file": prompt_file,
                "pre_test_pass": pre_pass,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            results.append(result)
    
    # Save results skeleton
    output = {
        "pilot": True,
        "generated": datetime.now(timezone.utc).isoformat(),
        "trials": results,
    }
    
    out_path = "/root/hermes-workspace/borg/dogfood/pilot_manifest.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n\nPilot manifest saved to: {out_path}")
    print(f"Total trials to run: {len(results)}")
    print("\nReady for agent dispatch.")


if __name__ == "__main__":
    main()
