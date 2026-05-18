#!/bin/bash
echo "=== django__django-11400 ==="
docker exec borg_ws_django__django-11400_1775048362 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py admin_filters.tests.ListFiltersTests model_fields.tests.GetChoicesOrderingTests --verbosity 0 2>&1" | tail -5

echo ""
echo "=== django__django-12708 ==="
docker exec borg_ws_django__django-12708_1775048381 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py migrations.test_operations.OperationTests.test_alter_index_together_remove_with_unique_together --verbosity 2 2>&1" | tail -5

echo ""
echo "=== django__django-15503 ==="
docker exec borg_ws_django__django-15503_1775048405 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_fields.test_jsonfield --verbosity 0 2>&1" | tail -5
