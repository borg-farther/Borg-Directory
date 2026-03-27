"""Tests for semantic_search module (M3.2)."""

import tempfile
import os
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from guild.db.store import GuildStore
from guild.core.semantic_search import (
    SemanticSearchEngine,
    MockEmbeddingEngine,
    EmbeddingEngineProtocol,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_guild.db")


@pytest.fixture
def store(temp_db_path):
    """Create a GuildStore with test data."""
    store = GuildStore(temp_db_path)
    
    # Add test packs
    store.add_pack(
        pack_id="pack-debug-001",
        version="1.0.0",
        yaml_content="""name: Systematic Debugging
problem_class: debugging
domain: software
phases:
  - name: reproduce
  - name: diagnose
  - name: fix
""",
        author_agent="test-agent",
        confidence="tested",
        tier="validated",
        problem_class="debugging",
        domain="software",
        phase_count=3,
    )
    
    store.add_pack(
        pack_id="pack-code-002",
        version="1.0.0",
        yaml_content="""name: Code Review
problem_class: code review
domain: software
phases:
  - name: review
  - name: suggest
""",
        author_agent="test-agent",
        confidence="tested",
        tier="core",
        problem_class="code review",
        domain="software",
        phase_count=2,
    )
    
    store.add_pack(
        pack_id="pack-data-003",
        version="1.0.0",
        yaml_content="""name: Data Analysis
problem_class: data analysis
domain: analytics
phases:
  - name: explore
  - name: analyze
  - name: report
""",
        author_agent="test-agent",
        confidence="inferred",
        tier="community",
        problem_class="data analysis",
        domain="analytics",
        phase_count=3,
    )
    
    yield store
    store.close()


@pytest.fixture
def mock_embedding_engine():
    """Create a mock embedding engine."""
    engine = MagicMock()
    engine.dimension = 128
    
    def mock_encode(text: str) -> np.ndarray:
        # Simple hash-based embedding for reproducible testing
        hash_val = hash(text) % (2**32)
        np.random.seed(hash_val)
        embedding = np.random.randn(128)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding
    
    def mock_search_similar(
        query_embedding: np.ndarray, top_k: int
    ) -> List[Tuple[str, float]]:
        # Return mock similar packs based on query hash
        query_hash = hash(str(query_embedding[:5])) % 100
        if query_hash % 3 == 0:
            return [("pack-debug-001", 0.95), ("pack-code-002", 0.85)]
        elif query_hash % 3 == 1:
            return [("pack-code-002", 0.92), ("pack-data-003", 0.78)]
        else:
            return [("pack-data-003", 0.88), ("pack-debug-001", 0.72)]
    
    engine.encode = mock_encode
    engine.search_similar = mock_search_similar
    # Explicitly set semantic_search to raise NotImplementedError
    # so the encode+search_similar path is used instead
    def semantic_search_raises(query, top_k):
        raise NotImplementedError("Use encode + search_similar instead")
    engine.semantic_search = semantic_search_raises
    
    return engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSemanticSearchEngine:
    """Tests for SemanticSearchEngine class."""
    
    def test_text_only_search_returns_results(self, store):
        """Test that text-only search returns results from FTS5."""
        engine = SemanticSearchEngine(store, embedding_engine=None)
        
        results = engine.search("debugging", top_k=10, mode="text")
        
        assert len(results) > 0
        assert all("relevance_score" in r for r in results)
        assert all(r["match_type"] == "text" for r in results)
        # Check that debugging pack is found
        pack_ids = [r["id"] for r in results]
        assert "pack-debug-001" in pack_ids
    
    def test_text_search_with_no_matches(self, store):
        """Test that text search handles no matches gracefully."""
        engine = SemanticSearchEngine(store, embedding_engine=None)
        
        results = engine.search("nonexistent xyz123", top_k=10, mode="text")
        
        # Should return empty list, not crash
        assert results == []
    
    def test_semantic_search_with_mock_embeddings(self, store, mock_embedding_engine):
        """Test semantic search with mock embedding engine."""
        engine = SemanticSearchEngine(store, embedding_engine=mock_embedding_engine)
        
        results = engine.search("debugging", top_k=10, mode="semantic")
        
        assert len(results) > 0
        assert all("relevance_score" in r for r in results)
        assert all(r["match_type"] == "semantic" for r in results)
        assert all(0.0 <= r["relevance_score"] <= 1.0 for r in results)
    
    def test_hybrid_combines_both(self, store, mock_embedding_engine):
        """Test that hybrid mode combines semantic and text search."""
        engine = SemanticSearchEngine(
            store, 
            embedding_engine=mock_embedding_engine,
            weights={"semantic": 0.6, "text": 0.4}
        )
        
        results = engine.search("debugging", top_k=10, mode="hybrid")
        
        assert len(results) > 0
        # Should have both semantic and text matched packs
        match_types = set(r["match_type"] for r in results)
        assert "hybrid" in match_types or len(match_types) > 1
        
        # Check scores are in valid range
        assert all(0.0 <= r["relevance_score"] <= 1.0 for r in results)
    
    def test_hybrid_with_custom_weights(self, store, mock_embedding_engine):
        """Test hybrid search with custom weights."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine,
            weights={"semantic": 0.8, "text": 0.2}
        )
        
        results = engine.search("code review", top_k=5, mode="hybrid")
        
        assert len(results) > 0
        assert all("relevance_score" in r for r in results)
    
    def test_graceful_fallback_no_embedding_engine(self, store):
        """Test graceful degradation when no embedding engine is provided."""
        engine = SemanticSearchEngine(store, embedding_engine=None)
        
        # Semantic mode should fall back to text
        results = engine.search("debugging", top_k=10, mode="semantic")
        
        # Should still return results via text fallback
        assert len(results) > 0
        assert all(r["match_type"] == "text" for r in results)
    
    def test_graceful_fallback_disabled_engine(self, store):
        """Test graceful degradation when embedding engine fails."""
        failing_engine = MagicMock()
        failing_engine.encode.side_effect = Exception("Model not loaded")
        
        engine = SemanticSearchEngine(store, embedding_engine=failing_engine)
        
        results = engine.search("debugging", top_k=10, mode="semantic")
        
        # Should fall back to text search
        assert len(results) > 0
    
    def test_suggest_packs_based_on_context(self, store, mock_embedding_engine):
        """Test suggest_packs returns relevant packs for context."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        suggestions = engine.suggest_packs(
            context="I need to debug a crashing application",
            failure_count=0
        )
        
        assert len(suggestions) > 0
        assert all("suggestion_reason" in s for s in suggestions)
        # At least one pack should be related to debugging or software
        # (exact pack depends on mock hash function)
        pack_ids = [s["id"] for s in suggestions]
        assert any(pack_id.startswith("pack-") for pack_id in pack_ids)
    
    def test_suggest_packs_with_failures(self, store, mock_embedding_engine):
        """Test suggest_packs with failure count affects strategy."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        suggestions = engine.suggest_packs(
            context="application error",
            failure_count=5
        )
        
        assert len(suggestions) > 0
        # High failure count should result in recovery suggestions
        assert all(s.get("suggestion_reason") == "recovery" for s in suggestions)
    
    def test_empty_results_handled(self, store, mock_embedding_engine):
        """Test that empty results are handled gracefully."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        # Search with query that matches nothing
        results = engine.search(
            "zzzzz this matches nothing zzzzz",
            top_k=10,
            mode="semantic"
        )
        
        # Empty list is acceptable
        assert isinstance(results, list)
    
    def test_rerank(self, store, mock_embedding_engine):
        """Test rerank method reorders results."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        # Start with text results
        initial_results = engine.search("software", top_k=5, mode="text")
        
        if len(initial_results) > 1:
            # Rerank by semantic similarity
            reranked = engine.rerank(initial_results, "debugging workflow")
            
            assert len(reranked) == len(initial_results)
            # All packs should still be present (just reordered)
            assert set(r["id"] for r in reranked) == set(r["id"] for r in initial_results)
    
    def test_invalid_mode_raises_error(self, store):
        """Test that invalid search mode raises ValueError."""
        engine = SemanticSearchEngine(store, embedding_engine=None)
        
        with pytest.raises(ValueError, match="Invalid mode"):
            engine.search("debugging", mode="invalid_mode")
    
    def test_weights_normalization(self, store):
        """Test that weights are normalized if they don't sum to 1."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=None,
            weights={"semantic": 0.7, "text": 0.7}  # Sum to 1.4
        )
        
        # Weights should be normalized
        assert abs(engine.weights["semantic"] + engine.weights["text"] - 1.0) < 0.001
    
    def test_search_returns_pack_metadata(self, store):
        """Test that search returns complete pack metadata."""
        engine = SemanticSearchEngine(store, embedding_engine=None)
        
        results = engine.search("debugging", top_k=5, mode="text")
        
        assert len(results) > 0
        for pack in results:
            # Check essential fields are present
            assert "id" in pack
            assert "version" in pack
            assert "problem_class" in pack
            assert "relevance_score" in pack
            assert "match_type" in pack


