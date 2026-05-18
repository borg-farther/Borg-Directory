"""Guild database migrations."""

import sqlite3
import threading
import time

# Global lock for thread-safe migration inside one Python process. SQLite
# BEGIN IMMEDIATE below is the cross-process lock for shared database files.
_migration_lock = threading.Lock()
_MIGRATION_BUSY_RETRIES = 5
_MIGRATION_BUSY_DELAYS_MS = [100, 200, 400, 800, 1600]


def _is_busy_error(exc: sqlite3.OperationalError) -> bool:
    code = getattr(exc, "sqlite_errorcode", getattr(exc, "code", None))
    message = str(exc).lower()
    return (
        code in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}
        or "database is locked" in message
        or "database table is locked" in message
        or "database schema is locked" in message
    )


def _retry_busy(operation):
    last_error = None
    for attempt in range(_MIGRATION_BUSY_RETRIES + 1):
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            if _is_busy_error(exc) and attempt < _MIGRATION_BUSY_RETRIES:
                last_error = exc
                time.sleep(_MIGRATION_BUSY_DELAYS_MS[attempt] / 1000.0)
                continue
            raise
    assert last_error is not None
    raise last_error

MIGRATIONS = [
    (
        1,
        "Initial schema with packs, feedback, agents, executions, schema_version",
        [
            """
            CREATE TABLE IF NOT EXISTS packs (
                id TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                yaml_content TEXT NOT NULL,
                confidence TEXT CHECK(confidence IN ('guessed','inferred','tested','validated')),
                tier TEXT CHECK(tier IN ('core','validated','community')) DEFAULT 'community',
                author_agent TEXT NOT NULL,
                author_operator TEXT,
                problem_class TEXT,
                domain TEXT,
                phase_count INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                pulled_at TEXT,
                local_path TEXT,
                metadata JSON
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                pack_id TEXT NOT NULL REFERENCES packs(id),
                author_agent TEXT NOT NULL,
                author_operator TEXT,
                confidence TEXT,
                outcome TEXT CHECK(outcome IN ('success','partial','failure')),
                execution_log_hash TEXT,
                evidence TEXT,
                suggestions TEXT,
                created_at TEXT NOT NULL,
                metadata JSON
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                operator TEXT NOT NULL,
                display_name TEXT,
                contribution_score REAL DEFAULT 0,
                reputation_score REAL DEFAULT 0.5,
                free_rider_score REAL DEFAULT 0,
                access_tier TEXT DEFAULT 'community',
                packs_published INTEGER DEFAULT 0,
                packs_consumed INTEGER DEFAULT 0,
                feedback_given INTEGER DEFAULT 0,
                registered_at TEXT NOT NULL,
                last_active_at TEXT,
                metadata JSON
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                pack_id TEXT NOT NULL REFERENCES packs(id),
                agent_id TEXT NOT NULL REFERENCES agents(agent_id),
                task TEXT,
                status TEXT CHECK(status IN ('started','in_progress','completed','failed','abandoned')),
                phases_completed INTEGER DEFAULT 0,
                phases_failed INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                log_hash TEXT,
                metadata JSON
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
            """,
            # Full-text search virtual table for packs
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS packs_fts USING fts5(
                id,
                problem_class,
                domain,
                author_agent,
                content='packs',
                content_rowid='rowid'
            )
            """,
            # Triggers to keep FTS in sync
            """
            CREATE TRIGGER IF NOT EXISTS packs_fts_insert AFTER INSERT ON packs BEGIN
                INSERT INTO packs_fts(rowid, id, problem_class, domain, author_agent)
                VALUES (NEW.rowid, NEW.id, NEW.problem_class, NEW.domain, NEW.author_agent);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS packs_fts_delete AFTER DELETE ON packs BEGIN
                INSERT INTO packs_fts(packs_fts, rowid, id, problem_class, domain, author_agent)
                VALUES ('delete', OLD.rowid, OLD.id, OLD.problem_class, OLD.domain, OLD.author_agent);
            END
            """,
            """
            CREATE TRIGGER IF NOT EXISTS packs_fts_update AFTER UPDATE ON packs BEGIN
                INSERT INTO packs_fts(packs_fts, rowid, id, problem_class, domain, author_agent)
                VALUES ('delete', OLD.rowid, OLD.id, OLD.problem_class, OLD.domain, OLD.author_agent);
                INSERT INTO packs_fts(rowid, id, problem_class, domain, author_agent)
                VALUES (NEW.rowid, NEW.id, NEW.problem_class, NEW.domain, NEW.author_agent);
            END
            """,
            # Indexes
            "CREATE INDEX IF NOT EXISTS idx_feedback_pack_id ON feedback(pack_id)",
            "CREATE INDEX IF NOT EXISTS idx_executions_pack_id ON executions(pack_id)",
            "CREATE INDEX IF NOT EXISTS idx_executions_agent_id ON executions(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_executions_session_id ON executions(session_id)",
        ],
    ),
    (
        2,
        "Add embeddings table for semantic search",
        [
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                pack_id TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
        ],
    ),
]


def get_current_version(conn):
    """Get the current schema version, or 0 if not initialized."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    if cursor.fetchone() is None:
        return 0
    cursor = conn.execute("SELECT MAX(version) FROM schema_version")
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0


def migrate(conn):
    """Apply all pending migrations safely across threads and processes."""
    latest_version = max(m[0] for m in MIGRATIONS)

    # Fast path for already-migrated DBs. This avoids taking a write lock on
    # every connection after the schema is current.
    current_version = get_current_version(conn)
    if current_version >= latest_version:
        return current_version

    def _migrate_in_transaction():
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Re-check after acquiring SQLite's cross-process writer lock. A
            # different process may have completed migration while we waited.
            current = get_current_version(conn)
            if current >= latest_version:
                conn.execute("COMMIT")
                return current

            for version, description, statements in MIGRATIONS:
                if version > current:
                    for stmt in statements:
                        conn.execute(stmt)

                    # Idempotent insert keeps stale/racy legacy databases from
                    # crashing if the schema table already has this version.
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_version (version, applied_at, description) VALUES (?, datetime('now'), ?)",
                        (version, description),
                    )
                    current = version

            conn.execute("COMMIT")
            return current
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise

    # Thread lock avoids duplicate work in one process; BEGIN IMMEDIATE is the
    # real cross-process guard for first-use DB bootstrap.
    with _migration_lock:
        return _retry_busy(_migrate_in_transaction)
