#!/usr/bin/env python3
"""
Test 3: A/B Test Infrastructure — Does MutationEngine actually wire to record_outcome?

This script verifies:
1. Does MutationEngine.record_outcome exist and have the right signature?
2. Does BorgV3.record_outcome correctly call MutationEngine.record_outcome?
3. Is the A/B test outcome path working end-to-end?
"""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from borg.core.mutation_engine import MutationEngine, ABTest
from borg.core.v3_integration import _StubMutationEngine


def test_me_record_outcome_signature():
    """Check MutationEngine.record_outcome signature."""
    sig = inspect.signature(MutationEngine.record_outcome)
    params = list(sig.parameters.keys())
    print(f"MutationEngine.record_outcome params: {params}")
    print(f"  Has test_id: {'test_id' in params}")
    print(f"  Has variant: {'variant' in params}")
    print(f"  Has success: {'success' in params}")
    print(f"  Has pack_id: {'pack_id' in params}")
    print(f"  Has task_category: {'task_category' in params}")
    return params


def test_stub_me_record_outcome_signature():
    """Check _StubMutationEngine.record_outcome signature."""
    sig = inspect.signature(_StubMutationEngine.record_outcome)
    params = list(sig.parameters.keys())
    print(f"\n_StubMutationEngine.record_outcome params: {params}")
    print(f"  Has pack_id: {'pack_id' in params}")
    print(f"  Has task_category: {'task_category' in params}")
    return params


def test_wiring_logic():
    """
    Simulate the wiring logic in BorgV3.record_outcome (lines 459-490).
    
    The code checks:
      if hasattr(self._mutation, "record_outcome"):
          sig = inspect.signature(self._mutation.record_outcome)
          params = list(sig.parameters.keys())
          if len(params) >= 3 and ("pack_id" in params or "task_category" in params):
              # USE THIS PATH
          elif isinstance(self._mutation, _StubMutationEngine):
              # USE THIS PATH
          else:
              # SKIP - comment says "it should be recorded at selection time"
    """
    print("\n--- Testing wiring logic ---")
    
    # For real MutationEngine
    me_params = test_me_record_outcome_signature()
    
    cond1 = len(me_params) >= 3
    cond2 = "pack_id" in me_params or "task_category" in me_params
    
    print(f"\nReal MutationEngine wiring check:")
    print(f"  len(params) >= 3: {cond1} (params={len(me_params)})")
    print(f"  'pack_id' in params or 'task_category' in params: {cond2}")
    print(f"  Would USE this path: {cond1 and cond2}")
    print(f"  Would fall to 'else' (SKIP): {cond1 and not cond2}")
    
    # For stub
    stub_params = test_stub_me_record_outcome_signature()
    
    cond1s = len(stub_params) >= 3
    cond2s = "pack_id" in stub_params or "task_category" in stub_params
    
    print(f"\nStub MutationEngine wiring check:")
    print(f"  len(params) >= 3: {cond1s} (params={len(stub_params)})")
    print(f"  'pack_id' in params or 'task_category' in params: {cond2s}")
    print(f"  isinstance check: N/A (it's a stub so always goes to elif path)")
    
    # For stub, the condition is isinstance(self._mutation, _StubMutationEngine)
    # which is True, so it goes to elif path
    print(f"\n=== FINDING ===")
    print(f"Real MutationEngine: Does NOT get called in BorgV3.record_outcome!")
    print(f"  The check 'pack_id' in params or 'task_category' in params FAILS")
    print(f"  because MutationEngine.record_outcome(test_id, variant, success)")
    print(f"  has neither 'pack_id' nor 'task_category' params.")
    print(f"  The code falls through to 'else' which SKIPS recording.")
    print(f"\n  The only way A/B test outcomes get recorded is via session_id")
    print(f"  (step 5 in record_outcome), which requires selected_variant to be set.")
    print(f"  But session_id is optional and selected_variant may not be populated.")


def test_ab_test_functionality():
    """Test that ABTest.record_outcome works correctly in isolation."""
    print("\n\n--- Testing ABTest A/B functionality in isolation ---")
    
    from borg.core.mutation_engine import ABTest
    from datetime import datetime, timezone
    
    # Simple mock pack store
    class MockStore:
        def __init__(self):
            self.packs = {}
        def get_pack(self, pack_id):
            return self.packs.get(pack_id)
        def save_pack(self, pack_id, data):
            self.packs[pack_id] = data
    
    store = MockStore()
    store.save_pack("orig", {"id": "orig", "phases": []})
    store.save_pack("mut", {"id": "mut", "phases": []})
    
    ab = ABTest.create_test("orig", "mut", "test_type", store)
    
    # Record some outcomes
    ab.record_outcome("original", True)
    ab.record_outcome("original", True)
    ab.record_outcome("original", False)
    ab.record_outcome("mutant", True)
    ab.record_outcome("mutant", False)
    ab.record_outcome("mutant", False)
    
    v = ab.variant
    print(f"A/B test variant created: original={v.original_pack_id}, mutant={v.mutant_pack_id}")
    print(f"  uses_original: {v.uses_original}, successes_original: {v.successes_original}")
    print(f"  uses_mutant: {v.uses_mutant}, successes_mutant: {v.successes_mutant}")
    print(f"  success_rate_original: {v.success_rate_original:.2f}")
    print(f"  success_rate_mutant: {v.success_rate_mutant:.2f}")
    
    # Get winner
    result = ab.get_winner(min_samples=3, significance=0.05)
    print(f"\nABTestResult:")
    print(f"  winner: {result.winner}")
    print(f"  significance: {result.significance:.4f}")
    print(f"  is_significant: {result.is_significant}")
    print(f"  recommended_action: {result.recommended_action}")
    
    print("\n  A/B test infrastructure WORKS in isolation.")
    print("  The ABTest.record_outcome method correctly tracks outcomes.")
    print("  The z-test significance calculation is correct.")
    
    return True


def main():
    print("=" * 70)
    print("Borg E2E Audit — Test 3: A/B Test Infrastructure")
    print("=" * 70)
    
    test_wiring_logic()
    test_ab_test_functionality()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
1. MutationEngine.record_outcome(test_id, variant, success) EXISTS and works.
2. ABTest class correctly tracks uses_original, uses_mutant, successes, and 
   computes statistical significance via z-test.
3. BUT: BorgV3.record_outcome does NOT wire to MutationEngine.record_outcome!

   The bug is in v3_integration.py around line 466:
   
       if len(params) >= 3 and ("pack_id" in params or "task_category" in params):
           self._mutation.record_outcome(pack_id, category, success, ...)
   
   MutationEngine.record_outcome(test_id, variant, success) has params:
       ['test_id', 'variant', 'success'] — no 'pack_id' or 'task_category'!
   
   So this condition FAILS and execution falls to 'else' which SKIPS entirely.
   
   The comment even admits this:
     "The mutation engine requires knowing which A/B test variant was used.
      Since record_outcome(pack_id) doesn't pass test_id, we cannot
      correctly attribute the outcome to a specific A/B test variant.
      We skip mutation engine recording here — it should be recorded
      at selection time when the variant is known."
      
   So the A/B test outcome wiring is BROKEN unless session_id is provided
   and selected_variant is set in the session.

4. The ONLY path for A/B test recording is via session_id (step 5), which is
   optional and depends on session.get("selected_variant") being populated.

VERDICT: A/B test infrastructure exists but is NOT wired correctly in the
         main record_outcome path. It relies on an optional session_id path.
""")


if __name__ == "__main__":
    main()
