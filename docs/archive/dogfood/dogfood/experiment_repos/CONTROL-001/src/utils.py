"""Utility functions."""
import json


def to_json(obj):
    """Convert object to JSON."""
    return json.dumps(obj)


def from_json(s):
    """Parse JSON string."""
    return json.loads(s)
