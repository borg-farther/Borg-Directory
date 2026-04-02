#!/bin/bash
# Check script for TASK-015: State machine bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-015_state_machine

python3 test_state_machine.py
exit $?
