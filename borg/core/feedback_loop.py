"""
Borg V3 Feedback Loop Module

Manages signal quality, free-rider detection, drift detection, and auto-feedback
for all packs in the Borg system. This is a general-purpose feedback system
independent of the DeFi layer.

Pure Python implementation using only stdlib dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import math


class SignalType(Enum):
    """Signal quality hierarchy with associated weights."""
    EXPLICIT_CONFIRMATION = 1.0
    VOTE = 0.5
    IMPLIED_USAGE = 0.2
    SILENCE = 0.0


@dataclass
class FeedbackSignal:
    """A single feedback signal from an agent about a pack."""
    agent_id: str
    pack_id: str
    signal_type: SignalType
    value: bool  # True = success, False = failure
    timestamp: datetime
    task_context: Optional[Dict[str, Any]] = None
    quality_score: float = 0.5  # quality ∈ [0, 1], default neutral
    success_rate_trend: float = 0.0  # trend ∈ [-1, 1], default neutral drift


@dataclass
class DriftEvent:
    """Event emitted when concept drift is detected in a pack."""
    pack_id: str
    old_rate: float
    new_rate: float
    timestamp: datetime


@dataclass
class QualityReport:
    """Report on pack quality with weighted metrics."""
    pack_id: str
    weighted_success_rate: float
    confidence_interval: tuple[float, float]
    sample_size: int
    drift_detected: bool
    drift_events: List[DriftEvent] = field(default_factory=list)


@dataclass
class AgentStatus:
    """Status report for an agent's behavior."""
    agent_id: str
    free_rider_score: float
    access_delay: float  # seconds
    contribution_count: int
    is_free_rider: bool


@dataclass
class QualityWeightedAggregator:
    """
    Aggregates feedback signals for a pack, weighting by signal type.
    Returns weighted success rate with confidence interval.
    """

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
        self._pack_signals: Dict[str, List[FeedbackSignal]] = {}

    def add_signal(self, signal: FeedbackSignal) -> None:
        """Add a feedback signal for a pack."""
        if signal.pack_id not in self._pack_signals:
            self._pack_signals[signal.pack_id] = []
        self._pack_signals[signal.pack_id].append(signal)

    def aggregate(self, pack_id: str) -> QualityReport:
        """
        Aggregate signals for a pack, returning weighted success rate
        with confidence interval.
        """
        signals = self._pack_signals.get(pack_id, [])

        if not signals:
            return QualityReport(
                pack_id=pack_id,
                weighted_success_rate=0.0,
                confidence_interval=(0.0, 0.0),
                sample_size=0,
                drift_detected=False
            )

        # Calculate weighted success
        total_weight = 0.0
        weighted_sum = 0.0

        for signal in signals:
            weight = signal.signal_type.value
            total_weight += weight
            if signal.value:  # success
                weighted_sum += weight

        if total_weight == 0:
            weighted_success_rate = 0.0
        else:
            weighted_success_rate = weighted_sum / total_weight

        # Calculate confidence interval using Wilson score method
        n = len(signals)
        ci = self._wilson_confidence_interval(weighted_success_rate, n)

        return QualityReport(
            pack_id=pack_id,
            weighted_success_rate=weighted_success_rate,
            confidence_interval=ci,
            sample_size=n,
            drift_detected=False
        )

    def _wilson_confidence_interval(self, p: float, n: int) -> tuple[float, float]:
        """Calculate Wilson score confidence interval for a proportion."""
        if n == 0:
            return (0.0, 0.0)

        z = 1.96  # 95% confidence level
        denominator = 1 + z**2 / n

        center = p + z**2 / (2 * n)
        spread = z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)

        lower = (center - spread) / denominator
        upper = (center + spread) / denominator

        return (max(0.0, lower), min(1.0, upper))

    def get_signals(self, pack_id: str) -> List[FeedbackSignal]:
        """Get all signals for a pack."""
        return self._pack_signals.get(pack_id, [])

    def clear_pack(self, pack_id: str) -> None:
        """Clear all signals for a pack."""
        if pack_id in self._pack_signals:
            del self._pack_signals[pack_id]


