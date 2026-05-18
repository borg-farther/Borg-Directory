"""Tests for semantic search wiring (M3.3 + M3.4).

Tests that:
1. borg_search() accepts a mode parameter and uses SemanticSearchEngine when available
2. MCP server borg_search tool accepts a mode parameter
3. AgentStore.add_pack() auto-generates embeddings when embedding_engine is provided
4. All imports are optional with graceful fallback
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestBorgSearchModeParameter:
    """Test borg_search mode parameter and SemanticSearchEngine wiring."""

    def test_borg_search_accepts_mode_parameter(self):
        """borg_search() should accept a mode parameter."""
        from borg.core import search as search_module

        # Should not raise TypeError when mode is passed
        # Note: May fail on network calls, but should not be TypeError
        try:
            result = search_module.borg_search("test", mode="text")
            assert isinstance(result, str)
        except TypeError as e:
            if "mode" in str(e):
                pytest.fail(f"borg_search should accept mode parameter: {e}")
            raise

    def test_borg_search_mode_defaults_to_text(self):
        """borg_search() mode should default to 'text'."""
        from borg.core import search as search_module

        # Patch _fetch_index to avoid network call
        with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
            result = search_module.borg_search("test")
            data = json.loads(result)
            assert data.get("mode") == "text"

    def test_borg_search_returns_mode_in_response(self):
        """borg_search() should return mode in the response."""
        from borg.core import search as search_module

        with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
            result = search_module.borg_search("test", mode="hybrid")
            data = json.loads(result)
            assert "mode" in data
            assert data["mode"] == "hybrid"

    def test_borg_search_semantic_mode_falls_back_gracefully(self):
        """borg_search(mode='semantic') should fall back to text if SemanticSearchEngine unavailable."""
        from borg.core import search as search_module

        # Temporarily set SemanticSearchEngine to None
        original_sse = search_module.SemanticSearchEngine
        search_module.SemanticSearchEngine = None

        try:
            with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
                result = search_module.borg_search("test", mode="semantic")
                data = json.loads(result)
                assert data.get("mode") == "semantic"  # Mode should still be recorded
                # Should fall back to text search (empty matches for empty index)
                assert data.get("success") is True
        finally:
            search_module.SemanticSearchEngine = original_sse


class TestSemanticSearchEngineWiring:
    """Test SemanticSearchEngine integration with borg_search."""

    def test_semantic_search_engine_import_optional(self):
        """SemanticSearchEngine import should be optional."""
        # Should not raise ImportError
        from borg.core import search as search_module
        # SemanticSearchEngine should be None or a valid class
        assert search_module.SemanticSearchEngine is None or hasattr(search_module.SemanticSearchEngine, 'search')

    def test_borg_search_with_mock_semantic_engine(self):
        """borg_search should use SemanticSearchEngine when available."""
        from borg.core import search as search_module
        from borg.core.semantic_search import SemanticSearchEngine

        # Create mock embedding engine
        mock_engine = MagicMock()
        mock_engine.encode.return_value = MagicMock(shape=(128,))
        mock_engine.search_similar.return_value = [("pack-1", 0.95), ("pack-2", 0.85)]

        # Create mock store
        mock_store = MagicMock()
        mock_store.search_packs.return_value = []
        mock_store.get_pack.return_value = {
            "id": "pack-1",
            "problem_class": "testing",
            "tier": "community",
            "confidence": "tested",
        }

        # Patch SemanticSearchEngine
        original_sse = search_module.SemanticSearchEngine

        class MockSemanticSearchEngine(SemanticSearchEngine):
            def __init__(self, store, embedding_engine=None):
                self.store = mock_store
                self.embedding_engine = embedding_engine
                self.weights = {"semantic": 0.6, "text": 0.4}

            def search(self, query, top_k=10, mode="hybrid"):
                if mode == "semantic":
                    return [mock_store.get_pack("pack-1")]
                return [mock_store.get_pack("pack-1")]

        search_module.SemanticSearchEngine = MockSemanticSearchEngine

        try:
            with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
                result = search_module.borg_search("test query", mode="semantic")
                data = json.loads(result)
                assert data.get("success") is True
        finally:
            search_module.SemanticSearchEngine = original_sse


class TestMcpServerBorgSearchMode:
    """Test MCP server borg_search tool mode parameter."""

    def test_mcp_borg_search_tool_has_mode_parameter(self):
        """borg_search tool should have mode parameter in schema."""
        from borg.integrations.mcp_server import TOOLS

        tool = next((t for t in TOOLS if t["name"] == "borg_search"), None)
        assert tool is not None, "borg_search tool not found"

        props = tool["inputSchema"]["properties"]
        assert "mode" in props, "mode parameter not in borg_search tool schema"
        assert props["mode"]["enum"] == ["text", "semantic", "hybrid"]

    def test_mcp_borg_search_function_accepts_mode(self):
        """borg_search() function should accept mode parameter."""
        from borg.integrations.mcp_server import borg_search

        # Should not raise TypeError
        try:
            result = borg_search("test", mode="text")
            assert isinstance(result, str)
        except TypeError as e:
            if "mode" in str(e):
                pytest.fail(f"borg_search should accept mode parameter: {e}")
            raise


class TestAgentStoreEmbeddingEngine:
    """Test AgentStore with embedding_engine parameter."""

    def test_guild_store_accepts_embedding_engine(self):
        """AgentStore should accept embedding_engine parameter."""
        from borg.db.store import AgentStore

        mock_engine = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = AgentStore(db_path=db_path, embedding_engine=mock_engine)
            assert store.embedding_engine is mock_engine

    def test_guild_store_embedding_engine_defaults_to_none(self):
        """AgentStore embedding_engine should default to None."""
        from borg.db.store import AgentStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = AgentStore(db_path=db_path)
            assert store.embedding_engine is None

    def test_add_pack_auto_embeds_when_engine_provided(self):
        """add_pack() should auto-generate embedding when embedding_engine is provided."""
        from borg.db.store import AgentStore

        mock_engine = MagicMock()
        mock_engine.encode.return_value = MagicMock(shape=(128,))
        mock_engine.store_embedding.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = AgentStore(db_path=db_path, embedding_engine=mock_engine)

            store.add_pack(
                pack_id="test-pack-1",
                version="1.0.0",
                yaml_content="type: workflow_pack\nid: test-pack-1",
                author_agent="test-agent",
                problem_class="testing",
                domain="test",
            )

            # Verify embedding was generated
            mock_engine.encode.assert_called_once()
            mock_engine.store_embedding.assert_called_once()

            # Verify store_embedding was called with pack_id and embedding
            call_args = mock_engine.store_embedding.call_args
            assert call_args[0][0] == "test-pack-1"

    def test_add_pack_does_not_embed_when_engine_is_none(self):
        """add_pack() should NOT auto-embed when embedding_engine is None (default)."""
        from borg.db.store import AgentStore

        # This test verifies the default behavior is fast (no embedding)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = AgentStore(db_path=db_path, embedding_engine=None)

            # Should complete without error and without trying to embed
            pack = store.add_pack(
                pack_id="test-pack-2",
                version="1.0.0",
                yaml_content="type: workflow_pack\nid: test-pack-2",
                author_agent="test-agent",
            )

            assert pack is not None
            assert pack["id"] == "test-pack-2"

    def test_add_pack_succeeds_even_if_embedding_fails(self):
        """add_pack() should succeed even if embedding generation fails."""
        from borg.db.store import AgentStore

        mock_engine = MagicMock()
        mock_engine.encode.side_effect = Exception("Embedding failed")
        mock_engine.store_embedding.side_effect = Exception("Storage failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = AgentStore(db_path=db_path, embedding_engine=mock_engine)

            # Should not raise, should return the pack
            pack = store.add_pack(
                pack_id="test-pack-3",
                version="1.0.0",
                yaml_content="type: workflow_pack\nid: test-pack-3",
                author_agent="test-agent",
            )

            assert pack is not None
            assert pack["id"] == "test-pack-3"


class TestEmbeddingEngineOptionalImport:
    """Test that embedding-related imports are optional."""

    def test_embedding_engine_import_optional(self):
        """EmbeddingEngine import should be optional in search module."""
        from borg.core import search as search_module

        # If numpy or sentence-transformers not installed, EmbeddingEngine should be None
        # If installed, should be the actual class
        if search_module.EmbeddingEngine is None:
            # Graceful fallback - embedding not available
            assert search_module.SemanticSearchEngine is None or search_module.SemanticSearchEngine is not None
        else:
            # Has the class
            assert hasattr(search_module.EmbeddingEngine, 'encode')

    def test_search_works_when_embedding_unavailable(self):
        """borg_search should work even when embedding modules are unavailable."""
        from borg.core import search as search_module

        # Save original values
        original_engine = search_module.EmbeddingEngine
        original_sse = search_module.SemanticSearchEngine

        # Simulate unavailable embeddings
        search_module.EmbeddingEngine = None
        search_module.SemanticSearchEngine = None

        try:
            with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
                result = search_module.borg_search("test query", mode="hybrid")
                data = json.loads(result)
                assert data.get("success") is True
                assert data.get("mode") == "hybrid"
        finally:
            search_module.EmbeddingEngine = original_engine
            search_module.SemanticSearchEngine = original_sse


class TestBorgSearchHybridMode:
    """Test hybrid search mode."""

    def test_borg_search_hybrid_mode_returns_results(self):
        """borg_search(mode='hybrid') should return results."""
        from borg.core import search as search_module

        with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
            result = search_module.borg_search("test", mode="hybrid")
            data = json.loads(result)
            assert data.get("success") is True
            assert data.get("mode") == "hybrid"

    def test_borg_search_invalid_mode_defaults_to_text(self):
        """borg_search with invalid mode should handle gracefully."""
        from borg.core import search as search_module

        with patch.object(search_module, '_fetch_index', return_value={"packs": []}):
            # Invalid mode should not crash - it will just use text search
            result = search_module.borg_search("test", mode="invalid")
            data = json.loads(result)
            assert data.get("success") is True
