#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.contextual_selector import _EXTENSION_CATEGORIES

path = "/tests/test_auth.py"
path_lower = path.lower()
print(f"path_lower = {path_lower}")

for pattern, cat in _EXTENSION_CATEGORIES.items():
    if pattern.lower() in path_lower:
        print(f"  MATCH: '{pattern}' in '{path_lower}' -> {cat}")
    else:
        print(f"  no match: '{pattern}'")
