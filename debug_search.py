#!/usr/bin/env python3
"""Debug the search index structure issue."""
import json
import sys
from pathlib import Path
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

with open('/root/hermes-workspace/guild-packs/index.json') as f:
    index = json.load(f)

print("Index type:", type(index))
print("Index keys (first 5):", list(index.keys())[:5])

# Check if packs key exists
print("Has 'packs' key:", 'packs' in index)
if 'packs' in index:
    print("packs type:", type(index['packs']))
    print("packs count:", len(index['packs']))
    print("First pack:", json.dumps(index['packs'][0], indent=2)[:300] if index['packs'] else 'empty')
else:
    print("No 'packs' key - top-level keys ARE the pack entries")
    print("Sample entry:")
    first_key = list(index.keys())[0]
    print(f"  Key: {first_key}")
    print(f"  Value keys: {list(index[first_key].keys())}")

# Show what borg_search would see
all_packs = list(index.get("packs", []))
print(f"\nborg_search would see {len(all_packs)} packs via index.get('packs', [])")

# Show what the correct approach would be
if 'packs' not in index:
    correct_packs = list(index.values())
    print(f"Correct approach (index.values()): {len(correct_packs)} packs")
    if correct_packs:
        print(f"First pack name: {correct_packs[0].get('name', 'NO NAME')}")
        print(f"First pack id: {correct_packs[0].get('id', 'NO ID')}")