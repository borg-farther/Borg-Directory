#!/usr/bin/env python3
"""
Analyze and filter hints_text for all selected tasks.
Produces clean reasoning traces suitable for the experiment.
"""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')

import json
import re
from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

# Get all hard Django tasks
tasks = []
for t in ds:
    if t["repo"] != "django/django":
        continue
    if t.get("difficulty") != "1-4 hours":
        continue
    hints = t.get("hints_text", "") or ""
    tasks.append({
        "instance_id": t["instance_id"],
        "hints_text": hints,
        "problem_statement": t["problem_statement"],
        "patch": t["patch"],
        "FAIL_TO_PASS": json.loads(t["FAIL_TO_PASS"]) if isinstance(t["FAIL_TO_PASS"], str) else t["FAIL_TO_PASS"],
    })

print(f"Total hard Django tasks: {len(tasks)}")

# Contamination checks
contaminated = []
clean = []
minimal = []

for task in tasks:
    tid = task["instance_id"]
    hints = task["hints_text"]
    
    # Check 1: Contains diff/patch code
    has_diff = bool(re.search(r'(diff --git|@@ -|\+\+\+b/|---a/)', hints))
    
    # Check 2: Contains Python code blocks with actual fixes
    has_code = bool(re.search(r'```python.*?```', hints, re.DOTALL))
    
    # Check 3: Contains file paths from the gold patch
    patch_files = re.findall(r'a/([\w/]+\.py)', task["patch"])
    mentions_patch_files = any(f in hints for f in patch_files)
    
    # Check 4: Too short to be useful
    is_minimal = len(hints) < 50
    
    # Check 5: Contains the actual fix line from gold patch
    patch_lines = [l.strip() for l in task["patch"].split('\n') if l.startswith('+') and not l.startswith('+++')]
    contains_fix = any(line[1:].strip() in hints for line in patch_lines if len(line) > 10)
    
    if has_diff or contains_fix:
        contaminated.append(tid)
        print(f"  CONTAMINATED: {tid} (diff={has_diff}, fix_line={contains_fix})")
    elif is_minimal:
        minimal.append(tid)
        print(f"  MINIMAL: {tid} ({len(hints)} chars)")
    else:
        clean.append(tid)
        # Classify hint quality
        has_reasoning = bool(re.search(r'(because|therefore|the issue is|the problem is|root cause|the fix)', hints, re.I))
        has_approach = bool(re.search(r'(should|could|need to|try|approach|solution)', hints, re.I))
        quality = "GOOD" if has_reasoning and has_approach else "OK" if has_reasoning or has_approach else "WEAK"
        print(f"  CLEAN [{quality}]: {tid} ({len(hints)} chars)")

print(f"\nSUMMARY:")
print(f"  Clean: {len(clean)}")
print(f"  Contaminated: {len(contaminated)}")
print(f"  Minimal: {len(minimal)}")

# Save clean task list
result = {
    "clean_tasks": clean,
    "contaminated_tasks": contaminated,
    "minimal_tasks": minimal,
    "total": len(tasks),
}
with open("/root/hermes-workspace/borg/dogfood/v2_data/hints_filter_results.json", "w") as f:
    json.dump(result, f, indent=2)

print(f"\nSaved to hints_filter_results.json")
