#!/bin/bash
cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-025
python3 log_parser.py
exit $?