class FreeRiderTracker:
    """
    Tracks agent usage and reporting behavior to detect free-riders.
    
    Free-rider criteria: uses > 5 AND reports/uses < 0.2
    Consequence: delayed access to new packs (delay = 3600 * free_rider_score)
    """

    USES_THRESHOLD = 5
    REPORT_RATIO_THRESHOLD = 0.2
    DELAY_MULTIPLIER = 3600  # seconds per score unit

    def __init__(self):
        self._agent_uses: Dict[str, int] = {}
        self._agent_reports: Dict[str, int] = {}

    def record_use(self, agent_id: str) -> None:
        """Record that an agent used a pack."""
        self._agent_uses[agent_id] = self._agent_uses.get(agent_id, 0) + 1

    def record_report(self, agent_id: str) -> None:
        """Record that an agent submitted a report/feedback."""
        self._agent_reports[agent_id] = self._agent_reports.get(agent_id, 0) + 1

    def get_free_rider_score(self, agent_id: str) -> float:
        """
        Calculate free-rider score for an agent.
        Score = max(0, 1 - reports/uses) for agents with uses > 5
        Returns 0.0 for agents below usage threshold.
        """
        uses = self._agent_uses.get(agent_id, 0)

        if uses <= self.USES_THRESHOLD:
            return 0.0

        reports = self._agent_reports.get(agent_id, 0)
        report_ratio = reports / uses if uses > 0 else 0.0

        return max(0.0, 1.0 - report_ratio)

    def is_free_rider(self, agent_id: str) -> bool:
        """Check if an agent qualifies as a free-rider."""
        uses = self._agent_uses.get(agent_id, 0)
        reports = self._agent_reports.get(agent_id, 0)

        if uses <= self.USES_THRESHOLD:
            return False

        report_ratio = reports / uses if uses > 0 else 0.0
        return report_ratio < self.REPORT_RATIO_THRESHOLD

    def get_access_delay(self, agent_id: str) -> float:
        """
        Get the access delay in seconds for an agent.
        Delay = 3600 * free_rider_score for free-riders, else 0.
        """
        if not self.is_free_rider(agent_id):
            return 0.0

        score = self.get_free_rider_score(agent_id)
        return self.DELAY_MULTIPLIER * score

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """Get complete status for an agent."""
        return AgentStatus(
            agent_id=agent_id,
            free_rider_score=self.get_free_rider_score(agent_id),
            access_delay=self.get_access_delay(agent_id),
            contribution_count=self._agent_reports.get(agent_id, 0),
            is_free_rider=self.is_free_rider(agent_id)
        )

    def get_uses_count(self, agent_id: str) -> int:
        """Get the number of uses for an agent."""
        return self._agent_uses.get(agent_id, 0)

    def get_reports_count(self, agent_id: str) -> int:
        """Get the number of reports for an agent."""
        return self._agent_reports.get(agent_id, 0)


