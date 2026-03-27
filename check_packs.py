#!/usr/bin/env python3
"""Check pack names and IDs."""
import yaml, os, sys

packs_dir = '/root/hermes-workspace/guild-packs/packs'
for fname in sorted(os.listdir(packs_dir)):
    if not fname.endswith('.yaml'):
        continue
    fpath = os.path.join(packs_dir, fname)
    with open(fpath) as f:
        data = yaml.safe_load(f.read())
    print(f'{fname}: name={data.get("name", "MISSING")!r}, type={data.get("type")!r}, id={data.get("id", "MISSING")!r}')
