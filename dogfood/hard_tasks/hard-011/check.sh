#!/bin/bash
# Check script for HARD-011 Task Scheduler Bug

set -e

cd "$(dirname "$0")"

echo "Running tests for HARD-011 Task Scheduler Bug..."

# Run pytest with verbose output
python -m pytest tests/ -v --tb=short 2>&1 || {
    echo ""
    echo "=== VERIFICATION: Tests expose the bug ==="
    echo "The diamond dependency bug causes:"
    echo "1. scheduler.schedule() doesn't track which tasks have been executed"
    echo "2. When multiple paths lead to same task, it's added to queue multiple times"
    echo "3. executor.py runs D twice in diamond A->B->D, A->C->D pattern"
    echo "4. Side effects occur multiple times"
    exit 1
}

echo "Tests passed (unexpected - bug should cause failures)"
exit 0
