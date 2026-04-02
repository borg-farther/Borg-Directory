#!/bin/bash
echo "=== django__django-12754 (Cond B) ==="
docker exec borg_ws_django__django-12754_1775056174 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py migrations.test_autodetector.AutodetectorTests.test_create_model_and_remove_model_with_same_name --verbosity 2 2>&1" | grep -E "(OK|FAIL|ERROR|test_create)"

echo ""
echo "=== django__django-13315 (Cond B) ==="
docker exec borg_ws_django__django-13315_1775056183 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_formsets.tests.ModelFormsetTest.test_limit_choices_to_no_duplicates --verbosity 2 2>&1" | grep -E "(OK|FAIL|ERROR|test_limit)"

echo ""
echo "=== django__django-15503 (Cond B) ==="
docker exec borg_ws_django__django-15503_1775056194 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_fields.test_jsonfield --verbosity 0 2>&1" | tail -5
