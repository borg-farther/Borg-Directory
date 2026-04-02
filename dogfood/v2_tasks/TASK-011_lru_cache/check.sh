#!/bin/bash
# Check script for TASK-011: LRU Cache

cd /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-011_lru_cache

# Run the test suite
python3 test_lru.py
exit $?
