#!/bin/bash
# Check for CONTROL-001 - requires agent to create marker file after finding TODOs
cd "$(dirname "$0")"

# Verify the marker file exists (agent creates this after finding TODOs)
if [ -f /tmp/control001_done.txt ]; then
    echo "PASS: Agent completed TODO review"
    cat /tmp/control001_done.txt
    exit 0
else
    echo "FAIL: Agent has not completed TODO review yet"
    exit 1
fi
