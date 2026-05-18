#!/bin/bash
# Check script for TASK-019: Config merge bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-019_config_merge

python3 test_config_merge.py
exit $?
