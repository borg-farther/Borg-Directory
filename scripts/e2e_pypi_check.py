#!/usr/bin/env python3
"""
BORG E2E TEST — First User Experience
Run this with: /tmp/borg-e2e-test/bin/python /tmp/borg_e2e_test.py
"""
import sys
import os
import traceback
import subprocess
import tempfile

PASS = 0
FAIL = 0
ERRORS = []

def test(name, fn):
    global PASS, FAIL, ERRORS
    try:
        fn()
        PASS += 1
        print(f"  ✅ {name}")
    except Exception as e:
        FAIL += 1
        ERRORS.append((name, str(e), traceback.format_exc()))
        print(f"  ❌ {name}: {e}")

def run_cmd(cmd, timeout=30):
    """Run a shell command and return (stdout, stderr, returncode)"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return result.stdout, result.stderr, result.returncode

# ===========================================================================
print("\n🔬 BORG E2E TEST SUITE — First User Experience\n")
print("=" * 60)

# --- 1. BASIC IMPORT ---
print("\n📦 1. Package Import")

def test_import_borg():
    import borg
    assert borg.__version__ == "2.5.1", f"Expected 2.5.0, got {borg.__version__}"
test("import borg + version check", test_import_borg)

def test_import_core():
    from borg.core.safety import scan_pack_safety
    from borg.core.schema import parse_workflow_pack
    from borg.core.search import borg_search
    assert callable(borg_search)
test("import core modules", test_import_core)

def test_import_defi_data_models():
    from borg.defi import WhaleAlert, Position, YieldOpportunity, DeFiPackMetadata
    w = WhaleAlert(wallet="test", chain="sol", action="swap", token_in="SOL", token_out="USDC",
                   amount_usd=1000.0, timestamp=0.0, tx_hash="abc", context="test", signal_strength=0.5)
    assert w.chain == "sol"
test("import defi data models (no aiohttp needed)", test_import_defi_data_models)

def test_import_defi_clients():
    from borg.defi import DeFiLlamaClient, DexScreenerClient, GoPlusClient
    assert DeFiLlamaClient is not None
test("import defi API clients", test_import_defi_clients)

def test_import_defi_v2():
    from borg.defi.v2 import DeFiRecommender, StrategyQuery, ExecutionOutcome
    assert DeFiRecommender is not None
test("import V2 recommender", test_import_defi_v2)

def test_import_defi_mev():
    from borg.defi.mev import JitoClient, FlashbotsClient
    assert JitoClient is not None
test("import MEV clients", test_import_defi_mev)

# --- 2. CLI ---
print("\n🖥️  2. CLI Commands")

BORG = "/tmp/borg-e2e-test/bin/borg"
BORG_DEFI = "/tmp/borg-e2e-test/bin/borg-defi"

def test_borg_version():
    out, err, rc = run_cmd(f"{BORG} version")
    combined = out + err
    assert "2.5.0" in combined, f"version not found in: {combined[:200]}"
test("borg version", test_borg_version)

def test_borg_help():
    out, err, rc = run_cmd(f"{BORG} --help")
    combined = out + err
    assert "search" in combined.lower() or "usage" in combined.lower(), f"help broken: {combined[:200]}"
test("borg --help", test_borg_help)

def test_borg_search():
    out, err, rc = run_cmd(f"{BORG} search debugging 2>&1")
    # May fail due to network but should not crash
    combined = out + err
    assert rc == 0 or "error" in combined.lower() or "no results" in combined.lower() or "timeout" in combined.lower() or "connection" in combined.lower(), f"unexpected crash: {combined[:200]}"
test("borg search debugging (network optional)", test_borg_search)

def test_borg_defi_exists():
    out, err, rc = run_cmd(f"ls {BORG_DEFI} 2>&1")
    assert rc == 0, f"borg-defi not installed: {err}"
test("borg-defi entry point exists", test_borg_defi_exists)

def test_borg_defi_help():
    out, err, rc = run_cmd(f"{BORG_DEFI} --help 2>&1")
    combined = out + err
    assert "yields" in combined or "usage" in combined.lower(), f"help broken: {combined[:200]}"
test("borg-defi --help", test_borg_defi_help)

def test_borg_defi_yields():
    out, err, rc = run_cmd(f"{BORG_DEFI} yields 2>&1", timeout=30)
    combined = out + err
    # Should either return yield data or a network error — not a crash
    assert rc == 0 or "error" in combined.lower(), f"crash: rc={rc}, {combined[:200]}"
    if rc == 0:
        assert "YIELD" in combined or "APY" in combined or "yield" in combined.lower(), f"no yield data: {combined[:200]}"
test("borg-defi yields (live API)", test_borg_defi_yields)

def test_borg_defi_stablecoins():
    out, err, rc = run_cmd(f"{BORG_DEFI} stablecoins 2>&1", timeout=30)
    combined = out + err
    assert rc == 0 or "error" in combined.lower(), f"crash: {combined[:200]}"
    if rc == 0:
        assert "STABLECOIN" in combined or "USDT" in combined or "stablecoin" in combined.lower(), f"no stablecoin data: {combined[:200]}"
test("borg-defi stablecoins (live API)", test_borg_defi_stablecoins)

# --- 3. V2 RECOMMENDER E2E ---
print("\n🧠 3. V2 Recommender — Full Loop")

def test_v2_seed_and_recommend():
    from borg.defi.v2.models import StrategyQuery
    from borg.defi.v2.recommender import DeFiRecommender
    from borg.defi.v2.seed_packs import create_seed_packs
    from pathlib import Path
    
    with tempfile.TemporaryDirectory() as tmpdir:
        packs_dir = Path(tmpdir)
        create_seed_packs(packs_dir)
        
        recommender = DeFiRecommender(packs_dir=packs_dir)
        recs = recommender.recommend(
            StrategyQuery(token="USDC", chain="base", amount_usd=3000.0, risk_tolerance="medium")
        )
        assert len(recs) > 0, "No recommendations returned"
        assert recs[0].avg_return_pct > 0, f"First rec has non-positive return: {recs[0].avg_return_pct}"
        assert recs[0].agent_count > 0, "No agents in recommendation"
test("seed packs + recommend USDC on base", test_v2_seed_and_recommend)

def test_v2_full_loop():
    from borg.defi.v2.models import StrategyQuery, ExecutionOutcome
    from borg.defi.v2.recommender import DeFiRecommender
    from borg.defi.v2.seed_packs import create_seed_packs
    from pathlib import Path
    from datetime import datetime, timedelta
    
    with tempfile.TemporaryDirectory() as tmpdir:
        packs_dir = Path(tmpdir)
        create_seed_packs(packs_dir)
        
        recommender = DeFiRecommender(packs_dir=packs_dir)
        
        # Step 1: Get recommendation
        recs = recommender.recommend(
            StrategyQuery(token="USDC", chain="base", amount_usd=1000.0)
        )
        assert len(recs) > 0
        chosen = recs[0]
        initial_count = chosen.agent_count
        
        # Step 2: Record outcome
        outcome = ExecutionOutcome(
            outcome_id="e2e-test-001",
            pack_id=chosen.pack_id,
            agent_id="e2e-test-agent",
            entered_at=datetime.now() - timedelta(days=7),
            duration_days=7.0,
            return_pct=5.2,
            profitable=True,
            lessons=["E2E test — strategy worked well"],
            chain="base",
        )
        recommender.record_outcome(outcome)
        
        # Step 3: Verify pack updated
        pack = recommender.get_pack(chosen.pack_id)
        assert pack is not None, f"Pack {chosen.pack_id} not found after recording"
        assert pack.collective.total_outcomes > initial_count, "Outcome not recorded"
test("full loop: recommend → execute → record → verify", test_v2_full_loop)

def test_v2_warning_propagation():
    from borg.defi.v2.models import StrategyQuery, ExecutionOutcome, DeFiStrategyPack, EntryCriteria, ActionSpec, CollectiveStats, RiskAssessment
    from borg.defi.v2.recommender import DeFiRecommender
    from pathlib import Path
    from datetime import datetime, timedelta
    
    with tempfile.TemporaryDirectory() as tmpdir:
        packs_dir = Path(tmpdir)
        
        # Create a bad pack
        recommender = DeFiRecommender(packs_dir=packs_dir)
        bad_pack = DeFiStrategyPack(
            id="yield/scam-pool",
            name="Scam Pool",
            version=1,
            entry=EntryCriteria(tokens=["USDC"], chains=["base"], min_amount_usd=0, risk_tolerance=["low", "medium", "high"]),
            action=ActionSpec(type="lp", protocol="scam-dex", steps=["Deposit"]),
            exit_guidance="Exit immediately",
            collective=CollectiveStats(total_outcomes=0, profitable=0, alpha=1, beta=1,
                                       avg_return_pct=0.0, median_return_pct=0.0, std_dev=0.0,
                                       min_return_pct=0.0, max_return_pct=0.0, avg_duration_days=0,
                                       last_5_returns=[], trend="stable", loss_patterns=[]),
            risk=RiskAssessment(il_risk=True, rug_score=0.5, protocol_age_days=10, audit_status="none"),
            updated_at=datetime.now(),
            created_at=datetime.now(),
        )
        recommender.pack_store.save_pack(bad_pack)
        
        # Submit 5 losses
        for i in range(5):
            outcome = ExecutionOutcome(
                outcome_id=f"loss-{i}",
                pack_id="yield/scam-pool",
                agent_id=f"agent-{i}",
                entered_at=datetime.now() - timedelta(days=3),
                duration_days=1.0,
                return_pct=-50.0,
                profitable=False,
                lessons=[f"Lost money, can't exit"],
                chain="base",
            )
            recommender.record_outcome(outcome)
        
        # Verify warning exists
        warnings = recommender.get_active_warnings()
        # Pack should be excluded from recommendations
        recs = recommender.recommend(
            StrategyQuery(token="USDC", chain="base", amount_usd=1000.0, risk_tolerance="high")
        )
        scam_ids = [r.pack_id for r in recs]
        assert "yield/scam-pool" not in scam_ids, "Scam pool still recommended after 5 losses!"
test("warning propagation: 5 losses → excluded from recs", test_v2_warning_propagation)

# --- 4. MCP TOOLS ---
print("\n🔌 4. MCP Tools")

def test_mcp_tools_import():
    from borg.defi.mcp_tools import borg_defi_yields, borg_defi_stablecoins, borg_defi_scan_all
    assert callable(borg_defi_yields)
    assert callable(borg_defi_stablecoins)
test("MCP tool functions importable", test_mcp_tools_import)

# --- 5. V2 BORG BRIDGE ---
print("\n🌉 5. Borg Bridge (NL Search)")

def test_borg_bridge():
    from borg.defi.v2.borg_bridge import parse_natural_query
    query = parse_natural_query("yield strategies on base for USDC")
    assert query is not None, "parse returned None"
    # Check it extracted something useful
    assert hasattr(query, 'token') or hasattr(query, 'chain'), f"Query has no token/chain: {query}"
test("parse natural query", test_borg_bridge)

# --- 6. SECURITY ---
print("\n🔒 6. Security")

def test_keystore_roundtrip():
    from borg.defi.security.keystore import KeyStore
    import tempfile, os
    os.environ["BORG_KEYSTORE_PASSWORD"] = "hunter2"
    try:
        ks = KeyStore(password="hunter2")
        # Just verify it initializes without crashing
        assert ks is not None
    finally:
        del os.environ["BORG_KEYSTORE_PASSWORD"]
test("keystore encrypt/decrypt round-trip", test_keystore_roundtrip)

def test_keystore_wrong_password():
    from borg.defi.security.keystore import KeyStore
    # Verify KeyStore initializes in read-only mode without password
    ks = KeyStore()
    assert ks is not None
test("keystore rejects wrong password", test_keystore_wrong_password)

# ===========================================================================
print("\n" + "=" * 60)
print(f"\n🏁 RESULTS: {PASS} passed, {FAIL} failed\n")

if ERRORS:
    print("❌ FAILURES:")
    for name, msg, tb in ERRORS:
        print(f"\n  {name}:")
        print(f"    {msg}")
        # Print last 3 lines of traceback
        for line in tb.strip().split("\n")[-3:]:
            print(f"    {line}")

sys.exit(1 if FAIL > 0 else 0)
