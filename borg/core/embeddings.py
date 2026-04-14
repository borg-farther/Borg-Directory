"""
Borg semantic embedding engine.
Thread-safe. Batch encodes. In-memory cache after first load.
Falls back to keyword search if sentence-transformers not available.
"""
from __future__ import annotations

import json
import logging
import os
import pickle
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
    _NUMPY_AVAILABLE = True
except ImportError:
    np = None
    _NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

EMBEDDING_CACHE_PATH = os.path.expanduser("~/.borg/embeddings.pkl")
EMBEDDING_DIM = 384

_model = None
_model_loaded = False
_model_lock = threading.Lock()

_index_cache: Optional[Dict[str, np.ndarray]] = None
_index_cache_size: int = 0


def _get_model():
    global _model, _model_loaded
    if _model_loaded:
        return _model
    with _model_lock:
        if _model_loaded:
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            start = time.time()
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(f"embeddings: model loaded in {time.time()-start:.1f}s")
        except ImportError:
            logger.warning("embeddings: sentence-transformers not installed — keyword fallback active")
            _model = None
        except Exception as e:
            logger.warning(f"embeddings: model load failed ({e}) — keyword fallback active")
            _model = None
        finally:
            _model_loaded = True
    return _model


def embed_text(text: str) -> Optional[np.ndarray]:
    model = _get_model()
    if model is None:
        return None
    try:
        vec = model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vec.astype(np.float32)
    except Exception as e:
        logger.warning(f"embeddings: encode failed: {e}")
        return None


def _trace_to_text(trace: dict) -> Optional[str]:
    parts = []
    task = trace.get('task_description', '').strip()
    if task:
        parts.append(f"task: {task}")
    root_cause = trace.get('root_cause', '').strip()
    if root_cause:
        parts.append(f"cause: {root_cause}")
    approach = trace.get('approach_summary', '').strip()
    if approach:
        parts.append(f"approach: {approach}")
    tech = trace.get('technology', '').strip()
    if tech and tech != 'unknown':
        parts.append(f"technology: {tech}")
    keywords = trace.get('keywords', [])
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except Exception:
            keywords = []
    if keywords:
        parts.append(f"keywords: {' '.join(keywords[:10])}")
    if not parts:
        return None
    return '\n'.join(parts)


def load_embedding_cache() -> dict:
    try:
        if os.path.exists(EMBEDDING_CACHE_PATH):
            with open(EMBEDDING_CACHE_PATH, 'rb') as f:
                return pickle.load(f)
    except Exception as e:
        logger.warning(f"embeddings: cache load failed: {e}")
    return {}


def save_embedding_cache(cache: dict):
    try:
        Path(EMBEDDING_CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(EMBEDDING_CACHE_PATH, 'wb') as f:
            pickle.dump(cache, f)
    except Exception as e:
        logger.warning(f"embeddings: cache save failed: {e}")


def build_index_from_db(db_path: str, force_rebuild: bool = False) -> Tuple[dict, int]:
    """Build embedding index. Batch encodes new traces. Updates in-memory cache."""
    global _index_cache, _index_cache_size

    cache = {} if force_rebuild else load_embedding_cache()

    try:
        db = sqlite3.connect(db_path, timeout=10)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT id, task_description, root_cause, approach_summary, causal_intervention, "
            "technology, keywords FROM traces WHERE outcome IN ('success', 'failure', 'fixed', 'partial')"
        ).fetchall()
        db.close()
    except Exception as e:
        logger.error(f"embeddings: DB read failed: {e}")
        _index_cache = cache
        _index_cache_size = len(cache)
        return cache, len(cache)

    model = _get_model()
    if model is None:
        _index_cache = cache
        _index_cache_size = len(cache)
        return cache, len(cache)

    new_traces = [dict(r) for r in rows if r['id'] not in cache]

    if not new_traces:
        logger.info(f"embeddings: index up to date ({len(cache)} traces)")
        _index_cache = cache
        _index_cache_size = len(cache)
        return cache, len(cache)

    logger.info(f"embeddings: batch-encoding {len(new_traces)} new traces...")

    texts = []
    valid_ids = []
    for trace in new_traces:
        text = _trace_to_text(trace)
        if text:
            texts.append(text)
            valid_ids.append(trace['id'])

    if texts:
        try:
            vectors = model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False
            )
            for trace_id, vec in zip(valid_ids, vectors):
                cache[trace_id] = vec.astype(np.float32)
        except Exception as e:
            logger.error(f"embeddings: batch encode failed: {e}")

    save_embedding_cache(cache)
    _index_cache = cache
    _index_cache_size = len(cache)
    logger.info(f"embeddings: index built — {len(cache)} total traces")
    return cache, len(cache)


