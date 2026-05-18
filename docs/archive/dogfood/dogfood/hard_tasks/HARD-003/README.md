# HARD-003: Config Cascade Bug

## Task Description
You are debugging a configuration system where an application crashes when certain config values are set. The error manifests in `app.py` but the bug is believed to be in another file.

## Problem
The application uses a three-layer config system:
1. `config.py` - Loads configuration from a JSON file with defaults
2. `validator.py` - Validates configuration values before use  
3. `app.py` - Uses the validated config to run the application

When a config value is set to `"0"` (the string zero), the application crashes with a "missing required configuration" error, even though the value is clearly present.

## Your Goal
Find and fix the bug so that all tests pass. The error shows in `app.py` but the actual bug is in a different file.

## Files
- `src/config.py` - Configuration loader with defaults
- `src/validator.py` - Configuration validator
- `src/app.py` - Application entry point
- `tests/test_config.py` - Test suite

## Expected Behavior
Config values of `"0"` (string zero) should be treated as valid values, not missing configurations.
