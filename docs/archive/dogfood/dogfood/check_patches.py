from datasets import load_dataset
import re

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
django_tasks = [x for x in ds if 'django' in x['repo'].lower()]
tasks_with_hints = [x for x in django_tasks if x.get('hints_text') and len(x.get('hints_text', '').strip()) > 0]

print('='*80)
print('CHECKING FOR PATCH/DIFF CONTENT IN hints_text:')
print('='*80)

# Look for diff/patch patterns
patch_patterns = ['diff --git', '@@ -', '@@ +', '--- a/', '+++ b/', 
                  '+def ', '+class ', '-def ', '-class ',
                  '```diff', '```python', '```sql']

patch_count = 0
url_count = 0
code_snippet_count = 0
minimal_hint_count = 0  # hints that are very short

for task in tasks_with_hints:
    hints = task.get('hints_text', '') or ''
    
    # Check for patch-like content
    if any(p in hints for p in ['diff --git', '@@ -', '@@ +', '--- a/', '+++ b/']):
        patch_count += 1
        
    # Check for URLs
    if 'https://' in hints or 'http://' in hints:
        url_count += 1
        
    # Check for code snippets (backticks or indented code)
    if '```' in hints or ('    ' in hints and ('def ' in hints or 'class ' in hints)):
        code_snippet_count += 1
        
    # Very short hints (less than 50 chars)
    if len(hints) < 50:
        minimal_hint_count += 1

print(f'\nPatch/diff patterns found in: {patch_count} / {len(tasks_with_hints)} tasks')
print(f'URLs found in: {url_count} / {len(tasks_with_hints)} tasks')
print(f'Code snippets found in: {code_snippet_count} / {len(tasks_with_hints)} tasks')
print(f'Minimal hints (<50 chars): {minimal_hint_count} / {len(tasks_with_hints)} tasks')

print('\n' + '='*80)
print('EXAMPLES OF MINIMAL HINTS (less than 50 chars):')
print('='*80)

minimal_hints = [(t, t['hints_text']) for t in tasks_with_hints if len(t.get('hints_text', '')) < 50]
for t, h in minimal_hints[:10]:
    print(f'\n{t["instance_id"]}: "{h}"')

print('\n' + '='*80)
print('EXAMPLES OF HINTS WITH PATCH CONTENT:')
print('='*80)

patch_tasks = [t for t in tasks_with_hints if 'diff --git' in t.get('hints_text', '') or '@@ -' in t.get('hints_text', '')]
for t in patch_tasks[:3]:
    hints = t['hints_text']
    print(f'\n--- {t["instance_id"]} ---')
    # Find and show the patch portion
    idx = max(0, hints.find('diff --git') if 'diff --git' in hints else hints.find('@@ -'))
    print(hints[idx:idx+600])
    print('...')

print('\n' + '='*80)
print('COMPARING hints_text TO ACTUAL PATCH (ground truth):')
print('='*80)

# Show 3 tasks where we can compare hints_text to the actual patch
for task in tasks_with_hints[:5]:
    instance_id = task['instance_id']
    hints = task.get('hints_text', '') or ''
    patch = task.get('patch', '') or ''
    
    # Check if hints_text contains any of the actual patch content
    patch_lines = patch.split('\n')[:5]  # First 5 lines of patch
    overlap = any(pl in hints for pl in patch_lines if len(pl) > 20)
    
    print(f'\n--- {instance_id} ---')
    print(f'hints length: {len(hints)}, patch length: {len(patch)}')
    print(f'hints contains patch lines: {overlap}')
    if overlap:
        # Show what matched
        for pl in patch_lines[:3]:
            if len(pl) > 20 and pl in hints:
                print(f'  Matched: {pl[:80]}')