#!/bin/bash
# Check script for HARD-009 Cache Invalidation Bug

set -e

cd "$(dirname "$0")"

echo "Running tests for HARD-009 Cache Invalidation Bug..."

# Run pytest with verbose output
python -m pytest tests/ -v --tb=short 2>&1 || {
    echo ""
    echo "=== VERIFICATION: Tests expose the bug ==="
    echo "The cache invalidation bug causes:"
    echo "1. store.update() doesn't invalidate cache"
    echo "2. store.update_batch() doesn't invalidate cache"
    echo "3. service.py reads stale data from cache after updates"
    echo "4. cache itself works perfectly - bug is in integration"
    exit 1
}

echo "Tests passed (unexpected - bug should cause failures)"
exit 0
