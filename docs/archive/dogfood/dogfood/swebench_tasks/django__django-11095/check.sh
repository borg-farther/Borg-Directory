#!/bin/bash
# Verify fix for django__django-11095
cd /workspace/django
python -m pytest test_get_inline_instances_override_get_inlines (generic_inline_admin.tests.GenericInlineModelAdminTest) --no-header -q 2>&1
exit $?
