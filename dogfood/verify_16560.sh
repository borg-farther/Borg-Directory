#!/bin/bash
echo "=== django__django-16560 (Cond B) ==="
docker exec borg_ws_django__django-16560_1775056210 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py constraints.tests --verbosity 0 2>&1" | tail -5
