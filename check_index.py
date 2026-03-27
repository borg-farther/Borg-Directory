#!/usr/bin/env python3
"""Check index vs files."""
import json, os, yaml
from collections import Counter

packs_dir = '/root/hermes-workspace/guild-packs/packs'
index_path = '/root/hermes-workspace/guild-packs/index.json'

with open(index_path) as f:
    index = json.load(f)

print("Total index entries:", len(index['packs']))

all_names = [p['name'] for p in index['packs'] if p.get('name')]
unique_names = set(all_names)
print("Unique names in index:", len(unique_names))

counts = Counter(all_names)
dups = {k: v for k, v in counts.items() if v > 1}
print("Duplicate names:", dups)

print("\nTotal YAML files:", len([f for f in os.listdir(packs_dir) if f.endswith('.yaml')]))

# Check what files are in packs/ not in index
id_to_file = {}
for fname in sorted(os.listdir(packs_dir)):
    if not fname.endswith('.yaml'):
        continue
    fpath = os.path.join(packs_dir, fname)
    with open(fpath) as f:
        data = yaml.safe_load(f.read())
    if data:
        pid = data.get('id', '')
        id_to_file[pid] = fname

index_ids = {p['id'] for p in index['packs'] if p.get('id')}
file_ids = set(id_to_file.keys())
print("\nIndex IDs:", len(index_ids))
print("File IDs:", len(file_ids))
print("In index but no file:", index_ids - file_ids)
print("In files but not index:", file_ids - index_ids)
