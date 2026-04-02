# Solution: Add Docstrings

## Example Fix

```python
def add(a, b):
    """Add two numbers.

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of a and b
    """
    return a + b


def divide(a, b):
    """Divide two numbers.

    Args:
        a: Dividend
        b: Divisor

    Returns:
        The result of a divided by b

    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

## All Functions to Document
1. add(a, b)
2. subtract(a, b)
3. multiply(a, b)
4. divide(a, b)
5. power(base, exponent)
6. modulo(a, b)
7. is_even(n)
8. is_odd(n)
9. absolute_value(n)
10. square(n)
