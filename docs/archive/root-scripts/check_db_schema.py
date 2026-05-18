#!/usr/bin/env python3
"""Check DB schema for packs and outcomes tables."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.db.store import AgentStore
store = AgentStore()
conn = store._get_connection()

print("=== packs table columns ===")
cur = conn.execute("PRAGMA table_info(packs)")
for row in cur.fetchall():
    print(f"  {row[1]}: {row[2]}")

print("\n=== outcomes table ===")
try:
    cur = conn.execute("PRAGMA table_info(outcomes)")
    cols = []
    for row in cur.fetchall():
        print(f"  {row[1]}: {row[2]}")
except Exception as e:
    print(f"  Error: {e}")

print("\n=== outcomes sample ===")
try:
    cur = conn.execute("SELECT * FROM outcomes LIMIT 3")
    for row in cur.fetchall():
        print(row)
except Exception as e:
    print(f"  Error: {e}")

print("\n=== Check if tables exist ===")
cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
for row in cur.fetchall():
    print(f"  Table: {row[0]}")
