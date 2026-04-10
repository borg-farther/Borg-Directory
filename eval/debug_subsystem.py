import json, re, yaml
from pathlib import Path

def file_to_subsystem(file_path):
    if not file_path:
        return None
    m = re.match(r'django/(\w+)(?:/(\w+))?(?:/(\w+))?', file_path)
    if m:
        parts = [p for p in m.groups() if p and p not in ('py', '__pycache__')]
        if len(parts) >= 2:
            return 'django.' + parts[0] + '.' + parts[1]
        elif len(parts) == 1:
            return 'django.' + parts[0]
    return None

# Test on task 10087
data = json.load(open('/root/swebench/data/django__django-10087.json'))
patch = data.get('patch', '')
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

print('=== Patch files ===')
for f in files[:10]:
    sub = file_to_subsystem(f)
    print(f'  {f} -> {sub}')

# Check migration_state_desync pack
print()
SKILLS_DIR = Path('/root/hermes-workspace/borg/skills')
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
        if fm and fm.get('problem_class') == 'migration_state_desync':
            print('=== Pack files ===')
            for t in fm.get('investigation_trail', [])[:5]:
                f = t['file']
                sub = file_to_subsystem(f)
                print(f'  {f} -> {sub}')
            break
    except:
        pass

print()
print('=== Test file_to_subsystem ===')
test_files = ['django/db/migrations/state.py', 'django/db/models/query.py', 'django/urls/resolvers.py']
for f in test_files:
    print(f'  {f} -> {file_to_subsystem(f)}')
