"""Concrete observer classes for testing the observer pattern."""

from typing import Any


class EventCounter:
    """Observer that counts events received."""
    
    def __init__(self, name: str = "counter"):
        self.name = name
        self.events: list = []
        self._deleted = False
    
    def on_event(self, event: str, data: Any = None) -> None:
        """Handle an event notification."""
        self.events.append((event, data))
    
    def get_event_count(self) -> int:
        """Return the number of events received."""
        return len(self.events)
    
    # Red herring: This __del__ looks suspicious but isn't the problem
    def __del__(self):
        """Destructor - looks suspicious but isn't causing the memory leak."""
        self._deleted = True


class EventLogger:
    """Observer that logs all events to a list."""
    
    def __init__(self, name: str = "logger"):
        self.name = name
        self.logs: list = []
        self._deleted = False
    
    def on_event(self, event: str, data: Any = None) -> None:
        """Handle an event notification by logging it."""
        self.logs.append({"event": event, "data": data})
    
    def get_log_count(self) -> int:
        """Return the number of logs recorded."""
        return len(self.logs)
    
    # Red herring: This __del__ looks suspicious but isn't the problem
    def __del__(self):
        """Destructor - looks suspicious but isn't causing the memory leak."""
        self._deleted = True


class CallbackObserver:
    """Observer implemented via callback pattern."""
    
    def __init__(self, callback: Any = None):
        self.callback = callback
        self.call_count = 0
        self._deleted = False
    
    def on_event(self, event: str, data: Any = None) -> None:
        """Handle an event notification."""
        self.call_count += 1
        if self.callback:
            self.callback(event, data)
    
    # Red herring: This __del__ looks suspicious but isn't the problem
    def __del__(self):
        """Destructor - looks suspicious but isn't causing the memory leak."""
        self._deleted = True
