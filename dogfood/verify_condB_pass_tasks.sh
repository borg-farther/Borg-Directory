#!/bin/bash
echo "=== django__django-11265 (Cond B — was PASS in A) ==="
docker exec borg_ws_django__django-11265_1775063804 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py filtered_relation.tests.FilteredRelationTests.test_exclude_relation_with_join --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_exclude)"

echo ""
echo "=== django__django-12708 (Cond B — was PASS in A) ==="
docker exec borg_ws_django__django-12708_1775063826 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py migrations.test_operations.OperationTests.test_alter_index_together_remove_with_unique_together --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_alter)"

echo ""
echo "=== django__django-15128 (Cond B — was PASS in A) ==="
docker exec borg_ws_django__django-15128_1775063845 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py queries.test_q --verbosity 0 2>&1" | tail -5
