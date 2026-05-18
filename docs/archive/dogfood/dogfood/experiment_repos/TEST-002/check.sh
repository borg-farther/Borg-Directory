#!/bin/bash
# Check for TEST-002 - requires >= 10 tests
cd "$(dirname "$0")"
PYTHONPATH="$(pwd)/src:$(pwd)/tests" /root/.hermes/hermes-agent/venv/bin/python -m pytest tests/ --collect-only -q 2>/dev/null | grep 'test' | wc -l
test_count=$(python3 -m pytest tests/ --collect-only -q 2>/dev/null | grep 'test' | wc -l)
[ $test_count -ge 10 ]
