---
name: fix-python-imports
trigger: "Agent encounters ImportError, ModuleNotFoundError, or circular import"
---

# Fix Python Import Errors

## Principles
1. Python resolves imports depth-first — circular imports fail at the SECOND import, not the first.
2. Missing `__init__.py` makes a directory invisible to Python's import system.
3. Relative imports (from .X) only work inside packages, not standalone scripts.
4. sys.path order: the FIRST match wins, even if wrong.

## Output Format
Return: Root cause (1 sentence) | Fix (exact change) | Verification command

## Edge Cases
- CIRCULAR A→B→A: move shared code to C that both import
- SHADOW local=stdlib: rename the local file
- MESSY pytest≠script: check sys.path differences

## Example
INPUT: `ModuleNotFoundError: No module named 'utils'`
OUTPUT:
```
Root cause: utils/ missing __init__.py
Fix: touch utils/__init__.py
Verify: python -c "from utils import helper"
```

## Recovery
If fix fails, run `python -v` to trace the exact import path.
