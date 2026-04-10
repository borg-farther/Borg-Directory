#!/bin/bash
docker run --rm sweb.eval.x86_64.django__django-16631:latest bash -c "
source /opt/miniconda3/bin/activate testbed
echo '=== Python ==='
which python
python --version
echo '=== pytest ==='
pip list 2>&1 | grep -i pytest
echo '=== Django test runner ==='
cd /testbed
python -m django --version
echo '=== Running test with Django runner ==='
python tests/runtests.py sessions_tests.tests.SessionPatchTests 2>&1 | tail -20
echo '=== EXIT: $? ==='
"
