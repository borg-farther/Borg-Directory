#!/bin/bash
# Check script for HARD-008 Pipeline Transform Bug

set -e

cd "$(dirname "$0")"

echo "Running tests for HARD-008 Pipeline Transform Bug..."

# Run pytest with verbose output
python -m pytest tests/ -v --tb=short 2>&1 || {
    echo ""
    echo "=== VERIFICATION: Tests expose the bug ==="
    echo "The in-place mutation bug causes:"
    echo "1. Original data is corrupted after pipeline processing"
    echo "2. Rollback mechanism fails to restore original state"
    echo "3. Data validation passes but data is silently corrupted"
    exit 1
}

echo "Tests passed (unexpected - bug should cause failures)"
exit 0
