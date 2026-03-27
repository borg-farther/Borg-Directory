#!/usr/bin/env python3
"""Debug the index to file mapping."""
import json, os, yaml

packs_dir = '/root/hermes-workspace/guild-packs/packs'
index_path = '/root/hermes-workspace/guild-packs/index.json'

with open(index_path) as f:
    index = json.load(f)

# id -> file mapping
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

print("ID -> file mapping:")
for k, v in sorted(id_to_file.items()):
    print(f"  {k!r} -> {v}")

print("\nIndex entries with no matching file:")
for entry in index['packs']:
    pid = entry.get('id', '')
    if pid not in id_to_file:
        print(f"  {entry['name']!r} id={pid!r}")

# For each name, how many index entries and files?
from collections import defaultdict
name_to_entries = defaultdict(list)
name_to_files = defaultdict(list)
for entry in index['packs']:
    name = entry.get('name', '')
    name_to_entries[name].append(entry)
for pid, fname in id_to_file.items():
    for entry in index['packs']:
        if entry.get('id') == pid:
            name = entry.get('name', '')
            name_to_files[name].append(fname)

print("\nName -> index entries count, files count:")
for name in sorted(set(list(name_to_entries.keys()) + list(name_to_files.keys()))):
    ec = len(name_to_entries.get(name, []))
    fc = len(name_to_files.get(name, []))
    print(f"  {name!r}: {ec} index entries, {fc} files")
