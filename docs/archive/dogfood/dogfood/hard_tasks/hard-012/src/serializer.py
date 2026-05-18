"""Custom object serializer."""

import json
from dataclasses import is_dataclass, asdict
from datetime import datetime
from typing import Any


def serialize_dataclass(obj):
    """Convert a dataclass to a dict recursively."""
    if is_dataclass(obj):
        result = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, datetime):
                # BUG: Adds Z suffix for timezone
                result[key] = value.isoformat() + "Z"
            elif is_dataclass(value):
                result[key] = serialize_dataclass(value)
            elif isinstance(value, list):
                result[key] = [
                    serialize_dataclass(item) if is_dataclass(item) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result
    elif isinstance(obj, datetime):
        return obj.isoformat() + "Z"
    return obj


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime and dataclass objects.
    
    BUG: Serializes datetime as ISO format string with timezone info (Z suffix).
    """
    
    def default(self, obj: Any) -> Any:
        if is_dataclass(obj):
            return serialize_dataclass(obj)
        if isinstance(obj, datetime):
            # BUG: Adds timezone info (Z suffix) during serialization
            # This causes mismatch with deserializer which expects naive datetime
            return obj.isoformat() + "Z"
        return super().default(obj)


class Serializer:
    """
    Custom object serializer.
    
    BUG: datetime serialization includes Z suffix, but deserializer
    expects naive datetime strings without timezone info.
    """
    
    def serialize(self, obj: Any) -> str:
        """Serialize object to JSON string."""
        return json.dumps(obj, cls=DateTimeEncoder)
    
    def serialize_to_dict(self, obj: Any) -> dict:
        """Serialize object to dict."""
        return json.loads(self.serialize(obj))


def serialize_object(obj: Any) -> str:
    """
    Convenience function to serialize an object.
    
    BUG: Uses DateTimeEncoder which appends 'Z' to datetime strings.
    """
    return json.dumps(obj, cls=DateTimeEncoder)