class DriftDetector:
    """
    Detects concept drift in pack success rates using the Page-Hinkley test.
    
    The Page-Hinkley test maintains a cumulative sum of deviations from a
    running mean. When this sum exceeds a threshold, drift is declared.
    
    The epsilon parameter is a small constant (default 0.5) added to each
    deviation to make the test more sensitive to persistent drift.
    """

    def __init__(self, threshold: float = 50.0, drift_window: int = 100, epsilon: float = 0.5):
        self.threshold = threshold
        self.drift_window = drift_window
        self.epsilon = epsilon

        # State per pack: cumulative PH statistic, running mean, sample count
        self._pack_ph_state: Dict[str, Dict[str, float]] = {}
        self._pack_history: Dict[str, List[bool]] = {}
        self._drift_events: Dict[str, List[DriftEvent]] = {}

    def record_outcome(self, pack_id: str, success: bool, timestamp: datetime) -> Optional[DriftEvent]:
        """
        Record a success/failure outcome for a pack and check for drift.
        Returns a DriftEvent if drift is detected, None otherwise.
        """
        # Initialize state for new packs
        if pack_id not in self._pack_ph_state:
            self._pack_ph_state[pack_id] = {
                'cumulative_sum': 0.0,
                'running_mean': 0.0,
                'sample_count': 0.0,
                'last_mean': 0.0
            }
            self._pack_history[pack_id] = []
            self._drift_events[pack_id] = []

        state = self._pack_ph_state[pack_id]
        history = self._pack_history[pack_id]

        # Add to history (with window limit)
        history.append(success)
        if len(history) > self.drift_window:
            history.pop(0)

        # Update running mean
        state['sample_count'] += 1
        old_mean = state['running_mean']
        new_observation = 1.0 if success else 0.0
        state['running_mean'] = old_mean + (new_observation - old_mean) / state['sample_count']

        # Page-Hinkley test:
        # Compute deviation from current mean, minus epsilon to allow drift accumulation
        # We negate so that when success rate DROPS, cumulative sum goes POSITIVE
        deviation = -(new_observation - state['running_mean'] - self.epsilon)
        state['cumulative_sum'] += deviation

        # Store old rate before potential drift
        old_rate = state.get('last_mean', state['running_mean'])

        # Check for drift (positive cumulative sum means persistent drop in success rate)
        if state['cumulative_sum'] > self.threshold:
            # Drift detected!
            state['last_mean'] = state['running_mean']
            
            # Reset cumulative sum after drift detection
            state['cumulative_sum'] = 0.0

            event = DriftEvent(
                pack_id=pack_id,
                old_rate=old_rate,
                new_rate=state['running_mean'],
                timestamp=timestamp
            )
            self._drift_events[pack_id].append(event)
            return event

        return None

    def check_drift(self, pack_id: str) -> bool:
        """Check if drift has been detected for a pack."""
        return pack_id in self._drift_events and len(self._drift_events[pack_id]) > 0

    def get_drift_events(self, pack_id: str) -> List[DriftEvent]:
        """Get all drift events for a pack."""
        return self._drift_events.get(pack_id, [])

    def get_all_drift_events(self) -> List[DriftEvent]:
        """Get all drift events across all packs."""
        events = []
        for pack_events in self._drift_events.values():
            events.extend(pack_events)
        return events

    def reset_pack(self, pack_id: str) -> None:
        """Clear drift state for a pack."""
        if pack_id in self._pack_ph_state:
            del self._pack_ph_state[pack_id]
        if pack_id in self._pack_history:
            del self._pack_history[pack_id]
        if pack_id in self._drift_events:
            del self._drift_events[pack_id]

    def get_ph_statistic(self, pack_id: str) -> float:
        """Get the current Page-Hinkley cumulative statistic for a pack."""
        if pack_id not in self._pack_ph_state:
            return 0.0
        return self._pack_ph_state[pack_id]['cumulative_sum']

    def get_running_mean(self, pack_id: str) -> float:
        """Get the current running mean success rate for a pack."""
        if pack_id not in self._pack_ph_state:
            return 0.0
        return self._pack_ph_state[pack_id]['running_mean']


class AutoFeedbackDetector:
    """
    Infers task outcomes without explicit feedback using heuristics.
    
    Heuristics:
    - Completed all phases -> implied SUCCESS
    - Abandoned mid-phase (no checkpoint for >10 min) -> implied FAILURE
    - Called borg_suggest after applying pack -> implied STRUGGLE
    """

    ABANDONMENT_THRESHOLD_MINUTES = 10

    def infer_signal(
        self,
        agent_id: str,
        pack_id: str,
        session_data: Dict[str, Any],
        timestamp: datetime
    ) -> Optional[FeedbackSignal]:
        """
        Infer a feedback signal from session data.
        Returns None if no inference can be made.
        """
        # Check if agent completed all phases
        if self._completed_all_phases(session_data):
            return FeedbackSignal(
                agent_id=agent_id,
                pack_id=pack_id,
                signal_type=SignalType.IMPLIED_USAGE,
                value=True,
                timestamp=timestamp,
                task_context={'inference': 'completed_all_phases'}
            )

        # Check if agent abandoned mid-phase
        if self._abandoned_mid_phase(session_data, timestamp):
            return FeedbackSignal(
                agent_id=agent_id,
                pack_id=pack_id,
                signal_type=SignalType.IMPLIED_USAGE,
                value=False,
                timestamp=timestamp,
                task_context={'inference': 'abandoned_mid_phase'}
            )

        # Check if agent called borg_suggest after applying pack
        if self._called_suggest_after_apply(session_data):
            return FeedbackSignal(
                agent_id=agent_id,
                pack_id=pack_id,
                signal_type=SignalType.IMPLIED_USAGE,
                value=False,
                timestamp=timestamp,
                task_context={'inference': 'struggled_after_apply'}
            )

        return None

    def _completed_all_phases(self, session_data: Dict[str, Any]) -> bool:
        """Check if agent completed all phases in the session."""
        phases = session_data.get('phases', [])
        if not phases:
            return False

        completed_phases = session_data.get('completed_phases', [])
        return len(completed_phases) == len(phases) and len(phases) > 0

    def _abandoned_mid_phase(
        self,
        session_data: Dict[str, Any],
        current_time: datetime
    ) -> bool:
        """Check if agent abandoned the task mid-phase."""
        last_checkpoint = session_data.get('last_checkpoint')
        if last_checkpoint is None:
            return False

        # last_checkpoint should be a datetime or ISO string
        if isinstance(last_checkpoint, str):
            try:
                last_checkpoint = datetime.fromisoformat(last_checkpoint)
            except ValueError:
                return False

        time_diff = current_time - last_checkpoint
        return time_diff > timedelta(minutes=self.ABANDONMENT_THRESHOLD_MINUTES)

    def _called_suggest_after_apply(self, session_data: Dict[str, Any]) -> bool:
        """Check if agent called borg_suggest after applying the pack."""
        suggest_calls = session_data.get('borg_suggest_calls', [])
        apply_events = session_data.get('apply_events', [])

        if not suggest_calls or not apply_events:
            return False

        # Check if any suggest call happened after an apply event
        for suggest_time in suggest_calls:
            if isinstance(suggest_time, str):
                try:
                    suggest_time = datetime.fromisoformat(suggest_time)
                except ValueError:
                    continue

            for apply_time in apply_events:
                if isinstance(apply_time, str):
                    try:
                        apply_time = datetime.fromisoformat(apply_time)
                    except ValueError:
                        continue

                if suggest_time > apply_time:
                    return True

        return False


