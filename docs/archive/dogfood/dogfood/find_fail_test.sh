#!/bin/bash
CONTAINER="borg_test_e2e"

docker exec $CONTAINER bash -c "
source /opt/miniconda3/bin/activate testbed
cd /testbed
grep -rn 'SECRET_KEY_FALLBACKS\|test_session.*fallback' tests/sessions_tests/ 2>&1
echo '==='
# Check the git diff to see what test was added
git diff HEAD~1 -- tests/ 2>&1 | head -60
"
