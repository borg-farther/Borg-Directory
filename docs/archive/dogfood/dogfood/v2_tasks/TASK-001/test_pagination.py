"""
Tests to verify pagination logic.
"""
from pagination import get_page_boundaries, paginate_items

def test_page_1_size_10():
    """Page 1 with size 10 should return indices 0-9"""
    start, end = get_page_boundaries(1, 10)
    assert start == 0, f"Expected start=0, got {start}"
    assert end == 9, f"Expected end=9, got {end}"

def test_page_2_size_10():
    """Page 2 with size 10 should return indices 10-19"""
    start, end = get_page_boundaries(2, 10)
    assert start == 10, f"Expected start=10, got {start}"
    assert end == 19, f"Expected end=19, got {end}"

def test_paginate_items():
    """Test actual item pagination"""
    items = list(range(100))
    
    page1 = paginate_items(items, 1, 10)
    assert page1 == list(range(10)), f"Page 1 failed: {page1}"
    
    page2 = paginate_items(items, 2, 10)
    assert page2 == list(range(10, 20)), f"Page 2 failed: {page2}"
    
    page5 = paginate_items(items, 5, 10)
    assert page5 == list(range(40, 50)), f"Page 5 failed: {page5}"

def test_partial_page():
    """Test pagination when page extends past end of list"""
    items = list(range(25))
    
    page3 = paginate_items(items, 3, 10)
    # Page 3 should have items 20-24 (indices 20-24)
    assert page3 == list(range(20, 25)), f"Partial page 3 failed: {page3}"

def test_out_of_range_page():
    """Test requesting a page beyond available data"""
    items = list(range(25))
    
    result = paginate_items(items, 10, 10)
    assert result == [], f"Out of range page should return empty: {result}"

if __name__ == "__main__":
    test_page_1_size_10()
    test_page_2_size_10()
    test_paginate_items()
    test_partial_page()
    test_out_of_range_page()
    print("All tests passed!")
