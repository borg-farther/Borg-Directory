#!/usr/bin/env python3
"""Add reasoning traces to existing prompts for Condition B."""
import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
import json
from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
task_map = {t["instance_id"]: dict(t) for t in ds}

tasks = sys.argv[1:]
for tid in tasks:
    task = task_map.get(tid)
    if not task:
        print(f"SKIP {tid}: not found")
        continue
    
    hints = task.get("hints_text", "") or ""
    prompt_a_file = f"/tmp/cal_v2_{tid}_1.txt"
    prompt_b_file = f"/tmp/condB_{tid}_1.txt"
    
    with open(prompt_a_file) as f:
        prompt_a = f.read()
    
    trace_section = f"""

REASONING TRACE FROM PRIOR INVESTIGATION:
The following notes are from developers who investigated this bug.
They contain observations about the root cause and potential approaches.

{hints}

Use these notes to guide your debugging approach. Focus on understanding 
WHY the bug occurs and WHERE in the codebase to look."""
    
    prompt_b = prompt_a + trace_section
    
    with open(prompt_b_file, "w") as f:
        f.write(prompt_b)
    
    print(f"{tid}: B prompt at {prompt_b_file} ({len(prompt_b)} chars, +{len(trace_section)} trace)")
