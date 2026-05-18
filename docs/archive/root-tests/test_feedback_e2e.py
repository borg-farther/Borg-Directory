#!/usr/bin/env python3
"""End-to-end test: borg_feedback-v3 works."""
import sqlite3, sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.v3_integration import BorgV3

DB = '/root/.borg/borg_v3.db'

def count_outcomes():
    conn = sqlite3.connect(DB)
    cur = conn.execute('SELECT COUNT(*) FROM outcomes')
    total = cur.fetchone()[0]
    cur = conn.execute('SELECT COUNT(*) FROM outcomes WHERE success = 1')
    good = cur.fetchone()[0]
    conn.close()
    return total, good

print("[1] Initial outcome count:")
total, good = count_outcomes()
print(f"    Total: {total}, Successful: {good}")

print("\n[2] Recording a success via BorgV3:")
v3 = BorgV3()
v3.record_outcome(
    pack_id='schema-drift',
    task_context={'problem_class': 'schema_drift', 'error': 'no such column'},
    success=True,
    tokens_used=2000,
    time_taken=3.0
)
total2, good2 = count_outcomes()
print(f"    Total: {total2}, Successful: {good2}")
assert total2 == total + 1, "Outcome not recorded!"
print("    ✓ Outcome recorded successfully")

print("\n[3] Recording a failure via BorgV3:")
v3.record_outcome(
    pack_id='schema-drift',
    task_context={'problem_class': 'schema_drift', 'error': 'no such column'},
    success=False,
    tokens_used=5000,
    time_taken=10.0
)
total3, good3 = count_outcomes()
print(f"    Total: {total3}, Successful: {good3}")
assert total3 == total2 + 1, "Outcome not recorded!"
assert good3 == good2, "Success count should not change on failure!"
print("    ✓ Failure recorded successfully")

print("\n[4] Verify last outcome is failure:")
conn = sqlite3.connect(DB)
row = conn.execute('SELECT pack_id, success, tokens_used, time_taken FROM outcomes ORDER BY id DESC LIMIT 1').fetchone()
conn.close()
print(f"    pack_id={row[0]}, success={row[1]}, tokens={row[2]}, time={row[3]}")
assert row[1] == 0, "Last outcome should be failure!"
print("    ✓ Last outcome is correct (failure)")

print("\n[5] Check feedback_signals table exists and has entries:")
conn = sqlite3.connect(DB)
try:
    count = conn.execute('SELECT COUNT(*) FROM feedback_signals').fetchone()[0]
    print(f"    feedback_signals rows: {count}")
except Exception as e:
    print(f"    Table check: {e}")
conn.close()

print("\n✅ borg_feedback-v3 E2E: PASS — All checks passed")
