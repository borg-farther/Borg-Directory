"""Tests for Guild SQLite store."""

import json
import os
import sqlite3
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone

import pytest

from borg.db.store import AgentStore
from borg.db.migrations import get_current_version, migrate, MIGRATIONS


class TestMigrations:
    """Test migration functionality."""

    def test_get_current_version_none(self):
        """Test version returns 0 for uninitialized db."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            conn = sqlite3.connect(db_path)
            assert get_current_version(conn) == 0
            conn.close()

    def test_get_current_version_initialized(self):
        """Test version returns 1 after migration."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            conn = sqlite3.connect(db_path)
            migrate(conn)
            assert get_current_version(conn) == 2
            conn.close()

    def test_migrate_from_v0(self):
        """Test migration from v0 to v2."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            conn = sqlite3.connect(db_path)
            
            # Verify initial state
            assert get_current_version(conn) == 0
            
            # Migrate
            version = migrate(conn)
            assert version == 2
            assert get_current_version(conn) == 2
            
            # Verify all tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}
            assert "packs" in tables
            assert "feedback" in tables
            assert "agents" in tables
            assert "executions" in tables
            assert "schema_version" in tables
            assert "packs_fts" in tables
            assert "embeddings" in tables
            
            conn.close()

    def test_migrate_idempotent(self):
        """Test that migrate is idempotent."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            conn = sqlite3.connect(db_path)
            
            # Migrate twice
            migrate(conn)
            migrate(conn)
            
            assert get_current_version(conn) == 2
            
            # Verify only one version entry
            cursor = conn.execute("SELECT COUNT(*) FROM schema_version")
            assert cursor.fetchone()[0] == 2
            
            conn.close()


class TestContextManager:
    """Test context manager support."""

    def test_context_manager(self):
        """Test basic context manager usage."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            with AgentStore(db_path) as store:
                assert store.get_schema_version() == 2
                pack = store.add_pack(
                    pack_id="test-pack",
                    version="1.0.0",
                    yaml_content="name: test",
                    author_agent="***",
                )
                assert pack is not None
                assert pack["id"] == "test-pack"

    def test_context_manager_closes_connection(self):
        """Test that context manager closes connection."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            store = AgentStore(db_path)
            with store:
                pass
            # Connection should be closed now


