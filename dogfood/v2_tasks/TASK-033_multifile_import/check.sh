#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH=repo python3 repo/test_permissions.py 2>&1
