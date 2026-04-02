#!/usr/bin/env python3
"""Load SWE-bench Verified dataset and analyze task difficulty."""

from datasets import load_dataset
import json

print("Loading SWE-bench Verified...")
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
print(f'Total tasks: {len(ds)}')
print(f'Columns: {ds.column_names}')

# Show first 3 tasks
for i in range(min(3, len(ds))):
    t = ds[i]
    print(f'\n--- Task {i+1} ---')
    print(f'ID: {t["instance_id"]}')
    print(f'Repo: {t["repo"]}')
    print(f'Problem: {t["problem_statement"][:200]}...')
    fail_to_pass = t.get("FAIL_TO_PASS", "N/A")
    print(f'FAIL_TO_PASS: {fail_to_pass[:200] if isinstance(fail_to_pass, str) else fail_to_pass}')

# Count by repo
repos = {}
for t in ds:
    repo = t["repo"]
    repos[repo] = repos.get(repo, 0) + 1

print(f'\n--- Repos ---')
for repo, count in sorted(repos.items(), key=lambda x: -x[1]):
    print(f'  {repo}: {count} tasks')

# Save all task IDs and metadata for analysis
tasks = []
for t in ds:
    tasks.append({
        "instance_id": t["instance_id"],
        "repo": t["repo"],
        "problem_length": len(t["problem_statement"]),
        "hints_length": len(t.get("hints_text", "") or ""),
        "test_patch_length": len(t.get("test_patch", "") or ""),
    })

with open("/root/hermes-workspace/borg/dogfood/v2_data/swebench_verified_tasks.json", "w") as f:
    json.dump(tasks, f, indent=2)
print(f'\nSaved {len(tasks)} task metadata to swebench_verified_tasks.json')
