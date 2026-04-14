import os
from pathlib import Path

MARKERS = {
    'manage.py': 'django', 'tsconfig.json': 'typescript',
    'package.json': 'nodejs', 'Cargo.toml': 'rust',
    'go.mod': 'go', 'Dockerfile': 'docker',
    'pom.xml': 'java', 'requirements.txt': 'python',
    'pyproject.toml': 'python', 'Gemfile': 'ruby',
}
DIR_MARKERS = {'.github/workflows': 'github-actions'}

def detect_stack(cwd=None):
    cwd = Path(cwd or os.getcwd())
    found = []
    for marker, tech in MARKERS.items():
        if (cwd / marker).exists() and tech not in found:
            found.append(tech)
    for d, tech in DIR_MARKERS.items():
        if (cwd / d).is_dir() and tech not in found:
            found.append(tech)
    return found[:4]

def get_briefing(cwd=None):
    import sqlite3, os as _os
    stack = detect_stack(cwd)
    if not stack:
        return ''
    db_path = str(Path(_os.environ.get('BORG_HOME','~/.borg')).expanduser()/'traces.db')
    parts = []
    try:
        db = sqlite3.connect(db_path)
        for tech in stack[:3]:
            real = db.execute(
                "SELECT COUNT(*) FROM traces WHERE technology=? AND (source IS NULL OR source NOT IN ('seed_pack','e2e_test'))",
                (tech,)).fetchone()[0]
            if real < 3:
                continue
            fails = db.execute(
                "SELECT root_cause FROM traces WHERE technology=? AND outcome='failure' AND root_cause IS NOT NULL LIMIT 2",
                (tech,)).fetchall()
            wins = db.execute(
                "SELECT approach_summary FROM traces WHERE technology=? AND outcome='success' AND helpfulness_score>0.6 ORDER BY helpfulness_score DESC LIMIT 2",
                (tech,)).fetchall()
            if not wins:
                continue
            block = [f"[{tech.upper()} - {real} prior sessions]"]
            for (rc,) in fails:
                block.append(f"  Avoid: {str(rc)[:80]}")
            for (ap,) in wins:
                block.append(f"  Worked: {str(ap)[:80]}")
            parts.append('\n'.join(block))
        db.close()
    except Exception:
        pass
    if not parts:
        return ''
    return '=== BORG SESSION BRIEFING ===\n' + '\n\n'.join(parts) + '\n' + '-'*50
