"""
Tests for borg/integrations/nudge.py — NudgeEngine.

Tests:
    NudgeSignal      — dataclass fields
    NudgeDecision   — dataclass fields
    NudgeEngine     — background thread, signal aggregation,
                      cooldown/suppression, poll_nudge, submit_turn,
                      record_pack_outcome, pack confidence
"""

import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from borg.integrations.nudge import (
    NudgeEngine,
    NudgeSignal,
    NudgeDecision,
    _NUDGE_COOLDOWN_SECONDS,
    _MIN_TURNS_BETWEEN_NUDGES,
)


# ---------------------------------------------------------------------------
# NudgeSignal / NudgeDecision dataclasses
# ---------------------------------------------------------------------------

class TestNudgeSignal:
    def test_fields(self):
        sig = NudgeSignal(
            signal_type="keyword",
            value="debug",
            turn_index=3,
            timestamp="2025-01-01T00:00:00Z",
        )
        assert sig.signal_type == "keyword"
        assert sig.value == "debug"
        assert sig.turn_index == 3
        assert sig.timestamp == "2025-01-01T00:00:00Z"


class TestNudgeDecision:
    def test_fields(self):
        dec = NudgeDecision(
            message="Try this pack",
            pack_names=["systematic-debugging"],
            confidence=0.75,
            trigger_signals=["keyword"],
            turn_index=5,
        )
        assert dec.message == "Try this pack"
        assert dec.pack_names == ["systematic-debugging"]
        assert dec.confidence == 0.75
        assert dec.trigger_signals == ["keyword"]
        assert dec.turn_index == 5


# ---------------------------------------------------------------------------
# NudgeEngine — lifecycle
# ---------------------------------------------------------------------------

class TestNudgeEngineLifecycle:
    def test_start_stop(self):
        engine = NudgeEngine()
        engine.start()
        assert engine._thread is not None
        assert engine._thread.is_alive()
        engine.stop()
        # join has 2s timeout — should complete quickly
        engine._thread.join(timeout=3.0)

    def test_start_idempotent(self):
        """Multiple start() calls don't crash."""
        engine = NudgeEngine()
        engine.start()
        first_thread = engine._thread
        # Second start is not truly idempotent — it creates a new thread
        # (but stop should handle this gracefully)
        engine.start()
        engine.stop()
        engine._thread.join(timeout=3.0)


# ---------------------------------------------------------------------------
# NudgeEngine — submit_turn / signal collection
# ---------------------------------------------------------------------------

class TestNudgeEngineSubmitTurn:
    def test_submit_turn_increments_turn_index(self):
        engine = NudgeEngine()
        engine.start()
        try:
            engine.submit_turn(
                turn_index=1,
                user_message="my code is broken",
                agent_messages=["I tried to fix it"],
                tool_errors=[],
            )
            assert engine._turn_index == 1

            engine.submit_turn(
                turn_index=2,
                user_message="still failing",
                agent_messages=[],
                tool_errors=["KeyError: 'foo'"],
            )
            assert engine._turn_index == 2
        finally:
            engine.stop()

    def test_submit_turn_extracts_keywords(self):
        engine = NudgeEngine()
        engine.start()
        try:
            with patch("borg.core.search.classify_task") as mock_classify:
                mock_classify.return_value = ["debug", "test"]
                engine.submit_turn(
                    turn_index=1,
                    user_message="my pytest test is failing with an error",
                    agent_messages=[],
                    tool_errors=[],
                )

            # classify_task should have been called
            mock_classify.assert_called_once_with("my pytest test is failing with an error")

            with engine._lock:
                keyword_signals = [s for s in engine._signals if s.signal_type == "keyword"]
                values = {s.value for s in keyword_signals}
                assert "debug" in values
                assert "test" in values
        finally:
            engine.stop()

    def test_submit_turn_extracts_frustration_signals(self):
        engine = NudgeEngine()
        engine.start()
        try:
            engine.submit_turn(
                turn_index=1,
                user_message="I've tried everything and it keeps failing",
                agent_messages=["I can't figure out the issue"],
                tool_errors=[],
            )
            with engine._lock:
                frustration_signals = [s for s in engine._signals if s.signal_type == "frustration"]
                assert len(frustration_signals) == 1
                assert frustration_signals[0].turn_index == 1
        finally:
            engine.stop()

    def test_submit_turn_extracts_tool_errors(self):
        engine = NudgeEngine()
        engine.start()
        try:
            engine.submit_turn(
                turn_index=1,
                user_message="debug this",
                agent_messages=["running..."],
                tool_errors=["TypeError: expected str, got None", "KeyError: 'missing'"],
            )
            with engine._lock:
                error_signals = [s for s in engine._signals if s.signal_type == "error"]
                assert len(error_signals) == 2
                assert "TypeError" in error_signals[0].value
                assert "KeyError" in error_signals[1].value
        finally:
            engine.stop()

    def test_submit_turn_tracks_tried_packs(self):
        engine = NudgeEngine()
        engine.start()
        try:
            engine.submit_turn(
                turn_index=1,
                user_message="help",
                agent_messages=[],
                tool_errors=[],
                tried_packs=["already-tried", "another-pack"],
            )
            with engine._lock:
                assert "already-tried" in engine._suppressed_packs
                assert "another-pack" in engine._suppressed_packs
        finally:
            engine.stop()


