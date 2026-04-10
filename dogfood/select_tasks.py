#!/usr/bin/env python3
"""Select 15 tasks from hard + medium difficulty, all with clean hints."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import json
import re
from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

def check_contamination(hints, patch):
    """Return True if hints are contaminated (contain solution info)."""
    if not hints or len(hints) < 50:
        return True  # minimal = unusable
    if re.search(r'(diff --git|@@ -|\+\+\+b/|---a/)', hints):
        return True  # contains diff
    # Check if fix lines appear in hints
    patch_lines = [l.strip() for l in patch.split('\n') if l.startswith('+') and not l.startswith('+++')]
    for line in patch_lines:
        clean = line[1:].strip()
        if len(clean) > 15 and clean in hints:
            return True
    return False

def rate_quality(hints):
    """Rate hint quality for reasoning trace value."""
    has_reasoning = bool(re.search(r'(because|therefore|the issue is|the problem is|root cause|the fix)', hints, re.I))
    has_approach = bool(re.search(r'(should|could|need to|try|approach|solution)', hints, re.I))
    if has_reasoning and has_approach:
        return 3, "GOOD"
    elif has_reasoning or has_approach:
        return 2, "OK"
    return 1, "WEAK"

# Collect candidates from hard AND medium
candidates = []
for t in ds:
    if t["repo"] != "django/django":
        continue
    diff = t.get("difficulty", "")
    if diff not in ("1-4 hours", "15 min - 1 hour"):
        continue
    
    hints = t.get("hints_text", "") or ""
    patch = t.get("patch", "")
    
    if check_contamination(hints, patch):
        continue
    
    fail_to_pass = t["FAIL_TO_PASS"]
    if isinstance(fail_to_pass, str):
        fail_to_pass = json.loads(fail_to_pass)
    
    # Prefer tasks with 1-5 failing tests
    if len(fail_to_pass) > 8:
        continue
    
    score, label = rate_quality(hints)
    
    candidates.append({
        "instance_id": t["instance_id"],
        "difficulty": diff,
        "hints_length": len(hints),
        "quality": label,
        "quality_score": score,
        "num_tests": len(fail_to_pass),
        "problem_length": len(t["problem_statement"]),
        "raw": dict(t),
    })

# Sort: hard first, then by quality score, then by hints length
candidates.sort(key=lambda x: (
    0 if x["difficulty"] == "1-4 hours" else 1,  # hard first
    -x["quality_score"],  # better quality first
    -x["hints_length"],  # longer hints first
))

print(f"Total clean candidates: {len(candidates)}")
print(f"  Hard (1-4 hours): {sum(1 for c in candidates if c['difficulty'] == '1-4 hours')}")
print(f"  Medium (15 min - 1 hour): {sum(1 for c in candidates if c['difficulty'] == '15 min - 1 hour')}")

# Select top 15
selected = candidates[:15]

print(f"\nSELECTED 15 TASKS:")
for i, c in enumerate(selected):
    print(f"  {i+1:2d}. {c['instance_id']} [{c['difficulty']}] "
          f"quality={c['quality']} hints={c['hints_length']}chars tests={c['num_tests']}")

# Save
with open("/root/hermes-workspace/borg/dogfood/v2_data/selected_swebench_tasks.json", "w") as f:
    json.dump({
        "selected": [{"instance_id": c["instance_id"], "difficulty": c["difficulty"],
                      "quality": c["quality"], "hints_length": c["hints_length"],
                      "num_tests": c["num_tests"]} for c in selected],
        "total_candidates": len(candidates),
    }, f, indent=2)

# Also save full task data for each selected task
import os
task_dir = "/root/hermes-workspace/borg/dogfood/swebench_experiment"
os.makedirs(task_dir, exist_ok=True)

for c in selected:
    t = c["raw"]
    tid = t["instance_id"]
    tdir = os.path.join(task_dir, tid)
    os.makedirs(tdir, exist_ok=True)
    
    # Save task data (without raw record to save space)
    task_data = {k: v for k, v in t.items()}
    with open(os.path.join(tdir, "task_data.json"), "w") as f:
        json.dump(task_data, f, indent=2, default=str)
    
    # Save prompt (Condition A)
    fail_to_pass = t["FAIL_TO_PASS"]
    if isinstance(fail_to_pass, str):
        fail_to_pass = json.loads(fail_to_pass)
    
    with open(os.path.join(tdir, "prompt_A.txt"), "w") as f:
        f.write(f"""You are an expert software engineer. Fix the bug described below.
The Django codebase is at /testbed.

ISSUE:
{t['problem_statement']}

TESTS THAT MUST PASS AFTER YOUR FIX:
{json.dumps(fail_to_pass, indent=2)}

Use Django's test runner to verify:
cd /testbed && python tests/runtests.py {' '.join(test.split('(')[0].split('.')[-1] if '(' in test else test.replace('.', '/') for test in fail_to_pass[:3])} --verbosity 2

Fix the bug by editing the appropriate source files in /testbed/django/.""")
    
    # Save prompt (Condition B) — includes reasoning trace
    hints = t.get("hints_text", "")
    with open(os.path.join(tdir, "prompt_B.txt"), "w") as f:
        f.write(f"""You are an expert software engineer. Fix the bug described below.
The Django codebase is at /testbed.

ISSUE:
{t['problem_statement']}

REASONING TRACE FROM PRIOR INVESTIGATION:
The following notes are from developers who investigated this bug.
They contain observations about the root cause and potential approaches.

{hints}

TESTS THAT MUST PASS AFTER YOUR FIX:
{json.dumps(fail_to_pass, indent=2)}

Use Django's test runner to verify:
cd /testbed && python tests/runtests.py {' '.join(test.split('(')[0].split('.')[-1] if '(' in test else test.replace('.', '/') for test in fail_to_pass[:3])} --verbosity 2

Fix the bug by editing the appropriate source files in /testbed/django/.""")

print(f"\nTask data saved to {task_dir}")
