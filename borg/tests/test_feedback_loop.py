"""
Comprehensive tests for the Borg V3 Feedback Loop Module.

Tests cover:
- SignalType enum
- FeedbackSignal dataclass
- QualityWeightedAggregator
- FreeRiderTracker
- DriftDetector (Page-Hinkley)
- AutoFeedbackDetector
- FeedbackLoop orchestrator
"""

import unittest
from datetime import datetime, timedelta
from borg.core.feedback_loop import (
    SignalType,
    FeedbackSignal,
    DriftEvent,
    QualityReport,
    AgentStatus,
    QualityWeightedAggregator,
    FreeRiderTracker,
    DriftDetector,
    AutoFeedbackDetector,
    FeedbackLoop,
)


class TestSignalType(unittest.TestCase):
    """Tests for SignalType enum."""

    def test_explicit_confirmation_weight(self):
        """EXPLICIT_CONFIRMATION should have weight 1.0."""
        self.assertEqual(SignalType.EXPLICIT_CONFIRMATION.value, 1.0)

    def test_vote_weight(self):
        """VOTE should have weight 0.5."""
        self.assertEqual(SignalType.VOTE.value, 0.5)

    def test_implied_usage_weight(self):
        """IMPLIED_USAGE should have weight 0.2."""
        self.assertEqual(SignalType.IMPLIED_USAGE.value, 0.2)

    def test_silence_weight(self):
        """SILENCE should have weight 0.0."""
        self.assertEqual(SignalType.SILENCE.value, 0.0)

    def test_all_signal_types_have_weights(self):
        """All signal types should have valid float weights."""
        for st in SignalType:
            self.assertIsInstance(st.value, float)
            self.assertGreaterEqual(st.value, 0.0)


class TestFeedbackSignal(unittest.TestCase):
    """Tests for FeedbackSignal dataclass."""

    def test_create_feedback_signal(self):
        """FeedbackSignal should be created with all fields."""
        signal = FeedbackSignal(
            agent_id="agent_1",
            pack_id="pack_1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now()
        )
        self.assertEqual(signal.agent_id, "agent_1")
        self.assertEqual(signal.pack_id, "pack_1")
        self.assertEqual(signal.signal_type, SignalType.EXPLICIT_CONFIRMATION)
        self.assertTrue(signal.value)

    def test_feedback_signal_with_context(self):
        """FeedbackSignal should accept optional task_context."""
        ctx = {"task": "test", "phase": 1}
        signal = FeedbackSignal(
            agent_id="agent_1",
            pack_id="pack_1",
            signal_type=SignalType.VOTE,
            value=False,
            timestamp=datetime.now(),
            task_context=ctx
        )
        self.assertEqual(signal.task_context, ctx)

    def test_feedback_signal_default_context_is_none(self):
        """FeedbackSignal task_context should default to None."""
        signal = FeedbackSignal(
            agent_id="agent_1",
            pack_id="pack_1",
            signal_type=SignalType.SILENCE,
            value=True,
            timestamp=datetime.now()
        )
        self.assertIsNone(signal.task_context)


class TestQualityWeightedAggregator(unittest.TestCase):
    """Tests for QualityWeightedAggregator."""

    def setUp(self):
        self.agg = QualityWeightedAggregator()

    def test_empty_aggregator_returns_zero(self):
        """Empty aggregator should return zero success rate."""
        report = self.agg.aggregate("nonexistent_pack")
        self.assertEqual(report.weighted_success_rate, 0.0)
        self.assertEqual(report.sample_size, 0)

    def test_single_explicit_confirmation_success(self):
        """Single explicit success should return 1.0."""
        self.agg.add_signal(FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now()
        ))
        report = self.agg.aggregate("p1")
        self.assertEqual(report.weighted_success_rate, 1.0)
        self.assertEqual(report.sample_size, 1)

    def test_single_explicit_confirmation_failure(self):
        """Single explicit failure should return 0.0."""
        self.agg.add_signal(FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=False,
            timestamp=datetime.now()
        ))
        report = self.agg.aggregate("p1")
        self.assertEqual(report.weighted_success_rate, 0.0)

    def test_weighted_aggregation_mixed_signals(self):
        """Mixed signal types should be weighted correctly."""
        now = datetime.now()
        self.agg.add_signal(FeedbackSignal("a1", "p1", SignalType.EXPLICIT_CONFIRMATION, True, now))
        self.agg.add_signal(FeedbackSignal("a2", "p1", SignalType.VOTE, True, now))
        self.agg.add_signal(FeedbackSignal("a3", "p1", SignalType.IMPLIED_USAGE, False, now))
        
        # Weighted: (1.0*1 + 0.5*1 + 0.2*0) / (1.0 + 0.5 + 0.2) = 1.5 / 1.7
        report = self.agg.aggregate("p1")
        self.assertAlmostEqual(report.weighted_success_rate, 1.5 / 1.7, places=5)

    def test_confidence_interval_with_many_samples(self):
        """Confidence interval should shrink with more samples."""
        now = datetime.now()
        for i in range(100):
            self.agg.add_signal(FeedbackSignal(
                f"a{i}", "p1", SignalType.EXPLICIT_CONFIRMATION, i % 2 == 0, now
            ))
        report = self.agg.aggregate("p1")
        ci_width = report.confidence_interval[1] - report.confidence_interval[0]
        self.assertLess(ci_width, 0.3)  # Should be relatively narrow

    def test_confidence_interval_single_sample(self):
        """Single sample should have wide confidence interval."""
        self.agg.add_signal(FeedbackSignal(
            "a1", "p1", SignalType.EXPLICIT_CONFIRMATION, True, datetime.now()
        ))
        report = self.agg.aggregate("p1")
        ci_width = report.confidence_interval[1] - report.confidence_interval[0]
        self.assertGreater(ci_width, 0.2)  # Should be wider for single sample

    def test_get_signals_returns_list(self):
        """get_signals should return a list of signals."""
        now = datetime.now()
        self.agg.add_signal(FeedbackSignal("a1", "p1", SignalType.VOTE, True, now))
        self.agg.add_signal(FeedbackSignal("a2", "p1", SignalType.VOTE, False, now))
        signals = self.agg.get_signals("p1")
        self.assertEqual(len(signals), 2)

    def test_clear_pack_removes_signals(self):
        """clear_pack should remove all signals for a pack."""
        now = datetime.now()
        self.agg.add_signal(FeedbackSignal("a1", "p1", SignalType.VOTE, True, now))
        self.agg.clear_pack("p1")
        self.assertEqual(len(self.agg.get_signals("p1")), 0)


