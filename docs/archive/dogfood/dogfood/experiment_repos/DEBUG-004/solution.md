# Solution for DEBUG-004

## Bug Description
There's a circular import between `models.py` and `utils.py`:
- `models.py` imports from `utils.py`
- `utils.py` imports from `models.py`

This causes an `ImportError` when trying to import either module.

## Fix

Create a new file `src/common.py` with shared utilities:

```python
"""Common utilities shared between modules."""
from datetime import datetime


def format_timestamp():
    """Format current time as ISO string."""
    return datetime.now().isoformat()
```

Then update `utils.py` to import from `common.py` instead of `models.py`:

```python
"""Utils module - no more import cycle."""
from common import format_timestamp


def create_user(id, name, email):
    """Factory function to create User instance."""
    from models import User
    return User(id, name, email)
```

And update `models.py` to import from `common.py`:

```python
"""Models module."""
from common import format_timestamp
```

This breaks the cycle by introducing a third module that both import from.
