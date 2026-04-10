#!/bin/bash
# Verify fix for django__django-11477
cd /workspace/django
python -m pytest test_re_path_with_optional_parameter (urlpatterns.tests.SimplifiedURLTests) test_two_variable_at_start_of_path_pattern (urlpatterns.tests.SimplifiedURLTests) test_translate_url_utility (i18n.patterns.tests.URLTranslationTests) --no-header -q 2>&1
exit $?
