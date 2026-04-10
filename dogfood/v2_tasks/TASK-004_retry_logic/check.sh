#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_retry.py 2>&1
