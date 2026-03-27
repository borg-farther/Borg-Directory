"""Guild database migrations."""

import threading

# Global lock for thread-safe migration
_migration_lock = threading.Lock()

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
    """Apply all pending migrations in a thread-safe manner."""
    # First check without lock (fast path for already-migrated DBs)
    current_version = get_current_version(conn)
    latest_version = max(m[0] for m in MIGRATIONS)
    
    if current_version >= latest_version:
        return current_version
    
    # Need to migrate - acquire lock
    with _migration_lock:
        # Re-check version after acquiring lock (another thread may have migrated)
        current_version = get_current_version(conn)
        
        for version, description, statements in MIGRATIONS:
            if version > current_version:
                for stmt in statements:
                    conn.execute(stmt)
                
                # Insert version record after all schema changes
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at, description) VALUES (?, datetime('now'), ?)",
                    (version, description),
                )
                conn.commit()
                current_version = version
        
        return current_version
