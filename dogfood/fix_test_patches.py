#!/usr/bin/env python3
"""Investigate why test_patches don't apply for 12754, 13315, 15503."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
import json, subprocess, shutil, os
from pathlib import Path
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task_map = {t["instance_id"]: dict(t) for t in ds}

problem_tasks = ["django__django-12754", "django__django-13315", "django__django-15503"]
WORKSPACE = Path("/tmp/borg_patch_fix")

for tid in problem_tasks:
    task = task_map[tid]
    spec = make_test_spec(task)
    image = spec.instance_image_key
    
    ws = WORKSPACE / tid
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    
    # Extract
    temp = f"borg_pf_{tid.replace('/', '_')}"
    subprocess.run(["docker", "run", "-d", "--name", temp, image, "tail", "-f", "/dev/null"],
                  capture_output=True, timeout=30)
    subprocess.run(["docker", "cp", f"{temp}:/testbed", str(ws / "testbed")],
                  capture_output=True, timeout=120)
    subprocess.run(["docker", "rm", "-f", temp], capture_output=True, timeout=10)
    
    # Try applying test patch
    tp = task.get("test_patch", "")
    (ws / "test_patch.diff").write_text(tp)
    
    r = subprocess.run(["git", "apply", "--check", str(ws / "test_patch.diff")],
                      cwd=ws / "testbed", capture_output=True, text=True, timeout=30)
    
    if r.returncode == 0:
        print(f"{tid}: test_patch applies cleanly ✓")
        # Actually apply it
        subprocess.run(["git", "apply", str(ws / "test_patch.diff")],
                      cwd=ws / "testbed", capture_output=True, timeout=30)
        
        # Check if test method exists
        ftp = task["FAIL_TO_PASS"]
        if isinstance(ftp, str):
            ftp = json.loads(ftp)
        
        for test in ftp:
            if '(' in test:
                test_name = test.split(' ')[0]
                module = test.split('(')[1].rstrip(')')
            else:
                test_name = test
                module = test
            
            # Search for test method in files
            r2 = subprocess.run(["grep", "-r", test_name.split('.')[-1] if '.' in test_name else test_name, 
                                str(ws / "testbed" / "tests")],
                              capture_output=True, text=True, timeout=10)
            found = "def " + (test_name.split('.')[-1] if '.' in test_name else test_name) in r2.stdout
            print(f"  Test '{test_name}': {'FOUND' if found else 'NOT FOUND'}")
    else:
        print(f"{tid}: test_patch FAILS to apply")
        print(f"  Error: {r.stderr[:200]}")
    
    shutil.rmtree(ws)
