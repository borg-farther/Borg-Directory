#!/usr/bin/env python3
"""Analyze SWE-bench Django tasks for E1b report."""
import json
import os

TASKS_DIR = '/root/hermes-workspace/borg/dogfood/swebench_tasks'
OUTPUT_DIR = '/root/hermes-workspace/borg/eval/e1b_real_bugs/results'

tasks = sorted(os.listdir(TASKS_DIR))

print(f"Found {len(tasks)} SWE-bench Django tasks\n")

task_summaries = []
for t in tasks:
    task_path = os.path.join(TASKS_DIR, t, 'task_data.json')
    if not os.path.exists(task_path):
        continue
    with open(task_path) as f:
        d = json.load(f)
    
    patch = d.get('patch', '')
    files = [l.strip()[2:] for l in patch.split('\n') if l.startswith('a/')]
    fail_tests = d.get('FAIL_TO_PASS', [])
    
    summary = {
        'instance_id': t,
        'problem': d.get('problem_statement', '')[:200],
        'patched_files': files[:3],
        'fail_tests': fail_tests,
        'difficulty': d.get('difficulty', 'unknown'),
    }
    task_summaries.append(summary)
    
    print(f"=== {t} ===")
    print(f"Problem: {summary['problem'][:150]}...")
    print(f"Files: {summary['patched_files']}")
    print(f"Fail: {fail_tests[:2]}")
    print()

# Save results
os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(os.path.join(OUTPUT_DIR, 'task_summaries.json'), 'w') as f:
    json.dump(task_summaries, f, indent=2)

print(f"\nSaved summaries to {OUTPUT_DIR}/task_summaries.json")