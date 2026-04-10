#!/bin/bash
cd "$(dirname "$0")"
PYTHONPATH=src pytest tests/ -q
