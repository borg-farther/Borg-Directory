#!/usr/bin/env python3
"""
Phase 1: Pre-Experiment Verification
V1: Gold patch test — confirm each task IS solvable
V2: Hints contamination — confirm no solution leakage
V3: Prompt integrity — confirm A and B differ only by trace
"""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

WORKSPACE_BASE = Path("/tmp/borg_verify")
DATA_DIR = Path("/root/hermes-workspace/borg/dogfood/v2_data")

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task_map = {t["instance_id"]: dict(t) for t in ds}

with open(DATA_DIR / "final_task_selection.json") as f:
    task_ids = json.load(f)["tasks"]

# Only test tasks we actually calibrated
calibrated = [
    "django__django-10554", "django__django-11087", "django__django-11138",
    "django__django-11265", "django__django-11400", "django__django-12708",
    "django__django-12754", "django__django-13315", "django__django-13344",
    "django__django-15128", "django__django-15503", "django__django-16560",
]

results = {"verification": [], "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")}

for tid in calibrated:
    print(f"\n{'='*60}")
    print(f"VERIFYING: {tid}")
    task = task_map[tid]
    spec = make_test_spec(task)
    image = spec.instance_image_key
    
    v_result = {"task_id": tid, "V1": None, "V2": None, "V3": None}
    
    # === V2: Hints Contamination ===
    hints = task.get("hints_text", "") or ""
    patch = task.get("patch", "")
    
    has_diff = bool(re.search(r'(diff --git|@@ -|\+\+\+b/|---a/)', hints))
    patch_lines = [l[1:].strip() for l in patch.split('\n') if l.startswith('+') and not l.startswith('+++') and len(l) > 15]
    contains_fix = any(line in hints for line in patch_lines)
    hints_ok = len(hints) >= 50 and not has_diff and not contains_fix
    
    v_result["V2"] = {
        "pass": hints_ok,
        "has_diff": has_diff,
        "contains_fix_line": contains_fix,
        "hints_length": len(hints),
    }
    print(f"  V2 (hints contamination): {'PASS' if hints_ok else 'FAIL'}")
    if not hints_ok:
        print(f"    has_diff={has_diff}, contains_fix={contains_fix}, length={len(hints)}")
    
    # === V3: Prompt Integrity ===
    ftp = task["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)
    
    prompt_a = f"ISSUE:\n{task['problem_statement']}\n\nTESTS:\n{json.dumps(ftp)}"
    prompt_b = prompt_a + f"\n\nREASONING TRACE:\n{hints}"
    
    a_has_hints = hints in prompt_a
    b_has_hints = hints in prompt_b
    prompts_share_base = task['problem_statement'] in prompt_a and task['problem_statement'] in prompt_b
    
    v_result["V3"] = {
        "pass": (not a_has_hints) and b_has_hints and prompts_share_base,
        "a_has_hints": a_has_hints,
        "b_has_hints": b_has_hints,
        "base_shared": prompts_share_base,
    }
    print(f"  V3 (prompt integrity): {'PASS' if v_result['V3']['pass'] else 'FAIL'}")
    
    # === V1: Gold Patch Test ===
    workspace = WORKSPACE_BASE / tid.replace("/", "_")
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    
    try:
        # Extract source
        temp = f"borg_vfy_{int(time.time())}"
        subprocess.run(["docker", "run", "-d", "--name", temp, image, "tail", "-f", "/dev/null"],
                      capture_output=True, timeout=30)
        subprocess.run(["docker", "cp", f"{temp}:/testbed", str(workspace / "testbed")],
                      capture_output=True, timeout=120)
        subprocess.run(["docker", "rm", "-f", temp], capture_output=True, timeout=10)
        
        # Apply test patch
        tp = task.get("test_patch", "")
        if tp:
            (workspace / "test_patch.diff").write_text(tp)
            r = subprocess.run(["git", "apply", str(workspace / "test_patch.diff")],
                          cwd=workspace / "testbed", capture_output=True, text=True, timeout=30)
            test_patch_applied = r.returncode == 0
        else:
            test_patch_applied = True
        
        # Start container with mount
        container = f"borg_vfy_{tid.replace('/', '_')}_{int(time.time())}"
        subprocess.run(
            ["docker", "run", "-d", "--name", container, "--memory", "4g",
             "-v", f"{str(workspace / 'testbed')}:/testbed", image, "tail", "-f", "/dev/null"],
            capture_output=True, timeout=30)
        
        # Build test command
        test_args = set()
        for test in ftp:
            if '(' in test:
                test_args.add(test.split('(')[1].rstrip(')'))
            else:
                test_args.add(test)
        test_cmd = f"source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py {' '.join(test_args)} --verbosity 0"
        
        # Check tests FAIL before fix
        r = subprocess.run(["docker", "exec", container, "bash", "-c", test_cmd],
                          capture_output=True, text=True, timeout=120)
        tests_fail_before = r.returncode != 0 or "FAILED" in r.stdout + r.stderr
        
        # Apply gold patch
        gold_patch = task.get("patch", "")
        (workspace / "gold_patch.diff").write_text(gold_patch)
        r = subprocess.run(["git", "apply", str(workspace / "gold_patch.diff")],
                      cwd=workspace / "testbed", capture_output=True, text=True, timeout=30)
        gold_applied = r.returncode == 0
        
        # Check tests PASS after gold fix
        if gold_applied:
            r = subprocess.run(["docker", "exec", container, "bash", "-c", test_cmd],
                              capture_output=True, text=True, timeout=120)
            tests_pass_after = r.returncode == 0 and "FAILED" not in r.stdout + r.stderr
        else:
            tests_pass_after = False
        
        v_result["V1"] = {
            "pass": test_patch_applied and tests_fail_before and gold_applied and tests_pass_after,
            "test_patch_applied": test_patch_applied,
            "tests_fail_before": tests_fail_before,
            "gold_patch_applied": gold_applied,
            "tests_pass_after": tests_pass_after,
        }
        
        status = "PASS" if v_result["V1"]["pass"] else "FAIL"
        print(f"  V1 (gold patch): {status}")
        if not v_result["V1"]["pass"]:
            print(f"    patch_applied={test_patch_applied}, fail_before={tests_fail_before}, "
                  f"gold_applied={gold_applied}, pass_after={tests_pass_after}")
        
        # Cleanup
        subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=10)
        
    except Exception as e:
        v_result["V1"] = {"pass": False, "error": str(e)}
        print(f"  V1 (gold patch): ERROR — {e}")
    
    # Cleanup workspace
    if workspace.exists():
        shutil.rmtree(workspace)
    
    results["verification"].append(v_result)

# Summary
print(f"\n{'='*60}")
print("VERIFICATION SUMMARY")
print(f"{'='*60}")

all_pass = True
for v in results["verification"]:
    tid = v["task_id"]
    v1 = v["V1"]["pass"] if v["V1"] else False
    v2 = v["V2"]["pass"] if v["V2"] else False
    v3 = v["V3"]["pass"] if v["V3"] else False
    overall = v1 and v2 and v3
    if not overall:
        all_pass = False
    status = "✓ ALL PASS" if overall else "✗ ISSUES"
    print(f"  {tid}: {status} (V1={v1}, V2={v2}, V3={v3})")

print(f"\nOVERALL: {'ALL VERIFICATIONS PASS — PROCEED WITH EXPERIMENT' if all_pass else 'SOME VERIFICATIONS FAILED — INVESTIGATE BEFORE PROCEEDING'}")

# Save
with open(DATA_DIR / "swebench_results" / "verification_log.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to verification_log.json")
