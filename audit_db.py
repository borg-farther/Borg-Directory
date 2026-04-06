#!/usr/bin/env python3
"""Borg E2E audit - data store check."""
import sqlite3
conn = sqlite3.connect('/root/.borg/borg_v3.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM outcomes')
total = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM outcomes WHERE success=1')
success = cur.fetchone()[0]
print(f'Total outcomes: {total}')
print(f'Successful: {success}')
print(f'Failed: {total - success}')
