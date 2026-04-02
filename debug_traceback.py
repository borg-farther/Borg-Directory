#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.contextual_selector import classify_task, _CATEGORY_KEYWORDS

# Debug traceback
error = "Traceback (most recent call last):\n  File 'test.py', line 42"
err_lower = error.lower()
print(f"Error: {error}")
print(f"err_lower: {err_lower}")
for cat, kws in _CATEGORY_KEYWORDS.items():
    for kw in kws:
        if kw in err_lower:
            print(f"  MATCH: '{kw}' in '{err_lower}' -> {cat}")

result = classify_task(error_type=error)
print(f"\nResult: {result}")

# Debug combined
print("\n--- Combined ---")
ctx = {
    "task_type": "debug_flaky_test",
    "keywords": ["pytest", "test", "assert"],
    "file_path": "/tests/test_auth.py"
}
task_type = ctx["task_type"]
keywords = ctx["keywords"]

task_lower = task_type.lower()
print(f"task_type = {task_type}, task_lower = {task_lower}")
for cat, kws in _CATEGORY_KEYWORDS.items():
    for kw in kws:
        if kw in task_lower:
            print(f"  TASK '{kw}' -> {cat} (+3.0)")

for kw in keywords:
    kw_lower = kw.lower()
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if kw_lower in kws:
            print(f"  KW '{kw}' -> {cat} (+1.0)")
