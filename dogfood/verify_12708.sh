#!/bin/bash
docker exec borg_ws_django__django-12708_1775048381 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py migrations.test_operations.OperationTests.test_alter_index_together_remove_with_unique_together --verbosity 2 2>&1 | tail -15"
