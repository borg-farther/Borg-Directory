#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/root/.borg/traces.db')
cur = conn.cursor()

# Get actual schema
cur.execute('PRAGMA table_info(traces)')
cols = cur.fetchall()
print("traces schema:")
for c in cols:
    print(f"  {c[1]}: {c[2]}")
print()

# Get first few rows
cur.execute('SELECT * FROM traces LIMIT 5')
rows = cur.fetchall()
print(f"Total traces: {cur.execute('SELECT COUNT(*)').fetchone()[0]}")
print()
for r in rows:
    print(f"row: {r}")
    print()