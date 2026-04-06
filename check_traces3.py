#!/usr/bin/env python3
import sqlite3, os

# traces.db is separate from borg_v3.db
db = os.path.join(os.path.expanduser('~'), '.borg', 'traces.db')
print(f"Checking: {db}")
print(f"Exists: {os.path.exists(db)}")

if os.path.exists(db):
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables: {tables}")
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        n = cur.fetchone()[0]
        print(f"  {t}: {n} rows")
    conn.close()