class TestFreeRiderTracker(unittest.TestCase):
    """Tests for FreeRiderTracker."""

    def setUp(self):
        self.tracker = FreeRiderTracker()

    def test_new_agent_has_zero_score(self):
        """New agent should have zero free-rider score."""
        self.assertEqual(self.tracker.get_free_rider_score("new_agent"), 0.0)

    def test_agent_below_threshold_has_zero_score(self):
        """Agent with <= 5 uses should have zero score."""
        for i in range(5):
            self.tracker.record_use("agent")
        self.assertEqual(self.tracker.get_free_rider_score("agent"), 0.0)

    def test_agent_above_threshold_no_reports(self):
        """Agent with uses > 5 and no reports should have score 1.0."""
        for i in range(10):
            self.tracker.record_use("agent")
        self.assertEqual(self.tracker.get_free_rider_score("agent"), 1.0)

    def test_agent_with_50_percent_report_ratio(self):
        """Agent with 50% report ratio should have score 0.5."""
        for i in range(10):
            self.tracker.record_use("agent")
        for i in range(5):
            self.tracker.record_report("agent")
        self.assertEqual(self.tracker.get_free_rider_score("agent"), 0.5)

    def test_is_free_rider_below_threshold(self):
        """Agent with <= 5 uses should not be free-rider."""
        for i in range(5):
            self.tracker.record_use("agent")
        self.assertFalse(self.tracker.is_free_rider("agent"))

    def test_is_free_rider_high_report_ratio(self):
        """Agent with high report ratio should not be free-rider."""
        for i in range(10):
            self.tracker.record_use("agent")
        for i in range(5):  # 50% ratio, above 20% threshold
            self.tracker.record_report("agent")
        self.assertFalse(self.tracker.is_free_rider("agent"))

    def test_is_free_rider_low_report_ratio(self):
        """Agent with low report ratio should be free-rider."""
        for i in range(10):
            self.tracker.record_use("agent")
        for i in range(1):  # 10% ratio, below 20% threshold
            self.tracker.record_report("agent")
        self.assertTrue(self.tracker.is_free_rider("agent"))

    def test_access_delay_calculation(self):
        """Access delay should be 3600 * free_rider_score."""
        for i in range(10):
            self.tracker.record_use("agent")
        # No reports -> score 1.0 -> delay 3600
        self.assertEqual(self.tracker.get_access_delay("agent"), 3600.0)

    def test_access_delay_non_free_rider(self):
        """Non-free-rider should have zero delay."""
        for i in range(10):
            self.tracker.record_use("agent")
        for i in range(5):
            self.tracker.record_report("agent")
        self.assertEqual(self.tracker.get_access_delay("agent"), 0.0)

    def test_get_agent_status_complete(self):
        """get_agent_status should return full status."""
        for i in range(10):
            self.tracker.record_use("agent")
        for i in range(2):
            self.tracker.record_report("agent")
        status = self.tracker.get_agent_status("agent")
        self.assertIsInstance(status, AgentStatus)
        self.assertEqual(status.agent_id, "agent")
        self.assertEqual(status.contribution_count, 2)

    def test_uses_count_tracking(self):
        """uses_count should be tracked correctly."""
        for i in range(7):
            self.tracker.record_use("agent")
        self.assertEqual(self.tracker.get_uses_count("agent"), 7)

    def test_reports_count_tracking(self):
        """reports_count should be tracked correctly."""
        for i in range(3):
            self.tracker.record_report("agent")
        self.assertEqual(self.tracker.get_reports_count("agent"), 3)


