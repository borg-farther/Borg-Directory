#!/bin/bash
# Check script for TASK-016: Path joining bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-016_path_join

python3 test_path_utils.py
exit $?
