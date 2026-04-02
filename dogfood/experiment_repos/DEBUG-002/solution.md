# Solution for DEBUG-002

## Bug Description
The pipeline crashes with `TypeError` when processing lists that contain `None` values. This happens because `get_user_data()` returns `None` instead of an empty dict `{}` for missing users.

## Fix

In `src/pipeline.py`, change the `get_user_data` function to return an empty dict instead of `None`:

```python
def get_user_data(user_id):
    """Fetch user data from upstream service."""
    users = {
        1: {"name": "Alice", "email": "alice@example.com"},
        2: {"name": "Bob", "email": "bob@example.com"},
    }
    # Fix: return empty dict instead of None
    return users.get(user_id, {})
```
