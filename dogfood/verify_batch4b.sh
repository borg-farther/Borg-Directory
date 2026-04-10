#!/bin/bash
echo "=== django__django-11265 ==="
docker exec borg_ws_django__django-11265_1775050199 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py filtered_relation.tests.FilteredRelationTests.test_exclude_relation_with_join --verbosity 2 2>&1 | grep -E '(OK|FAIL|test_exclude)'"
echo ""
echo "=== django__django-12754 ==="
docker exec borg_ws_django__django-12754_1775050223 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py migrations.test_autodetector.AutodetectorTests.test_create_model_and_remove_model_with_same_name --verbosity 2 2>&1 | grep -E '(OK|FAIL|ERROR|test_create)'"
echo ""
echo "=== django__django-13315 ==="
docker exec borg_ws_django__django-13315_1775050238 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_formsets.tests.ModelFormsetTest.test_limit_choices_to_no_duplicates --verbosity 2 2>&1 | grep -E '(OK|FAIL|ERROR|test_limit)'"
