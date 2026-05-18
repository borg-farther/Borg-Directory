#!/bin/bash
# Verify fix for django__django-11728
cd /workspace/django
python -m pytest test_simplify_regex (admin_docs.test_views.AdminDocViewFunctionsTests) test_app_not_found (admin_docs.test_views.TestModelDetailView) --no-header -q 2>&1
exit $?
