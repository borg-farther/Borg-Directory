#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.seeds import get_seed_packs

seed_packs = get_seed_packs()
for sp in seed_packs:
    d = sp.to_search_dict()
    if 'null' in d['name'] or 'import' in d['name']:
        print(f"=== {d['name']} ===")
        print(f"  search_text: {d.get('search_text', 'MISSING')!r}")
        print(f"  problem_class: {d['problem_class']!r}")
        print(f"  solution (first 200): {d.get('solution','')[:200]!r}")

# Test the matching
query = "NoneType has no attribute"
query_terms = query.lower().split()
print(f"\nQuery terms: {query_terms}")

for sp in seed_packs:
    d = sp.to_search_dict()
    st = d.get('search_text', '').lower()
    matched = all(t in st for t in query_terms)
    print(f"  {d['name']}: all_terms_match={matched}")
    if not matched:
        missing = [t for t in query_terms if t not in st]
        print(f"    missing terms: {missing}")