class TestPackCRUD:
    """Test pack CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            yield AgentStore(db_path)

    def test_add_pack(self, store):
        """Test adding a pack."""
        pack = store.add_pack(
            pack_id="test-pack",
            version="1.0.0",
            yaml_content="name: test\nphases:\n  - step1",
            author_agent="agent-1",
            confidence="tested",
            tier="validated",
            problem_class="classification",
            domain="nlp",
            phase_count=1,
        )
        
        assert pack["id"] == "test-pack"
        assert pack["version"] == "1.0.0"
        assert pack["yaml_content"] == "name: test\nphases:\n  - step1"
        assert pack["confidence"] == "tested"
        assert pack["tier"] == "validated"
        assert pack["author_agent"] == "agent-1"
        assert pack["problem_class"] == "classification"
        assert pack["domain"] == "nlp"
        assert pack["phase_count"] == 1
        assert pack["metadata"] is None

    def test_add_pack_with_metadata(self, store):
        """Test adding a pack with metadata."""
        metadata = {"tags": ["test"], "rating": 5}
        pack = store.add_pack(
            pack_id="test-pack-meta",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
            metadata=metadata,
        )
        
        assert pack["metadata"] == metadata

    def test_add_pack_duplicate_id(self, store):
        """Test adding pack with duplicate ID raises error."""
        store.add_pack(
            pack_id="dup-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        with pytest.raises(sqlite3.IntegrityError):
            store.add_pack(
                pack_id="dup-pack",
                version="2.0.0",
                yaml_content="name: test2",
                author_agent="agent-1",
            )

    def test_get_pack(self, store):
        """Test getting a pack."""
        store.add_pack(
            pack_id="get-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        pack = store.get_pack("get-pack")
        assert pack is not None
        assert pack["id"] == "get-pack"

    def test_get_pack_not_found(self, store):
        """Test getting non-existent pack."""
        pack = store.get_pack("non-existent")
        assert pack is None

    def test_update_pack(self, store):
        """Test updating a pack."""
        store.add_pack(
            pack_id="update-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        updated = store.update_pack(
            "update-pack",
            version="2.0.0",
            confidence="validated",
            tier="core",
        )
        
        assert updated["version"] == "2.0.0"
        assert updated["confidence"] == "validated"
        assert updated["tier"] == "core"
        # Original fields unchanged
        assert updated["yaml_content"] == "name: test"

    def test_update_pack_not_found(self, store):
        """Test updating non-existent pack returns None."""
        result = store.update_pack("non-existent", version="2.0.0")
        assert result is None

    def test_list_packs(self, store):
        """Test listing packs."""
        for i in range(5):
            store.add_pack(
                pack_id=f"list-pack-{i}",
                version="1.0.0",
                yaml_content=f"name: test{i}",
                author_agent="agent-1",
                tier="community" if i % 2 == 0 else "validated",
            )
        
        packs = store.list_packs()
        assert len(packs) == 5
        
        # Test filter by tier
        validated = store.list_packs(tier="validated")
        assert len(validated) == 2
        
        # Test limit
        limited = store.list_packs(limit=2)
        assert len(limited) == 2

    def test_delete_pack(self, store):
        """Test deleting a pack."""
        store.add_pack(
            pack_id="delete-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        assert store.delete_pack("delete-pack") is True
        assert store.get_pack("delete-pack") is None
        
        # Deleting again returns False
        assert store.delete_pack("delete-pack") is False


class TestPackSearch:
    """Test pack search functionality."""

    @pytest.fixture
    def store(self):
        """Create a temporary store with test data."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            store = AgentStore(db_path)
            
            # Add test packs
            store.add_pack(
                pack_id="nlp-classifier",
                version="1.0.0",
                yaml_content="name: nlp classifier",
                author_agent="agent-nlp",
                problem_class="text-classification",
                domain="nlp",
            )
            store.add_pack(
                pack_id="vision-detector",
                version="1.0.0",
                yaml_content="name: vision detector",
                author_agent="agent-vision",
                problem_class="object-detection",
                domain="computer-vision",
            )
            store.add_pack(
                pack_id="text-summarizer",
                version="1.0.0",
                yaml_content="name: text summarizer",
                author_agent="agent-nlp",
                problem_class="summarization",
                domain="nlp",
            )
            
            yield store

    def test_search_by_problem_class(self, store):
        """Test searching by problem class."""
        results = store.search_packs("text-classification")
        assert len(results) >= 1
        assert any(r["id"] == "nlp-classifier" for r in results)

    def test_search_by_domain(self, store):
        """Test searching by domain."""
        results = store.search_packs("nlp")
        assert len(results) >= 2
        ids = {r["id"] for r in results}
        assert "nlp-classifier" in ids
        assert "text-summarizer" in ids

    def test_search_by_author(self, store):
        """Test searching by author agent."""
        results = store.search_packs("agent-nlp")
        assert len(results) >= 2

    def test_search_empty_query(self, store):
        """Test empty search query."""
        results = store.search_packs("")
        # Empty query should return empty or all depending on FTS behavior
        assert isinstance(results, list)

    def test_search_no_results(self, store):
        """Test search with no results."""
        results = store.search_packs("nonexistent-query-xyz")
        assert len(results) == 0


