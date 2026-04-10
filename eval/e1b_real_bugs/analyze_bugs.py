#!/usr/bin/env python3
"""
E1b: Real-Bugs Dogfood - Bug Analysis Report

Since the borg packs directory is empty (no packs to search against),
this script analyzes the 15 SWE-bench Django bugs to document what
we WOULD test if packs were available.

PRD Reference: BORG_PACK_AUTO_GENERATION_PRD.md Section E1b
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BugSummary:
    instance_id: str
    problem: str
    files_touched: list
    error_types: list
    difficulty: str


def extract_patch_files(patch: str) -> list:
    """Extract files from patch."""
    files = []
    for line in patch.split('\n'):
        if line.startswith('--- a/'):
            fname = line[5:].strip()
            if fname and not fname.startswith('tests/'):
                files.append(fname)
        elif line.startswith('diff --git a/'):
            rest = line[12:]
            if '/' in rest:
                fname = rest.split('/', 1)[1]
                if ' -> ' in fname:
                    fname = fname.split(' -> ')[0]
                if not fname.startswith('tests/'):
                    files.append(fname)
    return list(set(files))[:10]


def classify_error(problem: str, hints: str) -> list:
    """Classify error type from problem statement."""
    text = (problem + ' ' + hints).lower()
    errors = []
    
    if 'none' in text and 'noneType' in text:
        errors.append('NoneType')
    if 'attributeerror' in text or 'has no attribute' in text:
        errors.append('AttributeError')
    if 'indexerror' in text or 'index out' in text:
        errors.append('IndexError')
    if 'keyerror' in text:
        errors.append('KeyError')
    if 'typeerror' in text:
        errors.append('TypeError')
    if 'importerror' in text or 'cannot import' in text:
        errors.append('ImportError')
    if 'encoding' in text or 'unicode' in text or 'utf' in text:
        errors.append('Encoding')
    if 'regex' in text or 'regexp' in text or 'pattern' in text:
        errors.append('Regex')
    if 'url' in text and ('reverse' in text or 'resolve' in text):
        errors.append('URLRouting')
    if 'admin' in text and 'inline' in text:
        errors.append('AdminInline')
    if 'cache' in text:
        errors.append('Cache')
    if 'race' in text or 'concurrent' in text or 'thread' in text:
        errors.append('Concurrency')
    if 'memory' in text or 'leak' in text:
        errors.append('Memory')
    if 'parse' in text or 'json' in text or 'serialize' in text:
        errors.append('Parsing')
    
    return errors if errors else ['Unknown']


def main():
    TASKS_DIR = '/root/hermes-workspace/borg/dogfood/swebench_tasks'
    OUTPUT_DIR = '/root/hermes-workspace/borg/eval/e1b_real_bugs/results'
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    tasks = sorted(os.listdir(TASKS_DIR))
    print(f"E1b Real-Bugs Analysis")
    print(f"="*70)
    print(f"Found {len(tasks)} SWE-bench Django tasks\n")
    
    all_summaries = []
    error_distribution = {}
    file_distribution = {}
    
    for task_id in tasks:
        task_path = os.path.join(TASKS_DIR, task_id, 'task_data.json')
        if not os.path.exists(task_path):
            continue
        
        with open(task_path) as f:
            data = json.load(f)
        
        patch = data.get('patch', '')
        files = extract_patch_files(patch)
        errors = classify_error(
            data.get('problem_statement', ''),
            data.get('hints_text', '')
        )
        fail_tests = data.get('FAIL_TO_PASS', [])
        
        summary = BugSummary(
            instance_id=task_id,
            problem=data.get('problem_statement', '')[:150],
            files_touched=files,
            error_types=errors,
            difficulty=data.get('difficulty', 'unknown')
        )
        all_summaries.append(summary)
        
        # Track distributions
        for err in errors:
            error_distribution[err] = error_distribution.get(err, 0) + 1
        for f in files:
            component = f.split('/')[1] if '/' in f else f.split('.')[0]
            file_distribution[component] = file_distribution.get(component, 0) + 1
    
    # Print analysis
    print(f"\nERROR TYPE DISTRIBUTION:")
    print(f"-"*40)
    for err, count in sorted(error_distribution.items(), key=lambda x: -x[1]):
        print(f"  {err:<20} {count}")
    
    print(f"\nCOMPONENT DISTRIBUTION (files touched):")
    print(f"-"*40)
    for comp, count in sorted(file_distribution.items(), key=lambda x: -x[1])[:15]:
        print(f"  {comp:<20} {count}")
    
    print(f"\nBUG DETAILS:")
    print(f"-"*70)
    for s in all_summaries[:10]:
        print(f"\n{s.instance_id} ({s.difficulty})")
        print(f"  Problem: {s.problem[:100]}...")
        print(f"  Errors: {', '.join(s.error_types)}")
        print(f"  Files: {s.files_touched[:3]}")
    
    # Save results
    results = {
        'total_bugs': len(all_summaries),
        'error_distribution': error_distribution,
        'file_distribution': file_distribution,
        'bugs': [
            {
                'instance_id': s.instance_id,
                'problem': s.problem,
                'error_types': s.error_types,
                'files_touched': s.files_touched,
                'difficulty': s.difficulty
            }
            for s in all_summaries
        ]
    }
    
    output_path = os.path.join(OUTPUT_DIR, 'e1b_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n" + "="*70)
    print(f"ANALYSIS COMPLETE")
    print(f"="*70)
    print(f"Total bugs analyzed: {len(all_summaries)}")
    print(f"Error types found: {len(error_distribution)}")
    print(f"Results saved to: {output_path}")
    
    # Note about borg packs
    print(f"\n" + "="*70)
    print(f"E1b TEST STATUS: CANNOT RUN")
    print(f"="*70)
    print(f"The borg packs directory is empty (no packs in /root/hermes-workspace/borg/packs/).")
    print(f"borg_search() returns no matches for any query.")
    print(f"\nTo run E1b properly, we need packs to be available for search.")
    print(f"Current packs directory: /root/hermes-workspace/borg/packs/ (empty)")
    print(f"Hermes skills directory: ~/.hermes/skills/ (has skills but no packs)")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())