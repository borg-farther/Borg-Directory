#!/bin/bash
# Verify fix for django__django-15037
cd /workspace/django
python -m pytest test_foreign_key_to_field (inspectdb.tests.InspectDBTestCase) --no-header -q 2>&1
exit $?
