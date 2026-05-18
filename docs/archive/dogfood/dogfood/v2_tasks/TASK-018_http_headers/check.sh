#!/bin/bash
# Check script for TASK-018: HTTP header case sensitivity bug

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-018_http_headers

python3 test_http_parser.py
exit $?
