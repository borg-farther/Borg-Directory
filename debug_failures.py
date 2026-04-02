#!/usr/bin/env python3
"""Debug script for failing performance tests."""
import sys
import threading
import time
sys.path.insert(0, '/root/hermes-workspace/borg')

print("=== P-008: CLI Startup Debug ===")
import subprocess
start = time.perf_counter()
result = subprocess.run(["borg", "version"], capture_output=True, text=True)
elapsed = time.perf_counter() - start
print(f"borg version time: {elapsed:.2f}s")
print(f"return code: {result.returncode}")
print(f"stdout: {result.stdout[:200]}")
print(f"stderr: {result.stderr[:200]}")

print("\n=== P-009: SQLite WAL Debug ===")
from borg.db.store import AgentStore

store = AgentStore()
conn = store._get_connection()

# Check if outcomes table exists
try:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='outcomes'")
    table_exists = cur.fetchone() is not None
    print(f"outcomes table exists: {table_exists}")
except Exception as e:
    print(f"Error checking outcomes table: {e}")

# Check table structure
try:
    cur = conn.execute("PRAGMA table_info(outcomes)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"outcomes columns: {cols}")
except Exception as e:
    print(f"Error getting outcomes columns: {e}")

# Try a single insert
try:
    from datetime import datetime
    conn.execute(
        "INSERT OR REPLACE INTO outcomes (id, query_key, pack_name, success, metrics, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("test_outcome_1", "USDC-ETH", "pack-1", True, "{}", datetime.now().isoformat())
    )
    conn.commit()
    print("Single insert succeeded")
except Exception as e:
    print(f"Single insert failed: {e}")

print("\n=== P-010: DeFi API Caching Debug ===")
from borg.defi.yield_scanner import YieldScanner

scanner = YieldScanner()
print(f"YieldScanner attributes: {[a for a in dir(scanner) if not a.startswith('_')]}")

# Check for cache-related attributes
cache_attrs = [a for a in dir(scanner) if 'cache' in a.lower()]
print(f"Cache-related attributes: {cache_attrs}")

# Check method signatures
import inspect
try:
    sig = inspect.signature(scanner.get_yields)
    print(f"get_yields signature: {sig}")
except Exception as e:
    print(f"Could not get signature: {e}")

# Test actual timing
print("\nTiming tests:")
start = time.perf_counter()
try:
    result = scanner.get_yields()
    print(f"  First call: {(time.perf_counter() - start)*1000:.1f}ms, result type: {type(result)}")
except Exception as e:
    print(f"  First call failed: {e}")

start = time.perf_counter()
try:
    result = scanner.get_yields()
    print(f"  Second call: {(time.perf_counter() - start)*1000:.1f}ms, result type: {type(result)}")
except Exception as e:
    print(f"  Second call failed: {e}")
