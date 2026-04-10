"""Data transformation functions."""

from typing import Any, Dict


def normalize_names(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize name fields to lowercase."""
    if "name" in data:
        # BUG: Mutates input in-place instead of copying
        data["name"] = data["name"].lower().strip()
    if "user" in data:
        data["user"]["name"] = data["user"]["name"].lower().strip()
    return data


def apply_discounts(data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply discount percentages to prices."""
    if "prices" in data:
        # BUG: Mutates input list in-place
        for item in data["prices"]:
            if "price" in item and "discount" in item:
                item["price"] = item["price"] * (1 - item["discount"] / 100)
    return data


def enrich_timestamps(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add formatted timestamp to data."""
    from datetime import datetime
    # BUG: Mutates input in-place
    data["processed_at"] = datetime.now().isoformat()
    return data


def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove dangerous characters from input."""
    if "comment" in data:
        # BUG: Mutates input in-place
        data["comment"] = data["comment"].replace("<script>", "").replace("</script>", "")
    return data
