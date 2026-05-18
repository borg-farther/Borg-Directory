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
