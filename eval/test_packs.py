#!/usr/bin/env python3
"""Test that pack taxonomy works correctly."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.pack_taxonomy import classify_error, load_pack_by_problem_class, get_cache, render_pack_guidance, debug_error

# Test 1: How many packs are loaded
cache = get_cache()
packs = list(cache.values())
print(f'Packs loaded: {len(packs)}')
for p in packs:
    print(f'  - {p.get("id", "unknown")}: {p.get("problem_class", "unknown")}')

# Test 2: Classify various errors
test_errors = [
    'TypeError: "NoneType" object has no attribute "split"',
    'ImportError: cannot import name "CircularDependency"',
    'IntegrityError: FOREIGN KEY constraint failed',
    'django.core.exceptions.ImproperlyConfigured: SECRET_KEY...',
    'OperationalError: no such table: django_migrations',
]
for err in test_errors:
    pc = classify_error(err)
    print(f'  [{pc}] {err[:60]}')

# Test 3: Try rendering guidance for null_pointer_chain
pc = 'null_pointer_chain'
pack = load_pack_by_problem_class(pc)
if pack:
    guidance = render_pack_guidance(pack)
    print(f'\n  Rendered guidance for {pc}: {len(guidance)} chars')
    print(guidance[:800])
else:
    print(f'  No pack found for {pc}')

# Test 4: Try debug_error
err = 'TypeError: "NoneType" object has no attribute "split"'
result = debug_error(err)
print(f'\n  debug_error output: {len(result)} chars')
print(result[:600])
