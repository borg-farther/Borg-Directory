# Solution for DEBUG-003

## Bug Description
The `Counter` class has a race condition. The `increment()` method does a read-modify-write that is not atomic:

```python
current = self.count  # read
self.count = current + 1  # modify-write
```

When multiple threads call `increment()` concurrently, they can all read the same value before any writes happen, causing lost updates.

## Fix

Add a `threading.Lock` to make the increment operation atomic:

```python
import threading

class Counter:
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            current = self.count
            self.count = current + 1

    def get(self):
        return self.count
```

Or use a simpler approach with `threading.Lock` protecting the entire operation:

```python
def increment(self):
    with self._lock:
        self.count += 1
```
