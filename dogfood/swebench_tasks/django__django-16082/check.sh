#!/bin/bash
# Verify fix for django__django-16082
cd /workspace/django
python -m pytest test_resolve_output_field_number (expressions.tests.CombinedExpressionTests) test_resolve_output_field_with_null (expressions.tests.CombinedExpressionTests) --no-header -q 2>&1
exit $?
