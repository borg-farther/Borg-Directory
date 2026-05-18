# Solution: Logging Misconfiguration Fix

## The Problem
```python
logger = logging.getLogger('app')
logger.setLevel(logging.ERROR)  # Too high - misses WARNING and INFO
handler = logging.FileHandler(LOG_FILE)
handler.setLevel(logging.DEBUG)  # Handler level irrelevant when logger level is higher
# No formatter set
```

## The Fix
```python
def setup_logger():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    logger = logging.getLogger('app')
    logger.setLevel(logging.WARNING)  # Correct level: capture WARNING and above

    handler = logging.FileHandler(LOG_FILE)
    handler.setLevel(logging.DEBUG)  # Handler can be fine-grained

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)  # Add formatter

    logger.addHandler(handler)
    return logger
```

## Key Changes
1. Set `logger.setLevel(logging.WARNING)` instead of `ERROR`
2. Added a `logging.Formatter` with appropriate format string
3. Applied formatter to handler with `handler.setFormatter(formatter)`
