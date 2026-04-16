"""
Borg Trace Matcher — Find relevant investigation traces for new problems.

Multi-signal matching: FTS5 text search + error type + file overlap + helpfulness.
Zero ML dependencies. SQLite-only. <100ms latency.
"""

import json
import logging
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional

from borg.core.traces import _get_db, TRACE_DB_PATH

logger = logging.getLogger(__name__)

#  C1 FIX: FTS5 injection sanitizer 
_FTS5_SPECIAL = re.compile(r'["\'\*\(\)\-\+\:\^]')
_MULTI_SPACE = re.compile(r'\s+')
_FTS_KEYWORDS = {'NEAR', 'NOT', 'AND', 'OR'}

def _sanitize_fts(query: str) -> str:
    """Sanitize query for safe FTS5 MATCH. Strips operators, keywords, limits length."""
    if not query or not isinstance(query, str):
        return ''
    cleaned = _FTS5_SPECIAL.sub(' ', query)
    words = [w for w in cleaned.split() if w.upper() not in _FTS_KEYWORDS]
    result = _MULTI_SPACE.sub(' ', ' '.join(words)).strip()
    return result[:500].rsplit(' ', 1)[0] if len(result) > 500 else result


#  H3 FIX: Specific error patterns BEFORE generic catchall 
ERROR_CLASS_PATTERNS = [
    (re.compile(r'EADDRINUSE', re.I), 'port-already-in-use'),
    (re.compile(r'ENOMEM|OOM|OutOfMemory', re.I), 'memory-oom'),
    (re.compile(r'ECONNREFUSED|connection\s+refused', re.I), 'connection-refused'),
    (re.compile(r'ENOENT|FileNotFound|No such file', re.I), 'file-not-found'),
    (re.compile(r'EPERM|EACCES|PermissionError|permission denied', re.I), 'permission-error'),
    (re.compile(r'ETIMEOUT|TimeoutError|timed?\s*out', re.I), 'timeout-error'),
    (re.compile(r'CORS|Access-Control-Allow', re.I), 'cors-error'),
    (re.compile(r'SSL|certificate\s+(verify|expired|invalid)', re.I), 'ssl-cert-error'),
    (re.compile(r'ModuleNotFoundError|ImportError|No module named', re.I), 'python-import-error'),
    (re.compile(r'SyntaxError', re.I), 'syntax-error'),
    (re.compile(r'TypeError', re.I), 'type-error'),
    (re.compile(r'KeyError', re.I), 'key-error'),
    (re.compile(r'JSONDecodeError|JSON\.parse|Unexpected token', re.I), 'json-parse-error'),
    (re.compile(r'Cannot find module|MODULE_NOT_FOUND', re.I), 'node-module-not-found'),
    (re.compile(r'migration|migrate|alembic', re.I), 'db-migration-error'),
    (re.compile(r'peer dep|ERESOLVE|npm ERR', re.I), 'npm-dep-conflict'),
    # Generic catchall LAST (H3 fix)
    (re.compile(r'(\w+Error)\b'), 'generic-error'),
    (re.compile(r'(\w+Exception)\b'), 'generic-exception'),
]

def _classify_error(error_text: str):
    """Classify error into error class. Specific patterns first, generic last."""
    if not error_text:
        return None
    for pattern, error_class in ERROR_CLASS_PATTERNS:
        if pattern.search(error_text):
            return error_class
    return None



