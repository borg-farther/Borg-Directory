#!/usr/bin/env python3
"""Test timing of borg commands."""
import time
import sys

from borg.cli import main

# Test what happens when we import borg directly
t0 = time.time()
import borg
t1 = time.time()
print(f'Direct import borg: {t1-t0:.3f}s', file=sys.stderr)

# Test version command via main
sys.argv = ['borg', 'version']
t2 = time.time()
main()
t3 = time.time()
print(f'Version command: {t3-t2:.3f}s', file=sys.stderr)
