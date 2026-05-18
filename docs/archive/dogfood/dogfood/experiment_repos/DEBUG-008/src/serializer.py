"""Custom JSON serializer with bugs."""
import json
from datetime import datetime, date
from decimal import Decimal


class BuggyEncoder(json.JSONEncoder):
    """Custom encoder that breaks on datetime, Decimal, and sets."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            # BUG: Should return string but raises TypeError
            return obj  # Should be obj.isoformat() but returns raw object
        if isinstance(obj, Decimal):
            # BUG: Should return float but raises TypeError
            return obj  # Should be float(obj) but returns raw object
        if isinstance(obj, set):
            # BUG: Should return list but raises TypeError
            return obj  # Should be list(obj) but returns raw object
        return super().default(obj)


def buggy_serialize(obj):
    """Serialize object to JSON string using buggy encoder."""
    return json.dumps(obj, cls=BuggyEncoder)


def serialize_with_fallback(obj):
    """
    Try to serialize, but this also fails because BuggyEncoder
    doesn't properly handle these types.
    """
    try:
        return buggy_serialize(obj)
    except TypeError as e:
        # This fallback doesn't help because the encoder is broken
        return str(obj)