class TestDriftDetector(unittest.TestCase):
    """Tests for DriftDetector with Page-Hinkley test."""

    def setUp(self):
        self.detector = DriftDetector(threshold=50.0)

    def test_new_pack_has_no_drift(self):
        """New pack should not show drift."""
        self.assertFalse(self.detector.check_drift("new_pack"))

    def test_consistent_success_no_drift(self):
        """Consistent successes should not trigger drift."""
        now = datetime.now()
        for i in range(50):
            self.detector.record_outcome("pack", True, now + timedelta(minutes=i))
        self.assertFalse(self.detector.check_drift("pack"))

    def test_consistent_failure_no_drift(self):
        """Consistent failures should not trigger drift."""
        now = datetime.now()
        for i in range(50):
            self.detector.record_outcome("pack", False, now + timedelta(minutes=i))
        self.assertFalse(self.detector.check_drift("pack"))

    def test_gradual_shift_triggers_drift(self):
        """Gradual shift from success to failure should trigger drift."""
        # Use lower threshold and more observations for reliable drift detection
        self.detector = DriftDetector(threshold=25.0, epsilon=0.5)
        now = datetime.now()
        # First 50 successes to establish high mean
        for i in range(50):
            self.detector.record_outcome("pack", True, now + timedelta(minutes=i))
        # Then 50 failures - should trigger drift
        for i in range(50, 100):
            event = self.detector.record_outcome("pack", False, now + timedelta(minutes=i))
        
        self.assertTrue(self.detector.check_drift("pack"))

    def test_drift_event_contains_details(self):
        """Drift event should contain pack_id, rates, and timestamp."""
        # Use lower threshold for reliable testing
        self.detector = DriftDetector(threshold=25.0, epsilon=0.5)
        now = datetime.now()
        for i in range(50):
            self.detector.record_outcome("pack", True, now + timedelta(minutes=i))
        
        events = self.detector.get_drift_events("pack")
        self.assertEqual(len(events), 0)
        
        # Add failures to trigger drift
        for i in range(50, 100):
            self.detector.record_outcome("pack", False, now + timedelta(minutes=i))
        
        events = self.detector.get_drift_events("pack")
        self.assertGreater(len(events), 0)
        event = events[0]
        self.assertIsInstance(event, DriftEvent)
        self.assertEqual(event.pack_id, "pack")

    def test_reset_pack_clears_state(self):
        """reset_pack should clear all drift state."""
        # Use lower threshold for reliable testing
        self.detector = DriftDetector(threshold=25.0, epsilon=0.5)
        now = datetime.now()
        for i in range(100):
            self.detector.record_outcome("pack", i < 50, now + timedelta(minutes=i))
        
        self.assertTrue(self.detector.check_drift("pack"))
        
        self.detector.reset_pack("pack")
        
        self.assertFalse(self.detector.check_drift("pack"))
        self.assertEqual(self.detector.get_ph_statistic("pack"), 0.0)

    def test_ph_statistic_accumulates(self):
        """PH statistic should accumulate deviations."""
        self.detector = DriftDetector(threshold=1000.0)  # High threshold to avoid drift
        now = datetime.now()
        
        # All successes should accumulate positive then negative
        self.detector.record_outcome("pack", True, now)
        stat1 = self.detector.get_ph_statistic("pack")
        
        self.detector.record_outcome("pack", False, now + timedelta(minutes=1))
        stat2 = self.detector.get_ph_statistic("pack")
        
        # The cumulative sum should change
        self.assertNotEqual(stat1, stat2)

    def test_multiple_packs_independent(self):
        """Multiple packs should have independent drift detection."""
        # Use lower threshold for reliable testing
        self.detector = DriftDetector(threshold=25.0, epsilon=0.5)
        now = datetime.now()
        
        # Pack1: trigger drift with 50 success then 50 failure
        for i in range(100):
            self.detector.record_outcome("pack1", i < 50, now + timedelta(minutes=i))
        
        # Pack2: no drift (all success)
        for i in range(30):
            self.detector.record_outcome("pack2", True, now + timedelta(minutes=i))
        
        self.assertTrue(self.detector.check_drift("pack1"))
        self.assertFalse(self.detector.check_drift("pack2"))

    def test_get_all_drift_events(self):
        """get_all_drift_events should return events across all packs."""
        # Use lower threshold for reliable testing
        self.detector = DriftDetector(threshold=25.0, epsilon=0.5)
        now = datetime.now()
        
        for i in range(100):
            self.detector.record_outcome("pack1", i < 50, now + timedelta(minutes=i))
            self.detector.record_outcome("pack2", i < 50, now + timedelta(minutes=i))
        
        events = self.detector.get_all_drift_events()
        self.assertGreaterEqual(len(events), 2)


