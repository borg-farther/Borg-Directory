---
type: workflow_pack
version: '1.0'
id: import-cycle
problem_class: import_cycle
framework: python
problem_signature:
  error_types:
  - ImportError
  - ModuleNotFoundError
  framework: python
  problem_description: Python import system encounters a circular dependency. Module
    A imports B, B imports A. Python returns a partially-initialized module, causing
    AttributeError or ImportError.
root_cause:
  category: import_cycle
  explanation: Module A imports Module B at the top level. Module B imports Module
    A before Module A is fully initialized. Python returns a partially initialized
    A, causing attribute errors.
investigation_trail:
- file: django/db/models/sql/query.py
  position: FIRST
  what: Query.change_aliases raises AssertionError — check import cycle between query.py
    and expressions.py
  grep_pattern: change_aliases|AssertionError
- file: django/template/defaultfilters.py
  position: FIRST
  what: floatformat() import issue — check what defaultfilters imports and how it
    references other modules
  grep_pattern: import|from django
- file: django/db/models/query_utils.py
  position: SECOND
  what: Q object resolution — check if query_utils imports create a cycle with query.py
  grep_pattern: import|Q_|register
resolution_sequence:
- action: move_imports_to_functions
  command: Move the problematic import from the top of the module into the function
    that uses it
  why: Imports at function scope only run when the function is called, after all modules
    are fully initialized
- action: use_type_checking
  command: from __future__ import annotations; put type hints in quotes or use TYPE_CHECKING
    block
  why: TYPE_CHECKING imports are only evaluated at analysis time, not runtime
- action: restructure_package
  command: Move shared code to a third module neither of the cycling modules imports
  why: A common dependency that neither cyclic module depends on breaks the cycle
anti_patterns:
- action: Moving imports to the bottom of the file
  why_fails: Does not fix the problem, just delays it
- action: Using importlib
  why_fails: Masks the problem without solving it
- action: Adding try/except pass around imports
  why_fails: Hides the error without fixing the cycle
evidence:
  success_count: 15
  failure_count: 4
  success_rate: 0.79
  avg_time_to_resolve_minutes: 6.0
  uses: 19
provenance: Seed pack v1 | Updated with SWE-bench patch file analysis | 2026-04-03
---


## When to Use This Pack

Use when you encounter:
- `ImportError` or `ModuleNotFoundError` for a module you know exists
- Circular import tracebacks
- Errors that appear only on first import

Do NOT use when the module genuinely does not exist.
