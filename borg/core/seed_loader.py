"""
seed_loader.py  imports collective_seed.json into a fresh BORG_HOME database.
Called automatically on first borg_observe if the database has fewer than 10 traces.
"""
import json, os, sqlite3, importlib.resources
from pathlib import Path


def _db_path() -> str:
    return str(Path(os.environ.get('BORG_HOME', '~/.borg')).expanduser() / 'traces.db')


def needs_seeding(db_path: str) -> bool:
    try:
        db = sqlite3.connect(db_path)
        count = db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        db.close()
        return count < 10
    except Exception:
        return True


def load_collective_seed(db_path: str) -> int:
    """Load bundled collective traces into a fresh database. Returns count loaded."""
    try:
        # Find the seed file
        seed_path = Path(__file__).parent.parent / 'seeds_data' / 'collective_seed.json'
        if not seed_path.exists():
            return 0

        data = json.loads(seed_path.read_text())
        traces = data.get('traces', [])
        if not traces:
            return 0

        db = sqlite3.connect(db_path)
        # Ensure table exists
        db.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                outcome TEXT NOT NULL,
                root_cause TEXT,
                approach_summary TEXT,
                files_read TEXT,
                files_modified TEXT,
                key_files TEXT,
                tool_calls INTEGER DEFAULT 0,
                errors_encountered TEXT,
                dead_ends TEXT,
                keywords TEXT,
                technology TEXT,
                error_patterns TEXT,
                helpfulness_score REAL DEFAULT 0.5,
                times_shown INTEGER DEFAULT 0,
                times_helped INTEGER DEFAULT 0,
                agent_id TEXT,
                created_at TEXT NOT NULL,
                source TEXT DEFAULT 'auto',
                causal_intervention TEXT
            )
        """)

        loaded = 0
        for t in traces:
            try:
                db.execute("""
                    INSERT OR IGNORE INTO traces
                    (id, task_description, outcome, root_cause, approach_summary,
                     files_read, files_modified, key_files, tool_calls, errors_encountered,
                     dead_ends, keywords, technology, error_patterns, helpfulness_score,
                     times_shown, times_helped, agent_id, created_at, source, causal_intervention)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    t.get('id'), t.get('task_description', ''), t.get('outcome', 'unknown'),
                    t.get('root_cause'), t.get('approach_summary'),
                    t.get('files_read'), t.get('files_modified'), t.get('key_files'),
                    t.get('tool_calls', 0), t.get('errors_encountered'),
                    t.get('dead_ends'), t.get('keywords'), t.get('technology'),
                    t.get('error_patterns'), t.get('helpfulness_score', 0.5),
                    t.get('times_shown', 0), t.get('times_helped', 0),
                    t.get('agent_id', 'borg-collective'), t.get('created_at', '2026-01-01T00:00:00'),
                    t.get('source', 'auto'), t.get('causal_intervention')
                ))
                loaded += 1
            except Exception:
                continue

        db.commit()
        db.close()
        return loaded
    except Exception as e:
        return 0


def ensure_seeded(db_path: str = None) -> bool:
    """Call at startup. Seeds the DB if fresh. Returns True if seeding occurred."""
    if db_path is None:
        db_path = _db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if needs_seeding(db_path):
        count = load_collective_seed(db_path)
        return count > 0
    return False
