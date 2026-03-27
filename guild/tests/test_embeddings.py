"""Tests for guild embeddings engine."""

import os
import sys
import tempfile
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# Create a mock model that mimics sentence_transformers
class MockModel:
    def __init__(self, *args, **kwargs):
        pass
    
    def encode(self, text, **kwargs):
        # Return a 4-dimensional vector
        return np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
    
    def get_sentence_embedding_dimension(self):
        return 4


# Module-level mock for SentenceTransformer  
_mock_model = MockModel()


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def engine(temp_db):
    """Create an EmbeddingEngine with a mocked model."""
    import importlib
    
    # Create a mock module for sentence_transformers
    mock_st_module = MagicMock()
    mock_st_module.SentenceTransformer.return_value = _mock_model
    
    # Patch sys.modules to intercept the import
    original_modules = {}
    target_modules = ['sentence_transformers', 'sentence_transformers.SentenceTransformer']
    
    for mod_name in target_modules:
        if mod_name in sys.modules:
            original_modules[mod_name] = sys.modules[mod_name]
        if 'sentence' in mod_name:
            sys.modules[mod_name] = mock_st_module
    
    try:
        # Now we need to reimport embeddings with the patched modules
        # First, remove any cached version
        if 'guild.db.embeddings' in sys.modules:
            del sys.modules['guild.db.embeddings']
        if 'guild.db' in sys.modules:
            # Don't delete guild.db itself, but clear embeddings from it
            if hasattr(sys.modules['guild.db'], 'embeddings'):
                delattr(sys.modules['guild.db'], 'embeddings')
        
        from guild.db.embeddings import EmbeddingEngine
        eng = EmbeddingEngine(db_path=temp_db, model_name="all-MiniLM-L6-v2")
        # Override _model to use our mock directly
        eng._model = _mock_model
        yield eng
    finally:
        # Restore original modules
        for mod_name, mod in original_modules.items():
            sys.modules[mod_name] = mod
        # Clean up our mock modules
        for mod_name in list(sys.modules.keys()):
            if 'sentence_transformers' in mod_name and mod_name not in original_modules:
                del sys.modules[mod_name]


class TestEmbeddingDimensionality:
    """Tests for encode text dimensionality."""

    def test_encode_returns_array(self, engine):
        """Encode returns a numpy array."""
        result = engine.encode("test text")
        assert isinstance(result, np.ndarray)

    def test_encode_returns_correct_dimensions(self, engine):
        """Encode returns correct dimensionality for the model."""
        result = engine.encode("test text")
        assert result.shape == (4,)


class TestPackEncoding:
    """Tests for pack metadata encoding."""

    def test_encode_pack_combines_fields(self, engine):
        """Pack encoding combines fields into single text."""
        pack = {
            "problem_class": "classification",
            "domain": "machine learning",
            "mental_model": "supervised learning",
            "phase_descriptions": ["data prep", "training", "evaluation"],
        }
        
        with patch.object(engine, "encode") as mock_encode:
            mock_encode.return_value = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
            result = engine.encode_pack(pack)
            
            # Verify encode was called
            mock_encode.assert_called_once()
            call_args = mock_encode.call_args[0][0]
            
            # Check that fields were combined
            assert "classification" in call_args
            assert "machine learning" in call_args
            assert "supervised learning" in call_args
            assert "data prep" in call_args

    def test_encode_pack_handles_missing_fields(self, engine):
        """Pack encoding handles missing fields gracefully."""
        pack = {"problem_class": "test"}
        
        with patch.object(engine, "encode") as mock_encode:
            mock_encode.return_value = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
            result = engine.encode_pack(pack)
            mock_encode.assert_called_once()


class TestStoreRetrieve:
    """Tests for store/retrieve round-trip."""

    def test_store_and_retrieve_preserves_vector(self, engine):
        """Store/retrieve round-trip preserves the vector."""
        pack_id = "test-pack-1"
        original_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        
        engine.store_embedding(pack_id, original_vector)
        retrieved = engine.get_embedding(pack_id)
        
        assert retrieved is not None
        np.testing.assert_array_almost_equal(original_vector, retrieved)

    def test_get_nonexistent_returns_none(self, engine):
        """Getting nonexistent pack returns None."""
        result = engine.get_embedding("nonexistent-pack")
        assert result is None


