#!/bin/bash
echo "=== Verifying django__django-10554 ==="
docker exec borg_ws_django__django-10554_1775047015 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py urlpatterns_reverse.tests.ResolverTests.test_resolver_resolve_conflict --verbosity 2 2>&1" | tail -5

echo ""
echo "=== Verifying django__django-13344 ==="
docker exec borg_ws_django__django-13344_1775047034 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py deprecation.test_middleware_mixin --verbosity 2 2>&1" | tail -10

echo ""
echo "=== Verifying django__django-15128 ==="
docker exec borg_ws_django__django-15128_1775047048 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py queries.test_q --verbosity 2 2>&1" | tail -10
