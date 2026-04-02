#!/usr/bin/env python3
import sys
sys.path.insert(0,'/root/hermes-workspace/borg')
try:
    from borg.core.search import borg_search
    print("borg_search imported successfully")
except Exception as e:
    print(f"Error: {e}")