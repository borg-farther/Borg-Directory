#!/usr/bin/env python3
"""Verify A/B wiring fix — test the _last_ab_context path."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.v3_integration import BorgV3
from borg.core.mutation_engine import ABTest, PackVariant
from datetime import datetime, timezone

v3 = BorgV3()

# Create an A/B test
variant = PackVariant(
    original_pack_id="guild://hermes/systematic-debugging",
    mutant_pack_id="guild://hermes/systematic-debugging-mutant",
    mutation_type="anti_pattern_addition",
    created_at=datetime.now(timezone.utc),
)
ab_test = ABTest(variant=variant, _pack_store=v3._mutation.pack_store)
v3._mutation.ab_tests["test-001"] = ab_test
print(f"Created A/B test: test-001")
print(f"  uses_mutant before: {ab_test.variant.uses_mutant}")

# Manually set _last_ab_context (simulating what search() would set)
v3._last_ab_context = {"test_id": "test-001", "variant": "mutant"}
print(f"\nSet _last_ab_context manually: {v3._last_ab_context}")

# record_outcome() should use _last_ab_context
v3.record_outcome(
    pack_id="guild://hermes/systematic-debugging-mutant",
    task_context={"task_type": "debug"},
    success=True,
    tokens_used=500,
    time_taken=2.0,
)
print(f"\nrecord_outcome() fired")
print(f"  uses_mutant after: {ab_test.variant.uses_mutant} (should be 1)")
print(f"  successes_mutant after: {ab_test.variant.successes_mutant} (should be 1)")

# Now test the full search() → record_outcome() path
# Create a result with ab_test annotation and verify it gets stored
print("\n--- Testing search() → _last_ab_context ---")
v3._last_ab_context = None  # reset
# The problem_class path returns null-pointer-chain with no ab_test
results = v3.search(
    query="debug TypeError",
    task_context={
        "error_type": "TypeError",
        "error_message": "TypeError: 'NoneType' object has no attribute 'foo'",
        "task_type": "debug",
    }
)
print(f"search() returned: {len(results)} results")
print(f"  top: {results[0]['name'] if results else 'none'}")
print(f"  _last_ab_context: {v3._last_ab_context}")
# With the current seed packs (no ab_tests on them), _last_ab_context should be None

if ab_test.variant.uses_mutant == 1 and ab_test.variant.successes_mutant == 1:
    print("\n✅ A/B WIRING FIX VERIFIED — _last_ab_context path works!")
else:
    print("\n❌ A/B WIRING STILL BROKEN")
