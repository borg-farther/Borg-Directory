#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.contextual_selector import classify_task, _EXTENSION_CATEGORIES

# Debug process_generic_task
print("DEBUG process_generic_task:")
task_type = "process_generic_task"
task_lower = task_type.lower()
print(f"  task_lower = {task_lower}")

from borg.core.contextual_selector import _CATEGORY_KEYWORDS
for cat, kws in _CATEGORY_KEYWORDS.items():
    for kw in kws:
        if kw in task_lower:
            print(f"  MATCH: '{kw}' in '{task_lower}' -> {cat}")

# Debug SQL error
print("\nDEBUG SQL error:")
error = "sqlalchemy.exc.OperationalError: database connection failed"
err_lower = error.lower()
print(f"  err_lower = {err_lower}")
for cat, kws in _CATEGORY_KEYWORDS.items():
    for kw in kws:
        if kw in err_lower:
            print(f"  MATCH: '{kw}' in '{err_lower}' -> {cat}")

# Debug file path
print("\nDEBUG /tests/test_auth.py:")
path = "/tests/test_auth.py"
path_lower = path.lower()
print(f"  path_lower = {path_lower}")
for pattern, cat in _EXTENSION_CATEGORIES.items():
    if pattern.lower() in path_lower:
        print(f"  MATCH: '{pattern}' in '{path_lower}' -> {cat}")

# Debug combined
print("\nDEBUG combined signals:")
ctx = {
    "task_type": "debug_flaky_test",
    "keywords": ["pytest", "test", "assert"],
    "file_path": "/tests/test_auth.py"
}
result = classify_task(**ctx)
print(f"  Result: {result}")
# task_type
task_lower = "debug_flaky_test".lower()
for cat, kws in _CATEGORY_KEYWORDS.items():
    for kw in kws:
        if kw in task_lower:
            print(f"  TASK_MATCH: '{kw}' -> {cat} (+2.0)")
# keywords
for kw in ["pytest", "test", "assert"]:
    kw_lower = kw.lower()
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if kw_lower in kws:
            print(f"  KW_MATCH: '{kw}' -> {cat} (+1.0)")
