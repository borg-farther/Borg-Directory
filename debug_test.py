#!/usr/bin/env python3
import asyncio
from unittest.mock import patch

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

async def mock_query(url, query, variables=None):
    return MOCK_AAVE_RESPONSE

async def test():
    # Import fresh each time
    import importlib
    import borg.defi.liquidation_watcher
    importlib.reload(borg.defi.liquidation_watcher)
    lw = borg.defi.liquidation_watcher
    
    # Let me manually run the logic of scan_aave_positions with debug
    chain = "ethereum"
    health_threshold = 1.1
    limit = 100
    
    subgraph_url = lw.AAVE_SUBGRAPHS[chain]
    print(f"subgraph_url = {subgraph_url}")
    
    query_str = lw._build_aave_query(health_threshold, limit, 0)
    variables = {"maxHealthFactor": str(health_threshold), "first": limit, "skip": 0}
    print(f"query_str = {query_str[:50]}...")
    print(f"variables = {variables}")
    
    data = await lw.query_subgraph(subgraph_url, query_str, variables)
    print(f"data = {data}")
    print(f"type(data) = {type(data)}")
    print(f"bool(data) = {bool(data)}")
    
    if data:
        print(f"'users' in data = {'users' in data}")
        print(f"data['users'] = {data.get('users')}")
    
    print("\n--- Now calling scan_aave_positions ---")
    with patch.object(lw, 'query_subgraph', side_effect=mock_query):
        targets = await lw.scan_aave_positions("ethereum", health_threshold=1.1)
        print(f"Got {len(targets)} targets")

asyncio.run(test())
