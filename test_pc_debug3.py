#!/usr/bin/env python3
import sys; sys.path.insert(0, '.')
from borg.core.pack_taxonomy import load_pack_by_problem_class
mp = load_pack_by_problem_class('null_pointer_chain')
print('id:', mp.get('id'))
print('name:', mp.get('name'))

# The systematic-debugging pack - what's its problem_class?
import yaml
from pathlib import Path
sd = Path('/root/hermes-workspace/borg/skills/systematic-debugging.md')
content = sd.read_text()
yaml_text = content[3:]
idx = yaml_text.find('\n---')
if idx >= 0:
    fm = yaml.safe_load(yaml_text[:idx])
    print('\nsystematic-debugging:')
    print('  name:', fm.get('name'))
    print('  id:', fm.get('id'))
    print('  problem_class:', fm.get('problem_class'))

# Also check: what guild packs have 'null_pointer' or similar?
from borg.core.uri import get_available_pack_names
names = get_available_pack_names()
print('\nGuild packs with null/pointer/error:', [n for n in names if 'null' in n or 'pointer' in n or 'debug' in n.lower()])