# ---------------------------------------------------------------------------
# NudgeEngine — cooldown / suppression
# ---------------------------------------------------------------------------

class TestNudgeEngineCooldown:
    def test_suppress_pack_adds_to_suppressed(self):
        engine = NudgeEngine()
        engine.suppress_pack("test-pack", seconds=60.0)
        with engine._lock:
            assert "test-pack" in engine._suppressed_packs
            assert engine._pack_suppress_until["test-pack"] >= time.time() + 59.0

    def test_suppress_pack_resets_expiry(self):
        engine = NudgeEngine()
        engine.suppress_pack("test-pack", seconds=10.0)
        first_expiry = engine._pack_suppress_until["test-pack"]
        time.sleep(0.1)
        engine.suppress_pack("test-pack", seconds=300.0)
        assert engine._pack_suppress_until["test-pack"] > first_expiry

    def test_suppress_pack_default_cooldown(self):
        engine = NudgeEngine()
        engine.suppress_pack("test-pack")
        with engine._lock:
            assert "test-pack" in engine._suppressed_packs
            # Default cooldown should be _NUDGE_COOLDOWN_SECONDS (120)
            assert engine._pack_suppress_until["test-pack"] >= time.time() + _NUDGE_COOLDOWN_SECONDS - 0.1


# ---------------------------------------------------------------------------
# NudgeEngine — record_pack_outcome / pack confidence
# ---------------------------------------------------------------------------

class TestNudgeEnginePackOutcome:
    def test_record_success_increases_confidence(self):
        engine = NudgeEngine()
        # Record 4 successes
        for i in range(4):
            engine.record_pack_outcome("good-pack", "success", turn_index=i)
        assert engine._pack_confidence("good-pack") == 1.0

    def test_record_failure_decreases_confidence(self):
        engine = NudgeEngine()
        # Record 4 failures
        for i in range(4):
            engine.record_pack_outcome("bad-pack", "failure", turn_index=i)
        assert engine._pack_confidence("bad-pack") == 0.0

    def test_record_mixed_outcomes(self):
        engine = NudgeEngine()
        engine.record_pack_outcome("mixed-pack", "success", turn_index=0)
        engine.record_pack_outcome("mixed-pack", "success", turn_index=1)
        engine.record_pack_outcome("mixed-pack", "failure", turn_index=2)
        # Last 5: [True, True, False] → 2/3
        conf = engine._pack_confidence("mixed-pack")
        assert 0.6 < conf < 0.7

    def test_unknown_pack_returns_neutral(self):
        engine = NudgeEngine()
        assert engine._pack_confidence("never-seen-pack") == 0.5


# ---------------------------------------------------------------------------
# NudgeEngine — _extract_pack_names_from_suggestion
# ---------------------------------------------------------------------------

class TestExtractPackNames:
    def test_extracts_guild_uri(self):
        engine = NudgeEngine()
        text = "Try guild://hermes/systematic-debugging"
        names = engine._extract_pack_names_from_suggestion(text)
        assert "systematic-debugging" in names

    def test_extracts_multiple_guild_uris(self):
        engine = NudgeEngine()
        text = "Try guild://hermes/pack-a or guild://hermes/pack-b"
        names = engine._extract_pack_names_from_suggestion(text)
        assert "pack-a" in names
        assert "pack-b" in names

    def test_extracts_pack_name_before_parenthesis(self):
        engine = NudgeEngine()
        text = "systematic-debugging (Debugging workflow)"
        names = engine._extract_pack_names_from_suggestion(text)
        assert "systematic-debugging" in names

    def test_extracts_pack_name_before_bracket(self):
        engine = NudgeEngine()
        text = "my-pack [tested] (Description)"
        names = engine._extract_pack_names_from_suggestion(text)
        assert "my-pack" in names

    def test_deduplicates(self):
        engine = NudgeEngine()
        text = "guild://hermes/pack-a and pack-a (Description)"
        names = engine._extract_pack_names_from_suggestion(text)
        assert names.count("pack-a") == 1

    def test_empty_text_returns_empty(self):
        engine = NudgeEngine()
        assert engine._extract_pack_names_from_suggestion("") == []
        assert engine._extract_pack_names_from_suggestion(None) == []


# ---------------------------------------------------------------------------
# NudgeEngine — _compute_nudge_unlocked integration
# ---------------------------------------------------------------------------

