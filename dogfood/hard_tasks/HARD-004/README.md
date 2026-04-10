# HARD-004: Event System Race

## Task Description
You are debugging an event processing system where a "list changed size during iteration" error occurs. The error appears in `processor.py` but the bug may be in another file.

## Problem
The event system has three components:
1. `events.py` - Event emitter that manages subscriber lists
2. `handlers.py` - Event handlers that get registered and may modify state
3. `processor.py` - Processes events and calls registered handlers

When multiple events are emitted in sequence, the application crashes with a `RuntimeError: list changed size during iteration`.

## Your Goal
Find and fix the bug so that all tests pass. The error manifests in `processor.py` but the actual cause is in how handlers interact with the event system.

## Files
- `src/events.py` - Event emitter implementation
- `src/handlers.py` - Event handler implementations
- `src/processor.py` - Event processor
- `tests/test_events.py` - Test suite

## Expected Behavior
Events should be processed without runtime errors, even when handlers modify shared state during event processing.
