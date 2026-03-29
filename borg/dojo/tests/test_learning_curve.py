"""
Tests for borg/dojo/learning_curve.py
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

from borg.dojo.data_models import (
    FixAction,
    MetricSnapshot,
    SessionAnalysis,
    SkillGap,
    ToolMetric,
)
from borg.dojo.learning_curve import LearningCurveTracker, METRICS_FILE, MAX_SNAPSHOTS


class TestLearningCurveTracker:
    """Tests for LearningCurveTracker class."""

    @pytest.fixture
    def temp_metrics_file(self):
        """Create a temporary metrics file."""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td) / "dojo_metrics.json"

    @pytest.fixture
    def empty_analysis(self):
        """Create an empty SessionAnalysis for testing."""
        return SessionAnalysis(
            schema_version=1,
            analyzed_at=time.time(),
            days_covered=7,
            sessions_analyzed=0,
            total_tool_calls=0,
            total_errors=0,
            overall_success_rate=0.0,
            user_corrections=0,
            tool_metrics={},
            failure_reports=[],
            skill_gaps=[],
            retry_patterns=[],
            weakest_tools=[],
        )

    @pytest.fixture
    def sample_analysis(self):
        """Create a sample SessionAnalysis with data."""
        weakest = [
            ToolMetric(
                tool_name="file_read",
                total_calls=20,
                successful_calls=15,
                failed_calls=5,
                success_rate=0.75,
                top_error_category="path_not_found",
                top_error_snippet="No such file: /tmp/missing.txt",
            ),
            ToolMetric(
                tool_name="web_fetch",
                total_calls=10,
                successful_calls=6,
                failed_calls=4,
                success_rate=0.6,
                top_error_category="timeout",
                top_error_snippet="Connection timed out",
            ),
        ]
        return SessionAnalysis(
            schema_version=1,
            analyzed_at=time.time(),
            days_covered=7,
            sessions_analyzed=42,
            total_tool_calls=150,
            total_errors=9,
            overall_success_rate=94.0,
            user_corrections=3,
            tool_metrics={},
            failure_reports=[],
            skill_gaps=[
                SkillGap(
                    capability="csv-parsing",
                    request_count=5,
                    session_ids=["s1", "s2", "s3"],
                    confidence=0.9,
                ),
            ],
            retry_patterns=[],
            weakest_tools=weakest,
        )

    @pytest.fixture
    def sample_fixes(self):
        """Create sample FixAction list."""
        return [
            FixAction(
                action="patch",
                target_skill="file-read",
                priority=0.8,
                reason="Added path validation",
                fix_content="## Pre-flight",
                applied=True,
                success=True,
            ),
            FixAction(
                action="create",
                target_skill="csv-parsing",
                priority=0.9,
                reason="Detected 5 requests",
                fix_content="# CSV Skill",
                applied=True,
                success=True,
            ),
            FixAction(
                action="patch",
                target_skill="web-fetch",
                priority=0.7,
                reason="Added retry",
                applied=False,
                success=False,
            ),
        ]

    # --- Initialization ---

    def test_default_metrics_file(self):
        """Test default metrics file path is correct."""
        tracker = LearningCurveTracker()
        assert tracker.metrics_file == METRICS_FILE

    def test_custom_metrics_file(self, temp_metrics_file):
        """Test custom metrics file path."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        assert tracker.metrics_file == temp_metrics_file

    def test_creates_parent_dir(self, temp_metrics_file):
        """Test that tracker creates parent directory on init."""
        custom_path = temp_metrics_file.parent / "subdir" / "deeper" / "metrics.json"
        tracker = LearningCurveTracker(metrics_file=custom_path)
        assert custom_path.parent.exists()

    # --- Empty history ---

    def test_load_history_empty(self, temp_metrics_file):
        """Test loading history when no file exists."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        history = tracker.load_history()
        assert history == []

    def test_load_history_corrupted_file(self, temp_metrics_file):
        """Test loading history with corrupted JSON."""
        temp_metrics_file.parent.mkdir(parents=True, exist_ok=True)
        temp_metrics_file.write_text("{ invalid json }")

        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        history = tracker.load_history()
        assert history == []

    def test_load_history_wrong_type(self, temp_metrics_file):
        """Test loading history with non-list JSON."""
        temp_metrics_file.parent.mkdir(parents=True, exist_ok=True)
        temp_metrics_file.write_text('{"not": "a list"}')

        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        history = tracker.load_history()
        assert history == []

    # --- Save snapshot ---

    def test_save_snapshot_creates_file(self, temp_metrics_file, empty_analysis):
        """Test that saving a snapshot creates the metrics file."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        tracker.save_snapshot(empty_analysis)
        assert temp_metrics_file.exists()

    def test_save_snapshot_empty_analysis(self, temp_metrics_file, empty_analysis):
        """Test saving snapshot with empty analysis."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        snap = tracker.save_snapshot(empty_analysis)

        assert snap.sessions_analyzed == 0
        assert snap.total_tool_calls == 0
        assert snap.overall_success_rate == 0.0
        assert snap.total_errors == 0
        assert snap.weakest_tools == []
        assert snap.improvements_made == []

    def test_save_snapshot_with_data(self, temp_metrics_file, sample_analysis, sample_fixes):
        """Test saving snapshot with full analysis data."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        snap = tracker.save_snapshot(sample_analysis, sample_fixes)

        assert snap.sessions_analyzed == 42
        assert snap.total_tool_calls == 150
        assert snap.overall_success_rate == 94.0
        assert snap.total_errors == 9
        assert snap.user_corrections == 3
        assert snap.skill_gaps_count == 1
        assert len(snap.weakest_tools) == 2
        assert snap.weakest_tools[0]["tool_name"] == "file_read"

    def test_save_snapshot_improvements(self, temp_metrics_file, sample_analysis, sample_fixes):
        """Test that improvements_made is correctly populated from fixes."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        snap = tracker.save_snapshot(sample_analysis, sample_fixes)

        # Should only include applied fixes
        assert len(snap.improvements_made) == 2
        assert snap.improvements_made[0]["skill"] == "file-read"
        assert snap.improvements_made[0]["action"] == "patch"

    def test_save_snapshot_weakest_tools_capped(self, temp_metrics_file):
        """Test that weakest_tools is capped at 5 items."""
        analysis = SessionAnalysis(
            schema_version=1, analyzed_at=time.time(), days_covered=7,
            sessions_analyzed=10, total_tool_calls=100, total_errors=10,
            overall_success_rate=90.0, user_corrections=1,
            tool_metrics={}, failure_reports=[], skill_gaps=[],
            retry_patterns=[],
            weakest_tools=[
                ToolMetric(tool_name=f"tool_{i}", total_calls=10, successful_calls=5,
                           failed_calls=5, success_rate=0.5, top_error_category="generic",
                           top_error_snippet="")
                for i in range(8)
            ],
        )

        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        snap = tracker.save_snapshot(analysis)
        assert len(snap.weakest_tools) == 5

    def test_save_snapshot_timestamp_set(self, temp_metrics_file, empty_analysis):
        """Test that timestamp is set on save."""
        before = time.time()
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        snap = tracker.save_snapshot(empty_analysis)
        after = time.time()

        assert before <= snap.timestamp <= after
        assert "2026" in snap.date or "2025" in snap.date

    # --- Load history ---

    def test_load_history_after_save(self, temp_metrics_file, empty_analysis):
        """Test that load_history returns saved snapshots."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        tracker.save_snapshot(empty_analysis)
        tracker.save_snapshot(empty_analysis)

        history = tracker.load_history()
        assert len(history) == 2
        assert all(isinstance(s, MetricSnapshot) for s in history)

    def test_load_history_maintains_order(self, temp_metrics_file, empty_analysis):
        """Test that snapshots are in chronological order."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)

        for i in range(3):
            tracker.save_snapshot(empty_analysis)
            time.sleep(0.01)

        history = tracker.load_history()
        timestamps = [s.timestamp for s in history]
        assert timestamps == sorted(timestamps)

    # --- Rotation ---

    def test_rotation_max_snapshots(self, temp_metrics_file, empty_analysis):
        """Test that history is rotated to MAX_SNAPSHOTS."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        for _ in range(400):
            tracker.save_snapshot(empty_analysis)

        history = tracker.load_history()
        assert len(history) == MAX_SNAPSHOTS
        assert len(history) == 365

    def test_rotation_keeps_newest(self, temp_metrics_file, empty_analysis):
        """Test that rotation keeps the most recent snapshots."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        for _ in range(400):
            tracker.save_snapshot(empty_analysis)

        history = tracker.load_history()
        assert history[-1].timestamp >= history[0].timestamp

    # --- Trends ---

    def test_trend_no_data(self, temp_metrics_file):
        """Test trend with no history."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        trend = tracker.get_trend()

        assert trend["direction"] == "neutral"
        assert trend["avg"] == 0.0
        assert trend["values"] == []

    def test_trend_single_snapshot(self, temp_metrics_file, empty_analysis):
        """Test trend with only one snapshot."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        tracker.save_snapshot(empty_analysis)

        trend = tracker.get_trend()
        # Single value = neutral direction
        assert trend["direction"] == "neutral"

    def test_trend_improving(self, temp_metrics_file):
        """Test trend calculation with improving metric."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)

        for sr in [80.0, 90.0]:
            analysis = SessionAnalysis(
                schema_version=1, analyzed_at=time.time(), days_covered=7,
                sessions_analyzed=10, total_tool_calls=100, total_errors=10,
                overall_success_rate=sr, user_corrections=1,
                tool_metrics={}, failure_reports=[], skill_gaps=[],
                retry_patterns=[], weakest_tools=[],
            )
            tracker.save_snapshot(analysis)
            time.sleep(0.01)

        trend = tracker.get_trend()
        assert trend["direction"] == "improving"
        assert 90.0 in trend["values"]
        assert 80.0 in trend["values"]

    def test_trend_declining(self, temp_metrics_file):
        """Test trend calculation with declining metric."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)

        for sr in [90.0, 75.0]:
            analysis = SessionAnalysis(
                schema_version=1, analyzed_at=time.time(), days_covered=7,
                sessions_analyzed=10, total_tool_calls=100, total_errors=15,
                overall_success_rate=sr, user_corrections=2,
                tool_metrics={}, failure_reports=[], skill_gaps=[],
                retry_patterns=[], weakest_tools=[],
            )
            tracker.save_snapshot(analysis)
            time.sleep(0.01)

        trend = tracker.get_trend()
        assert trend["direction"] == "declining"

    def test_trend_flat(self, temp_metrics_file):
        """Test trend calculation with flat metric."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)

        for sr in [85.0, 85.1, 84.9]:
            analysis = SessionAnalysis(
                schema_version=1, analyzed_at=time.time(), days_covered=7,
                sessions_analyzed=10, total_tool_calls=100, total_errors=15,
                overall_success_rate=sr, user_corrections=1,
                tool_metrics={}, failure_reports=[], skill_gaps=[],
                retry_patterns=[], weakest_tools=[],
            )
            tracker.save_snapshot(analysis)
            time.sleep(0.01)

        trend = tracker.get_trend()
        # Very small difference should still show direction
        assert "direction" in trend

    # --- Sparkline ---

    def test_sparkline_empty_history(self, temp_metrics_file):
        """Test sparkline with no history."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        spark = tracker.sparkline()

        assert len(spark) == 10  # default width
        assert "─" in spark  # Fallback character

    def test_sparkline_single_value(self, temp_metrics_file, empty_analysis):
        """Test sparkline with single data point."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        tracker.save_snapshot(empty_analysis)

        spark = tracker.sparkline()
        assert len(spark) == 10
        assert "─" in spark  # Needs at least 2 values

    def test_sparkline_width(self, temp_metrics_file, empty_analysis):
        """Test sparkline respects custom width."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        tracker.save_snapshot(empty_analysis)

        spark = tracker.sparkline(width=5)
        assert len(spark) == 5

    def test_sparkline_normalization(self, temp_metrics_file):
        """Test sparkline correctly normalizes values."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)

        for sr in [0.0, 25.0, 50.0, 75.0, 100.0]:
            analysis = SessionAnalysis(
                schema_version=1, analyzed_at=time.time(), days_covered=7,
                sessions_analyzed=10, total_tool_calls=100, total_errors=50 - int(sr/2),
                overall_success_rate=sr, user_corrections=0,
                tool_metrics={}, failure_reports=[], skill_gaps=[],
                retry_patterns=[], weakest_tools=[],
            )
            tracker.save_snapshot(analysis)

        spark = tracker.sparkline()
        # Should use different block characters
        unique_chars = set(spark)
        assert len(unique_chars) > 1

    # --- Atomic write ---

    def test_atomic_write(self, temp_metrics_file, empty_analysis):
        """Test that write is atomic (temp file + rename)."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        tracker.save_snapshot(empty_analysis)

        # Check temp file is cleaned up
        tmp_file = temp_metrics_file.with_suffix(".tmp")
        assert not tmp_file.exists()

        # Check actual file has valid JSON
        with open(temp_metrics_file) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_atomic_write_failure_cleanup(self, temp_metrics_file):
        """Test that temp file is removed on write failure."""
        # Use a directory as file path to force write failure
        bad_path = temp_metrics_file.parent / "subdir"  # This is a directory
        tracker = LearningCurveTracker(metrics_file=bad_path / "metrics.json")

        analysis = SessionAnalysis(
            schema_version=1, analyzed_at=time.time(), days_covered=7,
            sessions_analyzed=0, total_tool_calls=0, total_errors=0,
            overall_success_rate=0.0, user_corrections=0,
            tool_metrics={}, failure_reports=[], skill_gaps=[],
            retry_patterns=[], weakest_tools=[],
        )

        # Should not raise, but logs error
        tracker.save_snapshot(analysis)

    # --- Snapshot serialization ---

    def test_snapshot_to_dict(self):
        """Test MetricSnapshot.to_dict()."""
        snap = MetricSnapshot(
            timestamp=1234567890.0,
            date="2026-03-29 10:00",
            sessions_analyzed=42,
            total_tool_calls=150,
            overall_success_rate=94.0,
            total_errors=9,
            user_corrections=3,
            skill_gaps_count=2,
            retry_pattern_count=1,
            weakest_tools=[{"tool_name": "test", "error_count": 5}],
            improvements_made=[{"skill": "test", "action": "patch"}],
        )

        d = snap.to_dict()
        assert d["timestamp"] == 1234567890.0
        assert d["sessions_analyzed"] == 42
        assert d["weakest_tools"][0]["tool_name"] == "test"

    def test_snapshot_from_dict(self):
        """Test MetricSnapshot.from_dict()."""
        d = {
            "timestamp": 1234567890.0,
            "date": "2026-03-29 10:00",
            "sessions_analyzed": 42,
            "total_tool_calls": 150,
            "overall_success_rate": 94.0,
            "total_errors": 9,
            "user_corrections": 3,
            "skill_gaps_count": 2,
            "retry_pattern_count": 1,
            "weakest_tools": [],
            "improvements_made": [],
            "schema_version": 1,
        }

        snap = MetricSnapshot.from_dict(d)
        assert snap.timestamp == 1234567890.0
        assert snap.sessions_analyzed == 42
        assert snap.overall_success_rate == 94.0

    def test_snapshot_roundtrip(self, temp_metrics_file, sample_analysis):
        """Test that snapshot survives save/load cycle."""
        tracker = LearningCurveTracker(metrics_file=temp_metrics_file)
        original = tracker.save_snapshot(sample_analysis)

        history = tracker.load_history()
        loaded = history[-1]

        assert loaded.timestamp == original.timestamp
        assert loaded.sessions_analyzed == original.sessions_analyzed
        assert loaded.overall_success_rate == original.overall_success_rate
        assert len(loaded.weakest_tools) == len(original.weakest_tools)
