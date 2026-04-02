#!/bin/bash
echo "=== django__django-11087 ==="
docker exec borg_ws_django__django-11087_1775049507 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py check_framework.tests --verbosity 0 2>&1" | tail -5
echo ""

echo "=== django__django-16560 ==="
docker exec borg_ws_django__django-16560_1775049526 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py constraints.tests --verbosity 0 2>&1" | tail -5
echo ""

echo "=== django__django-11138 ==="
docker exec borg_ws_django__django-11138_1775049543 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py timezones.tests.NewDatabaseTests.test_query_convert_timezones --verbosity 2 2>&1" | tail -5
