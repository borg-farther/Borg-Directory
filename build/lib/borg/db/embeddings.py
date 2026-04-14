"""Guild embeddings engine for semantic search using sentence-transformers."""

import io
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

_SENTENCE_TRANSFORMERS_AVAILABLE = True
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
    _SENTENCE_TRANSFORMERS_AVAILABLE = False

from .migrations import migrate
from .store import AgentStore


class EmbeddingEngine:
    """Vector storage and similarity search for guild packs.
    
    Uses sentence-transformers for encoding and SQLite for storage.
    Supports lazy model loading - model isn't loaded until first encode call.
    """

    def __init__(self, db_path: Optional[str] = None, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding engine.
        
        Args:
            db_path: Path to SQLite database. Defaults to ~/.hermes/guild/guild.db
            model_name: Name of sentence-transformers model to use
        """
        self.db_path = db_path
        self.model_name = model_name
        self._model = None
        self._local = threading.local()
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure the database directory exists."""
        if self.db_path:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path or self._default_db_path(),
                check_same_thread=False,
                isolation_level=None,
            )
            self._local.connection.row_factory = sqlite3.Row
            migrate(self._local.connection)
        return self._local.connection

    def _default_db_path(self) -> str:
        """Get default database path."""
        return os.path.expanduser("~/.hermes/guild/guild.db")

    def _load_model(self):
        """Lazy load the sentence-transformers model."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("Install guild-packs[embeddings] for semantic search")
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

    def _get_embedding_dim(self) -> int:
        """Get embedding dimensionality without loading full model."""
        if not _SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("Install guild-packs[embeddings] for semantic search")
        if self._model is None:
            model = SentenceTransformer(self.model_name)
            return model.get_sentence_embedding_dimension()
        return self._model.get_sentence_embedding_dimension()

    def encode(self, text: str) -> np.ndarray:
        """Encode text to embedding vector.
        
        Args:
            text: Text to encode
            
        Returns:
            Embedding vector as numpy array
        """
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding

    def encode_pack(self, pack: dict) -> np.ndarray:
        """Encode pack metadata to embedding vector.
        
        Combines problem_class, domain, mental_model, and phase descriptions
        into a single text for encoding.
        
        Args:
            pack: Pack dict with metadata fields
            
        Returns:
            Embedding vector as numpy array
        """
        parts = []
        
        if pack.get("problem_class"):
            parts.append(f"Problem class: {pack['problem_class']}")
        if pack.get("domain"):
            parts.append(f"Domain: {pack['domain']}")
        if pack.get("mental_model"):
            parts.append(f"Mental model: {pack['mental_model']}")
        if pack.get("phase_descriptions"):
            phases = pack["phase_descriptions"]
            if isinstance(phases, list):
                parts.append(f"Phases: {'; '.join(phases)}")
            else:
                parts.append(f"Phases: {phases}")
        if pack.get("description"):
            parts.append(f"Description: {pack['description']}")
        if pack.get("yaml_content"):
            # Use first 500 chars of yaml as context
            parts.append(f"YAML: {pack['yaml_content'][:500]}")
        
        combined_text = " | ".join(parts) if parts else ""
        return self.encode(combined_text)

    def store_embedding(self, pack_id: str, embedding: np.ndarray) -> None:
        """Store embedding vector in database.
        
        Args:
            pack_id: Unique pack identifier
            embedding: Embedding vector to store
        """
        conn = self._get_connection()
        vector_bytes = embedding.astype(np.float32).tobytes()
        created_at = datetime.now(timezone.utc).isoformat()
        
        conn.execute(
            """
            INSERT OR REPLACE INTO embeddings (pack_id, vector, model_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (pack_id, vector_bytes, self.model_name, created_at),
        )
        conn.commit()

    def get_embedding(self, pack_id: str) -> Optional[np.ndarray]:
        """Retrieve embedding vector from database.
        
        Args:
            pack_id: Unique pack identifier
            
        Returns:
            Embedding vector or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT vector FROM embeddings WHERE pack_id = ?",
            (pack_id,),
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        vector_bytes = row["vector"]
        embedding = np.frombuffer(vector_bytes, dtype=np.float32)
        return embedding

    def search_similar(
        self, query_embedding: np.ndarray, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Search for similar packs using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of (pack_id, score) tuples sorted by similarity (highest first)
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT pack_id, vector FROM embeddings",
        )
        
        results = []
        query_norm = np.linalg.norm(query_embedding)
        
        for row in cursor.fetchall():
            pack_id = row["pack_id"]
            vector_bytes = row["vector"]
            stored_embedding = np.frombuffer(vector_bytes, dtype=np.float32)
            
            # Cosine similarity (guard against zero-norm vectors)
            denom = query_norm * np.linalg.norm(stored_embedding)
            if denom > 0:
                similarity = np.dot(query_embedding, stored_embedding) / denom
            else:
                similarity = 0.0
            results.append((pack_id, float(similarity)))
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def index_all_packs(self, store: Optional[AgentStore] = None) -> int:
        """Index all packs from AgentStore.
        
        Args:
            store: AgentStore instance. If None, creates a new one.
            
        Returns:
            Number of packs indexed
        """
        if store is None:
            store = AgentStore(self.db_path)
        
        packs = store.list_packs(limit=10000)
        count = 0
        
        for pack in packs:
            pack_id = pack.get("id")
            if pack_id:
                embedding = self.encode_pack(pack)
                self.store_embedding(pack_id, embedding)
                count += 1
        
        return count

    def delete_embedding(self, pack_id: str) -> bool:
        """Delete an embedding from the database.
        
        Args:
            pack_id: Unique pack identifier
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "DELETE FROM embeddings WHERE pack_id = ?",
            (pack_id,),
        )
        conn.commit()
        return cursor.rowcount > 0

    def close(self):
        """Close the thread-local database connection."""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def __enter__(self) -> "EmbeddingEngine":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()