class TraceMatcher:
    """Match incoming problems to relevant prior investigation traces."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or TRACE_DB_PATH

    def find_relevant(self, task: str, error: str = "",
                      files: List[str] = None, top_k: int = 3) -> List[Dict]:
        """Find traces relevant to the current problem.

        Scoring:
          - FTS5 text match: base score from rank
          - Error type match: +5 per match
          - File path overlap: +3 per match
          - Helpfulness: multiply by helpfulness_score
        """
        start = time.time()

        db = _get_db(self.db_path)
        candidates: Dict[str, float] = {}  # trace_id -> score

        #  Strategy 1: Error class exact match (H3 patterns) 
        error_class = _classify_error(error or task)
        if error_class:
            try:
                rows = db.execute(
                    "SELECT id FROM traces WHERE LOWER(error_patterns) LIKE ? OR LOWER(keywords) LIKE ?",
                    (f"%{error_class}%", f"%{error_class}%")
                ).fetchall()
                for row in rows:
                    candidates[row[0]] = candidates.get(row[0], 0) + 8.0
                if rows:
                    logger.debug("Strategy 1 (error_class=%s): %d matches", error_class, len(rows))
            except Exception as e:
                logger.debug("Strategy 1 failed: %s", e)

        #  Strategy 2: Semantic embedding search 
        try:
            from borg.core.embeddings import semantic_search
            query = f"{task} {error}".strip()
            semantic = semantic_search(
                query=query, db_path=self.db_path,
                top_k=top_k, min_similarity=0.25
            )
            for t in (semantic or []):
                tid = t.get('id') or t.get('trace_id', '')
                if tid:
                    sim = float(t.get('similarity', t.get('score', 0.5)))
                    candidates[tid] = candidates.get(tid, 0) + 4.0 + sim * 2
            if semantic:
                logger.debug("Strategy 2 (semantic): %d results", len(semantic))
        except Exception as e:
            logger.debug("Strategy 2 skipped: %s", e)

        # Signal 1: FTS5 text search (with keyword fallback on FTS failure)
        search_terms = _sanitize_fts(self._extract_search_terms(task, error))
        if search_terms:
            fts_rows = []
            try:
                rows = db.execute(
                    "SELECT rowid, rank FROM traces_fts WHERE traces_fts MATCH ? ORDER BY rank LIMIT 20",
                    (search_terms,)
                ).fetchall()
                for row in rows:
                    trace_row = db.execute(
                        "SELECT id FROM traces WHERE rowid = ?", (row[0],)
                    ).fetchone()
                    if trace_row:
                        candidates[trace_row[0]] = abs(row[1])
            except Exception as _fts_err:
                logger.debug("FTS search failed, using keyword fallback: %s", _fts_err)
                # Keyword fallback: search task keywords in traces table
                for word in search_terms.split(' OR ')[:5]:
                    word = word.strip()
                    if len(word) > 2:
                        kw_rows = db.execute(
                            "SELECT id FROM traces WHERE "
                            "LOWER(task_description) LIKE ? OR LOWER(keywords) LIKE ?",
                            (f"%{word}%", f"%{word}%")
                        ).fetchall()
                        for kw_row in kw_rows:
                            candidates[kw_row[0]] = candidates.get(kw_row[0], 0) + 1.0

        # Signal 2: Error type matching
        if error:
            error_type = _classify_error(error)
            if error_type:
                rows = db.execute(
                    "SELECT trace_id FROM trace_error_index WHERE error_type = ?",
                    (error_type,)
                ).fetchall()
                for row in rows:
                    tid = row[0]
                    candidates[tid] = candidates.get(tid, 0) + 5.0

        # Signal 3: File overlap
        if files:
            for f in (files or [])[:5]:
                rows = db.execute(
                    "SELECT trace_id FROM trace_file_index WHERE file_path = ?",
                    (f,)
                ).fetchall()
                for row in rows:
                    tid = row[0]
                    candidates[tid] = candidates.get(tid, 0) + 3.0

        if not candidates:
            db.close()
            return []

        # Fetch full traces and apply helpfulness multiplier
        results = []
        for tid, score in sorted(candidates.items(), key=lambda x: -x[1])[:top_k * 2]:
            trace = db.execute("SELECT * FROM traces WHERE id = ?", (tid,)).fetchone()
            if trace:
                trace_dict = dict(trace)
                helpfulness = trace_dict.get("helpfulness_score", 0.5)
                trace_dict["match_score"] = score * max(0.1, helpfulness)
                results.append(trace_dict)

        db.close()

        results = self._apply_recency_decay(results)
        elapsed = time.time() - start
        logger.debug(f"Trace match: {len(results)} results in {elapsed:.3f}s")

        return results[:top_k]

    def format_for_agent(self, trace: Dict) -> str:
        """Format a trace as concise guidance for an agent."""
        parts = []

        if trace.get("root_cause"):
            parts.append(f"ROOT CAUSE: {trace['root_cause']}")

        key_files = trace.get("key_files", "[]")
        if isinstance(key_files, str):
            key_files = json.loads(key_files)
        if key_files:
            parts.append(f"KEY FILES: {', '.join(key_files[:3])}")

        if trace.get("approach_summary"):
            parts.append(f"APPROACH: {trace['approach_summary']}")

        dead_ends = trace.get("dead_ends", "[]")
        if isinstance(dead_ends, str):
            dead_ends = json.loads(dead_ends)
        if dead_ends:
            parts.append(f"AVOID: {'; '.join(str(d) for d in dead_ends[:2])}")

        outcome = trace.get("outcome", "unknown")
        calls = trace.get("tool_calls", "?")
        if outcome == "success":
            parts.append(f"(Solved a similar problem in {calls} steps)")
        elif outcome == "failure":
            parts.append(f"(Prior agent investigated but couldn't solve — learn from their findings)")

        return "\n".join(parts) if parts else ""

    def record_shown(self, trace_id: str, db_path: str = None):
        """Record that a trace was shown to an agent."""
        db = _get_db(db_path or self.db_path)
        db.execute("UPDATE traces SET times_shown = times_shown + 1 WHERE id = ?", (trace_id,))
        db.commit()
        db.close()
    def record_outcome(self, trace_id: str, helped: bool, db_path: str = None):
        """Record whether a shown trace helped the agent succeed."""
        db = _get_db(db_path or self.db_path)
        row = db.execute(
            "SELECT times_shown, times_helped FROM traces WHERE id = ?",
            (trace_id,)
        ).fetchone()
        if not row:
            db.close()
            return
        shown = row[0] or 0
        new_helped = (row[1] or 0) + (1 if helped else 0)
        score = new_helped / shown if shown > 0 else 0.5
        db.execute(
            "UPDATE traces SET times_helped = ?, helpfulness_score = ? WHERE id = ?",
            (new_helped, score, trace_id)
        )
        db.commit()
        db.close()

    def _get_recency_weight(self, created_at: str, source: str = None) -> float:
        """Apply exponential temporal decay to older traces."""
        try:
            from borg.core.temporal import recency_weight
            return recency_weight(created_at, source=source)
        except Exception:
            return 1.0

    def _apply_recency_decay(self, results: list) -> list:
        """Apply temporal decay to result scores, keeping seed_pack traces timeless."""
        for r in results:
            try:
                source = r.get('source', None)
                created = r.get('created_at', '')
                r['match_score'] = r.get('match_score', 0.5) * self._get_recency_weight(created, source)
            except Exception:
                pass
        return sorted(results, key=lambda x: x.get('match_score', 0), reverse=True)

    def _extract_search_terms(self, task: str, error: str) -> str:
        """Extract FTS5-compatible search terms."""
        text = f"{task} {error}".lower()
        noise = {"the", "a", "an", "is", "was", "in", "on", "at", "to", "for", "of",
                 "and", "or", "but", "not", "with", "this", "that", "it", "i", "my",
                 "fix", "bug", "error", "issue", "problem", "please", "help", "need"}
        words = [w for w in re.findall(r'\w+', text) if len(w) > 2 and w not in noise]
        if not words:
            return ""
        return " OR ".join(words[:8])

    def _extract_error_type(self, error: str) -> Optional[str]:
        """Extract error type from error message."""
        match = re.search(r'(\w+Error|\w+Exception)', error)
        return match.group(1) if match else None


#  Module-level API (matches Engineering Spec Section 2.3) 
def find_relevant(task: str, technology: str = None, limit: int = 5) -> list:
    """Module-level wrapper for TraceMatcher.find_relevant().
    Maps the public API (task, technology) to the internal API (task, error, top_k)."""
    tm = TraceMatcher()
    return tm.find_relevant(task=task, error=task, top_k=limit)


def extract_error_class(task: str) -> str:
    """Module-level wrapper for _classify_error."""
    return _classify_error(task) or ''
