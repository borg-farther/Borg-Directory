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
