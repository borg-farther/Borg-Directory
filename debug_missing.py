#!/usr/bin/env python3
"""Debug: check which local YAML files are NOT in the remote index."""
import json
from pathlib import Path
import yaml

with open('/root/hermes-workspace/guild-packs/index.json') as f:
    index = json.load(f)

# Get pack names from remote index
remote_names = set()
for uri, data in index.items():
    pack_name = uri.split("/")[-1] if "/" in uri else uri
    remote_names.add(pack_name)

# Get all local YAML files
packs_dir = Path('/root/hermes-workspace/guild-packs/packs')
local_packs = []
for f in sorted(packs_dir.glob('*.yaml')):
    stem = f.stem.replace('.workflow', '').replace('.rubric', '')
    with open(f) as fp:
        data = yaml.safe_load(fp.read())
    pid = data.get('id', '') if data and isinstance(data, dict) else ''
    local_packs.append((stem, f.name, pid))

print("=== Local packs NOT in remote index ===")
for name, fname, pid in local_packs:
    if name not in remote_names:
        print(f"  Local: {name} (file: {fname}, id: {pid})")
    else:
        print(f"  In index: {name}")