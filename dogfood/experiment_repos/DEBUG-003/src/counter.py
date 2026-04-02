"""Shared counter class with race condition bug."""
import threading


class Counter:
    """A shared counter - not thread-safe."""

    def __init__(self):
        self.count = 0

    def increment(self):
        """Increment the counter."""
        # Bug: read-modify-write is not atomic
        current = self.count
        # Simulate context switch by sleeping briefly
        # This is a classic race condition pattern
        import time
        time.sleep(0.0001)
        self.count = current + 1

    def get(self):
        """Get current count."""
        return self.count


def worker(counter, iterations, barrier=None):
    """Worker function that increments counter."""
    if barrier:
        barrier.wait()  # Synchronize start
    for _ in range(iterations):
        counter.increment()
