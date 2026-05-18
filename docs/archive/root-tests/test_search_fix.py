#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')
import json
from borg.core.search import borg_search

# Clear the index cache so we get fresh data
from borg.core import uri
uri._index_cache = (None, 0)

tests = [
    "NoneType has no attribute",
    "circular import error",
    "django migration state",
    "schema drift",
    "pytest flaky test",
    "merge conflict",
    "permission denied",
]

for q in tests:
    r = borg_search(q)
    data = json.loads(r)
    packs = data.get("matches", [])
    names = [p.get("name") for p in packs]
    print(f"Q: {q:<40} → {len(packs)} matches: {names}")
