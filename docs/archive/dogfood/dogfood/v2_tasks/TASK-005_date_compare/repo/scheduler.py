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
