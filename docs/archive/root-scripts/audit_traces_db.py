#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/root/.borg/traces.db')
cur = conn.cursor()

# Get full schema
cur.execute('PRAGMA table_info(traces)')
print('Traces schema:')
for col in cur.fetchall():
    print(f'  {col}')

print()

# Sample traces - use correct column names
cur.execute('SELECT * FROM traces ORDER BY id DESC LIMIT 3')
rows = cur.fetchall()
if rows:
    print('Sample traces (all columns):')
    for r in rows:
        print(f'  {r[:3]}...')  # first 3 cols only
else:
    print('No traces found')

# Check what columns exist
cur.execute('PRAGMA table_info(traces)')
cols = [col[1] for col in cur.fetchall()]
print(f'\nColumn names: {cols}')

# Try to get meaningful data
select_cols = ', '.join(cols[:5]) if len(cols) >= 5 else ', '.join(cols)
cur.execute(f'SELECT {select_cols} FROM traces ORDER BY id DESC LIMIT 3')
print(f'\nTop rows ({select_cols}):')
for r in cur.fetchall():
    print(f'  {r}')

conn.close()
