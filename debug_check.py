#!/usr/bin/env python3
"""Check which of the 23 local packs are NOT in the remote index."""
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

print("Remote index has 21 packs:")
for n in sorted(remote_names):
    print(f"  {n}")

# Now simulate _build_pack_list
packs_dir = Path('/root/hermes-workspace/guild-packs/packs')
fname_to_id = {}
id_to_entry = {}

for entry in index.get("packs", []):
    pid = entry.get("id", "")
    if pid:
        id_to_entry[pid] = entry

# Handle new format too
for uri, pack_data in index.items():
    if isinstance(pack_data, dict):
        pid = pack_data.get("id", uri)
        if pid and pid not in id_to_entry:
            id_to_entry[pid] = pack_data

for fname in sorted(packs_dir.glob("*.yaml")):
    if not fname.name.endswith(".yaml"):
        continue
    with open(fname, encoding="utf-8") as f:
        data = yaml.safe_load(f.read())
    if data and isinstance(data, dict):
        pid = data.get("id", "")
        if pid:
            fname_to_id[fname.name] = pid

print("\nLocal files vs remote index:")
for fname in sorted(packs_dir.glob("*.yaml")):
    if not fname.name.endswith(".yaml"):
        continue
    stem = fname.stem.replace(".workflow", "").replace(".rubric", "")
    pid = fname_to_id.get(fname.name, "")
    in_remote = stem in remote_names
    print(f"  {fname.name}: stem={stem}, id={pid[:50] if pid else 'NONE'}, in_remote={in_remote}")