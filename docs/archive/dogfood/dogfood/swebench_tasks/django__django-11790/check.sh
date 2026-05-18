#!/bin/bash
# Verify fix for django__django-11790
cd /workspace/django
python -m pytest test_username_field_max_length_defaults_to_254 (auth_tests.test_forms.AuthenticationFormTest) test_username_field_max_length_matches_user_model (auth_tests.test_forms.AuthenticationFormTest) --no-header -q 2>&1
exit $?
