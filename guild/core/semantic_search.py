"""Semantic search module for Guild packs (M3.2).

Combines vector similarity search with FTS5 text-based search for improved
relevance and recall. Provides hybrid search with configurable weights.

Protocol/Interface:
    EmbeddingEngine — see EmbeddingEngineProtocol

Classes:
    SemanticSearchEngine — High-level search combining vector + text search
"""

import logging
import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Protocol

try:
    import numpy as np
except ImportError:
    np = None

from guild.db.store import GuildStore

logger = logging.getLogger(__name__)


class EmbeddingEngineProtocol(Protocol):
    """Protocol for embedding engines used by SemanticSearchEngine.
    
    This defines the interface expected by SemanticSearchEngine.
    Implementations should provide encode() and search_similar() methods.
    
    Note: The existing guild.db.embeddings.EmbeddingStore can be used
    via its semantic_search() method, but this protocol allows for
    custom implementations.
    """
    
    def encode(self, text: str) -> Any:
        """Encode a single text into an embedding vector.
        
        Args:
            text: Text string to encode.
            
        Returns:
            Embedding vector as numpy array.
        """
        ...
    
    def search_similar(
        self, query_embedding: Any, top_k: int
    ) -> List[Tuple[str, float]]:
        """Search for similar packs using a query embedding.
        
        Args:
            query_embedding: The query embedding vector.
            top_k: Number of results to return.
            
        Returns:
            List of (pack_id, similarity_score) tuples, ordered by relevance.
        """
        ...


class MockEmbeddingEngine:
    """Mock embedding engine for testing and development.
    
    Provides simple hash-based embeddings for testing without
    loading a real model.
    """
    
    def __init__(self, dimension: int = 128):
        """Initialize mock embedding engine.
        
        Args:
            dimension: Embedding vector dimension. Default 128.
        """
        self.dimension = dimension
    
    def encode(self, text: str) -> Any:
        """Encode text using a simple hash-based approach.
        
        Creates deterministic embeddings based on text hash
        for reproducible testing.
        """
        if np is None:
            raise ImportError("numpy required for MockEmbeddingEngine")
        
        # Simple hash-based embedding for testing
        hash_val = hash(text) % (2**32)
        np.random.seed(hash_val)
        embedding = np.random.randn(self.dimension)
        # Normalize to unit vector
        embedding = embedding / np.linalg.norm(embedding)
        return embedding
    
    def search_similar(
        self, query_embedding: Any, top_k: int
    ) -> List[Tuple[str, float]]:
        """Search similar (not implemented for mock, use semantic_search)."""
        raise NotImplementedError(
            "Use SemanticSearchEngine.search(mode='semantic') instead"
        )


