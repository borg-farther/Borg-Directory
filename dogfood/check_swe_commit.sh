#!/bin/bash
CONTAINER="borg_test_e2e"

docker exec $CONTAINER bash -c "
source /opt/miniconda3/bin/activate testbed
cd /testbed
echo '=== SWE-bench commit contents ==='
git show HEAD --stat
echo ''
echo '=== SWE-bench commit diff (first 80 lines) ==='
git show HEAD --format='' | head -80
"
