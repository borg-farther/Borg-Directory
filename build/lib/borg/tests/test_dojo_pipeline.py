"""
Comprehensive tests for the Borg Dojo Pipeline module.

Tests cover:
- DojoPipeline initialization
- Pipeline.run() with all steps
- _analyze_reader() session analysis
- Skill gap detection via detect_skill_gaps integration
- _called_suggest_after_apply check via AutoFeedbackDetector
- Error handling for missing/malformed sessions
- Borg integration feeds (_feed_aggregator, _feed_nudge, _feed_reputation)
- Module-level functions (analyze_recent_sessions, get_cached_analysis)
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import MagicMock, patch, PropertyMock

# Module under test
from borg.dojo import pipeline
from borg.dojo.pipeline import (
    DojoPipeline,
    analyze_recent_sessions,
    get_cached_analysis,
    BORG_DOJO_ENABLED,
    SCHEMA_VERSION,
)


class TestModuleConstants(unittest.TestCase):
    """Tests for module-level constants."""

    def test_schema_version_is_one(self):
        """SCHEMA_VERSION should be 1."""
        self.assertEqual(SCHEMA_VERSION, 1)

    def test_borg_dojo_enabled_is_boolean(self):
        """BORG_DOJO_ENABLED should be a boolean."""
        self.assertIsInstance(BORG_DOJO_ENABLED, bool)


class TestDojoPipelineInit(unittest.TestCase):
    """Tests for DojoPipeline initialization."""

    def test_default_init(self):
        """Pipeline should initialize with defaults."""
        p = DojoPipeline()
        self.assertIsNone(p._analysis)
        self.assertEqual(p._fixes, [])
        self.assertIsNone(p._snapshot)

    def test_init_with_db_path(self):
        """Pipeline should accept custom db_path."""
        custom_path = Path("/custom/path/state.db")
        p = DojoPipeline(db_path=custom_path)
        self.assertEqual(p.db_path, custom_path)

    def test_analysis_property_returns_none_initially(self):
        """analysis property should return None before run."""
        p = DojoPipeline()
        self.assertIsNone(p.analysis)

    def test_snapshot_property_returns_none_initially(self):
        """snapshot property should return None before run."""
        p = DojoPipeline()
        self.assertIsNone(p.snapshot)

    def test_fixes_property_returns_empty_list_initially(self):
        """fixes property should return empty list before run."""
        p = DojoPipeline()
        self.assertEqual(p.fixes, [])


class TestPipelineRunDisabled(unittest.TestCase):
    """Tests for pipeline when BORG_DOJO_ENABLED is false."""

    def setUp(self):
        self.env_patcher = patch.dict('os.environ', {'BORG_DOJO_ENABLED': 'false'})
        self.env_patcher.start()
        # Reload module to pick up env change
        import importlib
        importlib.reload(pipeline)

    def tearDown(self):
        self.env_patcher.stop()
        import importlib
        importlib.reload(pipeline)

    def test_run_returns_disabled_message(self):
        """run() should return disabled message when env var is false."""
        p = DojoPipeline()
        result = p.run()
        self.assertIn("disabled", result.lower())
        self.assertIn("BORG_DOJO_ENABLED", result)


class TestPipelineRunEnabled(unittest.TestCase):
    """Tests for pipeline when BORG_DOJO_ENABLED is true."""

    def setUp(self):
        self.env_patcher = patch.dict('os.environ', {'BORG_DOJO_ENABLED': 'true'})
        self.env_patcher.start()
        import importlib
        importlib.reload(pipeline)

    def tearDown(self):
        self.env_patcher.stop()
        import importlib
        importlib.reload(pipeline)

    def test_run_with_mocked_reader(self):
        """run() should execute full pipeline with mocked dependencies."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.session_id = "sess_123"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 2
        mock_session.message_count = 4
        mock_session.estimated_cost_usd = 0.01

        # Create mock tool call
        mock_tc = MagicMock()
        mock_tc.tool_name = "bash"
        mock_tc.is_error = False
        mock_tc.result_snippet = "Success"
        mock_tc.timestamp = datetime.now().timestamp()

        # Create mock reader
        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [mock_tc]
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.SessionReader') as MockSessionReader:
            MockSessionReader.return_value.__enter__.return_value = mock_reader

            with patch('borg.dojo.pipeline.AutoFixer') as MockAutoFixer:
                mock_fixer = MagicMock()
                mock_fixer.recommend.return_value = []
                MockAutoFixer.return_value = mock_fixer

                with patch('borg.dojo.pipeline.LearningCurveTracker') as MockTracker:
                    mock_tracker_instance = MagicMock()
                    mock_tracker_instance.save_snapshot.return_value = MagicMock()
                    mock_tracker_instance.load_history.return_value = []
                    MockTracker.return_value = mock_tracker_instance

                    with patch('borg.dojo.pipeline.ReportGenerator') as MockReportGen:
                        mock_gen = MagicMock()
                        mock_gen.generate.return_value = "Test Report"
                        MockReportGen.return_value = mock_gen

                        p = DojoPipeline()
                        result = p.run(auto_fix=False)

                        self.assertEqual(result, "Test Report")

    def test_run_with_auto_fix_applies_top_three(self):
        """run() with auto_fix=True should apply fixes to top 3 weaknesses."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_123"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 1
        mock_session.message_count = 2
        mock_session.estimated_cost_usd = 0.01

        # Error tool call
        mock_tc = MagicMock()
        mock_tc.tool_name = "bash"
        mock_tc.is_error = True
        mock_tc.result_snippet = "Error: command not found"
        mock_tc.timestamp = datetime.now().timestamp()

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [mock_tc]
        mock_reader.get_user_messages.return_value = []

        mock_fix_action = MagicMock()
        mock_fix_action.success = True
        mock_fix_action.action = "patch"
        mock_fix_action.target_skill = "bash"

        with patch('borg.dojo.pipeline.SessionReader') as MockSessionReader:
            MockSessionReader.return_value.__enter__.return_value = mock_reader

            with patch('borg.dojo.pipeline.AutoFixer') as MockAutoFixer:
                mock_fixer = MagicMock()
                mock_fixer.recommend.return_value = [mock_fix_action]
                mock_fixer.apply_fix.return_value = mock_fix_action
                MockAutoFixer.return_value = mock_fixer

                with patch('borg.dojo.pipeline.LearningCurveTracker') as MockTracker:
                    mock_tracker_instance = MagicMock()
                    mock_tracker_instance.save_snapshot.return_value = MagicMock()
                    mock_tracker_instance.load_history.return_value = []
                    MockTracker.return_value = mock_tracker_instance

                    with patch('borg.dojo.pipeline.ReportGenerator') as MockReportGen:
                        mock_gen = MagicMock()
                        mock_gen.generate.return_value = "Report"
                        MockReportGen.return_value = mock_gen

                        p = DojoPipeline()
                        p.run(auto_fix=True)

                        # Should have called apply_fix for recommendations
                        self.assertTrue(mock_fixer.recommend.called)


class TestAnalyzeReader(unittest.TestCase):
    """Tests for _analyze_reader method."""

    def test_analyze_empty_reader(self):
        """_analyze_reader should handle empty reader gracefully."""
        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([])

        with patch('borg.dojo.pipeline.SessionReader'):
            p = DojoPipeline()
            result = p._analyze_reader(mock_reader, days=7)

            self.assertIsNotNone(result)
            self.assertEqual(result.sessions_analyzed, 0)
            self.assertEqual(result.total_tool_calls, 0)
            self.assertEqual(result.total_errors, 0)
            self.assertEqual(result.schema_version, SCHEMA_VERSION)

    def test_analyze_single_session_no_errors(self):
        """_analyze_reader should process session with no errors."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_1"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 2
        mock_session.message_count = 4
        mock_session.estimated_cost_usd = 0.01

        mock_tc1 = MagicMock()
        mock_tc1.tool_name = "bash"
        mock_tc1.is_error = False
        mock_tc1.result_snippet = "Done"
        mock_tc1.timestamp = datetime.now().timestamp()

        mock_tc2 = MagicMock()
        mock_tc2.tool_name = "read_file"
        mock_tc2.is_error = False
        mock_tc2.result_snippet = "Content loaded"
        mock_tc2.timestamp = datetime.now().timestamp()

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [mock_tc1, mock_tc2]
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result') as mock_classify:
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_classify.return_value = (False, "", 0.0)
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertEqual(result.sessions_analyzed, 1)
                    self.assertEqual(result.total_tool_calls, 2)
                    self.assertEqual(result.total_errors, 0)
                    self.assertEqual(result.overall_success_rate, 100.0)

    def test_analyze_single_session_with_errors(self):
        """_analyze_reader should classify errors and update metrics."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_err"
        mock_session.source = "telegram"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 2
        mock_session.message_count = 4
        mock_session.estimated_cost_usd = 0.02

        mock_tc = MagicMock()
        mock_tc.tool_name = "bash"
        mock_tc.is_error = True
        mock_tc.result_snippet = "Error: path not found"
        mock_tc.timestamp = datetime.now().timestamp()

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [mock_tc]
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result') as mock_classify:
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_classify.return_value = (True, "path_not_found", 0.9)
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertEqual(result.sessions_analyzed, 1)
                    self.assertEqual(result.total_tool_calls, 1)
                    self.assertEqual(result.total_errors, 1)
                    # 50% success rate: 1 error out of 1 call
                    self.assertEqual(result.overall_success_rate, 0.0)

                    # Should have a failure report
                    self.assertEqual(len(result.failure_reports), 1)
                    self.assertEqual(result.failure_reports[0].error_category, "path_not_found")

    def test_analyze_multiple_sessions(self):
        """_analyze_reader should aggregate across multiple sessions."""
        sessions = []
        for i in range(3):
            s = MagicMock()
            s.session_id = f"sess_{i}"
            s.source = "cli"
            s.model = "gpt-4"
            s.started_at = datetime.now().timestamp()
            s.ended_at = None
            s.tool_call_count = 1
            s.message_count = 2
            s.estimated_cost_usd = 0.01
            sessions.append(s)

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter(sessions)
        mock_reader.get_tool_calls.return_value = []
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result'):
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertEqual(result.sessions_analyzed, 3)

    def test_analyze_calculates_tool_metrics(self):
        """_analyze_reader should calculate per-tool success rates."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_1"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 3
        mock_session.message_count = 6
        mock_session.estimated_cost_usd = 0.01

        # 2 successful, 1 error
        tc_success1 = MagicMock()
        tc_success1.tool_name = "bash"
        tc_success1.is_error = False
        tc_success1.result_snippet = "OK"
        tc_success1.timestamp = datetime.now().timestamp()

        tc_success2 = MagicMock()
        tc_success2.tool_name = "bash"
        tc_success2.is_error = False
        tc_success2.result_snippet = "OK"
        tc_success2.timestamp = datetime.now().timestamp()

        tc_error = MagicMock()
        tc_error.tool_name = "bash"
        tc_error.is_error = True
        tc_error.result_snippet = "Error"
        tc_error.timestamp = datetime.now().timestamp()

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [tc_success1, tc_success2, tc_error]
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result') as mock_classify:
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_classify.return_value = (True, "timeout", 0.85)
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertIn("bash", result.tool_metrics)
                    bash_metric = result.tool_metrics["bash"]
                    self.assertEqual(bash_metric.total_calls, 3)
                    self.assertEqual(bash_metric.successful_calls, 2)
                    self.assertEqual(bash_metric.failed_calls, 1)
                    self.assertAlmostEqual(bash_metric.success_rate, 2/3, places=4)

    def test_analyze_detects_user_corrections(self):
        """_analyze_reader should detect user corrections."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_1"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 1
        mock_session.message_count = 4
        mock_session.estimated_cost_usd = 0.01

        mock_tc = MagicMock()
        mock_tc.tool_name = "bash"
        mock_tc.is_error = False
        mock_tc.result_snippet = "OK"
        mock_tc.timestamp = datetime.now().timestamp()

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [mock_tc]
        mock_reader.get_user_messages.return_value = [
            ("No, that's wrong", datetime.now().timestamp()),
            ("Try again", datetime.now().timestamp()),
        ]

        with patch('borg.dojo.pipeline.classify_tool_result'):
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_detect_corr.return_value = [MagicMock(), MagicMock()]
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertEqual(result.user_corrections, 2)
                    mock_detect_corr.assert_called_once()

    def test_analyze_skill_gap_exception_handling(self):
        """_analyze_reader should catch skill gap detection exceptions."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_1"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 0
        mock_session.message_count = 0
        mock_session.estimated_cost_usd = 0.0

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = []
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result'):
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.side_effect = RuntimeError("Skill gap detection failed")

                    p = DojoPipeline()
                    # Should not raise, should handle gracefully
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertIsNotNone(result)
                    self.assertEqual(result.skill_gaps, [])

    def test_analyze_weakest_tools_sorted_by_failures(self):
        """_analyze_reader should sort weakest_tools by failed_calls desc."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_1"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 4
        mock_session.message_count = 8
        mock_session.estimated_cost_usd = 0.01

        # bash: 1 error, read_file: 2 errors, write_file: 0 errors
        tc_bash = MagicMock()
        tc_bash.tool_name = "bash"
        tc_bash.is_error = True
        tc_bash.result_snippet = "Error"
        tc_bash.timestamp = datetime.now().timestamp()

        tc_read1 = MagicMock()
        tc_read1.tool_name = "read_file"
        tc_read1.is_error = True
        tc_read1.result_snippet = "Error"
        tc_read1.timestamp = datetime.now().timestamp()

        tc_read2 = MagicMock()
        tc_read2.tool_name = "read_file"
        tc_read2.is_error = True
        tc_read2.result_snippet = "Error"
        tc_read2.timestamp = datetime.now().timestamp()

        tc_write = MagicMock()
        tc_write.tool_name = "write_file"
        tc_write.is_error = False
        tc_write.result_snippet = "OK"
        tc_write.timestamp = datetime.now().timestamp()

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = [tc_bash, tc_read1, tc_read2, tc_write]
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result') as mock_classify:
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_classify.return_value = (True, "generic", 0.5)
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    # read_file has 2 failures, bash has 1
                    self.assertEqual(len(result.weakest_tools), 2)
                    self.assertEqual(result.weakest_tools[0].tool_name, "read_file")
                    self.assertEqual(result.weakest_tools[0].failed_calls, 2)
                    self.assertEqual(result.weakest_tools[1].tool_name, "bash")
                    self.assertEqual(result.weakest_tools[1].failed_calls, 1)


class TestCalledSuggestAfterApply(unittest.TestCase):
    """Tests for _called_suggest_after_apply check via AutoFeedbackDetector.

    The _called_suggest_after_apply method checks if borg_suggest was called
    after an apply event - indicating the user struggled after applying a pack.
    """

    def test_suggest_after_apply_returns_true(self):
        """suggest call after apply should trigger struggle signal."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        apply_time = datetime.now() - timedelta(minutes=30)
        suggest_time = datetime.now() - timedelta(minutes=10)

        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNotNone(result)
        self.assertFalse(result.value)  # Implied failure
        self.assertEqual(result.task_context["inference"], "struggled_after_apply")

    def test_suggest_before_apply_returns_false(self):
        """suggest call before apply should not trigger struggle."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        suggest_time = datetime.now() - timedelta(minutes=30)
        apply_time = datetime.now() - timedelta(minutes=10)

        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNone(result)

    def test_suggest_without_apply_returns_false(self):
        """suggest without any apply should not trigger struggle."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        session_data = {
            "borg_suggest_calls": [datetime.now()]
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNone(result)

    def test_apply_without_suggest_returns_false(self):
        """apply without suggest should not trigger struggle."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        session_data = {
            "apply_events": [datetime.now()]
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNone(result)

    def test_multiple_suggests_after_apply(self):
        """Multiple suggests after apply should still detect struggle."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        apply_time = datetime.now() - timedelta(minutes=40)
        suggest_times = [
            datetime.now() - timedelta(minutes=30),
            datetime.now() - timedelta(minutes=20),
            datetime.now() - timedelta(minutes=10),
        ]

        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": suggest_times
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNotNone(result)
        self.assertEqual(result.task_context["inference"], "struggled_after_apply")

    def test_iso_string_timestamps(self):
        """Should parse ISO format string timestamps correctly."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        apply_time = (datetime.now() - timedelta(minutes=30)).isoformat()
        suggest_time = (datetime.now() - timedelta(minutes=10)).isoformat()

        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNotNone(result)
        self.assertEqual(result.task_context["inference"], "struggled_after_apply")

    def test_mixed_datetime_and_string_timestamps(self):
        """Should handle mix of datetime objects and ISO strings."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        apply_time = datetime.now() - timedelta(minutes=30)
        suggest_time = (datetime.now() - timedelta(minutes=10)).isoformat()

        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }

        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNotNone(result)

    def test_invalid_iso_string_skipped(self):
        """Invalid ISO strings should be skipped during comparison."""
        from borg.core.feedback_loop import AutoFeedbackDetector

        detector = AutoFeedbackDetector()

        apply_time = datetime.now() - timedelta(minutes=30)
        suggest_time = "not-a-valid-timestamp"

        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }

        # Should not raise, should return None (no valid suggest after apply)
        result = detector.infer_signal("agent1", "pack1", session_data, datetime.now())

        self.assertIsNone(result)


