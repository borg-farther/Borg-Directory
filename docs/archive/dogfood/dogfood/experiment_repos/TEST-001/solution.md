# Solution for TEST-001

## Task
Write comprehensive tests for the calculator in `tests/test_calculator.py`.

The tests must achieve:
- At least 8 tests
- At least 80% code coverage

## Suggested Test Cases

```python
import pytest
from calculator import add, subtract, multiply, divide


class TestCalculator:
    def test_add_positive_numbers(self):
        assert add(2, 3) == 5

    def test_add_negative_numbers(self):
        assert add(-1, -1) == -2

    def test_add_mixed_signs(self):
        assert add(-5, 3) == -2

    def test_add_zeros(self):
        assert add(0, 0) == 0

    def test_subtract(self):
        assert subtract(10, 3) == 7

    def test_subtract_negative_result(self):
        assert subtract(3, 10) == -7

    def test_multiply(self):
        assert multiply(4, 5) == 20

    def test_multiply_by_zero(self):
        assert multiply(100, 0) == 0

    def test_divide(self):
        assert divide(10, 2) == 5

    def test_divide_by_zero_raises(self):
        with pytest.raises(ValueError):
            divide(1, 0)

    def test_divide_float(self):
        assert divide(7, 2) == 3.5
```
