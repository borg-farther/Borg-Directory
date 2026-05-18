#!/bin/bash
# Check for TEST-001 - requires >= 8 tests
cd "$(dirname "$0")"
test_count=$(grep -r 'def test_' tests/ 2>/dev/null | wc -l)
echo "Test count: $test_count"
[ $test_count -ge 8 ]
