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
    _ensure_schema(db)
    return db


def _ensure_schema(db: sqlite3.Connection):
    """Create tables if they don't exist."""
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
            source TEXT DEFAULT 'auto'
        );
        
        CREATE INDEX IF NOT EXISTS idx_traces_technology ON traces(technology);
        CREATE INDEX IF NOT EXISTS idx_traces_outcome ON traces(outcome);
        CREATE INDEX IF NOT EXISTS idx_traces_helpfulness ON traces(helpfulness_score DESC);
        
        CREATE TABLE IF NOT EXISTS trace_file_index (
            trace_id TEXT NOT NULL,
            file_path TEXT NOT NULL,
            role TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_tfi_file ON trace_file_index(file_path);
        
        CREATE TABLE IF NOT EXISTS trace_error_index (
            trace_id TEXT NOT NULL,
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
    except Exception:
        pass  # FTS5 might already exist
    
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
        self.tool_calls: int = 0
        self.started_at: float = time.time()
        self.approaches: List[str] = []

    def on_tool_call(self, tool_name: str, args: Dict[str, Any], result: str):
        """Called after every tool call the agent makes."""
        self.tool_calls += 1

        # Track file reads
        if tool_name in ("read_file", "search_files", "cat") and "path" in args:
            path = args["path"]
            if path and not path.startswith("/tmp"):
                self.files_read.append(path)

        # Track file modifications
        if tool_name in ("write_file", "patch", "sed") and "path" in args:
            path = args["path"]
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
    """Detect technology from file paths."""
    patterns = {
        "django": ["django/", "manage.py", "/models.py", "/views.py", "/urls.py"],
        "flask": ["flask/", "/app.py", "/routes.py"],
        "react": [".jsx", ".tsx", "/components/"],
        "node": ["/node_modules/", "package.json", ".mjs"],
        "docker": ["Dockerfile", "docker-compose"],
        "python": [".py"],
        "typescript": [".ts"],
        "rust": [".rs", "Cargo.toml"],
        "go": [".go", "go.mod"],
    }
    file_str = " ".join(files).lower()
    for tech, markers in patterns.items():
        if any(m.lower() in file_str for m in markers):
            return tech
    return "unknown"


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
    
    db.commit()
    db.close()
    
    return {"decayed": decayed, "deleted": deleted, "total": total}
