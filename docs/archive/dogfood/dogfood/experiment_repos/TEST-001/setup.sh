#!/bin/bash
# Setup for TEST-001
/root/.hermes/hermes-agent/venv/bin/python -m pip install pytest pytest-cov --break-system-packages -q 2>&1 | grep -v "WARNING\|Skipping\|notice"
