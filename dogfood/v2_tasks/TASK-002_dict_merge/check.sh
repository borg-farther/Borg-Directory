#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_config.py 2>&1
