#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_scheduler.py 2>&1
