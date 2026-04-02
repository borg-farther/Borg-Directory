#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_intervals.py 2>&1
