#!/bin/bash
echo "=== django__django-15503 SPECIFIC FAIL_TO_PASS tests ==="
docker exec borg_ws_django__django-15503_1775056194 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py model_fields.test_jsonfield.TestQuerying.test_has_key_number model_fields.test_jsonfield.TestQuerying.test_has_keys --verbosity 2 2>&1" | grep -E "(OK|FAIL|test_has)"
