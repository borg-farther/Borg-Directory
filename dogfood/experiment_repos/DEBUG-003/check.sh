#!/bin/bash
# Check for DEBUG-003 - tests must pass
cd "$(dirname "$0")"
PYTHONPATH="$(pwd)/src:$(pwd)/tests" /root/.hermes/hermes-agent/venv/bin/python -m pytest tests/test_counter.py -v