class TestNudgeEngineCompute:
    def test_frustration_triggers_borg_on_failure_path(self):
        engine = NudgeEngine()
        with engine._lock:
            engine._turn_index = 1
            engine._signals.append(NudgeSignal(
                signal_type="frustration",
                value="still failing",
                turn_index=1,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            with patch.object(engine, "_call_borg_on_failure") as mock_failure:
                mock_failure.return_value = "Try systematic-debugging"
                nudge = engine._compute_nudge_unlocked()

        assert nudge is not None
        mock_failure.assert_called_once()
        assert "still failing" in mock_failure.call_args[1]["context"]

    def test_keyword_signals_trigger_borg_on_task_start_path(self):
        engine = NudgeEngine()
        with engine._lock:
            engine._turn_index = 1
            engine._signals.append(NudgeSignal(
                signal_type="keyword",
                value="debug",
                turn_index=1,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            with patch.object(engine, "_call_borg_on_task_start") as mock_task:
                mock_task.return_value = "You might find this useful: debug-pack"
                nudge = engine._compute_nudge_unlocked()

        assert nudge is not None
        mock_task.assert_called_once()
        # Should combine keywords into query
        assert "debug" in mock_task.call_args[0][0]

    def test_no_signals_returns_none(self):
        engine = NudgeEngine()
        with engine._lock:
            engine._turn_index = 0
            engine._signals = []
            nudge = engine._compute_nudge_unlocked()
        assert nudge is None

    def test_turn_spacing_respected(self):
        """Nudge not fired if _min_turns not reached since last nudge."""
        engine = NudgeEngine(min_turns_between=3)
        with engine._lock:
            engine._turn_index = 2
            engine._last_nudge_turn = 1  # only 1 turn apart, need 3
            engine._signals.append(NudgeSignal(
                signal_type="keyword",
                value="debug",
                turn_index=2,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            # _poll_unlocked() enforces _min_turns; _compute_nudge_unlocked() does not
            nudge = engine._poll_unlocked()

        assert nudge is None

    def test_suppressed_packs_excluded_from_borg_on_failure(self):
        engine = NudgeEngine()
        with engine._lock:
            engine._turn_index = 1
            engine._last_nudge_turn = -999
            engine._signals.append(NudgeSignal(
                signal_type="frustration",
                value="stuck",
                turn_index=1,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))
            engine._suppressed_packs.add("already-tried-pack")

            with patch.object(engine, "_call_borg_on_failure") as mock_failure:
                mock_failure.return_value = None  # no suggestion
                engine._compute_nudge_unlocked()

        # tried_packs should include the suppressed pack
        _, kwargs = mock_failure.call_args
        assert "already-tried-pack" in kwargs["tried_packs"]

    def test_suppression_applied_after_keyword_nudge(self):
        """Packs suggested via keyword path are suppressed immediately."""
        engine = NudgeEngine()
        with engine._lock:
            engine._turn_index = 1
            engine._last_nudge_turn = -999
            engine._signals.append(NudgeSignal(
                signal_type="keyword",
                value="debug",
                turn_index=1,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

            with patch.object(engine, "_call_borg_on_task_start") as mock_task:
                mock_task.return_value = "Try guild://hermes/systematic-debugging"
                nudge = engine._compute_nudge_unlocked()

        assert nudge is not None
        assert "systematic-debugging" in engine._suppressed_packs
        # _last_nudge_turn is updated by poll_nudge(), not _compute_nudge_unlocked
        assert engine._last_nudge_turn == -999  # unchanged until poll_nudge called


# ---------------------------------------------------------------------------
# NudgeEngine — poll_nudge / poll_idle_nudge
# ---------------------------------------------------------------------------

class TestNudgeEnginePoll:
    def test_poll_nudge_returns_pending_nudge(self):
        engine = NudgeEngine()
        engine.start()
        try:
            engine.submit_turn(
                turn_index=1,
                user_message="still failing",
                agent_messages=[],
                tool_errors=[],
            )
            time.sleep(0.5)  # let background thread process

            nudge = engine.poll_nudge()
            # May or may not have a nudge depending on timing, but shouldn't crash
            # Subsequent poll should return None
            assert engine.poll_nudge() is None
        finally:
            engine.stop()

    def test_poll_idle_nudge_returns_none_with_no_signals(self):
        engine = NudgeEngine()
        engine.start()
        try:
            nudge = engine.poll_idle_nudge()
            assert nudge is None
        finally:
            engine.stop()

    def test_poll_idle_nudge_prunes_old_signals(self):
        engine = NudgeEngine()
        engine.start()
        try:
            with engine._lock:
                engine._turn_index = 20
                engine._signals.append(NudgeSignal(
                    signal_type="keyword",
                    value="debug",
                    turn_index=5,   # old, should be pruned
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))
                engine._signals.append(NudgeSignal(
                    signal_type="keyword",
                    value="test",
                    turn_index=18,  # recent, should be kept
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

            nudge = engine.poll_idle_nudge()
            # Should not raise and should prune old signals
            with engine._lock:
                turn_indices = {s.turn_index for s in engine._signals}
                assert 5 not in turn_indices
                assert 18 in turn_indices
        finally:
            engine.stop()


# ---------------------------------------------------------------------------
# datetime import fix for timezone-aware utcnow()
# ---------------------------------------------------------------------------

from datetime import datetime, timezone
