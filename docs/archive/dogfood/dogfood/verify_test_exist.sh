#!/bin/bash
echo "=== 12754: checking test exists ==="
docker exec borg_ws_django__django-12754_1775069988 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && grep -r 'test_add_model_with_field_removed_from_base_model' tests/ 2>&1 | head -3"

echo ""
echo "=== 13315: checking test exists ==="
docker exec borg_ws_django__django-13315_1775069998 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && grep -r 'test_limit_choices_to_no_duplicates' tests/ 2>&1 | head -3"

echo ""
echo "=== 15503: checking test exists ==="
docker exec borg_ws_django__django-15503_1775070022 bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && grep -r 'test_has_key_number' tests/ 2>&1 | head -3"
