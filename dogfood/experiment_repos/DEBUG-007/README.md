# DEBUG-007: Python Logging Misconfiguration

## Problem
The `setup_logger` function in `src/app.py` has two issues:
1. Log level is set to ERROR - this misses all WARNING and INFO messages
2. Missing formatter - log messages lack proper formatting

## Task
Fix the logging configuration to:
- Set log level to WARNING (so WARNING, ERROR, and CRITICAL appear)
- Add a proper formatter
- DEBUG messages should NOT appear in production log

## Verification
```bash
./check.sh
```
