#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

# Debug I-003 - DeFi recommender
print("=== I-003 Debug: DeFiRecommender ===")
from borg.defi.v2 import DeFiRecommender, StrategyQuery
r = DeFiRecommender()
q = StrategyQuery(token='USDC', limit=3)
rec = r.recommend(q)
print(f"recommend returned: {type(rec)}")
print(f"has strategies: {hasattr(rec, 'strategies') if rec else False}")
if rec:
    print(f"strategies: {rec.strategies}")
    print(f"len strategies: {len(rec.strategies) if rec.strategies else 0}")
print()

# Debug I-010 - Reputation
print("=== I-010 Debug: Reputation ===")
from borg.defi.v2.reputation import AgentReputationManager
from borg.defi.v2.models import ExecutionOutcome
from datetime import datetime
rm = AgentReputationManager()
user_id = "test_user_debug"
initial = rm.get_reputation(user_id)
print(f"Initial: outcomes_submitted={initial.outcomes_submitted}")
outcome = ExecutionOutcome(
    outcome_id="test_debug", pack_id="test_pack", agent_id=user_id,
    entered_at=datetime.utcnow(), return_pct=5.0, profitable=True
)
rm.update_reputation(user_id, outcome)
after = rm.get_reputation(user_id)
print(f"After: outcomes_submitted={after.outcomes_submitted}")

# Debug I-011 - YieldScanner
print()
print("=== I-011 Debug: YieldScanner ===")
from borg.defi.yield_scanner import YieldScanner
scanner = YieldScanner()
print(f"YieldScanner methods: {[m for m in dir(scanner) if not m.startswith('_')]}")
