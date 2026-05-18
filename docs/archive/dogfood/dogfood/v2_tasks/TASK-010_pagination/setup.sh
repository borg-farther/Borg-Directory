#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/paginator.py << 'PYEOF'
class Paginator:
    """Paginate a list of items."""
    
    def __init__(self, items, page_size=10):
        self.items = items
        self.page_size = page_size
    
    @property
    def total_pages(self):
        """Total number of pages."""
        # BUG: integer division drops remainder
        return len(self.items) // self.page_size
    
    def get_page(self, page_num):
        """Get items for a page (1-indexed). Returns (items, metadata)."""
        if page_num < 1 or page_num > self.total_pages:
            return [], {"page": page_num, "total_pages": self.total_pages, "error": "invalid page"}
        
        # BUG: off-by-one in start index for page > 1
        start = (page_num - 1) * self.page_size
        end = start + self.page_size
        
        items = self.items[start:end]
        return items, {
            "page": page_num,
            "total_pages": self.total_pages,
            "has_next": page_num < self.total_pages,
            "has_prev": page_num > 1,
            "total_items": len(self.items)
        }
PYEOF

cat > repo/test_paginator.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from paginator import Paginator

def test_total_pages():
    """11 items with page_size=5 should have 3 pages."""
    p = Paginator(list(range(11)), page_size=5)
    assert p.total_pages == 3, f"Expected 3, got {p.total_pages}"

def test_total_pages_exact():
    """10 items with page_size=5 should have 2 pages."""
    p = Paginator(list(range(10)), page_size=5)
    assert p.total_pages == 2, f"Expected 2, got {p.total_pages}"

def test_last_page_partial():
    """Last page should contain remaining items."""
    p = Paginator(list(range(11)), page_size=5)
    items, meta = p.get_page(3)
    assert items == [10], f"Expected [10], got {items}"

def test_first_page():
    p = Paginator(list(range(20)), page_size=5)
    items, meta = p.get_page(1)
    assert items == [0,1,2,3,4], f"Expected [0,1,2,3,4], got {items}"
    assert meta["has_next"] == True
    assert meta["has_prev"] == False

def test_has_next_last_page():
    p = Paginator(list(range(11)), page_size=5)
    items, meta = p.get_page(3)
    assert meta["has_next"] == False, f"Last page should not have next"

def test_single_item():
    p = Paginator([42], page_size=10)
    assert p.total_pages == 1
    items, meta = p.get_page(1)
    assert items == [42]

if __name__ == "__main__":
    tests = [test_total_pages, test_total_pages_exact, test_last_page_partial, 
             test_first_page, test_has_next_last_page, test_single_item]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
