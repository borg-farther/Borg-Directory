#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_cache.py 2>&1
