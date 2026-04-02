#!/bin/bash
# Setup for TEST-002
/root/.hermes/hermes-agent/venv/bin/python -m pip install pytest requests-mock --break-system-packages -q 2>&1 | grep -v "WARNING\|Skipping\|notice"