class SemanticSearchEngine:
    """High-level semantic search combining vector and text search.
    
    Provides three search modes:
    - 'semantic': Vector similarity only using embeddings
    - 'text': FTS5 full-text search only
    - 'hybrid': Combines semantic and text with configurable weights
    
    Gracefully degrades to text-only search if embeddings are unavailable.
    
    Attributes:
        store: The GuildStore instance for FTS5 search.
        embedding_engine: Optional EmbeddingEngine for semantic search.
        default_weights: Default weights for hybrid search (semantic, text).
    """
    
    DEFAULT_WEIGHTS = {"semantic": 0.6, "text": 0.4}
    
    def __init__(
        self,
        store: GuildStore,
        embedding_engine: Optional[Any] = None,
        weights: Optional[Dict[str, float]] = None,
    ):
        """Initialize SemanticSearchEngine.
        
        Args:
            store: GuildStore instance for FTS5 text search.
            embedding_engine: Optional embedding engine for semantic search.
                Can be any object implementing the EmbeddingEngineProtocol.
                If None, semantic search will gracefully degrade to text-only.
            weights: Optional custom weights for hybrid search.
                Should have keys 'semantic' and 'text' with float values
                that sum to 1.0. Defaults to 0.6 semantic + 0.4 text.
        """
        self.store = store
        self.embedding_engine = embedding_engine
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        
        # Validate weights
        semantic_w = self.weights.get("semantic", 0.6)
        text_w = self.weights.get("text", 0.4)
        if abs(semantic_w + text_w - 1.0) > 0.001:
            warnings.warn(
                f"Weights {self.weights} do not sum to 1.0, normalizing."
            )
            total = semantic_w + text_w
            self.weights["semantic"] = semantic_w / total
            self.weights["text"] = text_w / total
    
    def _check_embedding_available(self) -> bool:
        """Check if embedding engine is available and functional."""
        if self.embedding_engine is None:
            return False
        
        try:
            engine = self.embedding_engine
            
            # Check for EmbeddingStore-style semantic_search method
            # Must be callable and return a list when called
            if hasattr(engine, "semantic_search"):
                result = getattr(engine, "semantic_search", None)
                if callable(result):
                    # Try calling it to verify it works
                    try:
                        test_result = result("test", 1)
                        if isinstance(test_result, list):
                            return True
                    except Exception:
                        pass
            
            # Check for protocol-style encode + search_similar
            if hasattr(engine, "encode") and hasattr(engine, "search_similar"):
                encode_fn = getattr(engine, "encode", None)
                search_fn = getattr(engine, "search_similar", None)
                if callable(encode_fn) and callable(search_fn):
                    # Verify encode returns a proper numpy array
                    test_embedding = encode_fn("test")
                    if test_embedding is not None and hasattr(test_embedding, 'shape'):
                        return True
        except Exception as e:
            warnings.warn(f"Embedding engine not available: {e}")
        
        return False
    
    def _semantic_search(
        self, query: str, top_k: int
    ) -> List[Tuple[str, float]]:
        """Perform semantic search using embeddings.
        
        Args:
            query: Search query text.
            top_k: Number of results to return.
            
        Returns:
            List of (pack_id, similarity_score) tuples.
        """
        if self.embedding_engine is None:
            return []
        
        try:
            engine = self.embedding_engine
            
            # Check for protocol-style encode + search_similar FIRST
            # (semantic_search might exist but raise NotImplementedError)
            if hasattr(engine, "encode") and hasattr(engine, "search_similar"):
                try:
                    embedding = engine.encode(query)
                    # Verify embedding is a real numpy array, not MagicMock
                    if embedding is not None and hasattr(embedding, 'shape'):
                        # Check that shape is actually a tuple (not MagicMock)
                        if isinstance(embedding.shape, tuple):
                            search_result = engine.search_similar(embedding, top_k)
                            # Validate result is a list
                            if isinstance(search_result, list):
                                return search_result
                except Exception:
                    # Fall through to try other methods
                    pass
            
            # Fallback: try semantic_search method (e.g., EmbeddingStore)
            if hasattr(engine, "semantic_search"):
                result = engine.semantic_search(query, top_k)
                # Validate result is a list (not a MagicMock or None)
                if isinstance(result, list):
                    return result
            
            return []
        except Exception as e:
            warnings.warn(f"Semantic search failed: {e}")
            return []
    
    def _text_search(
        self, query: str, top_k: int
    ) -> List[dict]:
        """Perform FTS5 text search.
        
        Args:
            query: Search query text.
            top_k: Number of results to return.
            
        Returns:
            List of pack dicts from GuildStore.search_packs().
        """
        try:
            return self.store.search_packs(query, limit=top_k)
        except Exception as e:
            warnings.warn(f"Text search failed: {e}")
            return []
    
    def search(
        self, query: str, top_k: int = 10, mode: str = "hybrid"
    ) -> List[dict]:
        """Search for packs using the specified mode.
        
        Args:
            query: Search query string.
            top_k: Maximum number of results to return. Default 10.
            mode: Search mode - 'semantic', 'text', or 'hybrid'.
                Default 'hybrid'.
                
        Returns:
            List of pack dicts with added fields:
            - relevance_score: Combined relevance score (0.0 to 1.0)
            - match_type: 'semantic', 'text', or 'hybrid'
            
        Raises:
            ValueError: If mode is not one of 'semantic', 'text', 'hybrid'.
        """
        mode = mode.lower()
        if mode not in ("semantic", "text", "hybrid"):
            raise ValueError(
                f"Invalid mode '{mode}'. Must be 'semantic', 'text', or 'hybrid'."
            )
        
        if mode == "text":
            return self._search_text(query, top_k)
        elif mode == "semantic":
            return self._search_semantic(query, top_k)
        else:  # hybrid
            return self._search_hybrid(query, top_k)
    
    def _search_text(self, query: str, top_k: int) -> List[dict]:
        """Text-only search using FTS5."""
        packs = self._text_search(query, top_k)
        
        # Add relevance score based on result position (BM25 rank)
        results = []
        for i, pack in enumerate(packs):
            # BM25-style scoring: higher is better, position-based
            score = 1.0 / (i + 1) if packs else 0.0
            pack_copy = pack.copy()
            pack_copy["relevance_score"] = score
            pack_copy["match_type"] = "text"
            results.append(pack_copy)
        
        return results
    
    def _search_semantic(self, query: str, top_k: int) -> List[dict]:
        """Semantic-only search using embeddings."""
        if not self.embedding_engine:
            warnings.warn(
                "Semantic search requested but embedding engine not available. "
                "Falling back to text search."
            )
            return self._search_text(query, top_k)
        
        semantic_results = self._semantic_search(query, top_k)
        
        if not semantic_results:
            # Fall back to text search when semantic search yields no results
            return self._search_text(query, top_k)
        
        # Get full pack data for each result
        pack_id_to_score = {pack_id: score for pack_id, score in semantic_results}
        results = []
        
        for pack_id, score in semantic_results:
            pack = self.store.get_pack(pack_id)
            if pack is not None:
                pack_copy = pack.copy()
                pack_copy["relevance_score"] = float(score)
                pack_copy["match_type"] = "semantic"
                results.append(pack_copy)
        
        return results
    
    def _search_hybrid(self, query: str, top_k: int) -> List[dict]:
        """Hybrid search combining semantic and text search."""
        semantic_weight = self.weights.get("semantic", 0.6)
        text_weight = self.weights.get("text", 0.4)
        
        # Get results from both sources
        semantic_results = self._semantic_search(query, top_k * 2) if self.embedding_engine else []
        text_packs = self._text_search(query, top_k * 2)
        
        # Build score maps
        semantic_scores: Dict[str, float] = {}
        for pack_id, score in semantic_results:
            semantic_scores[pack_id] = float(score)
        
        text_scores: Dict[str, float] = {}
        for i, pack in enumerate(text_packs):
            # BM25-style: position-based scoring
            text_scores[pack["id"]] = 1.0 / (i + 1)
        
        # Get union of all pack IDs
        all_pack_ids = set(semantic_scores.keys()) | set(text_scores.keys())
        
        # Normalize scores within each source (0 to 1)
        if semantic_scores:
            max_sem = max(semantic_scores.values())
            if max_sem > 0:
                semantic_scores = {
                    k: v / max_sem for k, v in semantic_scores.items()
                }
        
        if text_scores:
            max_text = max(text_scores.values())
            if max_text > 0:
                text_scores = {
                    k: v / max_text for k, v in text_scores.items()
                }
        
        # Compute combined scores
        combined_scores: Dict[str, float] = {}
        for pack_id in all_pack_ids:
            sem_score = semantic_scores.get(pack_id, 0.0)
            txt_score = text_scores.get(pack_id, 0.0)
            combined_scores[pack_id] = (
                semantic_weight * sem_score + text_weight * txt_score
            )
        
        # Sort by combined score
        sorted_pack_ids = sorted(
            combined_scores.keys(),
            key=lambda pid: combined_scores[pid],
            reverse=True
        )[:top_k]
        
        # Build results
        results = []
        for pack_id in sorted_pack_ids:
            pack = self.store.get_pack(pack_id)
            if pack is not None:
                pack_copy = pack.copy()
                pack_copy["relevance_score"] = combined_scores[pack_id]
                
                # Determine match type
                sem = pack_id in semantic_scores
                txt = pack_id in text_scores
                if sem and txt:
                    pack_copy["match_type"] = "hybrid"
                elif sem:
                    pack_copy["match_type"] = "semantic"
                else:
                    pack_copy["match_type"] = "text"
                
                results.append(pack_copy)
        
        return results
    
    def rerank(
        self, results: List[dict], query: str
    ) -> List[dict]:
        """Rerank search results by semantic similarity to query.
        
        Args:
            results: List of pack dicts to rerank.
            query: Query string to compute semantic similarity against.
            
        Returns:
            Reranked list of pack dicts (same structure, reordered).
        """
        if not results:
            return []
        
        if not self.embedding_engine:
            # Fall back to keeping original order
            return results
        
        try:
            engine = self.embedding_engine
            
            # Encode query
            if hasattr(engine, "encode"):
                query_embedding = engine.encode(query)
            elif hasattr(engine, "semantic_search"):
                # For EmbeddingStore, we need to get embeddings differently
                # This is a limitation - EmbeddingStore doesn't expose encode
                return results
            else:
                return results
            
            if query_embedding is None:
                return results
            
            # Encode each result's text and compute similarity
            scored_results = []
            for pack in results:
                # Build text from pack fields
                pack_text = self._pack_to_text(pack)
                if hasattr(engine, "encode"):
                    pack_embedding = engine.encode(pack_text)
                    if pack_embedding is not None:
                        similarity = float(
                            np.dot(query_embedding, pack_embedding) / (
                                np.linalg.norm(query_embedding) *
                                np.linalg.norm(pack_embedding)
                                + 1e-8
                            )
                        )
                        pack_copy = pack.copy()
                        pack_copy["relevance_score"] = similarity
                        scored_results.append((similarity, pack_copy))
            
            # Sort by similarity
            scored_results.sort(key=lambda x: x[0], reverse=True)
            return [pack for _, pack in scored_results]
            
        except Exception as e:
            warnings.warn(f"Reranking failed: {e}")
            return results
    
    def _pack_to_text(self, pack: dict) -> str:
        """Convert a pack dict to searchable text."""
        parts = [
            pack.get("problem_class", ""),
            pack.get("domain", ""),
            pack.get("yaml_content", "")[:500],  # Limit content length
        ]
        return " ".join(p for p in parts if p)
    
    def suggest_packs(
        self, context: str, failure_count: int = 0
    ) -> List[dict]:
        """Suggest packs based on agent context for auto-suggest.
        
        Analyzes the agent's context to find relevant packs that might
        help with the current task or recover from failures.
        
        Args:
            context: Agent context/description of current task.
            failure_count: Number of recent failures (affects suggestion strategy).
            
        Returns:
            List of suggested pack dicts with relevance_score and match_type.
        """
        # Use hybrid search for suggestions
        # With higher failure count, prioritize debugging/recovery packs
        if failure_count > 2:
            # Try to find debugging or recovery packs
            suggestion_query = f"{context} debugging recovery error handling"
        elif failure_count > 0:
            suggestion_query = f"{context} troubleshooting help"
        else:
            suggestion_query = context
        
        suggestions = self.search(suggestion_query, top_k=5, mode="hybrid")
        
        # Add suggestion reason
        for pack in suggestions:
            if failure_count > 2:
                pack["suggestion_reason"] = "recovery"
            elif failure_count > 0:
                pack["suggestion_reason"] = "troubleshooting"
            else:
                pack["suggestion_reason"] = "general"
        
        return suggestions
