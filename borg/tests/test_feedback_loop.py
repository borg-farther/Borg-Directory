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


if __name__ == "__main__":
    unittest.main()
