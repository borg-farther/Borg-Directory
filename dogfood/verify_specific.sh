#!/bin/bash
echo "=== django__django-11138 specific test ==="
docker exec borg_ws_django__django-11138_1775049543 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py timezones.tests.NewDatabaseTests.test_query_convert_timezones --verbosity 2 2>&1 | grep -E '(test_query|OK|FAIL|ERROR|Traceback|skip)'"
