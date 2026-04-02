#!/bin/bash
# Verify fix for django__django-15561
cd /workspace/django
python -m pytest test_alter_field_choices_noop (schema.tests.SchemaTests) --no-header -q 2>&1
exit $?
