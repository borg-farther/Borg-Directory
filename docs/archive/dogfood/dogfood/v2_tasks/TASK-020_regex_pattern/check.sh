#!/bin/bash
# Check script for TASK-020: Regex pattern bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-020_regex_pattern

python3 test_regex_parser.py
exit $?
