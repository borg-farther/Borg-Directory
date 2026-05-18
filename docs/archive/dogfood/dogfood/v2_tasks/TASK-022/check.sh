#!/bin/bash
cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-022
python3 test_tree.py
exit $?