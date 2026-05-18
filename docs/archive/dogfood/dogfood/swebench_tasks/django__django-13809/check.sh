#!/bin/bash
# Verify fix for django__django-13809
cd /workspace/django
python -m pytest test_skip_checks (admin_scripts.tests.ManageRunserver) --no-header -q 2>&1
exit $?
