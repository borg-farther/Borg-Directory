#!/bin/bash
# Verify fix for django__django-16527
cd /workspace/django
python -m pytest test_submit_row_save_as_new_add_permission_required (admin_views.test_templatetags.AdminTemplateTagsTest.test_submit_row_save_as_new_add_permission_required) --no-header -q 2>&1
exit $?
