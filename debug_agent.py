#!/usr/bin/env python3
"""Debug the agent-a-debugging issue."""
import json

with open('/root/hermes-workspace/guild-packs/index.json') as f:
    index = json.load(f)

print("=== All pack names/IDs in remote index ===\n")
pack_names = []
for uri, data in index.items():
    pack_name = uri.split("/")[-1] if "/" in uri else uri
    pack_names.append(pack_name)
    print(f"URI: {uri} -> name: {pack_name}")

print(f"\nTotal packs: {len(pack_names)}")

# Check for 'agent-a-debugging' or similar
print("\n=== Looking for 'agent-a-debugging' ===")
matches = [n for n in pack_names if 'agent' in n.lower() or 'debugging' in n.lower()]
print(f"Similar names: {matches}")

# List local yaml files
from pathlib import Path
packs_dir = Path('/root/hermes-workspace/guild-packs/packs')
print("\n=== Local YAML files ===")
for f in sorted(packs_dir.glob('*.yaml')):
    print(f"  {f.name}")