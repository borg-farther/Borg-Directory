#!/bin/bash
cd "$(dirname "$0")"
# Count tests - must have >= 8 integration tests
TEST_COUNT=$(python -m pytest tests/test_api.py --collect-only -q 2>/dev/null | grep -c "test_" || echo "0")
echo "Found $TEST_COUNT tests"
if [ "$TEST_COUNT" -lt 8 ]; then
    echo "FAIL: Need at least 8 integration tests, found $TEST_COUNT"
    exit 1
fi
python -m pytest tests/test_api.py -v
