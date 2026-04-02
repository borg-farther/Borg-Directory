#!/bin/bash
cd "$(dirname "$0")"
timeout 30 python -m pytest tests/test_search.py -v
exit_code=$?
if [ $exit_code -eq 124 ]; then
    echo "FAIL: Test timed out after 30 seconds"
    exit 1
fi
exit $exit_code
