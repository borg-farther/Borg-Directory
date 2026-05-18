"""Event handlers that modify shared state."""
from typing import Any

# Shared state that handlers will modify
_state = {
    "event_a_count": 0,
    "event_b_count": 0,
    "handlers_called": [],
}


def get_state():
    """Get a copy of the current state."""
    return _state.copy()


def reset_state():
    """Reset the global state."""
    _state["event_a_count"] = 0
    _state["event_b_count"] = 0
    _state["handlers_called"] = []


def handle_event_A(event_name: str, data: Any) -> None:
    """Handler for event A - increments counter."""
    _state["event_a_count"] += 1
    _state["handlers_called"].append("handle_event_A")


def handle_event_B(event_name: str, data: Any) -> None:
    """Handler for event B - increments counter and modifies subscriber list."""
    _state["event_b_count"] += 1
    _state["handlers_called"].append("handle_event_B")

    # BUG: This modifies the subscriber list during event iteration
    # Import here to avoid circular import issues
    from events import get_emitter

    emitter = get_emitter()
    # Unsubscribe handle_event_A while we're inside the event loop
    # This causes "list changed size during iteration" in events.py
    emitter.unsubscribe(handle_event_A)


def handle_event_C(event_name: str, data: Any) -> None:
    """Handler for event C - just logs the call."""
    _state["handlers_called"].append("handle_event_C")
