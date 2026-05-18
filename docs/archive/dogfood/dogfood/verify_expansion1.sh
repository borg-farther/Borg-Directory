#!/bin/bash
echo "=== 12754 (Cond A retest) ==="
docker exec borg_ws_django__django-12754_1775069988 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py migrations.test_autodetector.AutodetectorTests.test_add_model_with_field_removed_from_base_model --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_add)"

echo ""
echo "=== 13315 (Cond B) ==="
docker exec borg_ws_django__django-13315_1775069998 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_forms.tests.LimitChoicesToTests.test_limit_choices_to_no_duplicates --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_limit)"

echo ""
echo "=== 15503 (Cond B - need retry) ==="
docker exec borg_ws_django__django-15503_1775070022 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_fields.test_jsonfield.TestQuerying.test_has_key_number model_fields.test_jsonfield.TestQuerying.test_has_keys --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_has)"
