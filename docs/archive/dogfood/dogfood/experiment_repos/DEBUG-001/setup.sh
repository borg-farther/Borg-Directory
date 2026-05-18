#!/bin/bash
# Setup for DEBUG-001
pip install flask pytest --break-system-packages 2>&1 | grep -v "WARNING\|Skipping\|cannot uninstall" | head -5
