# Solution: Performance Issues Fix

## The Problem

### O(n²) nested loop:
```python
def search_items_nested(items, target):
    for i in range(len(all_data)):
        for j in range(len(all_data)):
            if all_data[i].get('id') == target:
                return all_data[i]
```

### Loading entire file:
```python
def load_and_search_file(filename, target_id):
    with open(filename, 'r') as f:
        data = json.load(f)  # Loads entire file
```

## The Fix

### Dict lookup O(n) → O(1):
```python
def search_items_nested(items, target):
    # Build dict once: O(n)
    item_dict = {item['id']: item for item in items}
    # Lookup: O(1)
    return item_dict.get(target)
```

### Streaming file read:
```python
import ijson

def load_and_search_file(filename, target_id):
    results = []
    with open(filename, 'rb') as f:
        # Stream JSON array
        parser = ijson.items(f, 'item')
        for item in parser:
            if item.get('id') == target_id:
                results.append(item)
                break  # Found it, can stop
    return results
```

Or with simpler line-by-line JSON:
```python
def load_and_search_file(filename, target_id):
    results = []
    with open(filename, 'r') as f:
        for line in f:
            item = json.loads(line)
            if item.get('id') == target_id:
                results.append(item)
                break
    return results
```

## Key Changes
1. Use dict lookup instead of nested loops
2. Stream file instead of loading entirely into memory
