#!/bin/bash
cd "$(dirname "$0")"
# Count tests - must have >= 12 tests including edge cases
TEST_COUNT=$(python -m pytest tests/test_validator.py --collect-only -q 2>/dev/null | grep -c "test_" || echo "0")
echo "Found $TEST_COUNT tests"
if [ "$TEST_COUNT" -lt 12 ]; then
    echo "FAIL: Need at least 12 tests including edge cases, found $TEST_COUNT"
    exit 1
fi
python -m pytest tests/test_validator.py -v
