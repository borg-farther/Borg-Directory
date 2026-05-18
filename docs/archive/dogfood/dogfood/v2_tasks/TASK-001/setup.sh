#!/bin/bash
# TASK-001: Off-by-one error in pagination logic

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/pagination.py << 'EOF'
"""
Pagination module for retrieving paginated results.
"""

def get_page_boundaries(page_num, page_size):
    """
    Calculate start and end indices for a given page number.
    Page numbers are 1-indexed.
    
    Returns: (start_idx, end_idx) - both inclusive
    """
    if page_num < 1:
        raise ValueError("Page number must be >= 1")
    if page_size < 1:
        raise ValueError("Page size must be >= 1")
    
    # Bug: off-by-one error - page 1 should start at index 0, but uses page_num * page_size
    start_idx = page_num * page_size
    end_idx = start_idx + page_size - 1
    
    return start_idx, end_idx


def paginate_items(items, page_num, page_size):
    """
    Return the items for a specific page.
    """
    start_idx, end_idx = get_page_boundaries(page_num, page_size)
    
    if start_idx >= len(items):
        return []
    
    # Cap end_idx to available items
    end_idx = min(end_idx, len(items) - 1)
    
    return items[start_idx:end_idx + 1]
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/test_pagination.py << 'EOF'
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
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/check.sh << 'EOF'
#!/bin/bash
cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001
python test_pagination.py
EOF
chmod +x /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/check.sh

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/prompt.txt << 'EOF'
## Task: Fix Pagination Bug

A pagination module has a bug where page boundaries are calculated incorrectly.

### Files to examine:
- `pagination.py` - Contains the pagination logic with the bug
- `test_pagination.py` - Contains test cases that demonstrate the expected behavior

### Your task:
The `get_page_boundaries` function in `pagination.py` calculates wrong indices for pages. Currently:
- Page 1, size 10: returns (10, 19) instead of (0, 9)
- Page 2, size 10: returns (20, 29) instead of (10, 19)

The bug causes all pages to return empty results or wrong items.

Fix the `get_page_boundaries` function so all tests pass.
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/trace.txt << 'EOF'
## Reasoning Trace

### Understanding the Problem
The pagination function uses 1-indexed page numbers (page 1 is the first page), but the index calculation seems wrong.

### Key Observation
The formula `start_idx = page_num * page_size` is incorrect. For page 1 with size 10:
- Current: 1 * 10 = 10 (wrong!)
- Expected: 0

### Hint
Think about what the correct formula should be. For 1-indexed pages:
- Page 1 should start at index 0
- Page 2 should start at index 10
- Page n should start at index (n-1) * page_size

### Approach
Look at how `start_idx` is calculated and fix the formula. The fix is in the first line of the calculation in `get_page_boundaries`.
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-001/solution.txt << 'EOF'
## Solution

The bug is in the `get_page_boundaries` function in `pagination.py`.

### The Problem
```python
start_idx = page_num * page_size  # Bug: 1 * 10 = 10, should be 0
```

### The Fix
```python
start_idx = (page_num - 1) * page_size  # Correct: (1-1) * 10 = 0
```

### Explanation
For 1-indexed page numbers:
- Page 1 should start at index 0: (1-1) * page_size = 0
- Page 2 should start at index page_size: (2-1) * page_size = 10
- Page n should start at index (n-1) * page_size

The end_idx calculation `start_idx + page_size - 1` is correct once start_idx is fixed.
EOF
