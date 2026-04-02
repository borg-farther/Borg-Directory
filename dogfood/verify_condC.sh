#!/bin/bash
echo "=== 10554 Cond C (agent trace) ==="
docker exec borg_ws_django__django-10554_1775072143 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py queries.test_qs_combinators --verbosity 0 2>&1" | tail -5

echo ""
echo "=== 13344 Cond C (agent trace) ==="
docker exec borg_ws_django__django-13344_1775072149 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py deprecation.test_middleware_mixin --verbosity 0 2>&1" | tail -5