def _get_index(db_path: str) -> dict:
    """Get in-memory index, rebuilding from disk if stale."""
    global _index_cache, _index_cache_size
    try:
        db = sqlite3.connect(db_path, timeout=5)
        db_count = db.execute(
            "SELECT COUNT(*) FROM traces WHERE outcome IN ('success','failure','fixed','partial')"
        ).fetchone()[0]
        db.close()
    except Exception:
        db_count = 0

    if _index_cache is None or db_count > _index_cache_size + 5:
        build_index_from_db(db_path)

    return _index_cache or {}


def semantic_search(
    query: str,
    db_path: str,
    top_k: int = 5,
    min_similarity: float = 0.3,
    outcome_filter: Optional[str] = None
) -> List[dict]:
    """Find top-k semantically similar traces. Uses in-memory cache."""
    model = _get_model()
    if model is None:
        return []

    query_vec = embed_text(query)
    if query_vec is None:
        return []

    cache = _get_index(db_path)
    if not cache:
        return []

    trace_ids = list(cache.keys())
    matrix = np.stack([cache[tid] for tid in trace_ids])
    sims = matrix @ query_vec

    mask = sims >= min_similarity
    filtered_ids = [trace_ids[i] for i in range(len(trace_ids)) if mask[i]]
    filtered_sims = sims[mask]

    if len(filtered_ids) == 0:
        return []

    order = np.argsort(filtered_sims)[::-1]
    top_ids = [filtered_ids[i] for i in order[:top_k * 2]]
    top_sims = {filtered_ids[i]: float(filtered_sims[i]) for i in order[:top_k * 2]}

    try:
        db = sqlite3.connect(db_path, timeout=10)
        db.row_factory = sqlite3.Row
        placeholders = ','.join(['?'] * len(top_ids))
        query_sql = f"""
            SELECT id, task_description, technology, outcome,
                   root_cause, approach_summary, keywords,
                   helpfulness_score, times_shown,
                   times_helped, created_at
            FROM traces WHERE id IN ({placeholders})
        """
        params = list(top_ids)
        if outcome_filter:
            query_sql += " AND outcome IN ('success', 'fixed', 'partial')"
            # outcome_filter already embedded in query
        rows = db.execute(query_sql, params).fetchall()
        db.close()
    except Exception as e:
        logger.error(f"embeddings: trace fetch failed: {e}")
        return []

    results = []
    for row in rows:
        trace = dict(row)
        trace['similarity'] = top_sims.get(trace['id'], 0.0)
        for field in ('keywords',):
            if isinstance(trace.get(field), str):
                try:
                    trace[field] = json.loads(trace[field])
                except Exception:
                    trace[field] = []
        results.append(trace)

    results.sort(key=lambda x: x['similarity'], reverse=True)
    return results[:top_k]


def get_embedding_stats(db_path: str) -> dict:
    cache = _index_cache or load_embedding_cache()
    try:
        db = sqlite3.connect(db_path, timeout=10)
        total = db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        db.close()
    except Exception:
        total = 0
    return {
        'model_available': _get_model() is not None,
        'total_traces': total,
        'indexed_traces': len(cache),
        'coverage_pct': round(len(cache) / max(total, 1) * 100, 1),
    }
