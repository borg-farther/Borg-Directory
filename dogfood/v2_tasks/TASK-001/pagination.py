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
