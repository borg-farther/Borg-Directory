#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')
from borg.core.search import borg_search
result = borg_search('admin inline')
print(result[:1000] if len(result) > 1000 else result)