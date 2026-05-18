#!/bin/bash
cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-023
python3 test_middleware.py
exit $?