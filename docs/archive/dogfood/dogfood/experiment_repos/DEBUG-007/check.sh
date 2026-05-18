#!/bin/bash
cd "$(dirname "$0")"
python -m pytest tests/test_logging.py -v
