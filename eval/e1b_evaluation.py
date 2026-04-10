#!/usr/bin/env python3
"""
E1b: Dogfood evaluation — Does borg guidance DIRECT agents toward correct subsystems?

Tests whether the investigation_trail in borg packs targets the same Django 
subsystems (db, urls, forms, etc.) as the actual patch.

METRIC DESIGN:
- guided_hit: Does at least one trail subsystem overlap with a patch subsystem?
- baseline_hit: Expected probability of random 3-subsystem sample overlapping patch.
  Computed analytically as: P(at least one match) = 1 - P(no match)
  where P(no match) = C(n-k,3)/C(n,3), n=total_subsystems, k=patch_subsystems.
- delta: guided_hit_rate - baseline_hit_rate (positive = borg helps).

NOTE: File-overlap is a PROXY metric. True evaluation requires running actual
agent sessions and measuring whether agents with borg guidance reach correct
patches faster/more often than without. This script tests pack quality only.
"""
import json, yaml, re, sys
from pathlib import Path
from datetime import datetime
from math import comb

SWEBENCH_DIR = Path('/root/swebench/data')
BORG_REPO = Path('/root/hermes-workspace/borg')
SKILLS_DIR = BORG_REPO / 'skills'
RESULTS_DIR = Path('/root/eval_results')
RESULTS_DIR.mkdir(exist_ok=True)

ERROR_MAP = {
    'AttributeError': 'null_pointer_chain',
    'TypeError': 'type_mismatch',
    'IntegrityError': ['circular_dependency', 'missing_foreign_key'],
    'OperationalError': ['migration_state_desync', 'schema_drift'],
    'ImportError': 'import_cycle',
    'ModuleNotFoundError': 'missing_dependency',
    'PermissionError': 'permission_denied',
}

# All Django subsystems found across SWE-bench Django patches
DJANGO_SUBSYSTEMS = [
    'django.db', 'django.urls', 'django.forms', 'django.views', 'django.middleware',
    'django.core', 'django.contrib', 'django.apps', 'django.conf', 'django.http',
    'django.utils', 'django.template', 'django.test', 'django.contrib.auth',
    'django.contrib.admin', 'django.db.backends', 'django.db.migrations',
    'django.db.models', 'django.db.models.sql', 'django.db.models.fields',
    'django.core.handlers', 'django.core.cache', 'django.core.mail',
    'django.core.management', 'django.core.serializers', 'django.forms.fields',
    'django.http.request', 'django.http.response', 'django.views.generic',
    'django.views.i18n', 'django.urls.resolvers', 'django.utils.functional',
    'django.utils.html', 'django.utils.translation', 'django.test.utils',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.contenttypes',
]

def load_swebench_tasks(max_count=30):
    tasks = []
    for f in sorted(SWEBENCH_DIR.glob('django__django-*.json'))[:max_count*3]:
        if '__main__' in f.name or 'test' in f.name:
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
            if not isinstance(data, dict):
                continue
            patch = data.get('patch', '')
            if not patch.strip():
                continue
            files = []
            for line in patch.split('\n'):
                if line.startswith('diff --git'):
                    try:
                        part = line.split('diff --git a/')[1]
                        file = part.split(' b/')[0] if ' b/' in part else part.split()[0]
                        if file:
                            files.append(file)
                    except:
                        pass
            tasks.append({
                'instance_id': data.get('instance_id', f.stem),
                'error_types': data.get('error_types', []),
                'problem_statement': data.get('problem_statement', '')[:500],
                'hints_text': data.get('hints_text', '')[:500],
                'patch': patch,
                'files_in_patch': files,
            })
        except:
            pass
        if len(tasks) >= max_count:
            break
    return tasks

def classify_task(task):
    hints = (task.get('problem_statement', '') + ' ' + task.get('hints_text', '')).lower()
    
    for err in task.get('error_types', []):
        if err in ERROR_MAP:
            pc = ERROR_MAP[err]
            return pc[0] if isinstance(pc, list) else pc
    
    keyword_map = {
        'null_pointer_chain': ['none has no attribute', "'none' has no attribute", 'attr is none'],
        'type_mismatch': ['type mismatch', 'invalid type', 'expected .* got'],
        'circular_dependency': ['circular import', 'circular dependency'],
        'missing_foreign_key': ['foreign key', 'integrity error'],
        'migration_state_desync': ['migration', 'operational error', 'schema'],
        'schema_drift': ['schema mismatch', 'schema'],
        'import_cycle': ['import error', 'module not found', 'cannot import'],
        'missing_dependency': ['modulenotfounderror', 'no module named', 'missing'],
    }
    
    for pc, keywords in keyword_map.items():
        if any(re.search(kw, hints) for kw in keywords):
            return pc
    return 'unknown'

def load_pack(problem_class):
    if problem_class == 'unknown':
        return None
    for pf in sorted(SKILLS_DIR.glob('*.md')):
        content = pf.read_text()
        if not content.startswith('---'):
            continue
        yaml_text = content[3:]
        if yaml_text.startswith('\n'):
            yaml_text = yaml_text[1:]
        idx = yaml_text.find('\n---')
        if idx < 0:
            continue
        try:
            fm = yaml.safe_load(yaml_text[:idx])
            if fm and fm.get('problem_class') == problem_class:
                return fm
        except:
            pass
    return None

