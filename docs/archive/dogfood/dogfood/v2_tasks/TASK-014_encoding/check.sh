#!/bin/bash
# Check script for TASK-014: UTF-8 BOM encoding issue

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-014_encoding

python3 test_processor.py
exit $?
