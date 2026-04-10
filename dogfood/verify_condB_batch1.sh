#!/bin/bash
echo "=== django__django-10554 (Cond B) ==="
docker exec borg_ws_django__django-10554_1775055431 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py urlpatterns_reverse.tests --verbosity 0 2>&1" | tail -5

echo ""
echo "=== django__django-11138 (Cond B) ==="
docker exec borg_ws_django__django-11138_1775055441 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py timezones.tests.NewDatabaseTests.test_query_convert_timezones --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_query)"

echo ""
echo "=== django__django-13344 (Cond B) ==="
docker exec borg_ws_django__django-13344_1775055454 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py deprecation.test_middleware_mixin --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_)"
