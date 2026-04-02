#!/bin/bash
cd "$(dirname "$0")"
python -m pytest tests/test_serializer.py -v
