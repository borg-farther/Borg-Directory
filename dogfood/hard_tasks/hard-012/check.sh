#!/bin/bash
# Check script for HARD-012 Serialization Round-Trip Bug

set -e

cd "$(dirname "$0")"

echo "Running tests for HARD-012 Serialization Round-Trip Bug..."

# Run pytest with verbose output
python -m pytest tests/ -v --tb=short 2>&1 || {
    echo ""
    echo "=== VERIFICATION: Tests expose the bug ==="
    echo "The serialization round-trip bug causes:"
    echo "1. serializer.py adds 'Z' suffix to datetime in isoformat()"
    echo "2. deserializer.py doesn't properly handle the 'Z' suffix"
    echo "3. Round-trip produces datetime objects that don't compare equal"
    echo "4. Objects that should be identical are different"
    exit 1
}

echo "Tests passed (unexpected - bug should cause failures)"
exit 0
