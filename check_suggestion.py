#!/usr/bin/env python3
import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')

import json
from borg.core.search import check_for_suggestion, _has_frustration_signals

# Test frustration signal detection
ctx = 'I tried everything, still failing, going in circles'
print('Frustration signals:', _has_frustration_signals(ctx))

# Test check_for_suggestion with frustration
result = json.loads(check_for_suggestion(ctx))
print('check_for_suggestion result:', result)

# Test check_for_suggestion with failure_count >= 2
result2 = json.loads(check_for_suggestion('I need to write a test', failure_count=2))
print('check_for_suggestion with failure_count=2:', result2)