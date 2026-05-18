"""Tests for search function - correctness and performance."""
import pytest
import time
import json
import os
from src.search import (
    search_items_linear,
    find_items_by_field,
    search_items_nested,
    load_and_search_file
)


def test_search_items_linear():
    """Test linear search correctness."""
    items = [
        {'id': 1, 'name': 'a'},
        {'id': 2, 'name': 'b'},
        {'id': 3, 'name': 'c'},
    ]

    result = search_items_linear(items, 2)
    assert result == {'id': 2, 'name': 'b'}

    result = search_items_linear(items, 99)
    assert result is None


def test_find_items_by_field():
    """Test finding items by field."""
    items = [
        {'id': 1, 'category': 'a'},
        {'id': 2, 'category': 'b'},
        {'id': 3, 'category': 'a'},
    ]

    results = find_items_by_field(items, 'category', 'a')
    assert len(results) == 2
    assert all(r['category'] == 'a' for r in results)


def test_performance_100k_items():
    """Test that search completes in < 1 second for 100K items."""
    # Generate 100K items
    items = [{'id': i, 'name': f'item_{i}'} for i in range(100000)]

    # Test the nested (bad) version
    start = time.time()
    result = search_items_nested(items, 99999)
    elapsed = time.time() - start

    assert result is not None
    assert elapsed < 1.0, f"Search took {elapsed:.2f}s, expected < 1s (O(n²) problem)"

    # Test the linear (good) version for comparison
    start = time.time()
    result = search_items_linear(items, 99999)
    elapsed_linear = time.time() - start

    assert result is not None
    assert elapsed_linear < 0.1, f"Linear search took {elapsed_linear:.2f}s, too slow"


def test_file_search_performance(tmp_path):
    """Test file search with 100K items - should use streaming."""
    # Create test file with 100K items
    test_file = tmp_path / "test_data.json"
    with open(test_file, 'w') as f:
        json.dump([{'id': i, 'name': f'item_{i}'} for i in range(100000)], f)

    start = time.time()
    results = load_and_search_file(str(test_file), 99999)
    elapsed = time.time() - start

    assert len(results) == 1
    assert results[0]['id'] == 99999
    assert elapsed < 1.0, f"File search took {elapsed:.2f}s, expected < 1s"
