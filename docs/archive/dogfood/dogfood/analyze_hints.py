from datasets import load_dataset
import json

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
django_tasks = [x for x in ds if 'django' in x['repo'].lower()]
tasks_with_hints = [x for x in django_tasks if x.get('hints_text') and len(x.get('hints_text', '').strip()) > 0]

print(f'Total Django tasks: {len(django_tasks)}')
print(f'Tasks with non-empty hints_text: {len(tasks_with_hints)}')

# Analyze hints_text length distribution
lengths = [len(x.get('hints_text', '')) for x in tasks_with_hints]
print(f'\nHints_text length stats:')
print(f'  Min: {min(lengths)}, Max: {max(lengths)}, Avg: {sum(lengths)/len(lengths):.0f}')

# Categorize hints_text by characteristics
print('\n' + '='*80)
print('ANALYZING hints_text CONTENT PATTERNS:')
print('='*80)

# Sample 10 more tasks to see variety
import random
random.seed(42)
sample_tasks = random.sample(tasks_with_hints, min(10, len(tasks_with_hints)))

for i, task in enumerate(sample_tasks):
    hints = task.get('hints_text', '') or ''
    print(f'\n--- Task {i+1}: {task["instance_id"]} (len={len(hints)}) ---')
    # Show first 500 chars
    preview = hints[:500] + '...' if len(hints) > 500 else hints
    print(f'Preview: {preview}')
    
    # Check for patterns
    patterns_found = []
    if 'patch' in hints.lower() or 'diff' in hints.lower():
        patterns_found.append('CODE/PATCH')
    if 'https://' in hints or 'http://' in hints:
        patterns_found.append('URLS')
    if 'fix' in hints.lower() and ('should' in hints.lower() or 'need' in hints.lower()):
        patterns_found.append('SUGGESTS_FIX')
    if 'try' in hints.lower() and ('catch' in hints.lower() or 'except' in hints.lower()):
        patterns_found.append('TRY_EXCEPT')
    if any(x in hints for x in ['#', '//', 'def ', 'class ']):
        patterns_found.append('HAS_CODE')
    print(f'Patterns: {patterns_found}')

print('\n' + '='*80)
print('LOOKING FOR ACTUAL REASONING TRACES (if any):')
print('='*80)

# Look for tasks where hints_text appears to be step-by-step reasoning
reasoning_keywords = ['because', 'therefore', 'thus', 'hence', 'reason', 'conclusion', 
                       'step', 'first', 'then', 'next', 'finally', 'analyze', 'think']
                      
reasoning_tasks = []
for task in tasks_with_hints[:50]:  # Check first 50
    hints = (task.get('hints_text', '') or '').lower()
    keyword_count = sum(1 for kw in reasoning_keywords if kw in hints)
    if keyword_count >= 3:
        reasoning_tasks.append((task, keyword_count))

print(f'\nTasks with 3+ reasoning keywords in first 50: {len(reasoning_tasks)}')
for task, count in reasoning_tasks[:3]:
    print(f'\n--- {task["instance_id"]} ({count} keywords) ---')
    print(task['hints_text'][:800])