"""Tests for thread-safe counter."""
import pytest
import threading
from counter import Counter, worker


def test_counter_single_thread():
    """Single-threaded increment works correctly."""
    counter = Counter()
    counter.increment()
    counter.increment()
    counter.increment()
    assert counter.get() == 3


def test_counter_multi_thread_exact_count():
    """Multi-threaded counter should have exact count."""
    counter = Counter()
    num_threads = 10
    iterations_per_thread = 100

    # Barrier to ensure all threads start at the same time
    barrier = threading.Barrier(num_threads)

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(counter, iterations_per_thread, barrier))
        threads.append(t)

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # With proper thread safety, count should be exactly num_threads * iterations
    expected = num_threads * iterations_per_thread
    assert counter.get() == expected, f"Expected {expected}, got {counter.get()}"
