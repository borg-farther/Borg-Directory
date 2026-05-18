"""CLI Calculator with basic operations."""
import sys
import argparse


def add(a, b):
    """Add two numbers."""
    return a + b


def subtract(a, b):
    """Subtract b from a."""
    return a - b


def multiply(a, b):
    """Multiply two numbers."""
    return a * b


def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def main():
    parser = argparse.ArgumentParser(description="Simple Calculator")
    parser.add_argument("operation", choices=["add", "sub", "mul", "div"])
    parser.add_argument("a", type=float)
    parser.add_argument("b", type=float)
    args = parser.parse_args()

    if args.operation == "add":
        result = add(args.a, args.b)
    elif args.operation == "sub":
        result = subtract(args.a, args.b)
    elif args.operation == "mul":
        result = multiply(args.a, args.b)
    elif args.operation == "div":
        result = divide(args.a, args.b)

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
