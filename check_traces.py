#!/usr/bin/env python3
"""Check traces table and trace capture wiring."""
import sqlite3, os

# Check traces table
db = '/root/.borg/borg_v3.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    
    # Check traces table schema and data
    cur.execute("PRAGMA table_info(traces)")
    cols = cur.fetchall()
    print("traces table schema:")
    for c in cols:
        print(f"  {c}")
    
    cur.execute("SELECT COUNT(*) FROM traces")
    n = cur.fetchone()[0]
    print(f"\ntraces rows: {n}")
    
    if n > 0:
        cur.execute("SELECT * FROM traces LIMIT 3")
        rows = cur.fetchall()
        print("Sample traces:")
        for r in rows:
            print(f"  {r[:5]}...")
    
    conn.close()
else:
    print(f"{db} not found")

# Check: does borg_observe call init_trace_capture?
print("\n--- Checking borg_observe trace wiring ---")
with open('/root/hermes-workspace/borg/borg/integrations/mcp_server.py') as f:
    content = f.read()

# Find borg_observe function and check what's called
import re
observe_match = re.search(r'def borg_observe\([^)]*\):(.*?)(?=\ndef |\nclass |\Z)', content, re.DOTALL)
if observe_match:
    observe_body = observe_match.group(1)
    print("Functions called in borg_observe:")
    calls = re.findall(r'(\w+)\(', observe_body)
    for c in sorted(set(calls)):
        if c not in ['self', 'len', 'str', 'int', 'list', 'dict', 'tuple', 'set', 'bool', 'float', 'any', 'all']:
            print(f"  {c}")
else:
    print("borg_observe not found")
