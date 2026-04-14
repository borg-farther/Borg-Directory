"""BM25 keyword index for hybrid retrieval.

Provides keyword-based search over trace fields to complement
embedding-based semantic search. Combined via Reciprocal Rank Fusion.
"""
import math
import re
import sqlite3
from collections import Counter, defaultdict
from typing import List, Tuple, Optional

# BM25 parameters
K1 = 1.2
B = 0.75
RRF_K = 60  # Standard RRF constant


class BM25Index:
    """In-memory BM25 index over trace fields."""

    def __init__(self, db_path: str = None):
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.doc_lens: dict[str, int] = {}
        self.avg_dl: float = 0.0
        self.n_docs: int = 0
        self.inverted_index: dict[str, list[tuple[str, int]]] = defaultdict(list)
        self.docs: dict[str, str] = {}
        if db_path:
            self.build_from_db(db_path)

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer."""
        if not text:
            return []
        text = text.lower()
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        return [t for t in text.split() if len(t) > 1]

    def build_from_db(self, db_path: str):
        """Build index from traces.db."""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, task_description, keywords, technology, "
            "error_patterns, root_cause, approach_summary "
            "FROM traces"
        ).fetchall()
        conn.close()

        for row in rows:
            doc_text = ' '.join(filter(None, [
                row['task_description'] or '',
                row['keywords'] or '',
                row['technology'] or '',
                row['error_patterns'] or '',
                row['root_cause'] or '',
                row['approach_summary'] or '',
            ]))
            self.add_document(row['id'], doc_text)

        self._compute_stats()

    def add_document(self, doc_id: str, text: str):
        """Add a single document to the index."""
        tokens = self.tokenize(text)
        self.docs[doc_id] = text
        self.doc_lens[doc_id] = len(tokens)
        tf = Counter(tokens)
        for term, count in tf.items():
            self.inverted_index[term].append((doc_id, count))

    def _compute_stats(self):
        """Compute document frequencies and average document length."""
        self.n_docs = len(self.docs)
        if self.n_docs == 0:
            self.avg_dl = 0
            return
        self.avg_dl = sum(self.doc_lens.values()) / self.n_docs
        self.doc_freqs = defaultdict(int)
        for term, postings in self.inverted_index.items():
            self.doc_freqs[term] = len(postings)

    def search(self, query: str, top_k: int = 20) -> List[Tuple[str, float]]:
        """Search the index and return (doc_id, score) pairs."""
        if self.n_docs == 0:
            return []

        tokens = self.tokenize(query)
        if not tokens:
            return []

        scores: dict[str, float] = defaultdict(float)

        for term in tokens:
            if term not in self.inverted_index:
                continue
            df = self.doc_freqs[term]
            idf = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id, tf in self.inverted_index[term]:
                dl = self.doc_lens[doc_id]
                tf_norm = (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * dl / self.avg_dl))
                scores[doc_id] += idf * tf_norm

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def rrf_fusion(
    embedding_results: List[Tuple[str, float]],
    bm25_results: List[Tuple[str, float]],
    k: int = RRF_K,
    embedding_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion of embedding and BM25 results.
    
    Args:
        embedding_results: [(doc_id, score), ...] from embedding search
        bm25_results: [(doc_id, score), ...] from BM25 search
        k: RRF constant (default 60)
        embedding_weight: weight for embedding scores
        bm25_weight: weight for BM25 scores
    
    Returns:
        Fused [(doc_id, rrf_score), ...] sorted by score desc
    """
    scores: dict[str, float] = defaultdict(float)

    for rank, (doc_id, _) in enumerate(embedding_results):
        scores[doc_id] += embedding_weight * (1.0 / (k + rank + 1))

    for rank, (doc_id, _) in enumerate(bm25_results):
        scores[doc_id] += bm25_weight * (1.0 / (k + rank + 1))

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked


# Singleton index instance
_index: Optional[BM25Index] = None


def get_bm25_index(db_path: str = None) -> BM25Index:
    """Get or create the singleton BM25 index."""
    global _index
    if _index is None:
        from borg.core.traces import TRACE_DB_PATH
        path = db_path or str(TRACE_DB_PATH)
        _index = BM25Index(path)
    return _index


def rebuild_bm25_index(db_path: str = None):
    """Force rebuild the BM25 index."""
    global _index
    from borg.core.traces import TRACE_DB_PATH
    path = db_path or str(TRACE_DB_PATH)
    _index = BM25Index(path)
    return _index
