#!/bin/bash
# Verify fix for django__django-15382
cd /workspace/django
python -m pytest test_negated_empty_exists (expressions.tests.ExistsTests) --no-header -q 2>&1
exit $?
