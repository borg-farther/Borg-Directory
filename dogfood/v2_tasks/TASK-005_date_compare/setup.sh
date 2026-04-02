#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/scheduler.py << 'PYEOF'
from datetime import datetime, timezone, timedelta

class Scheduler:
    """Schedule events and check which are due."""
    
    def __init__(self):
        self.events = []
    
    def add_event(self, name, due_at):
        """Add event with a due datetime."""
        self.events.append({"name": name, "due_at": due_at})
    
    def get_due_events(self, now=None):
        """Return events that are due (due_at <= now)."""
        if now is None:
            now = datetime.now()  # BUG: naive datetime
        
        due = []
        for event in self.events:
            # BUG: comparing naive and aware datetimes raises TypeError
            # but only when mixed — if all naive or all aware, it works
            if event["due_at"] <= now:
                due.append(event["name"])
        return due
    
    def get_next_event(self):
        """Return the soonest upcoming event."""
        if not self.events:
            return None
        
        now = datetime.now()  # BUG: naive datetime again
        future = [e for e in self.events if e["due_at"] > now]
        if not future:
            return None
        
        # BUG: min comparison also fails with mixed tz
        return min(future, key=lambda e: e["due_at"])["name"]
PYEOF

cat > repo/test_scheduler.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from datetime import datetime, timezone, timedelta
from scheduler import Scheduler

def test_aware_datetimes():
    """Events with timezone-aware datetimes should work."""
    s = Scheduler()
    now = datetime.now(timezone.utc)
    s.add_event("past", now - timedelta(hours=1))
    s.add_event("future", now + timedelta(hours=1))
    
    due = s.get_due_events(now)
    assert due == ["past"], f"Expected ['past'], got {due}"

def test_get_next_with_aware():
    """get_next_event should work with timezone-aware datetimes."""
    s = Scheduler()
    now = datetime.now(timezone.utc)
    s.add_event("soon", now + timedelta(minutes=5))
    s.add_event("later", now + timedelta(hours=2))
    
    nxt = s.get_next_event()
    assert nxt == "soon", f"Expected 'soon', got {nxt}"

def test_mixed_not_crash():
    """Should handle all events consistently using UTC."""
    s = Scheduler()
    now = datetime.now(timezone.utc)
    s.add_event("e1", now - timedelta(hours=1))
    s.add_event("e2", now + timedelta(hours=1))
    
    # Should not raise TypeError
    due = s.get_due_events()
    assert "e1" in due, f"e1 should be due"
    assert "e2" not in due, f"e2 should not be due"

if __name__ == "__main__":
    tests = [test_aware_datetimes, test_get_next_with_aware, test_mixed_not_crash]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
