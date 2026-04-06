#!/usr/bin/env python3
import sys; sys.path.insert(0, '.')
from borg.core.v3_integration import BorgV3
v3 = BorgV3()
cands = v3._get_candidates()
names = [c.name for c in cands]
print('All candidate names:', names)
print()
print('null-pointer-chain in candidates:', 'null-pointer-chain' in names)
print('code-review in candidates:', 'code-review' in names)
print()
from borg.core.pack_taxonomy import load_pack_by_problem_class
mp = load_pack_by_problem_class('null_pointer_chain')
print('matched pack name:', mp.get('name'))
print('matched pack id:', mp.get('id'))
print('matched pack keys:', list(mp.keys()))
