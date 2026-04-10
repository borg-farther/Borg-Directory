"""Report generation with duplicate code - needs refactoring."""
from datetime import datetime


def generate_user_report(users):
    """Generate user activity report."""
    # Header
    lines = []
    lines.append("=" * 60)
    lines.append("USER ACTIVITY REPORT")
    lines.append("Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append("=" * 60)
    lines.append("")

    # Body
    for user in users:
        lines.append("User: " + user['name'])
        lines.append("  Email: " + user['email'])
        lines.append("  Status: " + user.get('status', 'active'))
        lines.append("  Last Login: " + user.get('last_login', 'never'))
        lines.append("-" * 40)

    # Footer
    lines.append("")
    lines.append("Total Users: " + str(len(users)))
    lines.append("END OF REPORT")

    return "\n".join(lines)


def generate_sales_report(sales):
    """Generate sales performance report."""
    # Header
    lines = []
    lines.append("=" * 60)
    lines.append("SALES PERFORMANCE REPORT")
    lines.append("Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append("=" * 60)
    lines.append("")

    # Body
    for sale in sales:
        lines.append("Product: " + sale['product'])
        lines.append("  Amount: $" + str(sale['amount']))
        lines.append("  Region: " + sale.get('region', 'unknown'))
        lines.append("  Date: " + sale.get('date', 'n/a'))
        lines.append("-" * 40)

    # Footer
    lines.append("")
    total = sum(s['amount'] for s in sales)
    lines.append("Total Sales: $" + str(total))
    lines.append("END OF REPORT")

    return "\n".join(lines)


def generate_inventory_report(items):
    """Generate inventory status report."""
    # Header
    lines = []
    lines.append("=" * 60)
    lines.append("INVENTORY STATUS REPORT")
    lines.append("Generated: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append("=" * 60)
    lines.append("")

    # Body
    for item in items:
        lines.append("Item: " + item['name'])
        lines.append("  Quantity: " + str(item['quantity']))
        lines.append("  Category: " + item.get('category', 'uncategorized'))
        lines.append("  Reorder Level: " + item.get('reorder_level', 'n/a'))
        lines.append("-" * 40)

    # Footer
    lines.append("")
    lines.append("Total Items: " + str(len(items)))
    lines.append("END OF REPORT")

    return "\n".join(lines)
