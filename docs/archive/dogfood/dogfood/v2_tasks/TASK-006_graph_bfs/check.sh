#!/bin/bash
cd "$(dirname "$0")/repo"
timeout 10 python3 test_graph.py 2>&1
