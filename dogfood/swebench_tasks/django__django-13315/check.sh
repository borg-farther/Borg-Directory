#!/bin/bash
# Verify fix for django__django-13315
cd /workspace/django
python -m pytest test_limit_choices_to_no_duplicates (model_forms.tests.LimitChoicesToTests) --no-header -q 2>&1
exit $?
