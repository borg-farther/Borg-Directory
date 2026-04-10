# HARD-002: Config Management Bug

## Task Description
You are debugging a configuration management system. The system reads config values, applies transformations, and uses them to configure a service. 

Users report that the service starts but uses wrong values - specifically, the port number shows 8080 when it should be 3000, and the timeout is 30 instead of 5.

## Your Goal
Fix the bug so all tests pass. The bug involves multiple files.

## Expected Behavior
- Default port should be 3000 (from defaults), not 8080
- Timeout should be 5 seconds (from defaults), not 30

## Files
- `src/config_loader.py` - Loads configuration from environment
- `src/transformer.py` - Applies transformations to config values  
- `src/service.py` - Uses the transformed config
- `tests/test_config.py` - Test suite

Run `bash check.sh` to verify your fix.
EOF; __hermes_rc=$?; printf '__HERMES_FENCE_a9f7b3__'; exit $__hermes_rc
