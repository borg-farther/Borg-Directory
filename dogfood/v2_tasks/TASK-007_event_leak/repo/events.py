class EventBus:
    """Simple event bus with subscribe/publish."""
    
    def __init__(self):
        self._handlers = {}  # event_name -> [handler_funcs]
    
    def subscribe(self, event_name, handler):
        """Register a handler for an event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)
    
    def unsubscribe(self, event_name, handler):
        """Remove a handler for an event."""
        if event_name in self._handlers:
            # BUG: uses remove() which compares by identity for bound methods
            # but bound methods create new objects each time, so == comparison fails
            self._handlers[event_name].remove(handler)
    
    def publish(self, event_name, *args, **kwargs):
        """Publish event to all handlers."""
        if event_name not in self._handlers:
            return
        for handler in self._handlers[event_name]:
            handler(*args, **kwargs)
    
    def handler_count(self, event_name):
        """Return number of handlers for an event."""
        return len(self._handlers.get(event_name, []))


class Widget:
    """A widget that subscribes to events."""
    
    def __init__(self, name, bus):
        self.name = name
        self.bus = bus
        self.received = []
        bus.subscribe("update", self.on_update)
    
    def on_update(self, data):
        self.received.append(data)
    
    def destroy(self):
        """Clean up — unsubscribe from events."""
        self.bus.unsubscribe("update", self.on_update)
