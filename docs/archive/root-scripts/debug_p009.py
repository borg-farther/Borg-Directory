#!/usr/bin/env python3
"""Debug P-009 SQLite WAL concurrent writes."""
import sys
import threading
import time
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.db.store import AgentStore

store = AgentStore()
conn = store._get_connection()

# Check schema
print("=== agents table schema ===")
cur = conn.execute("PRAGMA table_info(agents)")
for row in cur.fetchall():
    print(row)

# Test single insert
print("\n=== Test single insert ===")
from datetime import datetime
try:
    conn.execute(
        "INSERT OR REPLACE INTO agents (agent_id, operator, display_name, reputation_score, contribution_score, free_rider_score, access_tier, packs_published, packs_consumed, feedback_given, registered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("debug_agent_1", "test-op", "Debug Agent", 0.5, 0.0, 0.0, "community", 0, 0, 0, datetime.now().isoformat())
    )
    conn.commit()
    print("Single insert succeeded")
except Exception as e:
    print(f"Single insert failed: {e}")

# Test concurrent inserts
print("\n=== Test concurrent inserts ===")
errors = []
success_count = [0]
lock = threading.Lock()

def writer(thread_id: int):
    try:
        t_store = AgentStore()
        t_conn = t_store._get_connection()
        for i in range(10):
            try:
                t_conn.execute(
                    "INSERT OR REPLACE INTO agents (agent_id, operator, display_name, reputation_score, contribution_score, free_rider_score, access_tier, packs_published, packs_consumed, feedback_given, registered_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (f"concurrent_agent_{thread_id}_{i}", f"operator-{thread_id}", f"Agent {thread_id}-{i}", 0.5, 0.0, 0.0, "community", 0, 0, 0, datetime.now().isoformat())
                )
                t_conn.commit()
            except Exception as e:
                with lock:
                    errors.append(f"thread_{thread_id}_iter_{i}: {str(e)[:100]}")
        with lock:
            success_count[0] += 1
    except Exception as e:
        with lock:
            errors.append(f"thread_{thread_id}_setup: {str(e)[:100]}")

threads = []
for t in range(10):
    th = threading.Thread(target=writer, args=(t,))
    threads.append(th)
    th.start()

for th in threads:
    th.join(timeout=30)

print(f"Success count: {success_count[0]}/10")
print(f"Errors: {errors}")
print(f"Error count: {len(errors)}")

# Check integrity
cur = conn.execute("PRAGMA integrity_check")
print(f"Integrity check: {cur.fetchone()[0]}")
