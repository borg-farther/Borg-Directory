#!/bin/bash
# Verify fix for django__django-14500
cd /workspace/django
python -m pytest test_migrate_marks_replacement_unapplied (migrations.test_executor.ExecutorTests) --no-header -q 2>&1
exit $?
