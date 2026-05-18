#!/bin/bash
# Check script for TASK-017: Priority queue bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-017_priority_queue

python3 test_priority_queue.py
exit $?
