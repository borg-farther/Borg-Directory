#!/bin/bash
# Check for DEBUG-002 - tests must pass
cd "$(dirname "$0")"
PYTHONPATH="$(pwd)/src:$(pwd)/tests" /root/.hermes/hermes-agent/venv/bin/python -m pytest tests/test_pipeline.py -v
