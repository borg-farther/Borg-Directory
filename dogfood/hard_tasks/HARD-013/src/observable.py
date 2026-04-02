"""Observable base class with observer pattern implementation."""

import weakref
from typing import List, Callable, Any


class Observable:
    """Base class for observable objects.
    
    Stores strong references to observers, which prevents garbage collection.
    This is the bug - observers should be stored as weak references.
    """
    
    def __init__(self):
        # BUG: Using strong references instead of weakref.WeakSet
        self._observers: List[Any] = []
        self._callback_observers: List[Callable] = []
    
    def add_observer(self, observer: Any) -> None:
        """Register an observer to be notified of changes."""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def add_callback(self, callback: Callable) -> None:
        """Register a callback function to be called on changes."""
        self._callback_observers.append(callback)
    
    def remove_observer(self, observer: Any) -> None:
        """Unregister an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, event: str, data: Any = None) -> None:
        """Notify all registered observers of an event."""
        for observer in self._observers:
            observer.on_event(event, data)
        for callback in self._callback_observers:
            callback(event, data)
    
    def get_observer_count(self) -> int:
        """Return the number of registered observers."""
        return len(self._observers)
    
    def clear_observers(self) -> None:
        """Remove all observers."""
        self._observers.clear()
        self._callback_observers.clear()
