#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_workflow.py 2>&1
