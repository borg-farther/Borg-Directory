#!/bin/bash
# Verify fix for django__django-16485
cd /workspace/django
python -m pytest test_zero_values (template_tests.filter_tests.test_floatformat.FunctionTests.test_zero_values) --no-header -q 2>&1
exit $?
