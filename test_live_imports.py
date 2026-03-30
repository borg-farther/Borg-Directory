#!/usr/bin/env python3
"""Quick test script for live_scans imports and basic validation."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg')

# Test that imports resolve
from borg.defi.cron.live_scans import yield_hunter, token_radar, tvl_pulse, stablecoin_watch, run_all_scans
print('All imports successful')
print('Functions:', [yield_hunter, token_radar, tvl_pulse, stablecoin_watch])

# Test message length with max results
import asyncio

async def test_message_lengths():
    # Test with max results cranked up
    yh = await yield_hunter(max_results=50, min_apy=0, min_tvl=0)
    print(f"\nyield_hunter (50 results): {len(yh)} chars")
    
    tr = await token_radar(max_results=50)
    print(f"token_radar (50 results): {len(tr)} chars")
    
    tvl = await tvl_pulse(max_results=50)
    print(f"tvl_pulse (50 results): {len(tvl)} chars")
    
    sw = await stablecoin_watch(top_n=50)
    print(f"stablecoin_watch (50 results): {len(sw)} chars")
    
    # Check for 4096 limit
    for name, msg in [("yield_hunter", yh), ("token_radar", tr), ("tvl_pulse", tvl), ("stablecoin_watch", sw)]:
        if len(msg) > 4096:
            print(f"⚠️ {name} EXCEEDS 4096 chars: {len(msg)}")
        else:
            print(f"✓ {name}: {len(msg)} chars (limit OK)")

asyncio.run(test_message_lengths())
