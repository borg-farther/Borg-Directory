#!/usr/bin/env python3
import sqlite3, os

db_paths = ['/root/.borg/borg_v3.db', '/root/.hermes/borg/borg_v3.db', '/root/.borg/borg.db']
for db in db_paths:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f'{db}: {tables}')
        for t in tables:
            cur.execute(f'SELECT COUNT(*) FROM {t}')
            n = cur.fetchone()[0]
            print(f'  {t}: {n} rows')
        conn.close()
    else:
        print(f'{db}: NOT FOUND')
