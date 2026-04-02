#!/bin/bash
CONTAINER="borg_test_e2e"

docker exec $CONTAINER bash -c "
source /opt/miniconda3/bin/activate testbed
cd /testbed
echo '=== Git log ==='
git log --oneline -5
echo ''
echo '=== Check if test patch was applied ==='
git diff HEAD~1 --stat 2>&1
echo ''
echo '=== Applied patches ==='
git log --all --oneline | head -5
"
