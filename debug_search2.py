#!/usr/bin/env python3
"""Debug script to replicate exact test conditions."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from unittest.mock import patch
from pathlib import Path
import json
import pytest

# Load the actual index from the test's expected location
PACKS_INDEX_PATH = Path("/root/hermes-workspace/guild-packs/index.json")

def _load_index() -> dict:
    with open(PACKS_INDEX_PATH, encoding="utf-8") as f:
        import json
        return json.load(f)

fake_index = _load_index()
print(f"Loaded index with {len(fake_index.get('packs', []))} packs")
print(f"First 5 packs: {[p['name'] for p in fake_index['packs'][:5]]}")

# Test with first pack name from ALL_PACK_NAMES
test_pack_name = "systematic-debugging"
print(f"\nTesting with pack name: {test_pack_name}")

# Clear any cached imports
for mod in list(sys.modules.keys()):
    if mod.startswith('borg'):
        del sys.modules[mod]

with patch('borg.core.search._fetch_index', return_value=fake_index):
    with patch('borg.core.search.BORG_DIR', Path('/nonexistent')):
        from borg.core.search import borg_search
        result = json.loads(borg_search(test_pack_name))
        print(f'Result success: {result.get("success")}')
        matched_names = [m.get("name") for m in result.get("matches", [])]
        print(f'Matched names: {matched_names}')
        print(f'Pack "{test_pack_name}" found: {test_pack_name in matched_names}')
