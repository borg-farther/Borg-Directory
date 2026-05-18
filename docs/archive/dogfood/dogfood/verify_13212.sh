#!/bin/bash
docker exec borg_ws_django__django-13212_1775045304 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py forms_tests.tests.test_validators --verbosity 2 2>&1" | tail -20
