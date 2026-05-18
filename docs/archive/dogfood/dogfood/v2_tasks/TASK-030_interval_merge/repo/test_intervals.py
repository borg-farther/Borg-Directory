import sys
sys.path.insert(0, '.')
from intervals import merge_intervals, find_gaps

def test_overlapping():
    result = merge_intervals([(1,3), (2,5), (7,9)])
    assert result == [(1,5), (7,9)], f"Got: {result}"

def test_adjacent():
    """Adjacent intervals should merge: (1,3) and (3,5) -> (1,5)."""
    result = merge_intervals([(1,3), (3,5)])
    assert result == [(1,5)], f"Adjacent not merged: {result}"

def test_contained():
    result = merge_intervals([(1,10), (3,5)])
    assert result == [(1,10)], f"Got: {result}"

def test_no_overlap():
    result = merge_intervals([(1,2), (4,5)])
    assert result == [(1,2), (4,5)], f"Got: {result}"

def test_gaps():
    result = find_gaps([(1,3), (5,7)], 0, 10)
    assert result == [(0,1), (3,5), (7,10)], f"Got: {result}"

def test_empty():
    assert merge_intervals([]) == []

if __name__ == "__main__":
    tests = [test_overlapping, test_adjacent, test_contained, test_no_overlap, test_gaps, test_empty]
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
