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
