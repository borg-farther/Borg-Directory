#!/usr/bin/env python3
"""Check trace data quality for extraction pipeline."""
import sqlite3, json

conn = sqlite3.connect('/root/.borg/traces.db')
cur = conn.cursor()

# How many traces have actual content (non-empty fields)?
cur.execute("""
    SELECT id, outcome, task_description, root_cause, approach_summary,
           files_read, files_modified, errors_encountered, keywords, technology,
           helpfulness_score, source
    FROM traces
    WHERE outcome = 'success'
""")
success_traces = cur.fetchall()
print(f"Traces with outcome=success: {len(success_traces)}")

non_empty = 0
for r in success_traces:
    id, outcome, task_desc, root_cause, approach, files_read, files_mod, errors, keywords, tech, helpful, source = r
    has_content = any([
        task_desc and len(task_desc) > 5,
        root_cause and len(root_cause) > 5,
        approach and len(approach) > 5,
        files_read not in ('[]', None, ''),
        errors not in ('[]', None, ''),
        keywords and len(keywords) > 5
    ])
    if has_content:
        non_empty += 1
        print(f"\n  Rich trace {id}:")
        print(f"    task_description: {task_desc[:60] if task_desc else None}")
        print(f"    root_cause: {root_cause[:60] if root_cause else None}")
        print(f"    approach: {approach[:60] if approach else None}")
        print(f"    files_read: {files_read[:60] if files_read else None}")
        print(f"    errors: {errors[:80] if errors else None}")
        print(f"    keywords: {keywords[:60] if keywords else None}")

print(f"\nTotal: {non_empty} traces with actual content out of {len(success_traces)} success traces")

# What about outcomes table - any useful data there?
conn2 = sqlite3.connect('/root/.borg/borg_v3.db')
cur2 = conn2.cursor()
cur2.execute("""
    SELECT COUNT(*) FROM outcomes WHERE success = 1
""")
print(f"\nOutcomes with success=1: {cur2.fetchone()[0]}")

cur2.execute("""
    SELECT pack_id, task_context, tokens_used, time_taken
    FROM outcomes WHERE success = 1
    ORDER BY timestamp DESC LIMIT 5
""")
for r in cur2.fetchall():
    print(f"  {r}")