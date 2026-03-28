"""
Tests for run_aggregator.py - verifies aggregator produces valid output given sample data.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Set up test BORG_DIR before importing borg modules
TEST_BORG_DIR = None


@pytest.fixture
def temp_borg_dir():
    """Create a temporary BORG_DIR for testing."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def mock_env(temp_borg_dir, monkeypatch):
    """Set BORG_DIR environment variable for the test."""
    monkeypatch.setenv("BORG_DIR", str(temp_borg_dir))
    return temp_borg_dir


class TestRunAggregator:
    """Tests for the aggregator script using sample data."""

    def _create_sample_feedback_db(self, db_path: Path) -> None:
        """Create a sample SQLite db with feedback data."""
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS packs (
                id TEXT PRIMARY KEY,
                version TEXT,
                yaml_content TEXT,
                confidence TEXT,
                tier TEXT,
                author_agent TEXT,
                author_operator TEXT,
                problem_class TEXT,
                domain TEXT,
                phase_count INTEGER,
                created_at TEXT,
                updated_at TEXT,
                pulled_at TEXT,
                local_path TEXT,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                pack_id TEXT,
                author_agent TEXT,
                author_operator TEXT,
                confidence TEXT,
                outcome TEXT,
                execution_log_hash TEXT,
                evidence TEXT,
                suggestions TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                operator TEXT,
                display_name TEXT,
                access_tier TEXT,
                registered_at TEXT,
                last_active_at TEXT,
                contribution_score REAL,
                reputation_score REAL,
                free_rider_score REAL,
                packs_published INTEGER,
                packs_consumed INTEGER,
                feedback_given INTEGER,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                pack_id TEXT,
                agent_id TEXT,
                task TEXT,
                status TEXT,
                phases_completed INTEGER,
                phases_failed INTEGER,
                started_at TEXT,
                completed_at TEXT,
                log_hash TEXT,
                metadata TEXT
            )
        """)
        conn.commit()

        # Insert sample packs
        packs = [
            ("pack-001", "v1.0", "yaml content 1", "tested", "core", "agent-a", None, "classification", "domain-a", 3, "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z", None, None, None),
            ("pack-002", "v1.0", "yaml content 2", "inferred", "community", "agent-b", None, "classification", "domain-b", 2, "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z", None, None, None),
            ("pack-003", "v1.0", "yaml content 3", "guessed", "validated", "agent-c", None, "classification", "domain-c", 4, "2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z", None, None, None),
        ]
        for p in packs:
            conn.execute("""
                INSERT INTO packs (id, version, yaml_content, confidence, tier, author_agent, author_operator, problem_class, domain, phase_count, created_at, updated_at, pulled_at, local_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, p)

        # Insert sample feedback
        feedbacks = [
            ("fb-001", "pack-001", "agent-a", None, "high", "success", None, "Pack worked well", "Consider adding more phases", "2024-01-01T00:00:00Z", None),
            ("fb-002", "pack-001", "agent-b", None, "medium", "success", None, "Good results", None, "2024-01-02T00:00:00Z", None),
            ("fb-003", "pack-002", "agent-a", None, "low", "failure", None, "Phase 2 failed validation", "Add error handling", "2024-01-03T00:00:00Z", None),
            ("fb-004", "pack-002", "agent-c", None, "medium", "partial", None, "Some issues with Phase 1", "Improve Phase 1 checkpoint", "2024-01-04T00:00:00Z", None),
            ("fb-005", "pack-003", "agent-b", None, "high", "success", None, "Excellent", None, "2024-01-05T00:00:00Z", None),
        ]
        for f in feedbacks:
            conn.execute("""
                INSERT INTO feedback (id, pack_id, author_agent, author_operator, confidence, outcome, execution_log_hash, evidence, suggestions, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, f)

        conn.close()

    def _create_sample_telemetry(self, borg_dir: Path) -> None:
        """Create sample telemetry.jsonl file."""
        telemetry_path = borg_dir / "telemetry.jsonl"
        events = [
            {"type": "execution_completed", "session_id": "sess-001", "pack_id": "pack-001", "status": "completed", "duration_s": 5.2, "error": ""},
            {"type": "execution_completed", "session_id": "sess-002", "pack_id": "pack-001", "status": "completed", "duration_s": 4.8, "error": ""},
            {"type": "execution_completed", "session_id": "sess-003", "pack_id": "pack-002", "status": "failed", "duration_s": 3.1, "error": "Phase 2 failed"},
            {"type": "execution_completed", "session_id": "sess-004", "pack_id": "pack-002", "status": "failed", "duration_s": 2.9, "error": "Phase 1 failed"},
            {"type": "execution_completed", "session_id": "sess-005", "pack_id": "pack-003", "status": "completed", "duration_s": 6.0, "error": ""},
        ]
        with open(telemetry_path, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")

    def test_aggregator_produces_valid_report(self, mock_env):
        """Test that aggregator generates a valid JSON report with expected structure."""
        # Setup sample data
        self._create_sample_feedback_db(mock_env / "guild.db")
        self._create_sample_telemetry(mock_env)

        from scripts.run_aggregator import _load_telemetry, generate_report_for_dir

        # Verify telemetry loaded correctly
        telemetry = _load_telemetry(mock_env)
        assert len(telemetry) == 5

        # Generate the report
        report = generate_report_for_dir(mock_env)

        # Verify report structure
        assert "generated_at" in report
        assert "total_packs_analyzed" in report
        assert "total_feedback_entries" in report
        assert "total_telemetry_events" in report
        assert "most_used_packs" in report
        assert "most_failed_packs" in report
        assert "packs_with_negative_feedback" in report
        assert "all_pack_reports" in report

        # Verify values
        assert report["total_packs_analyzed"] == 3
        assert report["total_telemetry_events"] == 5

    def test_most_used_pack_ranking(self, mock_env):
        """Test that most_used_packs is correctly sorted by usage_count."""
        self._create_sample_feedback_db(mock_env / "guild.db")
        self._create_sample_telemetry(mock_env)

        from scripts.run_aggregator import generate_report_for_dir

        report = generate_report_for_dir(mock_env)
        most_used = report["most_used_packs"]

        # pack-002 has 2 feedback + 2 telemetry = 4
        # pack-001 has 2 feedback + 2 telemetry = 4
        # pack-003 has 1 feedback + 1 telemetry = 2
        # So pack-002 and pack-001 should be at top
        assert len(most_used) > 0
        # Verify sorted by usage_count descending
        for i in range(len(most_used) - 1):
            assert most_used[i]["usage_count"] >= most_used[i + 1]["usage_count"]

    def test_most_failed_pack_ranking(self, mock_env):
        """Test that most_failed_packs is correctly sorted by lowest success_rate."""
        self._create_sample_feedback_db(mock_env / "guild.db")
        self._create_sample_telemetry(mock_env)

        from scripts.run_aggregator import generate_report_for_dir

        report = generate_report_for_dir(mock_env)
        most_failed = report["most_failed_packs"]

        # pack-002 has telemetry with failures (2 failed out of 2 = 0% success)
        # pack-001 has 100% success (2 completed out of 2)
        # So pack-002 should be first
        if len(most_failed) > 0:
            assert most_failed[0]["pack_id"] == "pack-002"
            # Verify sorted by success_rate ascending
            for i in range(len(most_failed) - 1):
                assert most_failed[i]["success_rate"] <= most_failed[i + 1]["success_rate"]

    def test_negative_feedback_packs_identified(self, mock_env):
        """Test that packs with negative feedback are correctly identified."""
        self._create_sample_feedback_db(mock_env / "guild.db")
        self._create_sample_telemetry(mock_env)

        from scripts.run_aggregator import generate_report_for_dir

        report = generate_report_for_dir(mock_env)
        negative_packs = report["packs_with_negative_feedback"]

        # pack-002 has failure and partial outcomes
        assert len(negative_packs) >= 1
        pack_ids_with_negative = [p["pack_id"] for p in negative_packs]
        assert "pack-002" in pack_ids_with_negative

    def test_pack_report_has_required_fields(self, mock_env):
        """Test that each pack report contains all required fields."""
        self._create_sample_feedback_db(mock_env / "guild.db")
        self._create_sample_telemetry(mock_env)

        from scripts.run_aggregator import generate_report_for_dir

        report = generate_report_for_dir(mock_env)

        required_fields = ["pack_id", "usage_count", "success_rate", "common_failure_patterns", "suggested_improvements"]

        for pack_report in report["all_pack_reports"]:
            for field in required_fields:
                assert field in pack_report, f"Missing field '{field}' in pack report"

            # Verify types
            assert isinstance(pack_report["pack_id"], str)
            assert isinstance(pack_report["usage_count"], int)
            assert isinstance(pack_report["success_rate"], (int, float))
            assert 0.0 <= pack_report["success_rate"] <= 1.0
            assert isinstance(pack_report["common_failure_patterns"], list)
            assert isinstance(pack_report["suggested_improvements"], list)

    def test_empty_data_handling(self, mock_env):
        """Test that aggregator handles empty data gracefully."""
        # Create empty db
        self._create_sample_feedback_db(mock_env / "guild.db")
        # Don't create telemetry file

        from scripts.run_aggregator import generate_report_for_dir

        report = generate_report_for_dir(mock_env)

        assert report["total_packs_analyzed"] == 3  # Still have packs in db
        assert report["total_telemetry_events"] == 0
        assert "most_used_packs" in report
        assert "all_pack_reports" in report

    def test_report_written_to_borg_dir(self, mock_env):
        """Test that running the main function writes report to BORG_DIR."""
        self._create_sample_feedback_db(mock_env / "guild.db")
        self._create_sample_telemetry(mock_env)

        # Run main
        from scripts.run_aggregator import main

        # Capture stdout
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            main()

        output = f.getvalue()
        assert "Report written to:" in output
        assert "aggregator_report.json" in output

        # Verify file exists
        report_path = mock_env / "aggregator_report.json"
        assert report_path.exists()

        # Verify valid JSON
        with open(report_path) as rf:
            loaded = json.load(rf)
            assert "generated_at" in loaded
            assert "all_pack_reports" in loaded
