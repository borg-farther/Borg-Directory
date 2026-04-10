#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_parser.py 2>&1
