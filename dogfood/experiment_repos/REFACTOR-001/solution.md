# Solution for REFACTOR-001

## Task
Extract the duplicated code in `src/reports.py` into a shared helper function.

## The Problem
All three report functions have ~80% identical code:
- Header generation (border, title, timestamp)
- Footer generation (totals, end marker)
- Item formatting with dashed separators

## Solution

```python
from datetime import datetime


def _generate_report_header(title):
    """Generate common report header."""
    lines = []
    lines.append("=" * 60)
    lines.append(title)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    return lines


def _generate_report_footer(items, total_label):
    """Generate common report footer."""
    lines = []
    lines.append("")
    lines.append(total_label)
    lines.append("END OF REPORT")
    return lines


def _format_item_lines(item, field_configs):
    """Format a single item's fields."""
    lines = []
    for label, key in field_configs:
        lines.append(f"  {label}: {item.get(key, 'n/a')}")
    lines.append("-" * 40)
    return lines


def generate_user_report(users):
    """Generate user activity report."""
    lines = _generate_report_header("USER ACTIVITY REPORT")

    for user in users:
        lines.append(f"User: {user['name']}")
        lines.extend(_format_item_lines(user, [
            ("Email", "email"),
            ("Status", "status"),
            ("Last Login", "last_login"),
        ]))

    lines.extend(_generate_report_footer(users, f"Total Users: {len(users)}"))
    return "\n".join(lines)


def generate_sales_report(sales):
    """Generate sales performance report."""
    lines = _generate_report_header("SALES PERFORMANCE REPORT")

    for sale in sales:
        lines.append(f"Product: {sale['product']}")
        lines.extend(_format_item_lines(sale, [
            ("Amount", "amount"),
            ("Region", "region"),
            ("Date", "date"),
        ]))

    total = sum(s['amount'] for s in sales)
    lines.extend(_generate_report_footer(sales, f"Total Sales: ${total}"))
    return "\n".join(lines)


def generate_inventory_report(items):
    """Generate inventory status report."""
    lines = _generate_report_header("INVENTORY STATUS REPORT")

    for item in items:
        lines.append(f"Item: {item['name']}")
        lines.extend(_format_item_lines(item, [
            ("Quantity", "quantity"),
            ("Category", "category"),
            ("Reorder Level", "reorder_level"),
        ]))

    lines.extend(_generate_report_footer(items, f"Total Items: {len(items)}"))
    return "\n".join(lines)
```
