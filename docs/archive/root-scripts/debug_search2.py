#!/usr/bin/env python3
import sys, time
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.uri import _fetch_index
from borg.core.seeds import get_seed_packs

# Time the index fetch
t0 = time.time()
try:
    index = _fetch_index()
    print(f"_fetch_index: {time.time()-t0:.1f}s, packs: {len(index.get('packs', []))}")
except Exception as e:
    print(f"_fetch_index failed: {e}")

# Check seeds
seed_packs = get_seed_packs()
print(f"Seed packs: {len(seed_packs)}")
for sp in seed_packs[:3]:
    d = sp.to_search_dict()
    print(f"  {d['name']}: id={d['id']!r}, problem_class={d['problem_class']!r}, phase_names={d['phase_names']}")

# Now do a simple text match simulation
print("\n--- Text search simulation ---")
query = "NoneType has no attribute"
query_terms = set(query.lower().split())
print(f"Query terms: {query_terms}")

# Build corpus from seeds
for sp in seed_packs:
    d = sp.to_search_dict()
    name = d['name'].lower().replace('-', ' ')
    pc = d['problem_class'].lower()
    phases = ' '.join(d['phase_names']).lower()
    text = f"{name} {pc} {phases}"
    matched = bool(query_terms & set(text.split()))
    print(f"  {d['name']}: match={matched} | text={text[:80]}")
