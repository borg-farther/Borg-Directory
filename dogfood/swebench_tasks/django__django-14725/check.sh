#!/bin/bash
# Verify fix for django__django-14725
cd /workspace/django
python -m pytest test_edit_only (model_formsets.tests.ModelFormsetTest) test_edit_only_inlineformset_factory (model_formsets.tests.ModelFormsetTest) test_edit_only_object_outside_of_queryset (model_formsets.tests.ModelFormsetTest) --no-header -q 2>&1
exit $?
