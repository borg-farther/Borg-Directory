"""
Borg Auto-Trace System — Capture, store, and retrieve investigation traces.

When agents solve (or fail at) hard problems, this module automatically
captures what they learned: which files mattered, what errors appeared,
what approaches worked or didn't.
"""

import json
import logging
import os
import re
import sqlite3
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_fts_available = True  # module-level FTS5 flag

# Database location
TRACE_DB_PATH = os.path.join(
    os.getenv("BORG_HOME", os.path.join(str(Path.home()), ".borg")),
    "traces.db"
)


def _get_db(db_path: str = None) -> sqlite3.Connection:
    """Get or create the trace database."""
    path = db_path or TRACE_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")  # Cascade deletes
    _ensure_schema(db)
    return db


def _ensure_schema(db: sqlite3.Connection):
    """Create tables if they don't exist."""
    global _fts_available
    db.executescript("""
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
        );
        
        CREATE INDEX IF NOT EXISTS idx_traces_technology ON traces(technology);
        CREATE INDEX IF NOT EXISTS idx_traces_outcome ON traces(outcome);
        CREATE INDEX IF NOT EXISTS idx_traces_helpfulness ON traces(helpfulness_score DESC);
        
        CREATE TABLE IF NOT EXISTS trace_file_index (
            trace_id TEXT NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tfi_file ON trace_file_index(file_path);
        
        CREATE TABLE IF NOT EXISTS trace_error_index (
            trace_id TEXT NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
            error_type TEXT NOT NULL,
            error_context TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tei_error ON trace_error_index(error_type);
    """)
    
    # Create FTS5 table if not exists
    try:
        db.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS traces_fts USING fts5(
                task_description, root_cause, approach_summary, keywords, error_patterns,
                content=traces, content_rowid=rowid
            )
        """)
        # Verify FTS5 is functional
        db.execute("SELECT * FROM traces_fts LIMIT 0")
        _fts_available = True
    except Exception as _e:
        logger.warning(
            "FTS5 not available (%s). Trace search will use keyword fallback. "
            "Install SQLite with FTS5 for better results.", _e
        )
        _fts_available = False
    
    db.commit()


# ---------------------------------------------------------------------------
# Trace Capture
# ---------------------------------------------------------------------------

class TraceCapture:
    """Accumulates agent activity and extracts investigation traces."""

    def __init__(self, task: str = "", agent_id: str = ""):
        self.task = task
        self.agent_id = agent_id
        self.files_read: List[str] = []
        self.files_modified: List[str] = []
        self.errors: List[str] = []
        self.calls: List[Dict[str, Any]] = []
        self.tool_calls: int = 0
        self.started_at: float = time.time()
        self.approaches: List[str] = []

    def on_tool_call(self, tool_name: str, args: Dict[str, Any], result: str):
        """Called after every tool call the agent makes."""
        self.tool_calls += 1
        self.calls.append({"tool": tool_name, "args": args, "result": result})

        # Track file reads
        READ_TOOLS = {"read_file", "search_files", "cat", "view", "get_file_content", "read_page"}
        WRITE_TOOLS = {"write_file", "patch", "sed", "str_replace", "create_file",
                       "insert", "edit_file", "apply_patch"}

        if tool_name in READ_TOOLS and "path" in args:
            path = args["path"]
            if path and not path.startswith("/tmp"):
                self.files_read.append(path)

        # Track file modifications
        if tool_name in WRITE_TOOLS:
            path = args.get("path") or args.get("file_path") or args.get("target")
            if path and not path.startswith("/tmp"):
                self.files_modified.append(path)

        # Track errors from terminal output
        if isinstance(result, str) and len(result) > 10:
            for line in result.split("\n"):
                line_s = line.strip()
                if re.search(r'(Error|Exception|FAILED|Traceback)', line_s) and len(line_s) < 300:
                    self.errors.append(line_s[:200])
                    break

    def extract_trace(self, outcome: str = "unknown", root_cause: str = "",
                      approach_summary: str = "") -> Dict[str, Any]:
        """Extract a structured trace from accumulated activity."""
        read_counts = Counter(self.files_read)
        mod_counts = Counter(self.files_modified)

        # Key files = modified + most frequently read
        key_files = sorted(
            set(list(mod_counts.keys()) + [f for f, _ in read_counts.most_common(3)]),
            key=lambda f: mod_counts.get(f, 0) * 10 + read_counts.get(f, 0),
            reverse=True
        )[:5]

        technology = _detect_technology(key_files + list(read_counts.keys())[:10])
        keywords = _extract_keywords(self.task, self.errors)
        error_patterns = _normalize_errors(self.errors)

        # Identify dead ends: files read many times but never modified
        dead_ends = []
        for f, count in read_counts.most_common(5):
            if count >= 3 and f not in mod_counts:
                dead_ends.append(f"Read {f} {count} times without modifying — may be a dead end")

        return {
            "id": str(uuid.uuid4())[:8],
            "task_description": self.task,
            "outcome": outcome,
            "root_cause": root_cause,
            "approach_summary": approach_summary,
            "files_read": json.dumps(list(set(self.files_read))),
            "files_modified": json.dumps(list(set(self.files_modified))),
            "key_files": json.dumps(key_files),
            "tool_calls": self.tool_calls,
            "errors_encountered": json.dumps(self.errors[:10]),
            "dead_ends": json.dumps(dead_ends),
            "keywords": keywords,
            "technology": technology,
            "error_patterns": error_patterns,
            "agent_id": self.agent_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "auto",
        }


def save_trace(trace: Dict[str, Any], db_path: str = None) -> str:
    """Save a trace to the database. Returns trace ID."""
    # Invariant I3: real traces only. Synthetic goes to seed_traces.
    if trace.get("source") in ("seed_pack", "golden_seed", "curated"):
        raise ValueError(
            f"save_trace() refuses non-organic source={trace.get('source')!r}. "
            "Non-organic traces must go to seed_traces (invariant I3)."
        )
    # Quality gate: reject hollow traces (competitive review #6)
    from borg.core.quality_gate import check_trace_quality
    passed, reason, qscore = check_trace_quality(trace)
    if not passed:
        raise ValueError(f'Trace rejected by quality gate: {reason}')

    db = _get_db(db_path)
    trace_id = trace.get("id", str(uuid.uuid4())[:8])
    
    db.execute("""
        INSERT OR REPLACE INTO traces 
        (id, task_description, outcome, root_cause, approach_summary,
         files_read, files_modified, key_files, tool_calls,
         errors_encountered, dead_ends, keywords, technology,
         error_patterns, agent_id, created_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trace_id, trace["task_description"], trace["outcome"],
        trace.get("root_cause", ""), trace.get("approach_summary", ""),
        trace.get("files_read", "[]"), trace.get("files_modified", "[]"),
        trace.get("key_files", "[]"), trace.get("tool_calls", 0),
        trace.get("errors_encountered", "[]"), trace.get("dead_ends", "[]"),
        trace.get("keywords", ""), trace.get("technology", ""),
        trace.get("error_patterns", ""), trace.get("agent_id", ""),
        trace.get("created_at", time.strftime("%Y-%m-%dT%H:%M:%SZ")),
        trace.get("source", "auto"),
    ))
    
    # Index files
    key_files = json.loads(trace.get("key_files", "[]"))
    for f in key_files:
        db.execute("INSERT INTO trace_file_index (trace_id, file_path, role) VALUES (?, ?, 'key')", 
                   (trace_id, f))
    
    modified = json.loads(trace.get("files_modified", "[]"))
    for f in modified:
        if f not in key_files:
            db.execute("INSERT INTO trace_file_index (trace_id, file_path, role) VALUES (?, ?, 'modified')",
                       (trace_id, f))
    
    # Index errors
    for pattern in trace.get("error_patterns", "").split():
        if pattern:
            db.execute("INSERT INTO trace_error_index (trace_id, error_type, error_context) VALUES (?, ?, ?)",
                       (trace_id, pattern, ""))
    
    # Update FTS
    try:
        db.execute("INSERT INTO traces_fts(rowid, task_description, root_cause, approach_summary, keywords, error_patterns) "
                   "VALUES ((SELECT rowid FROM traces WHERE id = ?), ?, ?, ?, ?, ?)",
                   (trace_id, trace["task_description"], trace.get("root_cause", ""),
                    trace.get("approach_summary", ""), trace.get("keywords", ""),
                    trace.get("error_patterns", "")))
    except Exception:
        pass
    
    db.commit()
    db.close()
    
    logger.info(f"Saved trace {trace_id}: {trace['outcome']} ({trace.get('tool_calls', 0)} calls)")
    return trace_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_technology(files: List[str]) -> str:
    """Detect technology from file paths — returns best match, not first."""
    patterns = {
        "django": ["django/", "manage.py", "/models.py", "/views.py", "/urls.py", "/migrations/"],
        "flask": ["flask/", "/app.py", "/routes.py"],
        "react": [".jsx", ".tsx", "/components/"],
        "node": ["/node_modules/", "package.json", ".mjs"],
        "docker": ["Dockerfile", "docker-compose"],
        "typescript": [".ts"],
        "python": [".py"],
        "rust": [".rs", "Cargo.toml"],
        "go": [".go", "go.mod"],
    }
    file_str = " ".join(files).lower()
    scores = {}
    for tech, markers in patterns.items():
        score = sum(1 for m in markers if m.lower() in file_str)
        if score > 0:
            scores[tech] = score
    if not scores:
        return "unknown"
    return max(scores, key=lambda k: scores[k])


