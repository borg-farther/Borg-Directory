"""Guild persistent store — SQLite backend."""

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, List, Optional

from .migrations import migrate, get_current_version


def _json_default(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _ensure_iso8601(value: Optional[str]) -> str:
    """Ensure a value is an ISO8601 string or return current time."""
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return value


def _parse_json(value: Optional[str]) -> Optional[dict]:
    """Parse JSON string to dict, returning None if invalid."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _json_dumps(value: Any) -> str:
    """Serialize value to JSON string."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, default=_json_default)


class AgentStore:
    """Guild SQLite store with thread-safe access and auto-migration."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        embedding_engine: Optional[Any] = None,
    ):
        """Initialize store with database path.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.hermes/guild/guild.db
            embedding_engine: Optional embedding engine for auto-generating
                embeddings when packs are added. If None (default), embeddings
                are not auto-generated. This keeps add_pack() fast for tests.
                Can be any object implementing the EmbeddingEngineProtocol
                (has encode() and store_embedding() methods).
        """
        if db_path is None:
            db_path = os.path.expanduser("~/.hermes/guild/guild.db")
        self.db_path = db_path
        self.embedding_engine = embedding_engine
        self._local = threading.local()
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure the database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                isolation_level=None,
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            # Auto-migrate on first connection
            migrate(self._local.connection)
        return self._local.connection

    def close(self):
        """Close the thread-local database connection."""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def __enter__(self) -> "AgentStore":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()

    # --- Pack CRUD ---

    def add_pack(
        self,
        pack_id: str,
        version: str,
        yaml_content: str,
        author_agent: str,
        confidence: str = "guessed",
        tier: str = "community",
        author_operator: Optional[str] = None,
        problem_class: Optional[str] = None,
        domain: Optional[str] = None,
        phase_count: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        pulled_at: Optional[str] = None,
        local_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Add a new pack to the store.
        
        Args:
            pack_id: Unique identifier for the pack
            version: Version string
            yaml_content: Full pack YAML content
            author_agent: Agent that authored the pack
            confidence: Confidence level
            tier: Pack tier (core, validated, community)
            author_operator: Operator that authored the pack
            problem_class: Problem classification
            domain: Domain
            phase_count: Number of phases
            created_at: Creation timestamp (ISO8601)
            updated_at: Update timestamp (ISO8601)
            pulled_at: Last pulled timestamp
            local_path: Local file path
            metadata: Additional metadata dict
            
        Returns:
            The inserted pack dict
            
        Raises:
            sqlite3.IntegrityError: If pack_id already exists
        """
        conn = self._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        created_at = _ensure_iso8601(created_at)
        updated_at = _ensure_iso8601(updated_at)
        
        conn.execute(
            """
            INSERT INTO packs (
                id, version, yaml_content, confidence, tier, author_agent,
                author_operator, problem_class, domain, phase_count,
                created_at, updated_at, pulled_at, local_path, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pack_id,
                version,
                yaml_content,
                confidence,
                tier,
                author_agent,
                author_operator,
                problem_class,
                domain,
                phase_count,
                created_at,
                updated_at,
                _ensure_iso8601(pulled_at) if pulled_at else None,
                local_path,
                _json_dumps(metadata),
            ),
        )
        conn.commit()

        # Auto-generate embedding if embedding_engine is available
        if self.embedding_engine is not None:
            try:
                self._generate_embedding(pack_id, yaml_content, problem_class, domain, metadata)
            except Exception:
                # Don't fail pack insertion if embedding fails
                pass

        return self.get_pack(pack_id)

    def _generate_embedding(
        self,
        pack_id: str,
        yaml_content: str,
        problem_class: Optional[str],
        domain: Optional[str],
        metadata: Optional[dict],
    ) -> None:
        """Generate and store embedding for a pack.

        Args:
            pack_id: Pack identifier.
            yaml_content: Pack YAML content for embedding.
            problem_class: Problem classification.
            domain: Pack domain.
            metadata: Additional metadata.
        """
        engine = self.embedding_engine

        # Build combined text for embedding
        parts = []
        if problem_class:
            parts.append(f"Problem class: {problem_class}")
        if domain:
            parts.append(f"Domain: {domain}")
        if metadata:
            desc = metadata.get("description", "")
            if desc:
                parts.append(f"Description: {desc}")
        if yaml_content:
            parts.append(f"YAML: {yaml_content[:500]}")

        combined_text = " | ".join(parts) if parts else pack_id

        # Check if engine has encode() + store_embedding() methods
        if hasattr(engine, "encode") and hasattr(engine, "store_embedding"):
            try:
                embedding = engine.encode(combined_text)
                engine.store_embedding(pack_id, embedding)
            except Exception:
                pass

    def get_pack(self, pack_id: str) -> Optional[dict]:
        """Get a pack by ID.
        
        Args:
            pack_id: The pack identifier
            
        Returns:
            Pack dict or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM packs WHERE id = ?", (pack_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_pack(row)

    def update_pack(
        self,
        pack_id: str,
        version: Optional[str] = None,
        yaml_content: Optional[str] = None,
        confidence: Optional[str] = None,
        tier: Optional[str] = None,
        author_operator: Optional[str] = None,
        problem_class: Optional[str] = None,
        domain: Optional[str] = None,
        phase_count: Optional[int] = None,
        updated_at: Optional[str] = None,
        pulled_at: Optional[str] = None,
        local_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """Update a pack.
        
        Args:
            pack_id: The pack identifier
            version: New version string
            yaml_content: New YAML content
            confidence: New confidence level
            tier: New tier
            author_operator: New author operator
            problem_class: New problem class
            domain: New domain
            phase_count: New phase count
            updated_at: New updated timestamp
            pulled_at: New pulled timestamp
            local_path: New local path
            metadata: New metadata dict
            
        Returns:
            Updated pack dict or None if not found
        """
        conn = self._get_connection()
        
        # Check if pack exists
        if self.get_pack(pack_id) is None:
            return None
        
        # Build dynamic update
        updates = []
        params = []
        
        if version is not None:
            updates.append("version = ?")
            params.append(version)
        if yaml_content is not None:
            updates.append("yaml_content = ?")
            params.append(yaml_content)
        if confidence is not None:
            updates.append("confidence = ?")
            params.append(confidence)
        if tier is not None:
            updates.append("tier = ?")
            params.append(tier)
        if author_operator is not None:
            updates.append("author_operator = ?")
            params.append(author_operator)
        if problem_class is not None:
            updates.append("problem_class = ?")
            params.append(problem_class)
        if domain is not None:
            updates.append("domain = ?")
            params.append(domain)
        if phase_count is not None:
            updates.append("phase_count = ?")
            params.append(phase_count)
        if updated_at is not None:
            updates.append("updated_at = ?")
            params.append(_ensure_iso8601(updated_at))
        if pulled_at is not None:
            updates.append("pulled_at = ?")
            params.append(_ensure_iso8601(pulled_at))
        if local_path is not None:
            updates.append("local_path = ?")
            params.append(local_path)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(_json_dumps(metadata))
        
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.append(pack_id)
            
            conn.execute(
                f"UPDATE packs SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
        
        return self.get_pack(pack_id)

    def list_packs(
        self,
        tier: Optional[str] = None,
        confidence: Optional[str] = None,
        author_agent: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List packs with optional filters.
        
        Args:
            tier: Filter by tier
            confidence: Filter by confidence
            author_agent: Filter by author agent
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of pack dicts
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM packs WHERE 1=1"
        params = []
        
        if tier is not None:
            query += " AND tier = ?"
            params.append(tier)
        if confidence is not None:
            query += " AND confidence = ?"
            params.append(confidence)
        if author_agent is not None:
            query += " AND author_agent = ?"
            params.append(author_agent)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        return [self._row_to_pack(row) for row in cursor.fetchall()]

    def search_packs(self, query: str, limit: int = 50) -> List[dict]:
        """Search packs using full-text search.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching pack dicts
        """
        conn = self._get_connection()
        
        # Escape FTS5 special characters and prepare query
        escaped = query.replace('"', '""')
        fts_query = f'"{escaped}"'
        
        cursor = conn.execute(
            """
            SELECT p.* FROM packs p
            INNER JOIN packs_fts fts ON p.rowid = fts.rowid
            WHERE packs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, limit),
        )
        return [self._row_to_pack(row) for row in cursor.fetchall()]

    def delete_pack(self, pack_id: str) -> bool:
        """Delete a pack.
        
        Args:
            pack_id: The pack identifier
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM packs WHERE id = ?", (pack_id,))
        conn.commit()
        return cursor.rowcount > 0

    def _row_to_pack(self, row: sqlite3.Row) -> dict:
        """Convert a row to a pack dict."""
        return {
            "id": row["id"],
            "version": row["version"],
            "yaml_content": row["yaml_content"],
            "confidence": row["confidence"],
            "tier": row["tier"],
            "author_agent": row["author_agent"],
            "author_operator": row["author_operator"],
            "problem_class": row["problem_class"],
            "domain": row["domain"],
            "phase_count": row["phase_count"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "pulled_at": row["pulled_at"],
            "local_path": row["local_path"],
            "metadata": _parse_json(row["metadata"]),
        }

    # --- Feedback CRUD ---

    def add_feedback(
        self,
        feedback_id: str,
        pack_id: str,
        author_agent: str,
        outcome: str,
        confidence: Optional[str] = None,
        author_operator: Optional[str] = None,
        execution_log_hash: Optional[str] = None,
        evidence: Optional[str] = None,
        suggestions: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Add feedback for a pack.
        
        Args:
            feedback_id: Unique feedback identifier
            pack_id: Pack being feedback on
            author_agent: Agent providing feedback
            outcome: Outcome (success, partial, failure)
            confidence: Confidence level
            author_operator: Operator providing feedback
            execution_log_hash: Hash of execution log
            evidence: Evidence text
            suggestions: Suggestions text
            created_at: Creation timestamp
            metadata: Additional metadata
            
        Returns:
            The inserted feedback dict
            
        Raises:
            sqlite3.IntegrityError: If feedback_id exists or pack_id doesn't exist
        """
        conn = self._get_connection()
        created_at = _ensure_iso8601(created_at)
        
        conn.execute(
            """
            INSERT INTO feedback (
                id, pack_id, author_agent, author_operator, confidence,
                outcome, execution_log_hash, evidence, suggestions,
                created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                pack_id,
                author_agent,
                author_operator,
                confidence,
                outcome,
                execution_log_hash,
                evidence,
                suggestions,
                created_at,
                _json_dumps(metadata),
            ),
        )
        conn.commit()
        return self.get_feedback(feedback_id)

    def get_feedback(self, feedback_id: str) -> Optional[dict]:
        """Get feedback by ID.
        
        Args:
            feedback_id: The feedback identifier
            
        Returns:
            Feedback dict or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM feedback WHERE id = ?", (feedback_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_feedback(row)

    def list_feedback(
        self,
        pack_id: Optional[str] = None,
        author_agent: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List feedback with optional filters.
        
        Args:
            pack_id: Filter by pack
            author_agent: Filter by author agent
            outcome: Filter by outcome
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of feedback dicts
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM feedback WHERE 1=1"
        params = []
        
        if pack_id is not None:
            query += " AND pack_id = ?"
            params.append(pack_id)
        if author_agent is not None:
            query += " AND author_agent = ?"
            params.append(author_agent)
        if outcome is not None:
            query += " AND outcome = ?"
            params.append(outcome)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        return [self._row_to_feedback(row) for row in cursor.fetchall()]

    def delete_feedback(self, feedback_id: str) -> bool:
        """Delete feedback.
        
        Args:
            feedback_id: The feedback identifier
            
        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()
        cursor = conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        conn.commit()
        return cursor.rowcount > 0

    def _row_to_feedback(self, row: sqlite3.Row) -> dict:
        """Convert a row to a feedback dict."""
        return {
            "id": row["id"],
            "pack_id": row["pack_id"],
            "author_agent": row["author_agent"],
            "author_operator": row["author_operator"],
            "confidence": row["confidence"],
            "outcome": row["outcome"],
            "execution_log_hash": row["execution_log_hash"],
            "evidence": row["evidence"],
            "suggestions": row["suggestions"],
            "created_at": row["created_at"],
            "metadata": _parse_json(row["metadata"]),
        }

    # --- Agent CRUD ---

    def register_agent(
        self,
        agent_id: str,
        operator: str,
        display_name: Optional[str] = None,
        access_tier: str = "community",
        registered_at: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Register a new agent.
        
        Args:
            agent_id: Unique agent identifier
            operator: Operator name
            display_name: Display name
            access_tier: Access tier (default: community)
            registered_at: Registration timestamp
            metadata: Additional metadata
            
        Returns:
            The registered agent dict
            
        Raises:
            sqlite3.IntegrityError: If agent_id already exists
        """
        conn = self._get_connection()
        registered_at = _ensure_iso8601(registered_at)
        
        conn.execute(
            """
            INSERT INTO agents (
                agent_id, operator, display_name, access_tier,
                registered_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                agent_id,
                operator,
                display_name,
                access_tier,
                registered_at,
                _json_dumps(metadata),
            ),
        )
        conn.commit()
        return self.get_agent(agent_id)

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get an agent by ID.
        
        Args:
            agent_id: The agent identifier
            
        Returns:
            Agent dict or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_agent(row)

    def update_agent_stats(
        self,
        agent_id: str,
        contribution_score: Optional[float] = None,
        reputation_score: Optional[float] = None,
        free_rider_score: Optional[float] = None,
        access_tier: Optional[str] = None,
        packs_published: Optional[int] = None,
        packs_consumed: Optional[int] = None,
        feedback_given: Optional[int] = None,
        last_active_at: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """Update agent statistics.
        
        Args:
            agent_id: The agent identifier
            contribution_score: New contribution score
            reputation_score: New reputation score
            free_rider_score: New free rider score
            access_tier: New access tier
            packs_published: New packs published count
            packs_consumed: New packs consumed count
            feedback_given: New feedback given count
            last_active_at: New last active timestamp
            metadata: New metadata
            
        Returns:
            Updated agent dict or None if not found
        """
        conn = self._get_connection()
        
        if self.get_agent(agent_id) is None:
            return None
        
        updates = []
        params = []
        
        if contribution_score is not None:
            updates.append("contribution_score = ?")
            params.append(contribution_score)
        if reputation_score is not None:
            updates.append("reputation_score = ?")
            params.append(reputation_score)
        if free_rider_score is not None:
            updates.append("free_rider_score = ?")
            params.append(free_rider_score)
        if access_tier is not None:
            updates.append("access_tier = ?")
            params.append(access_tier)
        if packs_published is not None:
            updates.append("packs_published = ?")
            params.append(packs_published)
        if packs_consumed is not None:
            updates.append("packs_consumed = ?")
            params.append(packs_consumed)
        if feedback_given is not None:
            updates.append("feedback_given = ?")
            params.append(feedback_given)
        if last_active_at is not None:
            updates.append("last_active_at = ?")
            params.append(_ensure_iso8601(last_active_at))
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(_json_dumps(metadata))
        
        if updates:
            params.append(agent_id)
            conn.execute(
                f"UPDATE agents SET {', '.join(updates)} WHERE agent_id = ?",
                params,
            )
            conn.commit()
        
        return self.get_agent(agent_id)

    def list_agents(
        self,
        access_tier: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List agents with optional filters.
        
        Args:
            access_tier: Filter by access tier
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of agent dicts
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM agents WHERE 1=1"
        params = []
        
        if access_tier is not None:
            query += " AND access_tier = ?"
            params.append(access_tier)
        
        query += " ORDER BY registered_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        return [self._row_to_agent(row) for row in cursor.fetchall()]

    def _row_to_agent(self, row: sqlite3.Row) -> dict:
        """Convert a row to an agent dict."""
        return {
            "agent_id": row["agent_id"],
            "operator": row["operator"],
            "display_name": row["display_name"],
            "contribution_score": row["contribution_score"],
            "reputation_score": row["reputation_score"],
            "free_rider_score": row["free_rider_score"],
            "access_tier": row["access_tier"],
            "packs_published": row["packs_published"],
            "packs_consumed": row["packs_consumed"],
            "feedback_given": row["feedback_given"],
            "registered_at": row["registered_at"],
            "last_active_at": row["last_active_at"],
            "metadata": _parse_json(row["metadata"]),
        }

    # --- Execution CRUD ---

    def record_execution(
        self,
        execution_id: str,
        session_id: str,
        pack_id: str,
        agent_id: str,
        task: Optional[str] = None,
        status: str = "started",
        phases_completed: int = 0,
        phases_failed: int = 0,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        log_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Record a new execution.
        
        Args:
            execution_id: Unique execution identifier
            session_id: Session identifier
            pack_id: Pack being executed
            agent_id: Agent executing
            task: Task description
            status: Execution status
            phases_completed: Number of phases completed
            phases_failed: Number of phases failed
            started_at: Start timestamp
            completed_at: Completion timestamp
            log_hash: Hash of execution log
            metadata: Additional metadata
            
        Returns:
            The recorded execution dict
            
        Raises:
            sqlite3.IntegrityError: If execution_id exists or pack_id/agent_id don't exist
        """
        conn = self._get_connection()
        started_at = _ensure_iso8601(started_at)
        
        conn.execute(
            """
            INSERT INTO executions (
                id, session_id, pack_id, agent_id, task, status,
                phases_completed, phases_failed, started_at,
                completed_at, log_hash, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                execution_id,
                session_id,
                pack_id,
                agent_id,
                task,
                status,
                phases_completed,
                phases_failed,
                started_at,
                _ensure_iso8601(completed_at) if completed_at else None,
                log_hash,
                _json_dumps(metadata),
            ),
        )
        conn.commit()
        return self.get_execution(execution_id)

    def get_execution(self, execution_id: str) -> Optional[dict]:
        """Get an execution by ID.
        
        Args:
            execution_id: The execution identifier
            
        Returns:
            Execution dict or None if not found
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM executions WHERE id = ?", (execution_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_execution(row)

    def update_execution(
        self,
        execution_id: str,
        status: Optional[str] = None,
        phases_completed: Optional[int] = None,
        phases_failed: Optional[int] = None,
        completed_at: Optional[str] = None,
        log_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[dict]:
        """Update an execution.
        
        Args:
            execution_id: The execution identifier
            status: New status
            phases_completed: New phases completed count
            phases_failed: New phases failed count
            completed_at: New completion timestamp
            log_hash: New log hash
            metadata: New metadata
            
        Returns:
            Updated execution dict or None if not found
        """
        conn = self._get_connection()
        
        if self.get_execution(execution_id) is None:
            return None
        
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if phases_completed is not None:
            updates.append("phases_completed = ?")
            params.append(phases_completed)
        if phases_failed is not None:
            updates.append("phases_failed = ?")
            params.append(phases_failed)
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(_ensure_iso8601(completed_at))
        if log_hash is not None:
            updates.append("log_hash = ?")
            params.append(log_hash)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(_json_dumps(metadata))
        
        if updates:
            params.append(execution_id)
            conn.execute(
                f"UPDATE executions SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
        
        return self.get_execution(execution_id)

    def list_executions(
        self,
        pack_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """List executions with optional filters.
        
        Args:
            pack_id: Filter by pack
            agent_id: Filter by agent
            session_id: Filter by session
            status: Filter by status
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of execution dicts
        """
        conn = self._get_connection()
        
        query = "SELECT * FROM executions WHERE 1=1"
        params = []
        
        if pack_id is not None:
            query += " AND pack_id = ?"
            params.append(pack_id)
        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if session_id is not None:
            query += " AND session_id = ?"
            params.append(session_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(query, params)
        return [self._row_to_execution(row) for row in cursor.fetchall()]

    def _row_to_execution(self, row: sqlite3.Row) -> dict:
        """Convert a row to an execution dict."""
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "pack_id": row["pack_id"],
            "agent_id": row["agent_id"],
            "task": row["task"],
            "status": row["status"],
            "phases_completed": row["phases_completed"],
            "phases_failed": row["phases_failed"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "log_hash": row["log_hash"],
            "metadata": _parse_json(row["metadata"]),
        }

    # --- Execution aliases for compatibility ---

    def add_execution(self, **kwargs) -> dict:
        """Alias for record_execution() — logs a pack execution to the store.

        Args (same as record_execution):
            execution_id: Unique execution identifier
            session_id: Session identifier
            pack_id: Pack being executed
            agent_id: Agent executing
            task: Task description
            status: Execution status
            phases_completed: Number of phases completed
            phases_failed: Number of phases failed
            started_at: Start timestamp
            completed_at: Completion timestamp
            log_hash: Hash of execution log
            metadata: Additional metadata

        Returns:
            The recorded execution dict
        """
        return self.record_execution(**kwargs)

    def record_publish(
        self,
        pack_id: str,
        author_agent: str,
        confidence: str,
        outcome: str = "published",
        author_operator: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Record a pack publish event to the store.

        Args:
            pack_id: Pack that was published
            author_agent: Agent that authored the pack
            confidence: Confidence level at time of publish
            outcome: Publish outcome (default: published)
            author_operator: Operator that approved the publish
            created_at: Publish timestamp
            metadata: Additional metadata

        Returns:
            The recorded execution dict
        """
        import uuid
        execution_id = f"publish-{pack_id}-{uuid.uuid4().hex[:8]}"
        return self.record_execution(
            execution_id=execution_id,
            session_id="",  # publish events don't have sessions
            pack_id=pack_id,
            agent_id=author_agent,
            task="publish",
            status=outcome,
            phases_completed=0,
            phases_failed=0,
            started_at=created_at or datetime.now(timezone.utc).isoformat(),
            completed_at=created_at or datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )

    # --- Utility methods ---

    def get_schema_version(self) -> int:
        """Get the current schema version.
        
        Returns:
            Schema version number, or 0 if not initialized
        """
        return get_current_version(self._get_connection())

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for explicit transactions.
        
        Usage:
            with store.transaction() as conn:
                conn.execute(...)
        """
        conn = self._get_connection()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
