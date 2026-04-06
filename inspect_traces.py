#!/usr/bin/env python3
"""Inspect actual traces and understand extraction needs."""
import sqlite3, os, json

db = '/root/.borg/traces.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

# Get schema
cur.execute("PRAGMA table_info(traces)")
print("traces schema:")
for c in cur.fetchall():
    print(f"  {c[1]}: {c[2]}")

# Sample traces
cur.execute("SELECT * FROM traces LIMIT 3")
rows = cur.fetchall()
print(f"\n3 sample traces (total {cur.execute('SELECT COUNT(*) FROM traces').fetchone()[0]}):")
for r in rows:
    trace = {
        'id': r[0], 'session_id': r[1], 'task': r[2], 'outcome': r[3],
        'tool_calls_count': r[4], 'errors': r[5], 'files': r[6],
        'error_types': r[7], 'keywords': r[8], 'technologies': r[9],
        'root_cause': r[10], 'timestamp': r[11]
    }
    print(f"\n  id={trace['id'][:8]} session={trace['session_id'][:12]} outcome={trace['outcome']}")
    print(f"  task: {trace['task'][:60]}...")
    print(f"  tool_calls: {trace['tool_calls_count']}, errors: {trace['errors']}, files: {trace['files']}")
    print(f"  error_types: {trace['error_types']}")
    print(f"  root_cause: {trace['root_cause'][:80] if trace['root_cause'] else 'None'}...")

# trace_file_index
cur.execute("SELECT * FROM trace_file_index LIMIT 5")
print("\n\ntrace_file_index (what files matter):")
for r in cur.fetchall():
    print(f"  {r}")

# trace_error_index
cur.execute("SELECT * FROM trace_error_index")
print("\ntrace_error_index:")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
