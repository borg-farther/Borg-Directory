#!/bin/bash
# Check for CONTROL-002 - all files should be snake_case
cd "$(dirname "$0")"

EXPECTED_FILES="api_client.py
cache_manager.py
data_validator.py
database_connection.py
file_upload_handler.py
logger_config.py
message_queue.py
request_handler.py
session_state.py
user_auth.py"

ACTUAL_FILES=$(ls src/*.py 2>/dev/null | xargs -n1 basename | sort)

if [ "$ACTUAL_FILES" = "$EXPECTED_FILES" ]; then
    echo "PASS: All files renamed to snake_case"
    echo "$ACTUAL_FILES"
    exit 0
else
    echo "FAIL: File names don't match"
    echo "Expected:"
    echo "$EXPECTED_FILES"
    echo "Got:"
    echo "$ACTUAL_FILES"
    exit 1
fi
