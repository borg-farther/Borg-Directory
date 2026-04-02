from datasets import load_dataset
import json

ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
# Filter for Django tasks
django_tasks = [x for x in ds if 'django' in x['repo'].lower()]
print(f'Total Django tasks: {len(django_tasks)}')

if django_tasks:
    print(f'\nFields available: {list(django_tasks[0].keys())}')
    
    # Check which tasks have hints_text
    tasks_with_hints = [x for x in django_tasks if x.get('hints_text') and len(x.get('hints_text', '').strip()) > 0]
    print(f'Tasks with non-empty hints_text: {len(tasks_with_hints)}')
    
    # Show first 5 hints_text samples
    print('\n' + '='*80)
    print('SAMPLE hints_text FIELDS (first 5 tasks with hints):')
    print('='*80)
    
    for i, task in enumerate(tasks_with_hints[:5]):
        print(f'\n--- Task {i+1}: {task["instance_id"]} ---')
        print(f'hints_text length: {len(task.get("hints_text", "") or "")}')
        print(f'hints_text:\n{task.get("hints_text", "") or "EMPTY"}')
        print('-'*40)