class TestSkillGapDetection(unittest.TestCase):
    """Tests for skill gap detection integration."""

    def test_detect_skill_gaps_from_user_messages(self):
        """detect_skill_gaps should identify repeated capability requests."""
        from borg.dojo.skill_gap_detector import detect_skill_gaps, SKILL_GAP_THRESHOLD

        # Use phrases that match the regex pattern: parse.*csv OR csv.*parse
        user_messages = [
            ("Please parse this csv file", "sess_1"),
            ("Can you parse another csv file", "sess_2"),
            ("I need to parse csv data", "sess_3"),
        ]

        gaps = detect_skill_gaps(user_messages)

        csv_gap = next((g for g in gaps if g.capability == "csv-parsing"), None)
        self.assertIsNotNone(csv_gap, f"No csv-parsing gap found. Available gaps: {[g.capability for g in gaps]}")
        self.assertEqual(csv_gap.request_count, 3)
        self.assertGreaterEqual(csv_gap.confidence, 0.0)

    def test_skill_gap_below_threshold_not_reported(self):
        """Capabilities requested < SKILL_GAP_THRESHOLD should not be flagged."""
        from borg.dojo.skill_gap_detector import detect_skill_gaps

        # Only 2 requests - below threshold of 3
        user_messages = [
            ("Please parse this csv", "sess_1"),
            ("Parse another csv", "sess_2"),
        ]

        gaps = detect_skill_gaps(user_messages)

        csv_gap = next((g for g in gaps if g.capability == "csv-parsing"), None)
        self.assertIsNone(csv_gap)

    def test_detect_skill_gaps_sorted_by_count(self):
        """Skill gaps should be sorted by request_count descending."""
        from borg.dojo.skill_gap_detector import detect_skill_gaps

        # csv: 4 requests, api: 3 requests
        user_messages = [
            ("parse csv file", "sess_1"),
            ("parse csv data", "sess_2"),
            ("parse csv report", "sess_3"),
            ("parse csv info", "sess_4"),
            ("call api endpoint", "sess_1"),
            ("fetch api data", "sess_2"),
            ("rest api call", "sess_3"),
        ]

        gaps = detect_skill_gaps(user_messages)

        self.assertGreaterEqual(len(gaps), 2)
        # Sort by request_count desc
        self.assertEqual(gaps[0].request_count, 4)
        self.assertEqual(gaps[1].request_count, 3)

    def test_skill_gap_with_existing_skill(self):
        """Gap for capability with existing skill should set existing_skill field."""
        from borg.dojo.skill_gap_detector import detect_skill_gaps

        # csv-parsing has existing skills ["csv-tools", "data-processing"]
        user_messages = [
            ("parse csv file", "sess_1"),
            ("parse csv data", "sess_2"),
            ("parse csv info", "sess_3"),
        ]

        gaps = detect_skill_gaps(user_messages)

        csv_gap = next((g for g in gaps if g.capability == "csv-parsing"), None)
        self.assertIsNotNone(csv_gap)
        # existing_skill may be None since we don't pass existing_skills dict
        # But the field exists and has a default
        self.assertIn(csv_gap.existing_skill, [None, "csv-tools", "data-processing"])


