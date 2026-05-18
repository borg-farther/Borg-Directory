#!/usr/bin/env python3
"""Analyze SWE-bench difficulty distribution and find tasks suitable for Borg experiment."""

from datasets import load_dataset
import json
from collections import Counter

print("Loading SWE-bench Verified...")
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')

# Check difficulty distribution
difficulties = Counter()
for t in ds:
    d = t.get("difficulty")
    difficulties[d] = difficulties.get(d, 0) + 1

print(f"\nDifficulty distribution:")
for d, count in sorted(difficulties.items(), key=lambda x: str(x[0])):
    print(f"  {d}: {count}")

# Check a few "easy" tasks — what do they look like?
print("\n\n--- Sample tasks by difficulty ---")
for difficulty_level in sorted(set(t.get("difficulty") for t in ds)):
    sample = [t for t in ds if t.get("difficulty") == difficulty_level][:2]
    print(f"\n[{difficulty_level}] ({len([t for t in ds if t.get('difficulty') == difficulty_level])} total)")
    for t in sample:
        print(f"  {t['instance_id']} ({t['repo']})")
        print(f"  Problem: {t['problem_statement'][:100]}...")
        ftps = t.get("FAIL_TO_PASS", "")
        if isinstance(ftps, str):
            ftps = json.loads(ftps) if ftps.startswith("[") else [ftps]
        print(f"  Tests to pass: {len(ftps)}")

# Find Django tasks (most common, likely best calibrated)
django_tasks = [t for t in ds if t["repo"] == "django/django"]
print(f"\n\n--- Django tasks by difficulty ---")
django_diffs = Counter(t.get("difficulty") for t in django_tasks)
for d, count in sorted(django_diffs.items(), key=lambda x: str(x[0])):
    print(f"  {d}: {count}")

# Check if there's hints_text
has_hints = sum(1 for t in ds if t.get("hints_text"))
print(f"\n{has_hints}/{len(ds)} tasks have hints_text")

# Save a subset of medium-difficulty Django tasks for the experiment
candidate_tasks = []
for t in ds:
    # We want tasks that are "medium" difficulty
    if t["repo"] == "django/django":
        candidate_tasks.append({
            "instance_id": t["instance_id"],
            "repo": t["repo"],
            "difficulty": t.get("difficulty"),
            "problem_statement": t["problem_statement"][:500],
            "has_hints": bool(t.get("hints_text")),
            "fail_to_pass_count": len(json.loads(t["FAIL_TO_PASS"]) if isinstance(t["FAIL_TO_PASS"], str) else t["FAIL_TO_PASS"]),
        })

with open("/root/hermes-workspace/borg/dogfood/v2_data/swebench_django_candidates.json", "w") as f:
    json.dump(candidate_tasks, f, indent=2)
print(f"\nSaved {len(candidate_tasks)} Django candidate tasks")
