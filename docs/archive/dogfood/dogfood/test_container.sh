#!/bin/bash
# Test that the SWE-bench container works and tests fail correctly
docker run --rm sweb.eval.x86_64.django__django-16631:latest bash -c "
cd /testbed && 
source /opt/miniconda3/bin/activate testbed && 
python -m pytest tests/sessions_tests/tests.py -x --no-header -q -k test_session_load_does_not_create_record 2>&1
echo EXIT_CODE: \$?
"
