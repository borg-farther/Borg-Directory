#!/usr/bin/env python3
"""Measure import time for borg CLI."""
import time
import sys

# Test 1: Import just the cli module
t0 = time.time()
from borg.cli import main
t1 = time.time()
print(f'borg.cli import: {t1-t0:.3f}s', file=sys.stderr)

# Test 2: Import full borg package
t2 = time.time()
import borg
t3 = time.time()
print(f'full borg import: {t3-t2:.3f}s', file=sys.stderr)
