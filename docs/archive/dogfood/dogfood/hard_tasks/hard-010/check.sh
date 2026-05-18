#!/bin/bash
# Check script for HARD-010 Parser State Machine Bug

set -e

cd "$(dirname "$0")"

echo "Running tests for HARD-010 Parser State Machine Bug..."

# Run pytest with verbose output
python -m pytest tests/ -v --tb=short 2>&1 || {
    echo ""
    echo "=== VERIFICATION: Tests expose the bug ==="
    echo "The lexer state machine bug causes:"
    echo "1. _current_char not reset between tokenize() calls"
    echo "2. Second parse fails or returns wrong values"
    echo "3. evaluate_expression returns corrupted results on second call"
    exit 1
}

echo "Tests passed (unexpected - bug should cause failures)"
exit 0
