#!/usr/bin/env python3
"""Test borg import."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')
from borg.core.search import borg_search
print("SUCCESS: borg_search imported")