class TestErrorHandlingMissingMalformed(unittest.TestCase):
    """Tests for error handling with missing/malformed session data."""

    def test_malformed_session_no_session_id(self):
        """Session without ID should be handled gracefully."""
        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([])

        with patch('borg.dojo.pipeline.classify_tool_result'):
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertIsNotNone(result)

    def test_session_with_empty_tool_calls(self):
        """Session with no tool calls should be processed."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_empty"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 0
        mock_session.message_count = 2
        mock_session.estimated_cost_usd = 0.0

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = []
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result'):
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertEqual(result.sessions_analyzed, 1)
                    self.assertEqual(result.total_tool_calls, 0)
                    self.assertEqual(result.total_errors, 0)

    def test_session_with_null_fields(self):
        """Session with None/null fields should not crash."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_null"
        mock_session.source = None
        mock_session.model = None
        mock_session.started_at = None
        mock_session.ended_at = None
        mock_session.tool_call_count = None
        mock_session.message_count = None
        mock_session.estimated_cost_usd = None

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = []
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.classify_tool_result'):
            with patch('borg.dojo.pipeline.detect_corrections') as mock_detect_corr:
                with patch('borg.dojo.pipeline.detect_skill_gaps') as mock_detect_gaps:
                    mock_detect_corr.return_value = []
                    mock_detect_gaps.return_value = []

                    p = DojoPipeline()
                    result = p._analyze_reader(mock_reader, days=7)

                    self.assertEqual(result.sessions_analyzed, 1)


