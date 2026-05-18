#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/root/.borg/traces.db')
cur = conn.cursor()

cur.execute('SELECT id, session_id, outcome, errors, technologies, keywords, created_at FROM traces LIMIT 10')
rows = cur.fetchall()
print(f'Total traces: {len(rows)}')
print()

for r in rows[:5]:
    id, session_id, outcome, errors, technologies, keywords, created_at = r
    print(f'id={id} outcome={outcome}')
    print(f'  session_id={session_id}')
    print(f'  errors={errors[:80] if errors else None}...')
    print(f'  technologies={technologies[:60] if technologies else None}...')
    print(f'  keywords={keywords[:60] if keywords else None}...')
    print()