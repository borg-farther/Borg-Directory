#!/usr/bin/env python3
"""Finalize task selection — add 4 medium tasks to get to 15."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
import json, re, os
from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

# Already selected clean tasks
already = {
    "django__django-15128", "django__django-13344", "django__django-13212",
    "django__django-11400", "django__django-15503", "django__django-12708",
    "django__django-16560", "django__django-10554", "django__django-11138",
    "django__django-12754", "django__django-15252",
}

def is_contaminated(hints, patch):
    if not hints or len(hints) < 50:
        return True
    if re.search(r'(diff --git|@@ -|\+\+\+b/|---a/)', hints):
        return True
    patch_lines = [l.strip() for l in patch.split('\n') if l.startswith('+') and not l.startswith('+++')]
    for line in patch_lines:
        clean = line[1:].strip()
        if len(clean) > 15 and clean in hints:
            return True
    return False

# Find 4 more medium tasks
extras = []
for t in ds:
    if t["repo"] != "django/django":
        continue
    if t.get("difficulty") != "15 min - 1 hour":
        continue
    if t["instance_id"] in already:
        continue
    
    hints = t.get("hints_text", "") or ""
    patch = t.get("patch", "")
    
    if is_contaminated(hints, patch):
        continue
    
    fail_to_pass = t["FAIL_TO_PASS"]
    if isinstance(fail_to_pass, str):
        fail_to_pass = json.loads(fail_to_pass)
    if len(fail_to_pass) > 5:
        continue
    
    has_reasoning = bool(re.search(r'(because|therefore|the issue|the problem|root cause)', hints, re.I))
    has_approach = bool(re.search(r'(should|could|need to|approach|solution)', hints, re.I))
    score = (2 if has_reasoning else 0) + (1 if has_approach else 0)
    
    extras.append({
        "instance_id": t["instance_id"],
        "difficulty": t.get("difficulty"),
        "hints_length": len(hints),
        "quality_score": score,
        "num_tests": len(fail_to_pass),
    })

# Sort by quality
extras.sort(key=lambda x: (-x["quality_score"], -x["hints_length"]))

# Take top 4
selected_extras = extras[:4]
print("4 additional medium tasks:")
for e in selected_extras:
    print(f"  {e['instance_id']} hints={e['hints_length']}chars tests={e['num_tests']} score={e['quality_score']}")

# Final 15
final_ids = list(already) + [e["instance_id"] for e in selected_extras]
print(f"\nFINAL 15 TASKS:")
for tid in sorted(final_ids):
    print(f"  {tid}")

# Save final selection
with open("/root/hermes-workspace/borg/dogfood/v2_data/final_task_selection.json", "w") as f:
    json.dump({"tasks": sorted(final_ids), "count": len(final_ids)}, f, indent=2)
print(f"\nSaved to final_task_selection.json")