def _extract_keywords(task: str, errors: List[str]) -> str:
    """Extract searchable keywords."""
    text = f"{task} {' '.join(errors)}".lower()
    stopwords = {"the", "a", "an", "is", "was", "in", "on", "at", "to", "for",
                 "of", "and", "or", "but", "not", "with", "this", "that", "it",
                 "i", "my", "we", "you", "be", "do", "has", "have", "had", "can"}
    words = [w for w in re.findall(r'\w+', text) if len(w) > 2 and w not in stopwords]
    return " ".join(sorted(set(words)))


def _normalize_errors(errors: List[str]) -> str:
    """Extract error type patterns."""
    types = set()
    for err in errors:
        match = re.search(r'(\w+Error|\w+Exception|\w+Warning)', err)
        if match:
            types.add(match.group(1))
    return " ".join(sorted(types))


# ---------------------------------------------------------------------------
# Trace Maintenance
# ---------------------------------------------------------------------------

from datetime import datetime, timezone, timedelta


def traces_maintenance(
    db_path: str = None,
    decay_factor: float = 0.95,
    decay_days: int = 30,
    max_traces: int = 10000,
) -> Dict[str, Any]:
    """
    Run trace maintenance: decay scores, delete low-value traces, enforce cap.
    
    Returns: {"decayed": int, "deleted": int, "total": int}
    """
    db = _get_db(db_path)
    
    decayed = 0
    deleted = 0
    
    # 1. Decay helpfulness_score for traces not shown in decay_days
    cutoff = (datetime.now(timezone.utc) - timedelta(days=decay_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = db.execute(
        """UPDATE traces 
           SET helpfulness_score = helpfulness_score * ?
           WHERE times_shown = 0 
             AND created_at < ?
             AND helpfulness_score > 0""",
        (decay_factor, cutoff)
    )
    decayed = cur.rowcount
    
    # 2. Delete traces with times_shown > 5 AND helpfulness_score < 0.1
    cur = db.execute(
        """DELETE FROM traces 
           WHERE times_shown > 5 AND helpfulness_score < 0.1"""
    )
    deleted = cur.rowcount
    
    # 3. Enforce 10,000 trace cap (FIFO — delete oldest)
    cur = db.execute("SELECT COUNT(*) FROM traces")
    total = cur.fetchone()[0]
    if total > max_traces:
        excess = total - max_traces
        db.execute(
            f"""DELETE FROM traces WHERE id IN (
                SELECT id FROM traces ORDER BY created_at ASC LIMIT ?
            )""",
            (excess,)
        )

    # 4. Clean up FTS orphans (traces deleted but FTS rows remain)
    try:
        db.execute("DELETE FROM traces_fts WHERE rowid NOT IN (SELECT rowid FROM traces)")
    except Exception:
        pass

    db.commit()
    db.close()

    return {"decayed": decayed, "deleted": deleted, "total": total}
