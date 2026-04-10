"""Event processor that orchestrates event handling."""
from typing import Any
from events import get_emitter, EventEmitter
from handlers import handle_event_A, handle_event_B, handle_event_C


class EventProcessor:
    def __init__(self, emitter: EventEmitter = None):
        self.emitter = emitter or get_emitter()
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register the default event handlers."""
        self.emitter.subscribe(handle_event_A)
        self.emitter.subscribe(handle_event_B)
        self.emitter.subscribe(handle_event_C)

    def process_event(self, event_name: str, data: Any = None) -> None:
        """Process a single event."""
        self.emitter.emit(event_name, data)

    def process_events(self, events: list) -> None:
        """Process multiple events in sequence."""
        for event_name, data in events:
            self.emitter.emit(event_name, data)

    def get_emitter(self) -> EventEmitter:
        """Get the event emitter used by this processor."""
        return self.emitter
