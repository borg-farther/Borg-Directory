# Solution for HARD-003: Config Cascade Bug

## The Bug
In `src/validator.py`, line 14, the validation check uses:
```python
if not value:
    raise ConfigValidationError(...)
```

This treats the string `"0"` as falsy (since `not "0"` is `True` in Python), causing valid zero values to be rejected as missing.

## The Fix
Change line 14 in `src/validator.py` from:
```python
if not value:
```
to:
```python
if value is None:
```

This properly distinguishes between a missing value (`None`) and a valid string like `"0"`.

## Why This Works
- `"0"` is a valid string that should be treated as a real value
- `not "0"` evaluates to `True` because Python treats non-empty strings as truthy, then negates it
- `value is None` correctly checks only for truly missing values
- The string `"0"` is neither `None` nor falsy in a boolean context, so it passes validation
