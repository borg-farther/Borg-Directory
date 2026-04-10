#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/search.py << 'PYEOF'
def binary_search(arr, target):
    """Find index of target in sorted array. Returns -1 if not found."""
    if not arr:
        return -1
    
    left = 0
    right = len(arr)  # BUG: should be len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:  # BUG: can IndexError when right = len(arr)
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1


def find_insertion_point(arr, target):
    """Find the index where target should be inserted to maintain sorted order."""
    if not arr:
        return 0
    
    left = 0
    right = len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] < target:
            left = mid + 1
        elif arr[mid] > target:
            right = mid - 1
        else:
            return mid  # BUG: should return mid for exact match, but doesn't handle duplicates
    
    return left


def find_first_occurrence(arr, target):
    """Find index of first occurrence of target in sorted array with duplicates."""
    if not arr:
        return -1
    
    left = 0
    right = len(arr) - 1
    result = -1
    
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            result = mid
            right = mid - 1  # Keep searching left
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid  # BUG: should be mid - 1, causes infinite loop
    
    return result
PYEOF

cat > repo/test_search.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from search import binary_search, find_insertion_point, find_first_occurrence

def test_basic_search():
    assert binary_search([1,2,3,4,5], 3) == 2
    assert binary_search([1,2,3,4,5], 1) == 0
    assert binary_search([1,2,3,4,5], 5) == 4
    assert binary_search([1,2,3,4,5], 6) == -1

def test_search_single():
    assert binary_search([42], 42) == 0
    assert binary_search([42], 99) == -1

def test_search_empty():
    assert binary_search([], 1) == -1

def test_insertion_point():
    assert find_insertion_point([1,3,5,7], 4) == 2
    assert find_insertion_point([1,3,5,7], 0) == 0
    assert find_insertion_point([1,3,5,7], 8) == 4

def test_first_occurrence():
    arr = [1, 2, 2, 2, 3, 4]
    result = find_first_occurrence(arr, 2)
    assert result == 1, f"Expected 1, got {result}"

def test_first_occurrence_not_found():
    result = find_first_occurrence([1,3,5], 2)
    assert result == -1, f"Expected -1, got {result}"

if __name__ == "__main__":
    import signal
    signal.alarm(5)
    
    tests = [test_basic_search, test_search_single, test_search_empty, 
             test_insertion_point, test_first_occurrence, test_first_occurrence_not_found]
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
