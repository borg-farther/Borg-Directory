#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_pool.py 2>&1
