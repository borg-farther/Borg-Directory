#!/bin/bash
cd "$(dirname "$0")"
pip install flask pytest -q --break-system-packages
