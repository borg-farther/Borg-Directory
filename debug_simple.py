#!/usr/bin/env python3
"""Debug script to understand the mocking issue."""
import asyncio
import sys

# Add the borg path
sys.path.insert(0, '/root/hermes-workspace/borg')

import borg.defi.liquidation_watcher as liquidation_watcher
from borg.defi.liquidation_watcher import scan_aave_positions, LiquidationTarget

MOCK_AAVE_RESPONSE = {
    "data": {
        "users": [
            {
                "id": "0x1234567890abcdef1234567890abcdef12345678",
                "healthFactor": "1.05",
                "totalCollateralUSD": "50000.0",
                "totalDebtUSD": "45000.0",
            },
        ]
    }
}

async def main():
    original_query = liquidation_watcher.query_subgraph
    
    async def mock_query(url, query, variables=None):
        print(f"MOCK QUERY CALLED: url={url}")
        return MOCK_AAVE_RESPONSE
    
    print(f"Before replacement: query_subgraph = {liquidation_watcher.query_subgraph}")
    
    liquidation_watcher.query_subgraph = mock_query
    
    print(f"After replacement: query_subgraph = {liquidation_watcher.query_subgraph}")
    print(f"scan_aave_positions.__module__ = {scan_aave_positions.__module__}")
    
    # Call the function directly from the module
    result = await liquidation_watcher.scan_aave_positions("ethereum", health_threshold=1.1)
    print(f"Direct call result: {len(result)} targets")

asyncio.run(main())
