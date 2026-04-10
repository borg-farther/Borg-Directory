"""Tests for messy code - functionality tests."""
import pytest
from src.messy import greet, calculate_sum, process_data, find_max, Calculator


def test_greet():
    result = greet("World")
    assert result is True


def test_calculate_sum():
    assert calculate_sum([1, 2, 3, 4, 5]) == 15
    assert calculate_sum([]) == 0


def test_process_data():
    assert process_data([1, -2, 3, -4]) == [2, 0, 6, 0]
    assert process_data([]) == []


def test_find_max():
    assert find_max(5, 3) == 5
    assert find_max(2, 7) == 7
    assert find_max(5, 5) == 5


def test_calculator():
    calc = Calculator()
    assert calc.value == 0
    calc.add(5)
    assert calc.value == 5
    calc.subtract(2)
    assert calc.value == 3