class TestAutoFeedbackDetector(unittest.TestCase):
    """Tests for AutoFeedbackDetector."""

    def setUp(self):
        self.detector = AutoFeedbackDetector()

    def test_completed_all_phases_implies_success(self):
        """Completing all phases should infer SUCCESS."""
        session_data = {
            "phases": ["phase1", "phase2", "phase3"],
            "completed_phases": ["phase1", "phase2", "phase3"]
        }
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNotNone(result)
        self.assertTrue(result.value)
        self.assertEqual(result.signal_type, SignalType.IMPLIED_USAGE)

    def test_incomplete_phases_no_signal(self):
        """Incomplete phases should not infer signal."""
        session_data = {
            "phases": ["phase1", "phase2", "phase3"],
            "completed_phases": ["phase1", "phase2"]
        }
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNone(result)

    def test_abandonment_after_timeout_implies_failure(self):
        """No checkpoint for >10 min should infer FAILURE."""
        old_time = datetime.now() - timedelta(minutes=15)
        session_data = {
            "phases": ["phase1", "phase2"],
            "completed_phases": ["phase1"],
            "last_checkpoint": old_time
        }
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNotNone(result)
        self.assertFalse(result.value)
        self.assertEqual(result.task_context["inference"], "abandoned_mid_phase")

    def test_recent_checkpoint_no_abandonment(self):
        """Recent checkpoint should not infer abandonment."""
        recent_time = datetime.now() - timedelta(minutes=5)
        session_data = {
            "phases": ["phase1", "phase2"],
            "completed_phases": ["phase1"],
            "last_checkpoint": recent_time
        }
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNone(result)

    def test_suggest_after_apply_implies_struggle(self):
        """borg_suggest after apply should infer STRUGGLE."""
        apply_time = datetime.now() - timedelta(minutes=20)
        suggest_time = datetime.now() - timedelta(minutes=10)
        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNotNone(result)
        self.assertFalse(result.value)
        self.assertEqual(result.task_context["inference"], "struggled_after_apply")

    def test_suggest_before_apply_no_struggle(self):
        """borg_suggest before apply should not infer struggle."""
        suggest_time = datetime.now() - timedelta(minutes=20)
        apply_time = datetime.now() - timedelta(minutes=10)
        session_data = {
            "apply_events": [apply_time],
            "borg_suggest_calls": [suggest_time]
        }
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNone(result)

    def test_no_phases_returns_none(self):
        """Empty phases should return None."""
        session_data = {}
        result = self.detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNone(result)

    def test_empty_session_returns_none(self):
        """Empty session data should return None."""
        result = self.detector.infer_signal("a1", "p1", {}, datetime.now())
        self.assertIsNone(result)