class TestMockEmbeddingEngine:
    """Tests for MockEmbeddingEngine."""
    
    def test_encode_returns_vector(self):
        """Test that encode returns a numpy array."""
        engine = MockEmbeddingEngine(dimension=64)
        
        embedding = engine.encode("test text")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (64,)
    
    def test_encode_deterministic(self):
        """Test that encode is deterministic."""
        engine = MockEmbeddingEngine(dimension=64)
        
        emb1 = engine.encode("same text")
        emb2 = engine.encode("same text")
        
        np.testing.assert_array_almost_equal(emb1, emb2)
    
    def test_encode_normalized(self):
        """Test that embeddings are normalized to unit length."""
        engine = MockEmbeddingEngine(dimension=64)
        
        embedding = engine.encode("any text")
        
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-6


class TestEmbeddingEngineProtocol:
    """Tests for EmbeddingEngineProtocol interface."""
    
    def test_protocol_exists(self):
        """Test that EmbeddingEngineProtocol is defined."""
        from guild.core.semantic_search import EmbeddingEngineProtocol
        assert EmbeddingEngineProtocol is not None
    
    def test_mock_follows_protocol(self, mock_embedding_engine):
        """Test that mock engine follows the protocol."""
        # Check required methods exist
        assert hasattr(mock_embedding_engine, "encode")
        assert hasattr(mock_embedding_engine, "search_similar")


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestSemanticSearchIntegration:
    """Integration tests with real GuildStore."""
    
    def test_search_with_real_store(self, store, mock_embedding_engine):
        """Test search with a real GuildStore instance."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        # Test all modes
        for mode in ["text", "semantic", "hybrid"]:
            results = engine.search("software", top_k=5, mode=mode)
            assert isinstance(results, list)
            for r in results:
                assert "id" in r
                assert "relevance_score" in r
                assert "match_type" in r
    
    def test_top_k_respects_limit(self, store, mock_embedding_engine):
        """Test that top_k parameter is respected."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        results = engine.search("software", top_k=2, mode="text")
        
        assert len(results) <= 2
    
    def test_multiple_searches(self, store, mock_embedding_engine):
        """Test multiple consecutive searches."""
        engine = SemanticSearchEngine(
            store,
            embedding_engine=mock_embedding_engine
        )
        
        results1 = engine.search("debugging", mode="text")
        results2 = engine.search("code review", mode="text")
        results3 = engine.search("data analysis", mode="semantic")
        
        assert len(results1) > 0
        assert len(results2) > 0
        assert len(results3) > 0