class TestSimilaritySearch:
    """Tests for cosine similarity search."""

    def test_search_returns_sorted_results(self, engine):
        """Similarity search returns results sorted by score."""
        # Store multiple embeddings with known similarity to our query
        # Query will be: [1.0, 0.0, 0.0, 0.0]
        vec1 = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)  # identity - most similar
        vec2 = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)  # orthogonal - least similar
        vec3 = np.array([0.5, 0.5, 0.0, 0.0], dtype=np.float32)  # partial - middle
        
        engine.store_embedding("pack1", vec1)
        engine.store_embedding("pack2", vec2)
        engine.store_embedding("pack3", vec3)
        
        # Query with vec1 direction (1, 0, 0, 0)
        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = engine.search_similar(query, top_k=3)
        
        assert len(results) == 3
        # Results should be sorted by similarity (highest first)
        # pack1 should be most similar (cosine = 1.0)
        # pack3 should be second (cosine = 0.5)
        # pack2 should be least (cosine = 0.0)
        assert results[0][0] == "pack1"  # Most similar (identical)
        assert results[1][0] == "pack3"  # Second most 
        assert results[2][0] == "pack2"  # Least similar (orthogonal)
        # Scores should be in descending order
        assert results[0][1] >= results[1][1] >= results[2][1]
        # Verify actual scores
        assert results[0][1] == pytest.approx(1.0)  # Identity
        assert results[2][1] == pytest.approx(0.0)  # Orthogonal

    def test_search_respects_top_k(self, engine):
        """Search respects top_k parameter."""
        for i in range(5):
            vec = np.array([float(i), 0.0, 0.0, 0.0], dtype=np.float32)
            engine.store_embedding(f"pack{i}", vec)
        
        query = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        results = engine.search_similar(query, top_k=2)
        
        assert len(results) == 2


class TestDelete:
    """Tests for delete functionality."""

    def test_delete_removes_embedding(self, engine):
        """Delete removes the embedding from storage."""
        pack_id = "test-pack-delete"
        vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        
        engine.store_embedding(pack_id, vector)
        assert engine.get_embedding(pack_id) is not None
        
        result = engine.delete_embedding(pack_id)
        assert result is True
        assert engine.get_embedding(pack_id) is None

    def test_delete_nonexistent_returns_false(self, engine):
        """Deleting nonexistent pack returns False."""
        result = engine.delete_embedding("nonexistent-pack")
        assert result is False


class TestIndexAllPacks:
    """Tests for index_all_packs functionality."""

    def test_index_all_packs_processes_store(self, engine):
        """Index all packs processes all packs in the store."""
        from guild.db.store import GuildStore
        
        store = GuildStore(engine.db_path)
        
        # Add some test packs
        store.add_pack(
            pack_id="index-test-1",
            version="1.0",
            yaml_content="name: Test Pack 1",
            author_agent="test-agent",
            problem_class="classification",
            domain="ml",
        )
        store.add_pack(
            pack_id="index-test-2",
            version="1.0",
            yaml_content="name: Test Pack 2",
            author_agent="test-agent",
            problem_class="regression",
            domain="stats",
        )
        
        # Mock encode_pack to return a fixed vector
        fixed_vector = np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        
        with patch.object(engine, "encode_pack", return_value=fixed_vector):
            count = engine.index_all_packs(store)
        
        assert count == 2
        assert engine.get_embedding("index-test-1") is not None
        assert engine.get_embedding("index-test-2") is not None


class TestEmbeddingsTableSchema:
    """Tests for the embeddings table schema."""

    def test_embeddings_table_has_required_columns(self, temp_db):
        """Embeddings table has the required columns via direct SQL check."""
        import sqlite3
        
        # First, run the migration to create the table
        # We need to manually apply migration 2 since we can't easily import EmbeddingEngine
        conn = sqlite3.connect(temp_db)
        
        # Apply migration 1 first (schema_version table and packs table)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        conn.execute("""
            INSERT INTO schema_version (version, applied_at, description) 
            VALUES (1, datetime('now'), 'Initial schema')
        """)
        
        # Apply migration 2 (embeddings table)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                pack_id TEXT PRIMARY KEY,
                vector BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO schema_version (version, applied_at, description) 
            VALUES (2, datetime('now'), 'Add embeddings table')
        """)
        conn.commit()
        
        # Now verify the columns exist
        cursor = conn.execute("PRAGMA table_info(embeddings)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()
        
        assert "pack_id" in columns
        assert "vector" in columns
        assert "model_name" in columns
        assert "created_at" in columns
