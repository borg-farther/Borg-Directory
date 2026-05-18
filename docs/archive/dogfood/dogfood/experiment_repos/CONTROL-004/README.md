# CONTROL-004: Fix Whitespace/Formatting

## Problem
The `src/messy.py` file has valid Python but poor formatting:
- Mixed tabs and spaces on some lines
- Inconsistent indentation (2 spaces, 4 spaces, tabs mixed)
- Trailing whitespace on some lines

## Task
Fix the formatting issues:
1. Replace all tabs with 4 spaces (or consistent indentation)
2. Remove trailing whitespace
3. Ensure consistent indentation throughout
4. File must still pass `python3 -m py_compile` (valid syntax)

## Verification
```bash
./check.sh
```
