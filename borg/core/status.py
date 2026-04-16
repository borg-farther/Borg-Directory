"""Borg collective status  shows corpus health and user contributions."""
import sqlite3, os, time

def get_status(agent_id=None, db_path=None):
    db_path = db_path or os.path.join(os.environ.get('BORG_HOME', os.path.expanduser('~/.borg')), 'traces.db')
    db = sqlite3.connect(db_path)
    organic = db.execute('SELECT COUNT(*) FROM traces').fetchone()[0]
    seed = db.execute('SELECT COUNT(*) FROM seed_traces').fetchone()[0]
    total = organic + seed
    top_tech = db.execute('SELECT technology, COUNT(*) as c FROM traces WHERE length(technology)>=2 GROUP BY technology ORDER BY c DESC LIMIT 5').fetchall()
    recent = db.execute('SELECT task_description, technology, created_at FROM traces ORDER BY created_at DESC LIMIT 1').fetchone()
    user_count = 0
    if agent_id:
        user_count = db.execute('SELECT COUNT(*) FROM traces WHERE agent_id=?', (agent_id,)).fetchone()[0]
    db.close()
    lines = []
    lines.append('BORG COLLECTIVE STATUS')
    lines.append('=' * 40)
    lines.append(f'Total traces: {total} ({organic} real + {seed} seed)')
    if agent_id and user_count > 0:
        lines.append(f'Your contributions: {user_count} traces')
    lines.append(f'Top domains: {", ".join(f"{t[0]}({t[1]})" for t in top_tech)}')
    if recent:
        lines.append(f'Latest: {recent[0][:80]}... [{recent[1]}] {recent[2]}')
    lines.append('=' * 40)
    lines.append('Every error your agent fixes makes the collective smarter.')
    return '\n'.join(lines)