class FeedbackLoop:
    """
    Main orchestrator for the feedback loop system.
    
    Coordinates signal quality aggregation, free-rider detection,
    drift detection, and auto-feedback inference.
    """

    def __init__(
        self,
        aggregator: Optional[QualityWeightedAggregator] = None,
        free_rider_tracker: Optional[FreeRiderTracker] = None,
        drift_detector: Optional[DriftDetector] = None,
        auto_feedback: Optional[AutoFeedbackDetector] = None
    ):
        self.aggregator = aggregator or QualityWeightedAggregator()
        self.free_rider_tracker = free_rider_tracker or FreeRiderTracker()
        self.drift_detector = drift_detector or DriftDetector()
        self.auto_feedback = auto_feedback or AutoFeedbackDetector()

        self._signals: List[FeedbackSignal] = []

    def record_signal(self, signal: FeedbackSignal) -> None:
        """
        Record a feedback signal and update all tracking systems.
        """
        self._signals.append(signal)

        # Update aggregator
        self.aggregator.add_signal(signal)

        # Update free-rider tracker based on signal type
        if signal.signal_type == SignalType.EXPLICIT_CONFIRMATION:
            self.free_rider_tracker.record_report(signal.agent_id)

        # Update drift detector
        self.drift_detector.record_outcome(
            signal.pack_id,
            signal.value,
            signal.timestamp
        )

    def get_pack_quality(self, pack_id: str) -> QualityReport:
        """
        Get quality report for a pack.
        """
        report = self.aggregator.aggregate(pack_id)
        report.drift_detected = self.drift_detector.check_drift(pack_id)
        report.drift_events = self.drift_detector.get_drift_events(pack_id)
        return report

    def get_agent_status(self, agent_id: str) -> AgentStatus:
        """
        Get status for an agent including free-rider status.
        """
        return self.free_rider_tracker.get_agent_status(agent_id)

    def check_drift(self) -> List[DriftEvent]:
        """
        Check for any new drift events across all packs.
        """
        return self.drift_detector.get_all_drift_events()

    def infer_feedback(
        self,
        agent_id: str,
        pack_id: str,
        session_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> Optional[FeedbackSignal]:
        """
        Infer feedback from session data using auto-feedback detector.
        """
        if timestamp is None:
            timestamp = datetime.now()

        signal = self.auto_feedback.infer_signal(
            agent_id,
            pack_id,
            session_data,
            timestamp
        )

        if signal is not None:
            self.record_signal(signal)

        return signal

    def record_use(self, agent_id: str) -> None:
        """Record that an agent used a pack (for free-rider tracking)."""
        self.free_rider_tracker.record_use(agent_id)

    def get_all_signals(self) -> List[FeedbackSignal]:
        """Get all recorded signals."""
        return self._signals.copy()

    def get_signals_for_pack(self, pack_id: str) -> List[FeedbackSignal]:
        """Get all signals for a specific pack."""
        return self.aggregator.get_signals(pack_id)

    def get_signals(self, pack_id: str) -> List[FeedbackSignal]:
        """Get all signals for a specific pack (alias for get_signals_for_pack).

        This method is used by ContextualSelector.feedback_signal_boost()
        to compute multiplicative boosts from FeedbackLoop signals.
        """
        return self.aggregator.get_signals(pack_id)
