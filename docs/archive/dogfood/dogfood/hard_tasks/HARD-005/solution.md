# Solution for HARD-005: Database Layer Corruption

## The Bug
In `src/db.py`, the `get()` method returns a direct reference to the internal dictionary, not a copy:

```python
def get(self, key: str) -> Optional[Dict]:
    return self._data.get(key)  # Returns reference, not copy!
```

When API code modifies this returned dictionary, it directly mutates the database's internal state, corrupting the stored data.

## The Fix
In `src/db.py`, change the `get()` method to return a deep copy:

```python
def get(self, key: str) -> Optional[Dict]:
    import copy
    return copy.deepcopy(self._data.get(key))
```

Or alternatively in `src/api.py`, make a copy before modifying:
```python
data = db.get(user_id)
data["name"] = "new name"  # Don't do this - mutates internal state
# Instead:
data = dict(db.get(user_id))  # Make a copy first
data["name"] = "new name"
```

## Why This Happens
Python's dictionary is a mutable object. When `db.get()` returns a reference to the internal dict, any modification to that dict affects the original stored data. This is a classic aliasing bug.

## Correct Fix Location
The bug should be fixed in `db.py` because:
1. The database layer should protect its internal state
2. Returning copies is a standard defensive programming practice
3. Fixing in api.py would require changes in every place that uses the database
