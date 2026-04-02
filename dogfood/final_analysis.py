from datasets import load_dataset

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
django_tasks = [x for x in ds if 'django' in x['repo'].lower()]
tasks_with_hints = [x for x in django_tasks if x.get('hints_text') and len(x.get('hints_text', '').strip()) > 0]

print('='*80)
print('FINAL ANALYSIS: What does hints_text ACTUALLY provide?')
print('='*80)

# Categorize by content type
categories = {
    'minimal': [],           # Very short hints (<50 chars)
    'just_thanks': [],       # Just acknowledgment
    'suggests_fix': [],      # Suggests approach/fix
    'contains_patch': [],    # Contains diff/patch content
    'contains_so': [],      # Contains StackOverflow references
    'has_reasoning': [],     # Has step-by-step reasoning
}

for task in tasks_with_hints:
    hints = (task.get('hints_text', '') or '').strip()
    instance_id = task['instance_id']
    
    if len(hints) < 50:
        categories['minimal'].append(instance_id)
    if 'thanks' in hints.lower() and len(hints) < 100:
        categories['just_thanks'].append(instance_id)
    if any(x in hints.lower() for x in ['try', 'suggest', 'should', 'might', 'could']):
        categories['suggests_fix'].append(instance_id)
    if 'diff --git' in hints or '@@ -' in hints:
        categories['contains_patch'].append(instance_id)
    if 'stackoverflow' in hints.lower() or 'stack overflow' in hints.lower():
        categories['contains_so'].append(instance_id)
    if any(x in hints.lower() for x in ['because', 'therefore', 'first', 'then', 'next']):
        categories['has_reasoning'].append(instance_id)

print('\nCATEGORIZATION OF 162 TASKS WITH HINTS:')
print(f'  Minimal (<50 chars): {len(categories["minimal"])} tasks')
print(f'  Just thanks/acknowledgment: {len(categories["just_thanks"])} tasks')
print(f'  Suggests fix/approach: {len(categories["suggests_fix"])} tasks')
print(f'  Contains patch/diff: {len(categories["contains_patch"])} tasks')
print(f'  Contains StackOverflow ref: {len(categories["contains_so"])} tasks')
print(f'  Has reasoning keywords: {len(categories["has_reasoning"])} tasks')

# Show examples of problematic categories
print('\n' + '='*80)
print('EXAMPLES OF PROBLEMATIC HINTS (contain patch OR solution):')
print('='*80)

patch_tasks = [t for t in tasks_with_hints if 'diff --git' in t.get('hints_text', '')]
for t in patch_tasks[:2]:
    print(f'\n--- {t["instance_id"]} (CONTAINS PATCH) ---')
    hints = t['hints_text']
    # Show a representative snippet
    start = hints.find('diff --git')
    print(hints[start:start+400])
    print('...')

print('\n' + '='*80)
print('EXAMPLES OF MINIMAL HINTS (essentially useless):')
print('='*80)

for t in tasks_with_hints:
    hints = t.get('hints_text', '').strip()
    if len(hints) < 30:
        print(f'{t["instance_id"]}: "{hints}"')

print('\n' + '='*80)
print('COMPARISON: What hints_text claims vs what Borg reasoning would be:')
print('='*80)

print('''
hints_text (ACTUAL):
  - Bug reporter's notes about what they found
  - Developer discussion of the issue
  - Sometimes: actual diffs/patches
  - Sometimes: StackOverflow solutions
  - Sometimes: "Thanks for the report"
  - Variable quality: 3 chars to 13,753 chars

Borg reasoning trace (EXPECTED):
  - Root cause analysis
  - "Why" approaches failed
  - Start-here signals (error_pattern → where to look)
  - Wrong approaches to avoid
  - Collective patterns from prior agents

KEY CONFOUND:
  hints_text is developer-insider knowledge + sometimes solutions
  NOT a reasoning trace from an agent that previously attempted the task
''')