#!/bin/bash
cd "$(dirname "$0")"

# Check for docstrings using grep - should find none (all removed)
echo "Checking for docstrings in src/math_utils.py..."
if grep -q '"""' src/math_utils.py || grep -q "'''" src/math_utils.py; then
    echo "FAIL: Found docstrings in src/math_utils.py"
    exit 1
fi

echo "PASS: No docstrings found (all properly removed)"
python -m pytest tests/test_math_utils.py -v
