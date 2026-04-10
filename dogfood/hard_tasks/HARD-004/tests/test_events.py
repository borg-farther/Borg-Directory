"""Tests for the event system."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from events import EventEmitter, get_emitter
from processor import EventProcessor
from handlers import (
    handle_event_A, handle_event_B, handle_event_C,
    get_state, reset_state
)


class TestEventEmitter:
    """Test the event emitter."""

    def test_subscribe_and_emit(self):
        """Test basic subscribe and emit."""
        emitter = EventEmitter()
        calls = []

        def handler(event_name, data):
            calls.append((event_name, data))

        emitter.subscribe(handler)
        emitter.emit("test_event", {"key": "value"})

        assert len(calls) == 1
        assert calls[0] == ("test_event", {"key": "value"})

    def test_unsubscribe(self):
        """Test unsubscribe works."""
        emitter = EventEmitter()
        calls = []

        def handler(event_name, data):
            calls.append(event_name)

        emitter.subscribe(handler)
        emitter.emit("event1")
        emitter.unsubscribe(handler)
        emitter.emit("event2")

        assert calls == ["event1"]


class TestEventProcessor:
    """Test the event processor."""

    def setup_method(self):
        """Reset state before each test."""
        reset_state()

    def test_process_single_event(self):
        """Test processing a single event."""
        emitter = EventEmitter()
        processor = EventProcessor(emitter)

        processor.process_event("test_event", {"data": 123})

        state = get_state()
        assert "handle_event_A" in state["handlers_called"]
        assert "handle_event_B" in state["handlers_called"]
        assert "handle_event_C" in state["handlers_called"]

    def test_process_multiple_events(self):
        """Test processing multiple events sequentially."""
        emitter = EventEmitter()
        processor = EventProcessor(emitter)

        events = [
            ("event_a", None),
            ("event_b", None),
            ("event_c", None),
        ]

        # This should not raise an error
        processor.process_events(events)

        state = get_state()
        assert state["event_a_count"] == 1
        assert state["event_b_count"] == 1
        assert state["event_c_count"] == 1

    def test_event_b_unsubscribes_a(self):
        """Test that handle_event_B unsubscribes handle_event_A during processing."""
        emitter = EventEmitter()
        processor = EventProcessor(emitter)

        events = [
            ("first_event", None),
            ("second_event", None),
        ]

        # Process events - this should NOT raise RuntimeError
        processor.process_events(events)

        # After first event, handle_event_A should have been unsubscribed
        # So during second_event, only B and C should be called
        state = get_state()
        # Count how many times each handler was called
        handler_calls = state["handlers_called"]
        event_a_calls = handler_calls.count("handle_event_A")
        event_b_calls = handler_calls.count("handle_event_B")
        event_c_calls = handler_calls.count("handle_event_C")

        # handle_event_A should be called once (first_event only)
        assert event_a_calls == 1
        # handle_event_B and C should be called twice (both events)
        assert event_b_calls == 2
        assert event_c_calls == 2

    def test_event_loop_modification_safety(self):
        """Test that modifying subscriber list during event processing doesn't crash."""
        emitter = EventEmitter()
        processor = EventProcessor(emitter)

        # Emit multiple events - the bug causes this to crash with
        # RuntimeError: list changed size during iteration
        for i in range(5):
            processor.process_event(f"event_{i}")

        # If we get here without exception, the bug is fixed
        state = get_state()
        assert state["event_a_count"] == 1  # Only called once due to unsubscribe
        assert state["event_b_count"] == 5
        assert state["event_c_count"] == 5


class TestGlobalEmitter:
    """Test the global emitter singleton."""

    def setup_method(self):
        """Reset the global emitter state."""
        emitter = get_emitter()
        emitter.clear()

    def test_global_emitter_singleton(self):
        """Test that get_emitter returns the same instance."""
        emitter1 = get_emitter()
        emitter2 = get_emitter()
        assert emitter1 is emitter2
