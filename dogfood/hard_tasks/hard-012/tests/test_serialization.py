"""Tests for serialization round-trip bug."""

import pytest
from datetime import datetime
from src.models import Address, Person, Company, Event
from src.serializer import Serializer, serialize_object
from src.deserializer import Deserializer, deserialize_object


def test_serializer_handles_datetime():
    """Test that serializer can serialize datetime."""
    serializer = Serializer()
    
    data = {
        "name": "Test",
        "date": datetime(2020, 1, 15, 10, 30, 0)
    }
    
    result = serializer.serialize(data)
    assert "2020-01-15T10:30:00" in result


def test_roundtrip_simple_datetime():
    """Test round-trip with simple datetime."""
    original = {"date": datetime(2020, 1, 15, 0, 0, 0)}
    
    serializer = Serializer()
    serialized = serializer.serialize(original)
    
    deserializer = Deserializer()
    deserialized = deserializer.deserialize(serialized)
    
    # BUG: This fails because serializer adds 'Z' suffix
    # deserializer doesn't properly handle it
    assert deserialized["date"] == original["date"], \
        f"Round-trip failed: {deserialized['date']} != {original['date']}"


def test_roundtrip_nested_object():
    """Test round-trip with nested objects."""
    original = Person(
        name="John Doe",
        email="john@example.com",
        birth_date=datetime(1990, 5, 15, 12, 0, 0),
        address=Address(
            street="123 Main St",
            city="Boston",
            country="USA",
            postal_code="02101"
        )
    )
    
    serializer = Serializer()
    serialized = serializer.serialize(original)
    
    deserializer = Deserializer()
    deserialized = deserializer.deserialize(serialized)
    
    # BUG: Dates don't match due to Z suffix handling
    assert deserialized.name == original.name
    assert deserialized.email == original.email
    assert deserialized.birth_date == original.birth_date, \
        f"Birth date mismatch: {deserialized.birth_date} != {original.birth_date}"
    assert deserialized.address.street == original.address.street


def test_roundtrip_company():
    """Test round-trip with Company object."""
    original = Company(
        name="Acme Corp",
        founded_date=datetime(2000, 1, 1, 9, 0, 0),
        employees=[
            Person("Alice", "alice@acme.com", datetime(1985, 3, 10)),
            Person("Bob", "bob@acme.com", datetime(1990, 7, 20))
        ],
        headquarters=Address("100 Main St", "Seattle", "USA", "98101")
    )
    
    serializer = Serializer()
    serialized = serializer.serialize(original)
    
    deserializer = Deserializer()
    deserialized = deserializer.deserialize(serialized)
    
    assert deserialized.name == original.name
    assert deserialized.founded_date == original.founded_date, \
        f"Founded date mismatch: {deserialized.founded_date} != {original.founded_date}"
    assert len(deserialized.employees) == 2
    assert deserialized.employees[0].name == "Alice"
    assert deserialized.employees[0].birth_date == original.employees[0].birth_date


def test_roundtrip_event():
    """Test round-trip with Event object."""
    original = Event(
        title="Conference",
        event_date=datetime(2024, 6, 15, 9, 0, 0),
        created_at=datetime(2024, 1, 1, 0, 0, 0)
    )
    
    serializer = Serializer()
    serialized = serializer.serialize(original)
    
    deserializer = Deserializer()
    deserialized = deserializer.deserialize(serialized)
    
    assert deserialized.title == original.title
    assert deserialized.event_date == original.event_date, \
        f"Event date mismatch: {deserialized.event_date} != {original.event_date}"
    assert deserialized.created_at == original.created_at, \
        f"Created at mismatch: {deserialized.created_at} != {original.created_at}"


def test_date_fields_variety():
    """Test with various date field names."""
    original = {
        "created_date": datetime(2020, 1, 1),
        "modified_date": datetime(2021, 6, 15),
        "start_date": datetime(2022, 3, 20),
        "end_date": datetime(2022, 3, 25),
        "timestamp": datetime(2023, 12, 31, 23, 59, 59)
    }
    
    serializer = Serializer()
    serialized = serializer.serialize(original)
    
    deserializer = Deserializer()
    deserialized = deserializer.deserialize(serialized)
    
    for key, original_value in original.items():
        assert deserialized[key] == original_value, \
            f"Mismatch for {key}: {deserialized[key]} != {original_value}"
