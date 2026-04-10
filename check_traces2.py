#!/usr/bin/env python3
"""Check traces table and trace capture wiring."""
import sqlite3, os

db = '/root/.borg/borg_v3.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(traces)")
    cols = cur.fetchall()
    print("traces table schema:")
    for c in cols:
        print(f"  {c}")
    cur.execute("SELECT COUNT(*) FROM traces")
    n = cur.fetchone()[0]
    print(f"\ntraces rows: {n}")
    conn.close()

# Check save_trace function
import inspect
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')
from borg.core import traces
print("\ntraces.py exports:")
print([x for x in dir(traces) if not x.startswith('_')])

# Check save_trace signature
if hasattr(traces, 'save_trace'):
    print(f"\nsave_trace: {inspect.signature(traces.save_trace)}")
if hasattr(traces, 'TraceCapture'):
    tc = traces.TraceCapture
    print(f"\nTraceCapture.extract_trace: {inspect.signature(tc.extract_trace)}")
