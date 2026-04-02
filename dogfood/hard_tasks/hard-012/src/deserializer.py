"""Custom object deserializer."""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict


class Deserializer:
    """
    Custom object deserializer.
    
    BUG: Does not properly handle the 'Z' suffix on datetime strings.
    When datetime string has Z suffix (added by serializer), parsing
    produces a datetime with UTC timezone, but original was naive.
    """
    
    def deserialize(self, json_str: str) -> Any:
        """
        Deserialize JSON string to Python object.
        """
        def parse_value(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: parse_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [parse_value(item) for item in value]
            elif isinstance(value, str):
                # Try to parse as datetime
                dt = try_parse_datetime(value)
                if dt is not None:
                    return dt
                return value
            else:
                return value
        
        def try_parse_datetime(value: str) -> datetime | None:
            """
            Try to parse a string as ISO datetime.
            
            BUG: Only handles naive datetime parsing. When serializer
            adds 'Z' suffix, this produces different results.
            """
            # Check if it looks like ISO datetime
            iso_pattern = r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}'
            if not re.match(iso_pattern, value):
                return None
            
            try:
                # BUG: This only handles naive datetime
                # When serializer produces "2020-01-15T00:00:00Z", 
                # this fails or produces wrong result
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        
        data = json.loads(json_str)
        return parse_value(data)


def deserialize_object(json_str: str) -> Any:
    """
    Convenience function to deserialize.
    """
    deserializer = Deserializer()
    return deserializer.deserialize(json_str)