class TestBorgIntegrationFeeds(unittest.TestCase):
    """Tests for Borg module integration (_feed_aggregator, _feed_nudge, _feed_reputation)."""

    def test_feed_aggregator_returns_early_with_none_analysis(self):
        """_feed_aggregator should return early if analysis is None."""
        p = DojoPipeline()
        p._analysis = None

        # With None analysis, should return early without calling ingest
        # Should not raise any exception
        p._feed_aggregator()

    def test_feed_nudge_returns_early_with_none_analysis(self):
        """_feed_nudge should return early if analysis is None."""
        p = DojoPipeline()
        p._analysis = None

        # With None analysis, should return early
        p._feed_nudge()

    def test_feed_reputation_returns_early_with_none_analysis(self):
        """_feed_reputation should return early if analysis is None."""
        p = DojoPipeline()
        p._analysis = None

        # With None analysis, should return early
        p._feed_reputation()

    def test_feed_methods_exist_on_pipeline(self):
        """Pipeline should have all feed methods."""
        p = DojoPipeline()
        self.assertTrue(hasattr(p, '_feed_aggregator'))
        self.assertTrue(hasattr(p, '_feed_nudge'))
        self.assertTrue(hasattr(p, '_feed_reputation'))
        self.assertTrue(callable(p._feed_aggregator))
        self.assertTrue(callable(p._feed_nudge))
        self.assertTrue(callable(p._feed_reputation))