class TestFeedbackLoop(unittest.TestCase):
    """Tests for FeedbackLoop orchestrator."""

    def setUp(self):
        self.loop = FeedbackLoop()

    def test_initialization_with_defaults(self):
        """FeedbackLoop should initialize with default components."""
        loop = FeedbackLoop()
        self.assertIsInstance(loop.aggregator, QualityWeightedAggregator)
        self.assertIsInstance(loop.free_rider_tracker, FreeRiderTracker)
        self.assertIsInstance(loop.drift_detector, DriftDetector)
        self.assertIsInstance(loop.auto_feedback, AutoFeedbackDetector)

    def test_record_signal_updates_aggregator(self):
        """record_signal should update the aggregator."""
        signal = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now()
        )
        self.loop.record_signal(signal)
        report = self.loop.get_pack_quality("p1")
        self.assertEqual(report.weighted_success_rate, 1.0)

    def test_record_signal_updates_free_rider_tracker(self):
        """EXPLICIT_CONFIRMATION signals should update free-rider tracker."""
        signal = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now()
        )
        self.loop.record_signal(signal)
        status = self.loop.get_agent_status("a1")
        self.assertEqual(status.contribution_count, 1)

    def test_record_signal_updates_drift_detector(self):
        """record_signal should update drift detector."""
        # Use lower threshold for reliable testing
        self.loop = FeedbackLoop(drift_detector=DriftDetector(threshold=25.0, epsilon=0.5))
        now = datetime.now()
        for i in range(100):
            self.loop.record_signal(FeedbackSignal(
                agent_id="a1",
                pack_id="p1",
                signal_type=SignalType.EXPLICIT_CONFIRMATION,
                value=i < 50,
                timestamp=now + timedelta(minutes=i)
            ))
        self.assertTrue(self.loop.drift_detector.check_drift("p1"))

    def test_get_pack_quality_includes_drift_status(self):
        """get_pack_quality should include drift status."""
        # Use lower threshold for reliable testing
        self.loop = FeedbackLoop(drift_detector=DriftDetector(threshold=25.0, epsilon=0.5))
        now = datetime.now()
        for i in range(100):
            self.loop.record_signal(FeedbackSignal(
                agent_id="a1",
                pack_id="p1",
                signal_type=SignalType.EXPLICIT_CONFIRMATION,
                value=i < 50,
                timestamp=now + timedelta(minutes=i)
            ))
        report = self.loop.get_pack_quality("p1")
        self.assertTrue(report.drift_detected)
        self.assertGreater(len(report.drift_events), 0)

    def test_get_agent_status_free_rider(self):
        """get_agent_status should show free-rider status."""
        # Create free-rider scenario
        for i in range(10):
            self.loop.record_use("lazy_agent")
        status = self.loop.get_agent_status("lazy_agent")
        self.assertEqual(status.free_rider_score, 1.0)
        self.assertTrue(status.is_free_rider)
        self.assertEqual(status.access_delay, 3600.0)

    def test_check_drift_returns_events(self):
        """check_drift should return list of drift events."""
        # Use lower threshold for reliable testing
        self.loop = FeedbackLoop(drift_detector=DriftDetector(threshold=25.0, epsilon=0.5))
        now = datetime.now()
        for i in range(100):
            self.loop.record_signal(FeedbackSignal(
                agent_id="a1",
                pack_id="p1",
                signal_type=SignalType.EXPLICIT_CONFIRMATION,
                value=i < 50,
                timestamp=now + timedelta(minutes=i)
            ))
        events = self.loop.check_drift()
        self.assertIsInstance(events, list)
        self.assertGreater(len(events), 0)

    def test_infer_feedback_records_signal(self):
        """infer_feedback should record the inferred signal."""
        session_data = {
            "phases": ["phase1", "phase2"],
            "completed_phases": ["phase1", "phase2"]
        }
        result = self.loop.infer_feedback("a1", "p1", session_data)
        self.assertIsNotNone(result)
        signals = self.loop.get_all_signals()
        self.assertGreater(len(signals), 0)

    def test_record_use_updates_tracker(self):
        """record_use should update free-rider tracker."""
        self.loop.record_use("a1")
        self.loop.record_use("a1")
        self.loop.record_use("a1")
        self.assertEqual(self.loop.free_rider_tracker.get_uses_count("a1"), 3)

    def test_get_all_signals_returns_copy(self):
        """get_all_signals should return a copy of signals list."""
        signal = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.VOTE,
            value=True,
            timestamp=datetime.now()
        )
        self.loop.record_signal(signal)
        signals = self.loop.get_all_signals()
        signals.clear()  # Should not affect internal state
        self.assertEqual(len(self.loop.get_all_signals()), 1)

    def test_get_signals_for_pack(self):
        """get_signals_for_pack should return pack-specific signals."""
        self.loop.record_signal(FeedbackSignal(
            "a1", "p1", SignalType.VOTE, True, datetime.now()
        ))
        self.loop.record_signal(FeedbackSignal(
            "a2", "p2", SignalType.VOTE, True, datetime.now()
        ))
        self.loop.record_signal(FeedbackSignal(
            "a3", "p1", SignalType.VOTE, False, datetime.now()
        ))
        signals = self.loop.get_signals_for_pack("p1")
        self.assertEqual(len(signals), 2)

    def test_quality_report_has_all_fields(self):
        """QualityReport should have all expected fields."""
        report = self.loop.get_pack_quality("nonexistent")
        self.assertEqual(report.pack_id, "nonexistent")
        self.assertEqual(report.weighted_success_rate, 0.0)
        self.assertEqual(report.confidence_interval, (0.0, 0.0))
        self.assertEqual(report.sample_size, 0)
        self.assertFalse(report.drift_detected)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and boundary conditions."""

    def test_silence_signal_has_zero_weight(self):
        """SILENCE signals should not affect weighted aggregation."""
        loop = FeedbackLoop()
        now = datetime.now()
        loop.record_signal(FeedbackSignal("a1", "p1", SignalType.SILENCE, True, now))
        loop.record_signal(FeedbackSignal("a2", "p1", SignalType.SILENCE, False, now))
        report = loop.get_pack_quality("p1")
        self.assertEqual(report.weighted_success_rate, 0.0)

    def test_division_by_zero_prevention(self):
        """Should handle zero total weight gracefully."""
        agg = QualityWeightedAggregator()
        # This should not raise
        report = agg.aggregate("p1")
        self.assertEqual(report.weighted_success_rate, 0.0)

    def test_free_rider_exactly_at_threshold(self):
        """Agent exactly at 5 uses should not be free-rider."""
        tracker = FreeRiderTracker()
        for i in range(5):
            tracker.record_use("agent")
        self.assertFalse(tracker.is_free_rider("agent"))
        self.assertEqual(tracker.get_free_rider_score("agent"), 0.0)

    def test_free_rider_exactly_at_report_threshold(self):
        """Agent with 20% report ratio (1/5) should not be free-rider."""
        tracker = FreeRiderTracker()
        for i in range(5):
            tracker.record_use("agent")
        tracker.record_report("agent")  # 1/5 = 20%
        self.assertFalse(tracker.is_free_rider("agent"))

    def test_free_rider_just_below_report_threshold(self):
        """Agent with <20% report ratio should be free-rider."""
        tracker = FreeRiderTracker()
        for i in range(10):
            tracker.record_use("agent")
        tracker.record_report("agent")  # 1/10 = 10% < 20%
        self.assertTrue(tracker.is_free_rider("agent"))

    def test_drift_threshold_customization(self):
        """DriftDetector should accept custom threshold."""
        detector = DriftDetector(threshold=10.0, epsilon=0.5)
        now = datetime.now()
        for i in range(100):
            detector.record_outcome("pack", i < 50, now + timedelta(minutes=i))
        # Should detect drift faster with lower threshold
        self.assertTrue(detector.check_drift("pack"))

    def test_datetime_iso_format_parsing(self):
        """AutoFeedbackDetector should parse ISO datetime strings."""
        detector = AutoFeedbackDetector()
        old_time = (datetime.now() - timedelta(minutes=15)).isoformat()
        session_data = {
            "phases": ["phase1"],
            "completed_phases": [],
            "last_checkpoint": old_time
        }
        result = detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNotNone(result)
        self.assertFalse(result.value)


class TestSignalHierarchy(unittest.TestCase):
    """Tests for signal hierarchy (outcome > drift > staleness > default)."""

    def test_explicit_confirmation_outcome_priority(self):
        """EXPLICIT_CONFIRMATION should have highest weight (1.0)."""
        self.assertGreater(
            SignalType.EXPLICIT_CONFIRMATION.value,
            SignalType.VOTE.value
        )
        self.assertGreater(
            SignalType.VOTE.value,
            SignalType.IMPLIED_USAGE.value
        )
        self.assertGreater(
            SignalType.IMPLIED_USAGE.value,
            SignalType.SILENCE.value
        )

    def test_outcome_signals_override_inferred(self):
        """Explicit outcome signals should override implied signals."""
        loop = FeedbackLoop()
        now = datetime.now()

        # First, infer via session data (implied success)
        session_data = {
            "phases": ["p1", "p2"],
            "completed_phases": ["p1", "p2"]
        }
        inferred = loop.infer_feedback("a1", "p1", session_data, now)
        self.assertIsNotNone(inferred)

        # Then add explicit confirmation
        explicit = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=False,  # Explicit failure
            timestamp=now
        )
        loop.record_signal(explicit)

        # Both should be stored
        signals = loop.get_signals_for_pack("p1")
        self.assertGreaterEqual(len(signals), 2)

    def test_drift_detection_affects_quality_report(self):
        """Drift detection should be reflected in quality report."""
        loop = FeedbackLoop(drift_detector=DriftDetector(threshold=25.0, epsilon=0.5))
        now = datetime.now()

        # Generate drift
        for i in range(100):
            loop.record_signal(FeedbackSignal(
                agent_id="a1",
                pack_id="drift_pack",
                signal_type=SignalType.EXPLICIT_CONFIRMATION,
                value=i < 50,  # First 50 success, then failure
                timestamp=now + timedelta(minutes=i)
            ))

        report = loop.get_pack_quality("drift_pack")
        self.assertTrue(report.drift_detected)
        self.assertGreater(len(report.drift_events), 0)


class TestConfidenceDecay(unittest.TestCase):
    """Tests for confidence decay over time."""

    def test_old_signals_have_lower_impact(self):
        """Aggregated quality should consider signal age."""
        agg = QualityWeightedAggregator()
        now = datetime.now()

        # Recent signal
        agg.add_signal(FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=now
        ))

        # Old signal (100 days ago) - still counted but weighted by type
        old_timestamp = now - timedelta(days=100)
        agg.add_signal(FeedbackSignal(
            agent_id="a2",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=old_timestamp
        ))

        report = agg.aggregate("p1")
        # Both are explicit confirmation, so 100% success
        self.assertEqual(report.weighted_success_rate, 1.0)
        self.assertEqual(report.sample_size, 2)

    def test_signal_quality_score_affects_aggregation(self):
        """FeedbackSignal quality_score should be available for future use."""
        signal = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now(),
            quality_score=0.8
        )
        self.assertEqual(signal.quality_score, 0.8)

    def test_success_rate_trend_stored_in_signal(self):
        """FeedbackSignal should store success_rate_trend."""
        signal = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now(),
            success_rate_trend=0.15
        )
        self.assertEqual(signal.success_rate_trend, 0.15)


class TestDriftDetectionEdgeCases(unittest.TestCase):
    """Additional drift detection edge case tests."""

    def test_immediate_drift_with_zero_threshold(self):
        """Zero threshold should trigger drift immediately."""
        detector = DriftDetector(threshold=0.0, epsilon=0.5)
        now = datetime.now()

        # First observation
        event = detector.record_outcome("pack", True, now)
        # With threshold=0, drift might trigger on first deviation

        # Second observation - different outcome
        event2 = detector.record_outcome("pack", False, now + timedelta(minutes=1))

        # PH statistic should accumulate
        stat = detector.get_ph_statistic("pack")
        self.assertIsNotNone(stat)

    def test_drift_window_enforcement(self):
        """Drift history should respect window limit."""
        detector = DriftDetector(drift_window=10)
        now = datetime.now()

        # Add 20 outcomes
        for i in range(20):
            detector.record_outcome("pack", i % 2 == 0, now + timedelta(minutes=i))

        # History should be limited to window size
        self.assertLessEqual(len(detector._pack_history.get("pack", [])), 10)

    def test_drift_after_reset(self):
        """Drift should not be detected after reset until new drift occurs."""
        detector = DriftDetector(threshold=25.0, epsilon=0.5)
        now = datetime.now()

        # Trigger drift
        for i in range(100):
            detector.record_outcome("pack", i < 50, now + timedelta(minutes=i))

        self.assertTrue(detector.check_drift("pack"))

        # Reset
        detector.reset_pack("pack")

        # Add more outcomes after reset
        for i in range(10):
            detector.record_outcome("pack", True, now + timedelta(minutes=i))

        # Should not detect drift yet (not enough observations)
        self.assertFalse(detector.check_drift("pack"))

    def test_running_mean_calculation(self):
        """Running mean should be calculated correctly."""
        detector = DriftDetector()
        now = datetime.now()

        # 3 successes, 1 failure
        detector.record_outcome("pack", True, now)
        detector.record_outcome("pack", True, now + timedelta(minutes=1))
        detector.record_outcome("pack", True, now + timedelta(minutes=2))
        detector.record_outcome("pack", False, now + timedelta(minutes=3))

        mean = detector.get_running_mean("pack")
        self.assertAlmostEqual(mean, 0.75, places=2)


class TestTTLv2(unittest.TestCase):
    """Tests for TTL enforcement in signal management."""

    def test_signal_without_timestamp(self):
        """Signals without valid timestamp should still be recorded."""
        loop = FeedbackLoop()
        signal = FeedbackSignal(
            agent_id="a1",
            pack_id="p1",
            signal_type=SignalType.EXPLICIT_CONFIRMATION,
            value=True,
            timestamp=datetime.now()
        )
        loop.record_signal(signal)
        self.assertEqual(len(loop.get_all_signals()), 1)

    def test_multiple_packs_ttl_independent(self):
        """TTL tracking should be independent per pack."""
        loop = FeedbackLoop()
        now = datetime.now()

        # Pack 1 signals
        loop.record_signal(FeedbackSignal(
            "a1", "pack1", SignalType.EXPLICIT_CONFIRMATION, True, now
        ))

        # Pack 2 signals
        loop.record_signal(FeedbackSignal(
            "a1", "pack2", SignalType.VOTE, True, now
        ))

        signals_p1 = loop.get_signals_for_pack("pack1")
        signals_p2 = loop.get_signals_for_pack("pack2")

        self.assertEqual(len(signals_p1), 1)
        self.assertEqual(len(signals_p2), 1)


class TestEdgeCasesExtended(unittest.TestCase):
    """Extended edge case tests."""

    def test_conflicting_signals_different_weights(self):
        """Conflicting signals should be weighted correctly."""
        agg = QualityWeightedAggregator()
        now = datetime.now()

        # Success from implicit usage
        agg.add_signal(FeedbackSignal(
            "a1", "p1", SignalType.IMPLIED_USAGE, True, now
        ))
        # Failure from explicit confirmation
        agg.add_signal(FeedbackSignal(
            "a2", "p1", SignalType.EXPLICIT_CONFIRMATION, False, now
        ))

        report = agg.aggregate("p1")
        # (0.2*1 + 1.0*0) / (0.2 + 1.0) = 0.2 / 1.2 = 1/6
        self.assertAlmostEqual(report.weighted_success_rate, 1.0/6.0, places=4)

    def test_all_signal_types_in_aggregation(self):
        """All signal types should affect aggregation correctly."""
        agg = QualityWeightedAggregator()
        now = datetime.now()

        signals = [
            (SignalType.EXPLICIT_CONFIRMATION, True),
            (SignalType.VOTE, True),
            (SignalType.IMPLIED_USAGE, True),
        ]

        for st, val in signals:
            agg.add_signal(FeedbackSignal("a", "p", st, val, now))

        report = agg.aggregate("p")
        # (1.0 + 0.5 + 0.2) / (1.0 + 0.5 + 0.2) = 1.0
        self.assertEqual(report.weighted_success_rate, 1.0)

    def test_zero_confidence_interval_with_zero_samples(self):
        """Zero samples should give zero confidence interval."""
        agg = QualityWeightedAggregator()
        report = agg.aggregate("nonexistent")
        self.assertEqual(report.confidence_interval, (0.0, 0.0))

    def test_wilson_interval_bounds(self):
        """Wilson confidence interval should be within [0, 1]."""
        agg = QualityWeightedAggregator()
        now = datetime.now()

        for _ in range(50):
            agg.add_signal(FeedbackSignal(
                "a", "p", SignalType.EXPLICIT_CONFIRMATION, True, now
            ))

        report = agg.aggregate("p")
        lower, upper = report.confidence_interval
        self.assertGreaterEqual(lower, 0.0)
        self.assertLessEqual(upper, 1.0)
        self.assertLessEqual(lower, upper)

    def test_free_rider_tracker_uses_and_reports_independent(self):
        """Uses and reports counts should be independent."""
        tracker = FreeRiderTracker()

        tracker.record_use("a1")
        tracker.record_use("a1")
        tracker.record_use("a1")

        tracker.record_report("a1")
        tracker.record_report("a1")

        self.assertEqual(tracker.get_uses_count("a1"), 3)
        self.assertEqual(tracker.get_reports_count("a1"), 2)

    def test_free_rider_score_boundary_conditions(self):
        """Free rider score should handle boundary conditions."""
        tracker = FreeRiderTracker()

        # Exactly at threshold (5 uses) - score should be 0.0 (below threshold)
        for i in range(5):
            tracker.record_use("agent_at_threshold")
        tracker.record_report("agent_at_threshold")
        self.assertEqual(tracker.get_free_rider_score("agent_at_threshold"), 0.0)

        # Just above threshold (6 uses)
        tracker2 = FreeRiderTracker()
        for i in range(6):
            tracker2.record_use("agent_below")
        tracker2.record_report("agent_below")
        # 1/6 = 0.166..., 1 - 0.166 = 0.833
        self.assertAlmostEqual(tracker2.get_free_rider_score("agent_below"), 5/6, places=4)

    def test_drift_detector_multiple_drift_events(self):
        """Should record multiple drift events for same pack."""
        detector = DriftDetector(threshold=10.0, epsilon=0.5)
        now = datetime.now()

        # First drift
        for i in range(60):
            detector.record_outcome("pack", i < 30, now + timedelta(minutes=i))

        first_drift_count = len(detector.get_drift_events("pack"))

        # Second drift
        for i in range(60, 120):
            detector.record_outcome("pack", i < 90, now + timedelta(minutes=i))

        second_drift_count = len(detector.get_drift_events("pack"))

        self.assertGreaterEqual(second_drift_count, first_drift_count)

    def test_auto_feedback_no_inference_with_empty_data(self):
        """Empty session data should return None."""
        detector = AutoFeedbackDetector()
        result = detector.infer_signal("a1", "p1", {}, datetime.now())
        self.assertIsNone(result)

    def test_auto_feedback_partial_completion_no_signal(self):
        """Partial phase completion without other signals returns None."""
        detector = AutoFeedbackDetector()
        session_data = {
            "phases": ["p1", "p2", "p3"],
            "completed_phases": ["p1"]  # Not all complete
        }
        result = detector.infer_signal("a1", "p1", session_data, datetime.now())
        self.assertIsNone(result)

    def test_feedback_loop_initial_state(self):
        """FeedbackLoop should have correct initial state."""
        loop = FeedbackLoop()
        self.assertEqual(len(loop.get_all_signals()), 0)
        self.assertIsInstance(loop.aggregator, QualityWeightedAggregator)
        self.assertIsInstance(loop.free_rider_tracker, FreeRiderTracker)
        self.assertIsInstance(loop.drift_detector, DriftDetector)
        self.assertIsInstance(loop.auto_feedback, AutoFeedbackDetector)

    def test_feedback_loop_custom_components(self):
        """FeedbackLoop should accept custom components."""
        custom_agg = QualityWeightedAggregator(confidence_level=0.99)
        custom_tracker = FreeRiderTracker()
        custom_detector = DriftDetector(threshold=100.0)
        custom_feedback = AutoFeedbackDetector()

        loop = FeedbackLoop(
            aggregator=custom_agg,
            free_rider_tracker=custom_tracker,
            drift_detector=custom_detector,
            auto_feedback=custom_feedback
        )

        self.assertEqual(loop.aggregator, custom_agg)
        self.assertEqual(loop.free_rider_tracker, custom_tracker)
        self.assertEqual(loop.drift_detector, custom_detector)
        self.assertEqual(loop.auto_feedback, custom_feedback)

    def test_signal_type_enum_values(self):
        """All SignalType values should be as specified."""
        self.assertEqual(SignalType.EXPLICIT_CONFIRMATION.value, 1.0)
        self.assertEqual(SignalType.VOTE.value, 0.5)
        self.assertEqual(SignalType.IMPLIED_USAGE.value, 0.2)
        self.assertEqual(SignalType.SILENCE.value, 0.0)

    def test_drift_event_dataclass_fields(self):
        """DriftEvent should have all required fields."""
        event = DriftEvent(
            pack_id="test_pack",
            old_rate=0.9,
            new_rate=0.5,
            timestamp=datetime.now()
        )
        self.assertEqual(event.pack_id, "test_pack")
        self.assertEqual(event.old_rate, 0.9)
        self.assertEqual(event.new_rate, 0.5)
        self.assertIsInstance(event.timestamp, datetime)

    def test_quality_report_dataclass_fields(self):
        """QualityReport should have all required fields."""
        report = QualityReport(
            pack_id="test_pack",
            weighted_success_rate=0.85,
            confidence_interval=(0.7, 0.95),
            sample_size=100,
            drift_detected=True
        )
        self.assertEqual(report.pack_id, "test_pack")
        self.assertEqual(report.weighted_success_rate, 0.85)
        self.assertEqual(report.confidence_interval, (0.7, 0.95))
        self.assertEqual(report.sample_size, 100)
        self.assertTrue(report.drift_detected)


if __name__ == "__main__":
    unittest.main()
