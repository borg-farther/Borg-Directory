#!/bin/bash
echo "=== 10554 Cond A run 2 ==="
docker exec borg_ws_django__django-10554_1775070870 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py queries.test_qs_combinators --verbosity 0 2>&1" | tail -3

echo ""
echo "=== 13344 Cond A run 2 ==="
docker exec borg_ws_django__django-13344_1775070883 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py deprecation.test_middleware_mixin --verbosity 0 2>&1" | tail -3

echo ""
echo "=== 16560 Cond A run 2 ==="
docker exec borg_ws_django__django-16560_1775070894 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py constraints.tests --verbosity 0 2>&1" | tail -3