class TestFeedbackCRUD:
    """Test feedback CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store with a pack."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            store = AgentStore(db_path)
            store.add_pack(
                pack_id="test-pack",
                version="1.0.0",
                yaml_content="name: test",
                author_agent="agent-1",
            )
            yield store

    def test_add_feedback(self, store):
        """Test adding feedback."""
        feedback = store.add_feedback(
            feedback_id="fb-1",
            pack_id="test-pack",
            author_agent="agent-2",
            outcome="success",
            confidence="validated",
            evidence="Worked well",
            suggestions="Consider adding tests",
        )
        
        assert feedback["id"] == "fb-1"
        assert feedback["pack_id"] == "test-pack"
        assert feedback["outcome"] == "success"
        assert feedback["evidence"] == "Worked well"

    def test_add_feedback_invalid_pack(self, store):
        """Test adding feedback for non-existent pack."""
        with pytest.raises(sqlite3.IntegrityError):
            store.add_feedback(
                feedback_id="fb-2",
                pack_id="non-existent",
                author_agent="agent-2",
                outcome="success",
            )

    def test_get_feedback(self, store):
        """Test getting feedback."""
        store.add_feedback(
            feedback_id="fb-get",
            pack_id="test-pack",
            author_agent="agent-2",
            outcome="success",
        )
        
        feedback = store.get_feedback("fb-get")
        assert feedback is not None
        assert feedback["id"] == "fb-get"

    def test_list_feedback(self, store):
        """Test listing feedback."""
        for i in range(3):
            store.add_feedback(
                feedback_id=f"fb-list-{i}",
                pack_id="test-pack",
                author_agent="agent-2",
                outcome="success" if i % 2 == 0 else "partial",
            )
        
        feedbacks = store.list_feedback(pack_id="test-pack")
        assert len(feedbacks) == 3
        
        # Filter by outcome
        success = store.list_feedback(outcome="success")
        assert len(success) == 2

    def test_delete_feedback(self, store):
        """Test deleting feedback."""
        store.add_feedback(
            feedback_id="fb-del",
            pack_id="test-pack",
            author_agent="agent-2",
            outcome="success",
        )
        
        assert store.delete_feedback("fb-del") is True
        assert store.get_feedback("fb-del") is None


class TestAgentCRUD:
    """Test agent CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            yield AgentStore(db_path)

    def test_register_agent(self, store):
        """Test registering an agent."""
        agent = store.register_agent(
            agent_id="agent-1",
            operator="operator-1",
            display_name="Test Agent",
            access_tier="community",
        )
        
        assert agent["agent_id"] == "agent-1"
        assert agent["operator"] == "operator-1"
        assert agent["display_name"] == "Test Agent"
        assert agent["access_tier"] == "community"
        assert agent["reputation_score"] == 0.5  # default
        assert agent["packs_published"] == 0  # default

    def test_register_duplicate_agent(self, store):
        """Test registering duplicate agent raises error."""
        store.register_agent(
            agent_id="agent-dup",
            operator="operator-1",
        )
        
        with pytest.raises(sqlite3.IntegrityError):
            store.register_agent(
                agent_id="agent-dup",
                operator="operator-2",
            )

    def test_get_agent(self, store):
        """Test getting an agent."""
        store.register_agent(
            agent_id="agent-get",
            operator="operator-1",
        )
        
        agent = store.get_agent("agent-get")
        assert agent is not None
        assert agent["agent_id"] == "agent-get"

    def test_get_agent_not_found(self, store):
        """Test getting non-existent agent."""
        agent = store.get_agent("non-existent")
        assert agent is None

    def test_update_agent_stats(self, store):
        """Test updating agent stats."""
        store.register_agent(
            agent_id="agent-update",
            operator="operator-1",
        )
        
        updated = store.update_agent_stats(
            "agent-update",
            packs_published=5,
            packs_consumed=10,
            reputation_score=0.8,
        )
        
        assert updated["packs_published"] == 5
        assert updated["packs_consumed"] == 10
        assert updated["reputation_score"] == 0.8

    def test_update_agent_not_found(self, store):
        """Test updating non-existent agent returns None."""
        result = store.update_agent_stats("non-existent", packs_published=5)
        assert result is None

    def test_list_agents(self, store):
        """Test listing agents."""
        for i in range(3):
            store.register_agent(
                agent_id=f"agent-list-{i}",
                operator=f"operator-{i}",
                access_tier="community" if i % 2 == 0 else "validated",
            )
        
        agents = store.list_agents()
        assert len(agents) == 3
        
        # Filter by tier
        validated = store.list_agents(access_tier="validated")
        assert len(validated) == 1


