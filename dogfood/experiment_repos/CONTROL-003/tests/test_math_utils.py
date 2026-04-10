"""Tests for math utilities."""
import pytest
from src.math_utils import (
    add, subtract, multiply, divide, power,
    modulo, is_even, is_odd, absolute_value, square
)


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0


def test_subtract():
    assert subtract(5, 3) == 2
    assert subtract(1, 1) == 0


def test_multiply():
    assert multiply(2, 3) == 6
    assert multiply(0, 5) == 0


def test_divide():
    assert divide(6, 2) == 3
    assert divide(5, 2) == 2.5


def test_divide_by_zero():
    with pytest.raises(ValueError):
        divide(1, 0)


def test_power():
    assert power(2, 3) == 8
    assert power(5, 0) == 1


def test_modulo():
    assert modulo(7, 3) == 1
    assert modulo(6, 3) == 0


def test_is_even():
    assert is_even(4) is True
    assert is_even(3) is False


def test_is_odd():
    assert is_odd(3) is True
    assert is_odd(4) is False


def test_absolute_value():
    assert absolute_value(-5) == 5
    assert absolute_value(5) == 5


def test_square():
    assert square(4) == 16
    assert square(0) == 0
