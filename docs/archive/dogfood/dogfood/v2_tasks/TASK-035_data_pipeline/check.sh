#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_pipeline.py 2>&1
