"""Data validation between transforms."""

from typing import Any, Dict, List


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


def validate_required_fields(data: Dict[str, Any], required: List[str]) -> None:
    """Validate that required fields are present."""
    for field in required:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")


def validate_no_nulls(data: Dict[str, Any]) -> None:
    """Validate that no null values exist in top-level fields."""
    for key, value in data.items():
        if value is None:
            raise ValidationError(f"Null value found in field: {key}")


def validate_price_range(data: Dict[str, Any]) -> None:
    """Validate that prices are within acceptable range."""
    if "prices" in data:
        for item in data["prices"]:
            if "price" in item and item["price"] < 0:
                raise ValidationError("Negative price not allowed")
