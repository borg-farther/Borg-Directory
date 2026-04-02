#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_events.py 2>&1
