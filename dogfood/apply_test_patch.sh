#!/bin/bash
CONTAINER="borg_test_e2e"

# Read the test patch from our task data and apply it
python3 -c "
import sys, json
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
from datasets import load_dataset
ds = load_dataset('princeton-nlp/SWE-bench_Verified', split='test')
for t in ds:
    if t['instance_id'] == 'django__django-16631':
        print(t['test_patch'])
        break
" 2>/dev/null > /tmp/test_patch.diff

echo "=== Test patch ==="
head -20 /tmp/test_patch.diff

echo ""
echo "=== Applying test patch ==="
docker cp /tmp/test_patch.diff $CONTAINER:/tmp/test_patch.diff
docker exec $CONTAINER bash -c "
source /opt/miniconda3/bin/activate testbed
cd /testbed
git apply /tmp/test_patch.diff 2>&1
echo 'Apply exit code:' \$?
echo ''
echo '=== Running the specific FAIL_TO_PASS test ==='
python tests/runtests.py sessions_tests.tests.CookieSessionTests.test_session_key_is_read_only --verbosity 2 2>&1 | tail -20
"
