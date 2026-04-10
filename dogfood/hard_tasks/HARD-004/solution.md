# Solution for HARD-004: Event System Race

## The Bug
In `src/handlers.py`, the `handle_event_B` function modifies the global subscriber list during event processing. When `handle_event_B` is called as a handler, it removes a subscriber from `events.subscribers` while the event loop is still iterating over that same list.

## The Fix
Two possible fixes:

### Fix 1 (handlers.py): Don't modify subscriber list during event handling
Change `handle_event_B` to not modify `events.subscribers` directly during event processing. Instead, queue the changes for after event processing completes.

### Fix 2 (events.py): Iterate over a copy of the subscriber list
Change the `emit` method in `events.py` to iterate over a copy:
```python
def emit(self, event_name: str, data: Any) -> None:
    for handler in list(self.subscribers):  # Create a copy of the list
        handler(event_name, data)
```

## Why This Works
The error occurs because Python doesn't allow modifying a list while iterating over it. By creating a copy with `list(self.subscribers)`, we iterate over a snapshot while the original list can be safely modified.

## Root Cause
`handle_event_B` calls `events.unsubscribe(handle_event_A)` during event processing, which modifies `events.subscribers` while `emit()` is still iterating over it.
