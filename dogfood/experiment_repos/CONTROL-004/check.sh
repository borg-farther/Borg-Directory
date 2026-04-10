#!/bin/bash
cd "$(dirname "$0")"

echo "Checking Python compilation..."
python3 -m py_compile src/messy.py
if [ $? -ne 0 ]; then
    echo "FAIL: Syntax error in src/messy.py"
    exit 1
fi

echo "Checking for trailing whitespace..."
TRAILING=$(grep -n '[[:space:]]$' src/messy.py | head -5 || true)
if [ -n "$TRAILING" ]; then
    echo "FAIL: Found trailing whitespace on lines:"
    echo "$TRAILING"
    exit 1
fi

echo "Checking indentation consistency..."
# Check for mixed tabs/spaces - any line with both
MIXED=$(python3 -c "
import re
with open('src/messy.py', 'r') as f:
    lines = f.readlines()
issues = []
for i, line in enumerate(lines, 1):
    stripped = line.lstrip(' \t')
    leading = line[:len(line) - len(stripped)]
    if ' ' in leading and '\t' in leading:
        issues.append(i)
if issues:
    print('Lines with mixed tabs/spaces:', issues)
" 2>&1)

if [ -n "$MIXED" ]; then
    echo "FAIL: $MIXED"
    exit 1
fi

echo "PASS: All formatting checks passed"
python -m pytest tests/test_messy.py -v
