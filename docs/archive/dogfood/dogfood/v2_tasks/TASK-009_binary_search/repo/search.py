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
