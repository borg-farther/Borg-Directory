"""
Negative trace retrieval — finds failure traces similar to current task.
Returns structured dead-end warnings to inject into agent context.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import List, Dict

logger = logging.getLogger(__name__)


def find_negative_traces(task: str, error: str = '', db_path: str = None, top_k: int = 5) -> List[Dict]:
    if db_path is None:
        from borg.core.traces import TRACE_DB_PATH
        db_path = TRACE_DB_PATH
    if not os.path.exists(db_path):
        return []

    # Try semantic
    try:
        from borg.core.embeddings import semantic_search
        results = semantic_search(
            query=f"{task} {error}".strip(),
            db_path=db_path, top_k=top_k,
            min_similarity=0.2, outcome_filter='failure'
        )
        if results:
            return results
    except Exception:
        pass

    # Keyword fallback
    try:
        db = sqlite3.connect(db_path, timeout=10)
        db.row_factory = sqlite3.Row
        words = [w.lower() for w in task.split() if len(w) > 4][:3]
        if not words:
            db.close()
            return []
        conditions = ' OR '.join(f"task_description LIKE ?" for _ in words)
        rows = db.execute(
            f"SELECT id, task_description, technology, root_cause, approach_summary "
            f"FROM traces WHERE outcome='failure' AND ({conditions}) "
            f"ORDER BY created_at DESC LIMIT ?",
            [f'%{w}%' for w in words] + [top_k]
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.debug(f"negative_traces: keyword fallback failed: {e}")
    return []


def get_dead_end_patterns(task: str, error: str = '', db_path: str = None) -> Dict:
    negative = find_negative_traces(task, error, db_path, top_k=10)
    if not negative:
        return {'dead_ends': [], 'count': 0, 'total_failure_sessions': 0}

    approach_groups = {}
    for trace in negative:
        approach = trace.get('approach_summary', '').strip()
        if not approach:
            continue
        key = approach.lower()[:60]
        if key not in approach_groups:
            approach_groups[key] = {
                'approach': approach[:200],
                'root_cause': trace.get('root_cause', '')[:200],
                'count': 0
            }
        approach_groups[key]['count'] += 1

    dead_ends = sorted(approach_groups.values(), key=lambda x: x['count'], reverse=True)
    return {
        'dead_ends': dead_ends[:3],
        'count': len(negative),
        'total_failure_sessions': len(negative)
    }