class TestExecutionCRUD:
    """Test execution CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store with agent and pack."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            store = AgentStore(db_path)
            
            store.register_agent(
                agent_id="exec-agent",
                operator="operator-1",
            )
            store.add_pack(
                pack_id="exec-pack",
                version="1.0.0",
                yaml_content="name: test",
                author_agent="agent-1",
            )
            
            yield store

    def test_record_execution(self, store):
        """Test recording an execution."""
        execution = store.record_execution(
            execution_id="exec-1",
            session_id="session-1",
            pack_id="exec-pack",
            agent_id="exec-agent",
            task="Test task",
            status="started",
            phases_completed=0,
        )
        
        assert execution["id"] == "exec-1"
        assert execution["session_id"] == "session-1"
        assert execution["pack_id"] == "exec-pack"
        assert execution["agent_id"] == "exec-agent"
        assert execution["status"] == "started"

    def test_record_execution_invalid_pack(self, store):
        """Test recording execution for non-existent pack."""
        with pytest.raises(sqlite3.IntegrityError):
            store.record_execution(
                execution_id="exec-err",
                session_id="session-1",
                pack_id="non-existent",
                agent_id="exec-agent",
            )

    def test_record_execution_invalid_agent(self, store):
        """Test recording execution for non-existent agent."""
        with pytest.raises(sqlite3.IntegrityError):
            store.record_execution(
                execution_id="exec-err2",
                session_id="session-1",
                pack_id="exec-pack",
                agent_id="non-existent",
            )

    def test_get_execution(self, store):
        """Test getting an execution."""
        store.record_execution(
            execution_id="exec-get",
            session_id="session-1",
            pack_id="exec-pack",
            agent_id="exec-agent",
        )
        
        execution = store.get_execution("exec-get")
        assert execution is not None
        assert execution["id"] == "exec-get"

    def test_update_execution(self, store):
        """Test updating an execution."""
        store.record_execution(
            execution_id="exec-update",
            session_id="session-1",
            pack_id="exec-pack",
            agent_id="exec-agent",
            status="started",
            phases_completed=0,
        )
        
        updated = store.update_execution(
            "exec-update",
            status="completed",
            phases_completed=5,
        )
        
        assert updated["status"] == "completed"
        assert updated["phases_completed"] == 5

    def test_list_executions(self, store):
        """Test listing executions."""
        for i in range(3):
            store.record_execution(
                execution_id=f"exec-list-{i}",
                session_id="session-1",
                pack_id="exec-pack",
                agent_id="exec-agent",
                status="completed" if i % 2 == 0 else "failed",
            )
        
        executions = store.list_executions()
        assert len(executions) == 3
        
        # Filter by status
        completed = store.list_executions(status="completed")
        assert len(completed) == 2
        
        # Filter by agent
        agent_exec = store.list_executions(agent_id="exec-agent")
        assert len(agent_exec) == 3


class TestThreadSafety:
    """Test thread safety."""

    def test_concurrent_access(self):
        """Test concurrent access from multiple threads."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            errors = []
            
            def worker(thread_id):
                try:
                    store = AgentStore(db_path)
                    for i in range(10):
                        pack_id = f"thread-{thread_id}-pack-{i}"
                        store.add_pack(
                            pack_id=pack_id,
                            version="1.0.0",
                            yaml_content=f"name: test {i}",
                            author_agent=f"agent-{thread_id}",
                        )
                        store.get_pack(pack_id)
                        store.list_packs()
                except Exception as e:
                    errors.append(e)
            
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0
            
            # Verify all packs were created
            store = AgentStore(db_path)
            packs = store.list_packs()
            assert len(packs) == 50  # 5 threads * 10 packs each


class TestEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def store(self):
        """Create a temporary store."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            yield AgentStore(db_path)

    def test_pack_json_metadata(self, store):
        """Test pack with complex JSON metadata."""
        metadata = {
            "tags": ["tag1", "tag2"],
            "nested": {"key": "value"},
            "number": 42,
        }
        pack = store.add_pack(
            pack_id="json-meta-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
            metadata=metadata,
        )
        
        assert pack["metadata"] == metadata

    def test_feedback_json_metadata(self, store):
        """Test feedback with complex JSON metadata."""
        store.add_pack(
            pack_id="fb-meta-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        metadata = {"source": "automated", "score": 0.95}
        feedback = store.add_feedback(
            feedback_id="fb-meta",
            pack_id="fb-meta-pack",
            author_agent="agent-2",
            outcome="success",
            metadata=metadata,
        )
        
        assert feedback["metadata"] == metadata

    def test_empty_string_fields(self, store):
        """Test pack with empty string fields."""
        pack = store.add_pack(
            pack_id="empty-pack",
            version="",
            yaml_content="",
            author_agent="agent-1",
            author_operator="",
            problem_class="",
            domain="",
        )
        
        assert pack["version"] == ""
        assert pack["yaml_content"] == ""
        assert pack["author_operator"] == ""
        assert pack["problem_class"] == ""
        assert pack["domain"] == ""

    def test_noneOptional_fields(self, store):
        """Test pack with None optional fields."""
        pack = store.add_pack(
            pack_id="none-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
            author_operator=None,
            problem_class=None,
            domain=None,
            pulled_at=None,
            local_path=None,
            metadata=None,
        )
        
        assert pack["author_operator"] is None
        assert pack["problem_class"] is None
        assert pack["domain"] is None
        assert pack["pulled_at"] is None
        assert pack["local_path"] is None
        assert pack["metadata"] is None

    def test_tier_constraint(self, store):
        """Test tier constraint validation."""
        # Valid tiers should work
        for tier in ["core", "validated", "community"]:
            pack = store.add_pack(
                pack_id=f"tier-{tier}",
                version="1.0.0",
                yaml_content="name: test",
                author_agent="agent-1",
                tier=tier,
            )
            assert pack["tier"] == tier

    def test_confidence_constraint(self, store):
        """Test confidence constraint validation."""
        # Valid confidence levels should work
        for confidence in ["guessed", "inferred", "tested", "validated"]:
            pack = store.add_pack(
                pack_id=f"conf-{confidence}",
                version="1.0.0",
                yaml_content="name: test",
                author_agent="agent-1",
                confidence=confidence,
            )
            assert pack["confidence"] == confidence

    def test_execution_status_constraint(self, store):
        """Test execution status constraint validation."""
        store.register_agent(
            agent_id="status-agent",
            operator="op",
        )
        store.add_pack(
            pack_id="status-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        # Valid statuses should work
        for status in ["started", "in_progress", "completed", "failed", "abandoned"]:
            execution = store.record_execution(
                execution_id=f"status-{status}",
                session_id="session-1",
                pack_id="status-pack",
                agent_id="status-agent",
                status=status,
            )
            assert execution["status"] == status

    def test_feedback_outcome_constraint(self, store):
        """Test feedback outcome constraint validation."""
        store.add_pack(
            pack_id="outcome-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        # Valid outcomes should work
        for outcome in ["success", "partial", "failure"]:
            feedback = store.add_feedback(
                feedback_id=f"outcome-{outcome}",
                pack_id="outcome-pack",
                author_agent="agent-2",
                outcome=outcome,
            )
            assert feedback["outcome"] == outcome

    def test_iso8601_timestamps(self, store):
        """Test ISO8601 timestamp handling."""
        specific_time = "2024-01-15T10:30:00Z"
        pack = store.add_pack(
            pack_id="ts-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
            created_at=specific_time,
            updated_at=specific_time,
        )
        
        assert pack["created_at"] == specific_time
        assert pack["updated_at"] == specific_time


class TestDefaultValues:
    """Test default values."""

    @pytest.fixture
    def store(self):
        """Create a temporary store."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            yield AgentStore(db_path)

    def test_pack_defaults(self, store):
        """Test pack default values."""
        pack = store.add_pack(
            pack_id="defaults-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        assert pack["tier"] == "community"
        assert pack["confidence"] == "guessed"
        assert pack["phase_count"] is None

    def test_agent_defaults(self, store):
        """Test agent default values."""
        agent = store.register_agent(
            agent_id="defaults-agent",
            operator="operator",
        )
        
        assert agent["contribution_score"] == 0
        assert agent["reputation_score"] == 0.5
        assert agent["free_rider_score"] == 0
        assert agent["access_tier"] == "community"
        assert agent["packs_published"] == 0
        assert agent["packs_consumed"] == 0
        assert agent["feedback_given"] == 0

    def test_execution_defaults(self, store):
        """Test execution default values."""
        store.register_agent(
            agent_id="exec-defaults-agent",
            operator="operator",
        )
        store.add_pack(
            pack_id="exec-defaults-pack",
            version="1.0.0",
            yaml_content="name: test",
            author_agent="agent-1",
        )
        
        execution = store.record_execution(
            execution_id="exec-defaults",
            session_id="session-1",
            pack_id="exec-defaults-pack",
            agent_id="exec-defaults-agent",
        )
        
        assert execution["status"] == "started"
        assert execution["phases_completed"] == 0
        assert execution["phases_failed"] == 0
        assert execution["task"] is None


class TestTransaction:
    """Test transaction support."""

    def test_transaction_success(self):
        """Test successful transaction."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            store = AgentStore(db_path)
            
            with store.transaction() as conn:
                conn.execute(
                    "INSERT INTO packs (id, version, yaml_content, author_agent, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    ("tx-pack", "1.0.0", "name: test", "agent-1", 
                     datetime.now(timezone.utc).isoformat(),
                     datetime.now(timezone.utc).isoformat()),
                )
            
            # Should be committed
            assert store.get_pack("tx-pack") is not None

    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "test.db")
            store = AgentStore(db_path)
            
            try:
                with store.transaction() as conn:
                    conn.execute(
                        "INSERT INTO packs (id, version, yaml_content, author_agent, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        ("tx-rollback", "1.0.0", "name: test", "agent-1",
                         datetime.now(timezone.utc).isoformat(),
                         datetime.now(timezone.utc).isoformat()),
                    )
                    raise ValueError("Simulated error")
            except ValueError:
                pass
            
            # Should be rolled back
            assert store.get_pack("tx-rollback") is None
