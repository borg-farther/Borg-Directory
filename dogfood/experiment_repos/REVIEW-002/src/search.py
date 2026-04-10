"""Search function with O(n²) performance issues."""
import json


def search_items_linear(items, target):
    """
    Search for target in items - O(n) using dict lookup.
    THIS IS THE FIX - should be efficient.
    """
    item_dict = {item['id']: item for item in items}
    return item_dict.get(target)


def find_items_by_field(items, field_name, field_value):
    """
    Find all items matching a field value - O(n).
    THIS IS THE FIX - simple loop.
    """
    results = []
    for item in items:
        if item.get(field_name) == field_value:
            results.append(item)
    return results


def search_items_nested(items, target):
    """
    Search for target - O(n²) PROBLEM.
    Loads entire file into memory and uses nested loops.
    """
    # Load entire dataset into memory (not necessary)
    all_data = []
    for item in items:
        all_data.append(item)

    # Nested loop - O(n²)
    for i in range(len(all_data)):
        for j in range(len(all_data)):
            if all_data[i].get('id') == target:
                return all_data[i]

    return None


def load_and_search_file(filename, target_id):
    """
    Load entire file into memory then search - O(n²).
    Should use streaming.
    """
    with open(filename, 'r') as f:
        # Load entire file - problem for large files
        data = json.load(f)

    # Nested loop - O(n²)
    results = []
    for item in data:
        if item.get('id') == target_id:
            results.append(item)

    return results
