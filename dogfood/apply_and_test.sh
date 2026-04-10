#!/bin/bash
CONTAINER="borg_test_e2e"

# Apply test patch
docker cp /tmp/test_patch_16631.diff $CONTAINER:/tmp/test_patch.diff
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && git apply /tmp/test_patch.diff && echo APPLIED"

echo ""
echo "=== Running FAIL_TO_PASS test ==="
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py auth_tests.test_basic.TestGetUser.test_get_user_fallback_secret --verbosity 2 2>&1 | tail -15"

echo ""
echo "=== Test should FAIL (this is the starting state) ==="
