"""Event emitter implementation."""
from typing import Callable, Any, List


class EventEmitter:
    def __init__(self):
        self.subscribers: List[Callable] = []
        self.event_history: List[tuple] = []

    def subscribe(self, handler: Callable) -> None:
        """Register a new event handler."""
        self.subscribers.append(handler)

    def unsubscribe(self, handler: Callable) -> None:
        """Remove an event handler."""
        if handler in self.subscribers:
            self.subscribers.remove(handler)

    def emit(self, event_name: str, data: Any = None) -> None:
        """Emit an event to all subscribers."""
        self.event_history.append((event_name, data))
        # BUG: Iterating over self.subscribers directly
        # If a handler modifies this list (via unsubscribe), we get:
        # RuntimeError: list changed size during iteration
        for handler in self.subscribers:
            handler(event_name, data)

    def get_history(self) -> List[tuple]:
        """Get the history of emitted events."""
        return self.event_history.copy()

    def clear(self) -> None:
        """Clear all subscribers and history."""
        self.subscribers.clear()
        self.event_history.clear()


# Global event emitter instance
_global_emitter = EventEmitter()


def get_emitter() -> EventEmitter:
    """Get the global event emitter instance."""
    return _global_emitter
