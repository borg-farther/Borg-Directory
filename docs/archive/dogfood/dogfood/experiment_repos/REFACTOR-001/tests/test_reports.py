"""Tests for report generation."""
import pytest
from reports import generate_user_report, generate_sales_report, generate_inventory_report


def test_user_report_format():
    """User report should have correct structure."""
    users = [
        {"name": "Alice", "email": "alice@example.com", "status": "active"},
        {"name": "Bob", "email": "bob@example.com"},
    ]
    report = generate_user_report(users)

    assert "USER ACTIVITY REPORT" in report
    assert "Alice" in report
    assert "Bob" in report
    assert "alice@example.com" in report
    assert "Total Users: 2" in report
    assert "END OF REPORT" in report


def test_sales_report_format():
    """Sales report should have correct structure."""
    sales = [
        {"product": "Widget", "amount": 100, "region": "North"},
        {"product": "Gadget", "amount": 200},
    ]
    report = generate_sales_report(sales)

    assert "SALES PERFORMANCE REPORT" in report
    assert "Widget" in report
    assert "Gadget" in report
    assert "$100" in report
    assert "Total Sales: $300" in report
    assert "END OF REPORT" in report


def test_inventory_report_format():
    """Inventory report should have correct structure."""
    items = [
        {"name": "Apple", "quantity": 50, "category": "Fruit"},
        {"name": "Banana", "quantity": 30},
    ]
    report = generate_inventory_report(items)

    assert "INVENTORY STATUS REPORT" in report
    assert "Apple" in report
    assert "Banana" in report
    assert "Quantity: 50" in report
    assert "Total Items: 2" in report
    assert "END OF REPORT" in report


def test_empty_user_report():
    """Empty user report should still be valid."""
    report = generate_user_report([])
    assert "USER ACTIVITY REPORT" in report
    assert "Total Users: 0" in report


def test_empty_sales_report():
    """Empty sales report should still be valid."""
    report = generate_sales_report([])
    assert "SALES PERFORMANCE REPORT" in report
    assert "Total Sales: $0" in report
