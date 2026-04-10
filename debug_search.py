#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.search import borg_search

result = borg_search("NoneType has no attribute", mode="text", include_seeds=True)
print(result[:2000] if result else "EMPTY")
