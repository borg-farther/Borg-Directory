"""Math utility functions."""


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def power(base, exponent):
    return base ** exponent


def modulo(a, b):
    return a % b


def is_even(n):
    return n % 2 == 0


def is_odd(n):
    return n % 2 != 0


def absolute_value(n):
    if n < 0:
        return -n

    return n


def square(n):
    return n * n
