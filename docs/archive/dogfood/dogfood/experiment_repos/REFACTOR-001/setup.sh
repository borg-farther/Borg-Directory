#!/bin/bash
# Setup for REFACTOR-001
/root/.hermes/hermes-agent/venv/bin/python -m pip install pytest pylint --break-system-packages -q 2>&1 | grep -v "WARNING\|Skipping\|notice"
