# Solution: Fix Whitespace/Formatting

## The Problems

1. Mixed tabs/spaces:
```python
def greet(name):
	print(f"Hello, {name}")  # tab before 'print'
    return True  # spaces + trailing whitespace
```

2. Inconsistent indentation:
```python
def calculate_sum(numbers):
    result = 0
  for num in numbers:  # 2 spaces - inconsistent
	    result += num  # tab - inconsistent
	return result  # 1 space - inconsistent
```

## The Fix

```python
def greet(name):
    print(f"Hello, {name}")  # 4 spaces
    return True  # 4 spaces, no trailing whitespace


def calculate_sum(numbers):
    result = 0
    for num in numbers:  # 4 spaces
        result += num  # 4 spaces
    return result  # 4 spaces


def find_max(a, b):
    if a > b:
        return a  # 4 spaces
    else:
        return b  # 4 spaces
```

## Key Changes
1. Replace all tabs with 4 spaces
2. Remove trailing whitespace from all lines
3. Use consistent 4-space indentation
