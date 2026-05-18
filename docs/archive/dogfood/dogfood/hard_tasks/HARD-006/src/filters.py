"""Filter functions for template rendering."""
from typing import Any


def upper_filter(value: Any) -> str:
    """Convert value to uppercase string."""
    return str(value).upper()


def lower_filter(value: Any) -> str:
    """Convert value to lowercase string."""
    return str(value).lower()


def default_filter(value: Any, default_value: Any) -> Any:
    """Return default value if value is None or empty.

    BUG: The check 'if not value:' treats 0 and empty string as falsy,
    which may not be the intended behavior. If someone passes 0 as a
    valid value, it will be replaced with the default.
    """
    if value is None:
        return default_value
    # BUG: This treats 0 and "" as falsy and replaces them
    if not value:
        return default_value
    return value


def capitalize_filter(value: Any) -> str:
    """Capitalize the first character of value."""
    s = str(value)
    return s[0].upper() + s[1:] if len(s) > 0 else s


def strip_filter(value: Any) -> str:
    """Strip whitespace from value."""
    return str(value).strip()