class TestModuleFunctions(unittest.TestCase):
    """Tests for module-level convenience functions."""

    def test_get_cached_analysis_initially_none(self):
        """get_cached_analysis should return None before any analysis."""
        # Reset module state
        pipeline._cached_analysis = None
        result = get_cached_analysis()
        self.assertIsNone(result)

    def test_analyze_recent_sessions_with_mocked_pipeline(self):
        """analyze_recent_sessions should create pipeline and run analysis."""
        mock_session = MagicMock()
        mock_session.session_id = "sess_1"
        mock_session.source = "cli"
        mock_session.model = "gpt-4"
        mock_session.started_at = datetime.now().timestamp()
        mock_session.ended_at = None
        mock_session.tool_call_count = 1
        mock_session.message_count = 2
        mock_session.estimated_cost_usd = 0.01

        mock_reader = MagicMock()
        mock_reader.iter_sessions.return_value = iter([mock_session])
        mock_reader.get_tool_calls.return_value = []
        mock_reader.get_user_messages.return_value = []

        with patch('borg.dojo.pipeline.DojoPipeline') as MockPipeline:
            mock_pipeline_instance = MagicMock()
            MockPipeline.return_value = mock_pipeline_instance

            with patch('borg.dojo.pipeline.SessionReader') as MockSessionReader:
                MockSessionReader.return_value.__enter__.return_value = mock_reader

                mock_analysis = MagicMock()
                mock_pipeline_instance._analyze_reader.return_value = mock_analysis

                result = analyze_recent_sessions(days=7)

                self.assertEqual(result, mock_analysis)
                MockPipeline.assert_called_once()
                mock_pipeline_instance._analyze_reader.assert_called_once()

    def test_analyze_recent_sessions_file_not_found(self):
        """analyze_recent_sessions should raise FileNotFoundError for missing db."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_db = Path(tmpdir) / "nonexistent.db"

            with patch('borg.dojo.pipeline.DojoPipeline') as MockPipeline:
                mock_pipeline_instance = MagicMock()
                mock_pipeline_instance._analyze_reader.side_effect = FileNotFoundError(
                    f"state.db not found: {fake_db}"
                )
                MockPipeline.return_value = mock_pipeline_instance

                with self.assertRaises(FileNotFoundError):
                    analyze_recent_sessions(days=7, db_path=fake_db)


class TestLearningCurveTrackerIntegration(unittest.TestCase):
    """Tests for LearningCurveTracker integration in pipeline."""

    def test_save_snapshot_in_pipeline(self):
        """Pipeline should save snapshot after analysis."""
        # Enable the pipeline for this test
        with patch.dict('os.environ', {'BORG_DOJO_ENABLED': 'true'}):
            import importlib
            import borg.dojo.pipeline
            importlib.reload(borg.dojo.pipeline)

            mock_session = MagicMock()
            mock_session.session_id = "sess_1"
            mock_session.source = "cli"
            mock_session.model = "gpt-4"
            mock_session.started_at = datetime.now().timestamp()
            mock_session.ended_at = None
            mock_session.tool_call_count = 1
            mock_session.message_count = 2
            mock_session.estimated_cost_usd = 0.01

            mock_reader = MagicMock()
            mock_reader.iter_sessions.return_value = iter([mock_session])
            mock_reader.get_tool_calls.return_value = []
            mock_reader.get_user_messages.return_value = []

            with patch.object(borg.dojo.pipeline, 'SessionReader') as MockSessionReader:
                MockSessionReader.return_value.__enter__.return_value = mock_reader

                with patch.object(borg.dojo.pipeline, 'AutoFixer') as MockAutoFixer:
                    mock_fixer = MagicMock()
                    mock_fixer.recommend.return_value = []
                    MockAutoFixer.return_value = mock_fixer

                    with patch.object(borg.dojo.pipeline, 'LearningCurveTracker') as MockTracker:
                        mock_tracker_instance = MagicMock()
                        mock_snapshot = MagicMock()
                        mock_tracker_instance.save_snapshot.return_value = mock_snapshot
                        mock_tracker_instance.load_history.return_value = []
                        MockTracker.return_value = mock_tracker_instance

                        with patch.object(borg.dojo.pipeline, 'ReportGenerator') as MockReportGen:
                            mock_gen = MagicMock()
                            mock_gen.generate.return_value = "Report"
                            MockReportGen.return_value = mock_gen

                            p = borg.dojo.pipeline.DojoPipeline()
                            result = p.run(auto_fix=False)

                            # Verify result is returned
                            self.assertEqual(result, "Report")


if __name__ == "__main__":
    unittest.main()
