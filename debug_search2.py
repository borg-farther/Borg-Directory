#!/usr/bin/env python3
"""Debug the exact flow in test_search_finds_pack."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, '/root/hermes-workspace/guild-v2')

# Load the actual index
with open('/root/hermes-workspace/guild-packs/index.json') as f:
    fake_index = json.load(f)

print("=== Index Analysis ===")
print(f"Index type: {type(fake_index)}")
print(f"Has 'packs' key: {'packs' in fake_index}")
if 'packs' in fake_index:
    print(f"Number of packs in 'packs': {len(fake_index['packs'])}")
else:
    print(f"Number of top-level keys: {len(fake_index)}")
    print(f"First 3 keys: {list(fake_index.keys())[:3]}")
    # Check structure of first entry
    first_key = list(fake_index.keys())[0]
    first_val = fake_index[first_key]
    print(f"First entry key: {first_key}")
    print(f"First entry value type: {type(first_val)}")
    print(f"First entry value keys: {list(first_val.keys()) if isinstance(first_val, dict) else 'N/A'}")
    # Check if 'name' is in the entry
    if isinstance(first_val, dict):
        print(f"First entry has 'name': {'name' in first_val}")
        print(f"First entry has 'id': {'id' in first_val}")
        print(f"First entry 'id' value: {first_val.get('id', 'MISSING')}")

# Now simulate what the test does
print("\n=== Simulating borg_search with patched _fetch_index ===")
with patch("borg.core.search._fetch_index", return_value=fake_index):
    with patch("borg.core.search.BORG_DIR", Path("/nonexistent")):
        from borg.core.search import borg_search
        result_json = borg_search("ascii-art")
        result = json.loads(result_json)

print(f"Search success: {result.get('success')}")
print(f"Number of matches: {len(result.get('matches', []))}")
print(f"Matches: {result.get('matches', [])}")

# What would happen if we search with the NEW format
print("\n=== Checking if pack names would match ===")
all_packs_list = list(fake_index.get("packs", []))  # This is what borg_search does
print(f"all_packs via index.get('packs', []): {len(all_packs_list)}")

# The actual packs
actual_packs = list(fake_index.values())
print(f"Actual packs via index.values(): {len(actual_packs)}")

# Check what the pack names look like
if actual_packs:
    print("\nActual pack names (from values()):")
    for p in actual_packs[:5]:
        print(f"  id={p.get('id', 'NO_ID')[:50]}, keys={list(p.keys())[:5]}")