def file_to_subsystem(file_path):
    """Map a file path to Django subsystem."""
    if not file_path:
        return None
    # django/db/models/query.py -> django.db.models
    m = re.match(r'django/(\w+)(?:/(\w+))?(?:/(\w+))?', file_path)
    if m:
        parts = [p for p in m.groups() if p and p not in ('py', '__pycache__')]
        if len(parts) >= 2:
            return 'django.' + parts[0] + '.' + parts[1]
        elif len(parts) == 1:
            return 'django.' + parts[0]
    return None

def compute_baseline_hit_rate(n_patch_subs, n_total=31, n_sample=3):
    """Analytically compute P(random 3 subsystems intersects patch).

    Without replacement from n_total, probability that at least one sampled
    subsystem is in the patch of size k:
        P(hit) = 1 - C(n-k, 3) / C(n, 3)
    """
    k = n_patch_subs
    if k <= 0:
        return 0.0
    if k >= n_total:
        return 1.0
    # Need at least 3 non-patch subsystems to compute C(n-k, 3)
    n_non_patch = n_total - k
    if n_non_patch < n_sample:
        # Not enough non-patch subsystems; almost certainly a hit
        return 1.0
    try:
        return 1.0 - comb(n_non_patch, n_sample) / comb(n_total, n_sample)
    except ValueError:
        # comb error fallback
        return 1.0


def run_evaluation(tasks):
    results = []

    for i, task in enumerate(tasks):
        instance_id = task['instance_id']
        patch_files = task['files_in_patch']
        problem_class = classify_task(task)
        pack = load_pack(problem_class)

        # Subsystems targeted by patch
        patch_subs = set(s for f in patch_files for s in [file_to_subsystem(f)] if s)

        if pack:
            trail_files = [t['file'] for t in pack.get('investigation_trail', [])]
            trail_subs = set(s for f in trail_files for s in [file_to_subsystem(f)] if s)
        else:
            trail_subs = set()

        # With-borg: did guidance pick a subsystem in the patch?
        guided_hit = bool(trail_subs & patch_subs) if (trail_subs and patch_subs) else False

        # Baseline: analytical probability of random 3-subsystem overlap
        baseline_hit_rate = compute_baseline_hit_rate(len(patch_subs))

        # Binary baseline hit: does a single random draw of 3 overlap? (for comparison)
        # This is the same value (deterministic expected value)
        baseline_hit = baseline_hit_rate >= 0.5

        # Match counts
        guided_match_count = len(trail_subs & patch_subs) if (trail_subs and patch_subs) else 0

        result = {
            'instance_id': instance_id,
            'problem_class': problem_class,
            'has_guidance': bool(pack),
            'trail_subsystems': list(trail_subs)[:3],
            'patch_subsystems': list(patch_subs)[:5],
            'subsystem_overlap': list(trail_subs & patch_subs) if (trail_subs and patch_subs) else [],
            'guided_hit': int(guided_hit),
            'baseline_hit_rate': round(baseline_hit_rate, 4),
            'baseline_hit': int(baseline_hit),
            'delta': float(guided_hit) - baseline_hit_rate,
            'guided_match_count': guided_match_count,
            'patch_subsystem_count': len(patch_subs),
        }
        results.append(result)

        g = 'Y' if pack else 'N'
        overlap = list(trail_subs & patch_subs) if (trail_subs and patch_subs) else []
        ov_str = ','.join(overlap) if overlap else 'none'
        delta = result['delta']
        print(f"[{i+1}/{len(tasks)}] {instance_id} pc={problem_class} g={g} overlap=[{ov_str}] delta={delta:+.4f}")
    
    return results

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=30)
    args = parser.parse_args()

    print(f"E1b Dogfood Evaluation")
    print(f"Tasks: {args.count}\n")
    
    tasks = load_swebench_tasks(max_count=args.count)
    print(f"Loaded {len(tasks)} tasks\n")
    
    results = run_evaluation(tasks)
    
    print("\n=== SUMMARY ===")

    applicable = [r for r in results if r['has_guidance']]
    all_results = results

    for label, res_list in [('all tasks', all_results), ('guidance-applicable', applicable)]:
        n = len(res_list)
        if n == 0:
            continue

        g_hits = sum(r['guided_hit'] for r in res_list)
        b_rates = [r['baseline_hit_rate'] for r in res_list]
        b_rate = sum(b_rates) / n  # average baseline hit rate across tasks
        deltas = [r['delta'] for r in res_list]

        g_rate = g_hits / n
        delta = g_rate - b_rate

        helps = sum(1 for d in deltas if d > 0)
        hurts = sum(1 for d in deltas if d < 0)

        print(f"\n{label} (n={n}):")
        print(f"  borg subsystem hit:    {g_rate:.1%} ({g_hits}/{n})")
        print(f"  random baseline hit:   {b_rate:.1%} (expected avg)")
        print(f"  delta:                 {delta*100:+.1f}pp")
        print(f"  guidance helps:        {helps}/{n} ({helps/n:.0%})")
        print(f"  guidance hurts:        {hurts}/{n}")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output = RESULTS_DIR / f'e1b_results_{timestamp}.json'
    with open(output, 'w') as f:
        json.dump({
            'results': results,
            'metadata': {
                'count': len(tasks),
                'tasks': [t['instance_id'] for t in tasks],
                'timestamp': timestamp,
            }
        }, f, indent=2)

    print(f"\nSaved: {output}")

if __name__ == '__main__':
    main()
