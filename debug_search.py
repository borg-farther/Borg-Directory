#!/usr/bin/env python3
"""Debug script to understand search behavior."""
from unittest.mock import patch
from pathlib import Path
import json

# Reproduce the test setup
fake_index = {'packs': [{'name': 'test-driven-development', 'id': 'test-driven-development', 'problem_class': 'testing', 'phase_names': ['phase_one']}]}

with patch('borg.core.search._fetch_index', return_value=fake_index):
    with patch('borg.core.search.BORG_DIR', Path('/nonexistent')):
        from borg.core.search import borg_search
        result = json.loads(borg_search('test-driven-development'))
        print('Result:', json.dumps(result, indent=2))
        print('BORG_DIR after patch:', end=' ')
        from borg.core import search as search_mod
        print(search_mod.BORG_DIR)
