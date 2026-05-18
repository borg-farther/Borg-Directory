#!/usr/bin/env python3
"""Test problem_class filtering in BorgV3.search."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.v3_integration import BorgV3

v3 = BorgV3()

# Test: TypeError with a message that matches null_pointer_chain
result = v3.search(
    query="TypeError NoneType attribute",
    task_context={
        "error_type": "TypeError",
        "error_message": "TypeError: 'NoneType' object has no attribute 'foo'",
        "task_type": "debug",
        "keywords": ["null", "attribute", "error"],
    }
)
print(f"Results (TypeError null_pointer_chain): {len(result)} packs")
for r in result[:3]:
    print(f"  {r['name']} | category={r.get('category','')}")

# Test: no error_type - should return all candidates
result_all = v3.search(
    query="debug null pointer",
    task_context={"task_type": "debug"}
)
print(f"\nResults (no error_type): {len(result_all)} packs")
for r in result_all[:3]:
    print(f"  {r['name']}")
