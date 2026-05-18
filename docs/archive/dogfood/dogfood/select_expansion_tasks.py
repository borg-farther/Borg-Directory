#!/usr/bin/env python3
"""Select 10 more medium-difficulty Django tasks for experiment expansion."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
import json, re
from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

# Already used tasks
used = {
    "django__django-10554", "django__django-11087", "django__django-11138",
    "django__django-11265", "django__django-11400", "django__django-12708",
    "django__django-12754", "django__django-13212", "django__django-13315",
    "django__django-13344", "django__django-15128", "django__django-15252",
    "django__django-15503", "django__django-15732", "django__django-16560",
    "django__django-16631",
}

def is_contaminated(hints, patch):
    if not hints or len(hints) < 50:
        return True
    if re.search(r'(diff --git|@@ -|\+\+\+b/|---a/)', hints):
        return True
    patch_lines = [l[1:].strip() for l in patch.split('\n') if l.startswith('+') and not l.startswith('+++') and len(l) > 15]
    for line in patch_lines:
        if line in hints:
            return True
    return False

candidates = []
for t in ds:
    if t["repo"] != "django/django":
        continue
    if t["instance_id"] in used:
        continue
    if t.get("difficulty") not in ("15 min - 1 hour", "1-4 hours"):
        continue
    
    hints = t.get("hints_text", "") or ""
    patch = t.get("patch", "")
    if is_contaminated(hints, patch):
        continue
    
    ftp = t["FAIL_TO_PASS"]
    if isinstance(ftp, str):
        ftp = json.loads(ftp)
    if len(ftp) > 5:
        continue
    
    has_reasoning = bool(re.search(r'(because|therefore|the issue|the problem|root cause)', hints, re.I))
    has_approach = bool(re.search(r'(should|could|need to|approach|solution|fix)', hints, re.I))
    score = (2 if has_reasoning else 0) + (1 if has_approach else 0)
    
    candidates.append({
        "instance_id": t["instance_id"],
        "difficulty": t.get("difficulty"),
        "hints_length": len(hints),
        "quality_score": score,
        "num_tests": len(ftp),
    })

candidates.sort(key=lambda x: (-x["quality_score"], -x["hints_length"]))
selected = candidates[:10]

print(f"Total clean candidates: {len(candidates)}")
print(f"\nSELECTED 10 EXPANSION TASKS:")
for i, c in enumerate(selected):
    print(f"  {i+1:2d}. {c['instance_id']} [{c['difficulty']}] q={c['quality_score']} hints={c['hints_length']}chars tests={c['num_tests']}")

# Save
with open("/root/hermes-workspace/borg/dogfood/v2_data/expansion_tasks.json", "w") as f:
    json.dump({"tasks": [c["instance_id"] for c in selected]}, f, indent=2)
print(f"\nSaved to expansion_tasks.json")
