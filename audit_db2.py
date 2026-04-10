#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/root/.borg/borg_v3.db')
cur = conn.cursor()

# Outcomes schema
cur.execute('PRAGMA table_info(outcomes)')
print('outcomes schema:', cur.fetchall())

# Sample recent outcomes
cur.execute('SELECT pack_id, task_category, success, tokens_used, time_taken FROM outcomes ORDER BY id DESC LIMIT 5')
print('\nRecent outcomes:')
for r in cur.fetchall():
    print(f'  {r}')

# Check traces table
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traces'")
if cur.fetchone():
    cur.execute('SELECT COUNT(*) FROM traces')
    print(f'\ntraces: {cur.fetchone()[0]} rows')
else:
    print('\nNo traces table in borg_v3.db')

# Check pack_versions
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pack_versions'")
if cur.fetchone():
    cur.execute('SELECT COUNT(*) FROM pack_versions')
    print(f'pack_versions: {cur.fetchone()[0]} rows')

conn.close()
