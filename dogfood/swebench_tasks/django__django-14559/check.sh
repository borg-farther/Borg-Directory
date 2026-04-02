#!/bin/bash
# Verify fix for django__django-14559
cd /workspace/django
python -m pytest test_empty_objects (queries.test_bulk_update.BulkUpdateTests) test_large_batch (queries.test_bulk_update.BulkUpdateTests) test_updated_rows_when_passing_duplicates (queries.test_bulk_update.BulkUpdateTests) --no-header -q 2>&1
exit $?
