#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/intervals.py << 'PYEOF'
def merge_intervals(intervals):
    """
    Merge overlapping intervals.
    Input: list of (start, end) tuples
    Output: list of merged (start, end) tuples, sorted
    """
    if not intervals:
        return []
    
    # Sort by start time
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    
    merged = [sorted_intervals[0]]
    
    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        
        # BUG: uses < instead of <= for overlap check
        # Adjacent intervals like (1,3) and (3,5) should merge to (1,5)
        # but < misses the boundary case
        if start < last_end:
            # Overlapping — extend
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    
    return merged


def find_gaps(intervals, range_start, range_end):
    """Find gaps between intervals within a given range."""
    merged = merge_intervals(intervals)
    gaps = []
    
    current = range_start
    for start, end in merged:
        if start > current:
            gaps.append((current, start))
        current = max(current, end)
    
    if current < range_end:
        gaps.append((current, range_end))
    
    return gaps
PYEOF

cat > repo/test_intervals.py << 'PYEOF'
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
PYEOF
