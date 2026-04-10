"""Tests for JSON serializer - verifies datetime, Decimal, set handling."""
import pytest
import json
from datetime import datetime, date
from decimal import Decimal
from src.serializer import buggy_serialize


def test_serialize_datetime():
    """Test that datetime objects serialize correctly."""
    dt = datetime(2024, 1, 15, 10, 30, 0)
    result = buggy_serialize({'timestamp': dt})

    # Should be valid JSON with string value
    parsed = json.loads(result)
    assert parsed['timestamp'] == '2024-01-15T10:30:00'


def test_serialize_date():
    """Test that date objects serialize correctly."""
    d = date(2024, 1, 15)
    result = buggy_serialize({'date': d})

    # Should be valid JSON with string value
    parsed = json.loads(result)
    assert parsed['date'] == '2024-01-15'


def test_serialize_decimal():
    """Test that Decimal objects serialize correctly."""
    value = Decimal('19.99')
    result = buggy_serialize({'price': value})

    # Should be valid JSON with numeric value
    parsed = json.loads(result)
    assert parsed['price'] == 19.99
    assert isinstance(parsed['price'], float)


def test_serialize_set():
    """Test that set objects serialize correctly."""
    s = {'apple', 'banana', 'cherry'}
    result = buggy_serialize({'items': s})

    # Should be valid JSON with list value
    parsed = json.loads(result)
    assert isinstance(parsed['items'], list)
    assert set(parsed['items']) == {'apple', 'banana', 'cherry'}


def test_serialize_mixed():
    """Test serialization of mixed types."""
    data = {
        'name': 'Test',
        'created': datetime(2024, 1, 15, 10, 30, 0),
        'price': Decimal('29.99'),
        'tags': {'python', 'json', 'testing'},
        'active': True
    }
    result = buggy_serialize(data)

    # Should be valid JSON
    parsed = json.loads(result)
    assert parsed['name'] == 'Test'
    assert parsed['created'] == '2024-01-15T10:30:00'
    assert parsed['price'] == 29.99
    assert set(parsed['tags']) == {'python', 'json', 'testing'}
    assert parsed['active'] is True
