#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.contextual_selector import classify_task

# Test 1: process_generic_task
result = classify_task(task_type='process_generic_task')
print(f'process_generic_task -> {result}')

# Test 2: SQL error
result = classify_task(error_type='sqlalchemy.exc.OperationalError: database connection failed')
print(f'SQL error -> {result}')

# Test 3: /tests/test_auth.py
result = classify_task(file_path='/tests/test_auth.py')
print(f'/tests/test_auth.py -> {result}')

# Test 4: combined signals
result = classify_task(task_type='debug_flaky_test', keywords=['pytest', 'test', 'assert'], file_path='/tests/test_auth.py')
print(f'combined signals -> {result}')
