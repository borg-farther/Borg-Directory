#!/bin/bash
# Check for REFACTOR-001 - tests pass AND duplicate code exists
cd "$(dirname "$0")"
PYTHONPATH="$(pwd)/src:$(pwd)/tests" /root/.hermes/hermes-agent/venv/bin/python -m pytest tests/test_reports.py -v
TEST_RESULT=$?

# Check for duplicate code using simian (more reliable than pylint for this)
echo "Checking for duplicate code..."
SIMIAN_FOUND=false
if command -v simian &> /dev/null; then
    simian src/reports.py && SIMIAN_FOUND=true
elif /root/.hermes/hermes-agent/venv/bin/python -c "
import ast
import sys

with open('src/reports.py', 'r') as f:
    content = f.read()
    tree = ast.parse(content)

# Extract function bodies
functions = {}
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        funcs = content.split('def ' + node.name)
        if len(funcs) > 1:
            functions[node.name] = 'def ' + node.name + content.split('def ' + node.name)[1].split('\n\n')[0]

# Compare function bodies for similarity
names = list(functions.keys())
if len(names) >= 2:
    body1 = functions[names[0]]
    body2 = functions[names[1]]
    # Simple comparison: check if they have similar structure
    lines1 = [l.strip() for l in body1.split('\n') if l.strip() and not l.strip().startswith('#')]
    lines2 = [l.strip() for l in body2.split('\n') if l.strip() and not l.strip().startswith('#')]
    if len(lines1) > 5 and len(lines2) > 5:
        # Count matching lines
        matches = sum(1 for l1, l2 in zip(lines1, lines2) if l1 == l2)
        if matches >= 5:
            print('DUPLICATE_CODE_FOUND')
            sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    SIMIAN_FOUND=true
fi

if [ $TEST_RESULT -ne 0 ]; then
    echo "Tests FAILED"
    exit 1
fi

if [ "$SIMIAN_FOUND" = true ]; then
    echo "FAIL: Duplicate code detected (code needs refactoring)"
    exit 1
fi

echo "All checks passed!"
exit 0
