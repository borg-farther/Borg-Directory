"""
Tests for borg/dojo/report_generator.py
"""

import time

import pytest

from borg.dojo.data_models import (
    FixAction,
    MetricSnapshot,
    SessionAnalysis,
    SkillGap,
    ToolMetric,
)
from borg.dojo.report_generator import ReportGenerator


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    @pytest.fixture
    def empty_analysis(self):
        """Create an empty SessionAnalysis."""
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
                top_error_snippet="No such file",
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
            total_errors=12,
            overall_success_rate=92.0,
            user_corrections=5,
            tool_metrics={},
            failure_reports=[],
            skill_gaps=[
                SkillGap(
                    capability="csv-parsing",
                    request_count=5,
                    session_ids=["s1", "s2", "s3", "s4", "s5"],
                    confidence=0.9,
                ),
                SkillGap(
                    capability="pdf-conversion",
                    request_count=3,
                    session_ids=["s6", "s7", "s8"],
                    confidence=0.85,
                    existing_skill="pdf-tools",
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
                reason="Added path validation before file operations",
                applied=True,
                success=True,
            ),
            FixAction(
                action="create",
                target_skill="csv-parsing",
                priority=0.9,
                reason="Detected 5 requests with no existing skill",
                applied=True,
                success=True,
            ),
            FixAction(
                action="patch",
                target_skill="web-fetch",
                priority=0.7,
                reason="Added retry with exponential backoff",
                applied=False,
                success=False,
            ),
        ]

    @pytest.fixture
    def sample_history(self):
        """Create sample metric history."""
        return [
            MetricSnapshot(
                timestamp=time.time() - 86400 * 3,
                date="2026-03-26 10:00",
                sessions_analyzed=30,
                total_tool_calls=100,
                overall_success_rate=88.0,
                total_errors=12,
                user_corrections=3,
                skill_gaps_count=2,
                retry_pattern_count=1,
            ),
            MetricSnapshot(
                timestamp=time.time() - 86400 * 2,
                date="2026-03-27 10:00",
                sessions_analyzed=35,
                total_tool_calls=120,
                overall_success_rate=90.0,
                total_errors=10,
                user_corrections=4,
                skill_gaps_count=2,
                retry_pattern_count=1,
            ),
            MetricSnapshot(
                timestamp=time.time() - 86400,
                date="2026-03-28 10:00",
                sessions_analyzed=40,
                total_tool_calls=140,
                overall_success_rate=91.0,
                total_errors=9,
                user_corrections=4,
                skill_gaps_count=1,
                retry_pattern_count=1,
            ),
        ]

    @pytest.fixture
    def report_gen(self):
        """Create a ReportGenerator instance."""
        return ReportGenerator()

    # --- Format routing ---

    def test_generate_cli(self, report_gen, empty_analysis):
        """Test CLI format is generated."""
        result = report_gen.generate(empty_analysis, fmt="cli")
        assert isinstance(result, str)
        assert "DOJO SESSION ANALYSIS REPORT" in result

    def test_generate_telegram(self, report_gen, empty_analysis):
        """Test Telegram format is generated."""
        result = report_gen.generate(empty_analysis, fmt="telegram")
        assert isinstance(result, str)
        assert "Dojo Analysis" in result

    def test_generate_discord(self, report_gen, empty_analysis):
        """Test Discord format is generated."""
        result = report_gen.generate(empty_analysis, fmt="discord")
        assert isinstance(result, str)
        assert "Dojo Session Analysis" in result

    def test_generate_unknown_format_defaults_to_cli(self, report_gen, empty_analysis):
        """Test unknown format defaults to CLI."""
        result = report_gen.generate(empty_analysis, fmt="unknown")
        assert "DOJO SESSION ANALYSIS REPORT" in result

    # --- Trend data helper ---

    def test_get_trend_data_empty(self, report_gen):
        """Test _get_trend_data with empty history."""
        result = report_gen._get_trend_data([], "overall_success_rate")
        assert result["direction"] == "neutral"
        assert result["avg"] == 0.0
        assert result["values"] == []

    def test_get_trend_data_single_value(self, report_gen):
        """Test _get_trend_data with single value."""
        history = [
            MetricSnapshot(
                timestamp=time.time(), date="2026-03-29 10:00",
                sessions_analyzed=10, total_tool_calls=100,
                overall_success_rate=90.0, total_errors=10,
                user_corrections=2, skill_gaps_count=1,
                retry_pattern_count=0,
            )
        ]
        result = report_gen._get_trend_data(history, "overall_success_rate")
        assert result["direction"] == "neutral"
        assert 90.0 in result["values"]

    def test_get_trend_data_improving(self, report_gen):
        """Test _get_trend_data with improving values."""
        history = [
            MetricSnapshot(
                timestamp=time.time() - 1000, date="2026-03-28 10:00",
                sessions_analyzed=10, total_tool_calls=100,
                overall_success_rate=80.0, total_errors=20,
                user_corrections=3, skill_gaps_count=2,
                retry_pattern_count=1,
            ),
            MetricSnapshot(
                timestamp=time.time(), date="2026-03-29 10:00",
                sessions_analyzed=10, total_tool_calls=100,
                overall_success_rate=95.0, total_errors=5,
                user_corrections=1, skill_gaps_count=0,
                retry_pattern_count=0,
            ),
        ]
        result = report_gen._get_trend_data(history, "overall_success_rate")
        assert result["direction"] == "improving"
        assert result["min"] == 80.0
        assert result["max"] == 95.0

    def test_get_trend_data_declining(self, report_gen):
        """Test _get_trend_data with declining values."""
        history = [
            MetricSnapshot(
                timestamp=time.time() - 1000, date="2026-03-28 10:00",
                sessions_analyzed=10, total_tool_calls=100,
                overall_success_rate=95.0, total_errors=5,
                user_corrections=1, skill_gaps_count=0,
                retry_pattern_count=0,
            ),
            MetricSnapshot(
                timestamp=time.time(), date="2026-03-29 10:00",
                sessions_analyzed=10, total_tool_calls=100,
                overall_success_rate=75.0, total_errors=25,
                user_corrections=5, skill_gaps_count=3,
                retry_pattern_count=2,
            ),
        ]
        result = report_gen._get_trend_data(history, "overall_success_rate")
        assert result["direction"] == "declining"

    # --- Sparkline helper ---

    def test_sparkline_from_values_empty(self, report_gen):
        """Test _sparkline_from_values with empty list."""
        result = report_gen._sparkline_from_values([])
        assert result == "─" * 10

    def test_sparkline_from_values_single(self, report_gen):
        """Test _sparkline_from_values with single value."""
        result = report_gen._sparkline_from_values([50.0])
        assert result == "─" * 10

    def test_sparkline_from_values_normalizes(self, report_gen):
        """Test _sparkline_from_values normalizes values."""
        result = report_gen._sparkline_from_values([0.0, 50.0, 100.0])
        # Should use different block characters
        assert len(result) >= 3
        # Check it uses the actual unicode blocks, not dashes
        assert "▁" in result or "▃" in result or "▅" in result

    def test_sparkline_from_values_all_same(self, report_gen):
        """Test _sparkline_from_values with identical values."""
        result = report_gen._sparkline_from_values([50.0, 50.0, 50.0])
        # All same value should use middle character
        unique = set(result)
        assert len(unique) == 1

    # --- CLI Report ---

    def test_cli_report_empty(self, report_gen, empty_analysis):
        """Test CLI report with empty analysis."""
        result = report_gen._cli_report(empty_analysis, [], [])
        assert "DOJO SESSION ANALYSIS REPORT" in result
        assert "0 sessions" in result
        assert "0.0%" in result

    def test_cli_report_with_data(self, report_gen, sample_analysis):
        """Test CLI report with populated analysis."""
        result = report_gen._cli_report(sample_analysis, [], [])
        assert "42 sessions" in result
        assert "92.0%" in result
        assert "12" in result  # errors
        assert "5" in result  # corrections

    def test_cli_report_weak_tools(self, report_gen, sample_analysis):
        """Test CLI report shows weakest tools."""
        result = report_gen._cli_report(sample_analysis, [], [])
        assert "TOP TOOL FAILURES" in result
        assert "file_read" in result
        assert "web_fetch" in result

    def test_cli_report_skill_gaps(self, report_gen, sample_analysis):
        """Test CLI report shows skill gaps."""
        result = report_gen._cli_report(sample_analysis, [], [])
        assert "SKILL GAPS" in result
        assert "csv-parsing" in result

    def test_cli_report_fixes(self, report_gen, sample_analysis, sample_fixes):
        """Test CLI report shows fixes."""
        result = report_gen._cli_report(sample_analysis, sample_fixes, [])
        assert "FIXES APPLIED" in result
        assert "file-read" in result
        assert "[OK]" in result

    def test_cli_report_fixes_failed(self, report_gen, sample_analysis, sample_fixes):
        """Test CLI report shows failed fixes."""
        result = report_gen._cli_report(sample_analysis, sample_fixes, [])
        assert "[FAIL]" in result
        assert "web-fetch" in result

    def test_cli_report_trend(self, report_gen, empty_analysis, sample_history):
        """Test CLI report shows trend with sparkline."""
        result = report_gen._cli_report(empty_analysis, [], sample_history)
        assert "TREND" in result
        assert "improving" in result
        assert "Sparkline:" in result

    # --- Telegram Report ---

    def test_telegram_report_header(self, report_gen, empty_analysis):
        """Test Telegram report header."""
        result = report_gen._telegram_report(empty_analysis, [], [])
        assert "🧠" in result
        assert "*Dojo Analysis*" in result

    def test_telegram_report_summary(self, report_gen, sample_analysis):
        """Test Telegram report shows summary."""
        result = report_gen._telegram_report(sample_analysis, [], [])
        assert "42" in result
        assert "92.0%" in result
        assert "✅" in result

    def test_telegram_report_weak_tools(self, report_gen, sample_analysis):
        """Test Telegram report shows weakest tools."""
        result = report_gen._telegram_report(sample_analysis, [], [])
        assert "📉" in result
        assert "file_read" in result
        assert "fails" in result

    def test_telegram_report_skill_gaps(self, report_gen, sample_analysis):
        """Test Telegram report shows skill gaps."""
        result = report_gen._telegram_report(sample_analysis, [], [])
        assert "🔍" in result
        assert "csv-parsing" in result
        assert "5x" in result

    def test_telegram_report_fixes(self, report_gen, sample_analysis, sample_fixes):
        """Test Telegram report shows fixes."""
        result = report_gen._telegram_report(sample_analysis, sample_fixes, [])
        assert "🔧" in result
        assert "applied" in result.lower()
        assert "file-read" in result

    def test_telegram_report_fixes_failed(self, report_gen, sample_analysis, sample_fixes):
        """Test Telegram report shows failed fixes."""
        result = report_gen._telegram_report(sample_analysis, sample_fixes, [])
        assert "⚠️" in result
        assert "failed" in result.lower()

    def test_telegram_report_trend(self, report_gen, empty_analysis, sample_history):
        """Test Telegram report shows trend."""
        result = report_gen._telegram_report(empty_analysis, [], sample_history)
        assert "📈" in result
        assert "Trend:" in result
        assert "improving" in result

    def test_telegram_report_low_success_emoji(self, report_gen):
        """Test Telegram report uses warning emoji for low success rate."""
        analysis = SessionAnalysis(
            schema_version=1, analyzed_at=time.time(), days_covered=7,
            sessions_analyzed=10, total_tool_calls=50, total_errors=20,
            overall_success_rate=60.0, user_corrections=5,
            tool_metrics={}, failure_reports=[], skill_gaps=[],
            retry_patterns=[], weakest_tools=[],
        )
        result = report_gen._telegram_report(analysis, [], [])
        assert "⚠️" in result

    # --- Discord Report ---

    def test_discord_report_header(self, report_gen, empty_analysis):
        """Test Discord report header."""
        result = report_gen._discord_report(empty_analysis, [], [])
        assert "🧠" in result
        assert "Dojo Session Analysis" in result

    def test_discord_report_stats(self, report_gen, sample_analysis):
        """Test Discord report shows stats."""
        result = report_gen._discord_report(sample_analysis, [], [])
        assert "92.0%" in result
        assert "12" in result  # errors
        assert "5" in result  # corrections

    def test_discord_report_weak_tools(self, report_gen, sample_analysis):
        """Test Discord report shows weakest tools."""
        result = report_gen._discord_report(sample_analysis, [], [])
        assert "📉" in result
        assert "Top Tool Failures" in result
        assert "file_read" in result

    def test_discord_report_skill_gaps(self, report_gen, sample_analysis):
        """Test Discord report shows skill gaps."""
        result = report_gen._discord_report(sample_analysis, [], [])
        assert "🔍" in result
        assert "Detected Skill Gaps" in result
        assert "csv-parsing" in result

    def test_discord_report_fixes(self, report_gen, sample_analysis, sample_fixes):
        """Test Discord report shows fixes."""
        result = report_gen._discord_report(sample_analysis, sample_fixes, [])
        assert "🔧" in result
        assert "Fixes Applied" in result
        assert "file-read" in result

    def test_discord_report_trend(self, report_gen, empty_analysis, sample_history):
        """Test Discord report shows trend."""
        result = report_gen._discord_report(empty_analysis, [], sample_history)
        assert "Trend:" in result
        assert "improving" in result

    # --- Edge cases ---

    def test_none_fixes(self, report_gen, sample_analysis):
        """Test report with None fixes."""
        result = report_gen.generate(sample_analysis, fixes=None)
        assert "DOJO SESSION ANALYSIS REPORT" in result

    def test_none_history(self, report_gen, sample_analysis):
        """Test report with None history."""
        result = report_gen.generate(sample_analysis, history=None)
        assert "DOJO SESSION ANALYSIS REPORT" in result

    def test_empty_fixes_list(self, report_gen, sample_analysis):
        """Test report with empty fixes list."""
        result = report_gen.generate(sample_analysis, fixes=[])
        assert "DOJO SESSION ANALYSIS REPORT" in result
        assert "FIXES APPLIED" not in result

    def test_empty_history_list(self, report_gen, sample_analysis):
        """Test report with empty history list."""
        result = report_gen.generate(sample_analysis, history=[])
        assert "DOJO SESSION ANALYSIS REPORT" in result
        assert "TREND" not in result

    def test_only_failed_fixes(self, report_gen, sample_analysis):
        """Test report when all fixes failed."""
        failed_fixes = [
            FixAction(
                action="patch",
                target_skill="test",
                priority=0.5,
                reason="Will fail",
                applied=True,
                success=False,
            )
        ]
        result = report_gen._cli_report(sample_analysis, failed_fixes, [])
        assert "[FAIL]" in result
        assert "Fixes Applied: 1" not in result

    def test_report_truncates_long_tool_name(self, report_gen):
        """Test that very long tool names don't break formatting."""
        analysis = SessionAnalysis(
            schema_version=1, analyzed_at=time.time(), days_covered=7,
            sessions_analyzed=10, total_tool_calls=50, total_errors=10,
            overall_success_rate=80.0, user_corrections=2,
            tool_metrics={}, failure_reports=[], skill_gaps=[],
            retry_patterns=[],
            weakest_tools=[
                ToolMetric(
                    tool_name="a" * 100,  # Very long name
                    total_calls=10,
                    successful_calls=8,
                    failed_calls=2,
                    success_rate=0.8,
                    top_error_category="generic",
                    top_error_snippet="Error",
                )
            ],
        )
        result = report_gen._cli_report(analysis, [], [])
        assert "DOJO SESSION ANALYSIS REPORT" in result
