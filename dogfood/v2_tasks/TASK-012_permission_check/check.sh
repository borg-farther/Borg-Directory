#!/bin/bash
# Check script for TASK-012: Permission check bitwise operator bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-012_permission_check

# Run the test suite
python3 test_permissions.py
exit $?
