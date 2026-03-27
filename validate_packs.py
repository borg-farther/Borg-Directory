#!/usr/bin/env python3
"""Validate all guild packs."""
import sys, os
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

import yaml
from borg.core.schema import validate_pack

packs_dir = '/root/hermes-workspace/guild-packs/packs'
for fname in sorted(os.listdir(packs_dir)):
    if not fname.endswith('.yaml'):
        continue
    fpath = os.path.join(packs_dir, fname)
    with open(fpath) as f:
        content = f.read()
    try:
        pack = yaml.safe_load(content)
    except Exception as e:
        print(f'PARSE ERROR {fname}: {e}')
        continue
    errors = validate_pack(pack)
    if errors:
        print(f'VALIDATION ERROR {fname}:')
        for e in errors:
            print(f'  - {e}')
    else:
        print(f'OK {fname}')