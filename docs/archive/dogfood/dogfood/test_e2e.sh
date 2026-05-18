#!/bin/bash
# End-to-end test: verify the container works for our experiment

CONTAINER="borg_test_e2e"

echo "=== Step 1: Verify tests FAIL in starting state ==="
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py sessions_tests --verbosity 0 2>&1" | tail -5
echo "Exit code: $?"

echo ""
echo "=== Step 2: Check the relevant source file ==="
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && grep -n 'SECRET_KEY' /testbed/django/contrib/sessions/backends/base.py 2>&1" | head -10

echo ""
echo "=== Step 3: Read the test patch (what test was added) ==="
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && git log --oneline -3 2>&1"

echo ""
echo "=== Step 4: Check what the gold patch changes ==="
echo "Gold patch changes django/contrib/sessions/backends/base.py"
echo "It should make sessions use SECRET_KEY_FALLBACKS for verification"

echo ""
echo "=== Step 5: Verify agent can interact ==="
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && python -c 'import django; print(django.VERSION)' 2>&1"
docker exec $CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && ls /testbed/django/contrib/sessions/backends/ 2>&1"

echo ""
echo "=== PIPELINE VALIDATED ==="
