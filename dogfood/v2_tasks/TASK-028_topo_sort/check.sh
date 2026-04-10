#!/bin/bash
cd "$(dirname "$0")/repo"
python3 test_topo.py 2>&1
