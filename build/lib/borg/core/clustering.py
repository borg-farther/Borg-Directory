"""
Borg trace clustering — discovers problem clusters in the trace database.
Uses KMeans (sklearn) when available, keyword grouping as fallback.
Finds: common failure patterns, related error types, recurring problems.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

TRACE_DB_PATH = os.path.expanduser("~/.borg/traces.db")


def _get_traces(db_path: str, limit: int = 5000) -> List[Dict]:
    try:
        db = sqlite3.connect(db_path, timeout=10)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT id, task_description, technology, outcome, root_cause, "
            "approach_summary, keywords, helpfulness_score, "
            "times_shown, times_helped, error_type, created_at "
            "FROM traces ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"clustering: DB read failed: {e}")
        return []


def _text_for_trace(trace: Dict) -> str:
    parts = []
    for field in ('task_description', 'root_cause', 'approach_summary', 'error_type'):
        val = trace.get(field, '').strip()
        if val:
            parts.append(val)
    keywords = trace.get('keywords', [])
    if isinstance(keywords, str):
        try:
            keywords = json.loads(keywords)
        except Exception:
            keywords = []
    if keywords:
        parts.append(' '.join(keywords[:8]))
    return ' | '.join(parts)


def _keyword_clusters(traces: List[Dict], top_k: int = 8) -> List[Dict]:
    """Keyword-based clustering fallback — groups traces by shared important words."""
    from collections import Counter
    word_traces: Dict[str, List[Dict]] = {}
    STOPWORDS = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'to', 'of', 'in',
                 'for', 'on', 'with', 'and', 'or', 'not', 'this', 'that', 'it',
                 'i', 'you', 'we', 'they', 'have', 'has', 'be', 'been', 'being',
                 'fix', 'error', 'issue', 'problem', 'bug', 'task', 'trying'}

    for trace in traces:
        text = _text_for_trace(trace).lower()
        words = [w.strip('.,!?()[]{}:;') for w in text.split() if 5 <= len(w) <= 30 and w not in STOPWORDS]
        for word, count in Counter(words).most_common(3):
            if word not in word_traces:
                word_traces[word] = []
            word_traces[word].append(trace)

    # Pick top K words with most unique traces
    scored = [(w, len(v)) for w, v in word_traces.items()]
    scored.sort(key=lambda x: -x[1])
    top_words = [w for w, _ in scored[:top_k]]

    clusters = []
    for word in top_words:
        cluster_traces = word_traces[word]
        outcomes = [t.get('outcome', '') for t in cluster_traces]
        root_causes = list({t.get('root_cause', '') for t in cluster_traces if t.get('root_cause')})[:3]
        approaches = list({t.get('approach_summary', '') for t in cluster_traces if t.get('approach_summary')})[:3]
        clusters.append({
            'cluster_id': word,
            'keyword': word,
            'description': f"Traces mentioning '{word}'",
            'size': len(cluster_traces),
            'success_count': outcomes.count('success'),
            'failure_count': outcomes.count('failure'),
            'root_causes': root_causes,
            'approaches': approaches,
            'sample_trace_id': cluster_traces[0].get('id', '') if cluster_traces else '',
        })

    clusters.sort(key=lambda x: x['size'], reverse=True)
    return clusters


def _sklearn_clusters(traces: List[Dict], n_clusters: int = 8) -> List[Dict]:
    """KMeans clustering using trace text embeddings."""
    try:
        from sklearn.cluster import KMeans
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        return None  # Fall back to keyword

    texts = [_text_for_trace(t) for t in traces]
    texts = [t for t in texts if t.strip()]
    if len(texts) < n_clusters:
        return None

    try:
        vectorizer = TfidfVectorizer(max_features=500, min_df=2, max_df=0.8)
        X = vectorizer.fit_transform(texts)
        km = KMeans(n_clusters=min(n_clusters, len(texts)), random_state=42, n_init=3)
        labels = km.fit_predict(X)
    except Exception as e:
        logger.warning(f"clustering: KMeans failed: {e}")
        return None

    clusters = []
    for i in range(km.n_clusters):
        indices = [j for j, l in enumerate(labels) if l == i]
        cluster_traces = [traces[j] for j in indices if j < len(traces)]
        outcomes = [t.get('outcome', '') for t in cluster_traces]
        root_causes = list({t.get('root_cause', '') for t in cluster_traces if t.get('root_cause')})[:3]
        approaches = list({t.get('approach_summary', '') for t in cluster_traces if t.get('approach_summary')})[:3]
        centroid_terms = []
        try:
            feat_names = vectorizer.get_feature_names_out()
            for idx in (-km.cluster_centers_[i]).argsort()[:3]:
                if idx < len(feat_names):
                    centroid_terms.append(str(feat_names[idx]))
        except Exception:
            pass
        clusters.append({
            'cluster_id': f"cluster_{i}",
            'description': f"Common terms: {', '.join(centroid_terms[:3])}" if centroid_terms else f"Cluster {i}",
            'size': len(cluster_traces),
            'success_count': outcomes.count('success'),
            'failure_count': outcomes.count('failure'),
            'root_causes': root_causes,
            'approaches': approaches,
            'sample_trace_id': cluster_traces[0].get('id', '') if cluster_traces else '',
            'centroid_terms': centroid_terms,
        })

    clusters.sort(key=lambda x: x['size'], reverse=True)
    return clusters


def discover_clusters(db_path: str = None, n_clusters: int = 8,
                      min_trace_count: int = 3) -> Dict:
    if db_path is None:
        db_path = TRACE_DB_PATH
    if not os.path.exists(db_path):
        return {'clusters': [], 'method': 'none', 'total_traces': 0}

    traces = _get_traces(db_path)
    if not traces:
        return {'clusters': [], 'method': 'none', 'total_traces': 0}

    # Try sklearn first, fall back to keyword grouping
    method = 'sklearn'
    clusters = _sklearn_clusters(traces, n_clusters)
    if clusters is None:
        method = 'keyword'
        clusters = _keyword_clusters(traces, top_k=n_clusters)

    # Filter out tiny clusters
    clusters = [c for c in clusters if c['size'] >= min_trace_count]

    return {
        'clusters': clusters,
        'method': method,
        'total_traces': len(traces),
        'n_clusters': len(clusters),
    }


def get_cluster_detail(cluster_id: str, db_path: str = None) -> Dict:
    if db_path is None:
        db_path = TRACE_DB_PATH
    traces = _get_traces(db_path, limit=200)

    if cluster_id.startswith('cluster_'):
        # KMeans cluster — return all traces (approximate match)
        return {
            'cluster_id': cluster_id,
            'traces': traces[:20],
            'total': len(traces),
        }

    # Keyword cluster
    keyword = cluster_id
    matched = [t for t in traces if keyword.lower() in _text_for_trace(t).lower()]
    return {
        'cluster_id': cluster_id,
        'keyword': keyword,
        'traces': matched[:20],
        'total': len(matched),
    }


def get_technology_clusters(db_path: str = None) -> Dict:
    if db_path is None:
        db_path = TRACE_DB_PATH
    traces = _get_traces(db_path)
    if not traces:
        return {'clusters': [], 'total_traces': 0}

    tech_groups: Dict[str, List[Dict]] = {}
    for trace in traces:
        tech = (trace.get('technology') or 'unknown').strip()
        if not tech:
            tech = 'unknown'
        if tech not in tech_groups:
            tech_groups[tech] = []
        tech_groups[tech].append(trace)

    clusters = []
    for tech, tech_traces in sorted(tech_groups.items(), key=lambda x: -len(x[1])):
        outcomes = [t.get('outcome', '') for t in tech_traces]
        clusters.append({
            'cluster_id': f"tech:{tech}",
            'technology': tech,
            'description': f"Traces for technology: {tech}",
            'size': len(tech_traces),
            'success_count': outcomes.count('success'),
            'failure_count': outcomes.count('failure'),
        })

    clusters.sort(key=lambda x: x['size'], reverse=True)
    return {
        'clusters': clusters,
        'total_traces': len(traces),
        'n_technologies': len(clusters),
    }
