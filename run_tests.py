#!/usr/bin/env python
"""Run DeFi API client tests."""

import sys
from pathlib import Path

# Add borg to path
sys.path.insert(0, str(Path(__file__).parent))

from borg.defi import WhaleAlert, YieldOpportunity, Position, DeFiLlamaClient, DexScreenerClient
print("Import OK")

# Run pytest
import pytest
sys.exit(pytest.main([__file__.replace(".py", "_api_clients.py") if __file__.endswith("run_tests.py") else "borg/defi/tests/test_api_clients.py", "-v", "--tb=short", "-x"]))
