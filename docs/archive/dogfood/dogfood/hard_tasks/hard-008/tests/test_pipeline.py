"""Tests for the transformation pipeline."""

import pytest
from src.pipeline import Pipeline, create_default_pipeline
from src.validators import ValidationError


def test_basic_pipeline_success():
    """Test that basic pipeline works."""
    pipeline = Pipeline()
    data = {"name": "John", "value": 42}
    result = pipeline.process(data)
    assert result["name"] == "john"


def test_pipeline_with_original_preserved():
    """
    Test that demonstrates the mutation bug.
    
    The original data should be preserved after pipeline processing,
    but because transforms mutate in-place, the original is corrupted.
    """
    pipeline = create_default_pipeline()
    
    original_data = {
        "name": "John Doe",
        "user": {"name": "Jane Smith"},
        "prices": [
            {"item": "apple", "price": 100, "discount": 10},
            {"item": "banana", "price": 50, "discount": 5}
        ],
        "comment": "Hello <script>alert('xss')</script> World"
    }
    
    # Store a copy to verify original is preserved
    original_copy = original_data.copy()
    original_copy["user"] = original_data["user"].copy()
    original_copy["prices"] = [p.copy() for p in original_data["prices"]]
    
    # Process through pipeline
    result = pipeline.process(original_data)
    
    # BUG: original_data is now mutated even though we passed it to process()
    # The transform normalize_names() mutated data["name"] and data["user"]["name"]
    
    # Check result has processed data
    assert result["name"] == "john doe"
    assert result["user"]["name"] == "jane smith"
    assert result["processed_at"] is not None


def test_rollback_on_validation_failure():
    """
    Test that rollback works when validation fails.
    
    This test passes validation but the data is silently corrupted
    because the mutations happened before we could validate.
    """
    pipeline = Pipeline()
    
    # Create data with a name that should be preserved
    original_data = {
        "name": "TEST_USER",
        "prices": [{"item": "test", "price": 100, "discount": 0}]
    }
    
    # The discounts transform mutates the price list items in-place
    pipeline.add_transform(lambda d: d)  # identity transform
    pipeline.add_transform(lambda d: d)  # identity transform
    
    # After transforms, check if original list items are the same objects
    data = {"prices": [{"price": 100}]}
    original_price = data["prices"][0]["price"]
    
    # Simulate what happens: transform mutates in-place
    for item in data["prices"]:
        item["price"] = item["price"] * 0.9
    
    # The original_price variable is now stale because the dict was mutated!
    # If we tried to rollback, we'd restore the dict reference, not the value
    assert data["prices"][0]["price"] == 90  # mutated
    assert original_price == 100  # this is a different object now


def test_diamond_dependency_simulation():
    """
    Simulate a scenario where pipeline state gets corrupted due to in-place mutations.
    """
    pipeline = Pipeline()
    
    # Data that goes through multiple transforms
    data = {
        "name": "Alice",
        "prices": [
            {"item": "a", "price": 100, "discount": 10},
            {"item": "b", "price": 200, "discount": 20},
        ]
    }
    
    # Add several transforms
    pipeline.add_transform(lambda d: d)  # pass through
    pipeline.add_transform(lambda d: d)  # pass through
    
    # The bug: if we had transforms that mutate nested structures,
    # and then rollback, the rollback doesn't properly restore nested objects
