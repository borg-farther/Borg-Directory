#!/bin/bash
cd /root/hermes-workspace/borg
HERMES_HOME=/root/.hermes python3 - <<'PYEOF'
import os, sys, sqlite3
from pathlib import Path
sys.path.insert(0, '/root/hermes-workspace/borg')

HERMES_HOME = Path('/root/.hermes')
BORG_V3_DB = HERMES_HOME / '.borg' / 'borg_v3.db'
FAILURES_DIR = HERMES_HOME / 'borg' / 'failures'

print("=" * 70)
print("BORG V3 FEEDBACK LOOP — ADVERSARIAL E2E VALIDATION")
print("=" * 70)

def db_count():
    if not BORG_V3_DB.exists(): return 0
    with sqlite3.connect(str(BORG_V3_DB)) as conn:
        return conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]

def failure_count():
    if not FAILURES_DIR.exists(): return 0
    return sum(1 for _ in FAILURES_DIR.rglob("*.yaml"))

print(f"\n=== STEP 0: BASELINE ===")
print(f"BORG_V3_DB: {BORG_V3_DB}  exists={BORG_V3_DB.exists()}")
print(f"FAILURES_DIR: {FAILURES_DIR}  exists={FAILURES_DIR.exists()}")
baseline_db = db_count()
baseline_fail = failure_count()
print(f"Baseline outcomes rows: {baseline_db}")
print(f"Baseline failure YAMLs: {baseline_fail}")

print(f"\n=== STEP 1: IMPORT + INSTRUMENTATION CHECK ===")
from borg.core.v3_integration import BorgV3
v3 = BorgV3()
print(f"BorgV3 instantiated.")
print(f"  _selector type: {type(v3._selector).__name__}")
print(f"  _feedback type: {type(v3._feedback).__name__}")
print(f"  _mutation type: {type(v3._mutation).__name__}")
print(f"  hasattr(_feedback, 'record'): {hasattr(v3._feedback, 'record')}")

print(f"\n=== STEP 2: EXEC 1 — SUCCESS ===")
v3.record_outcome(
    pack_id="test://e2e-validation",
    task_context={"task_type":"debug_auth","error_type":"credential_error","language":"python","keywords":["auth","login"],"file_path":"/src/auth.py","error_message":None},
    success=True, tokens_used=100, time_taken=3.5, agent_id="e2e-tester", session_id=None
)
print(f"After exec1 — outcomes rows: {db_count()} (expected 1), failures: {failure_count()} (expected 0)")

print(f"\n=== STEP 3: EXEC 2 — FAILURE with error_message ===")
v3.record_outcome(
    pack_id="test://e2e-validation",
    task_context={"task_type":"debug_auth","error_type":"credential_error","language":"python","keywords":["auth","login"],"file_path":"/src/auth.py","error_message":"TypeError: 'NoneType' object has no attribute 'get' in /src/auth.py:42"},
    success=False, tokens_used=100, time_taken=3.5, agent_id="e2e-tester", session_id=None
)
print(f"After exec2 — outcomes rows: {db_count()} (expected 2), failures: {failure_count()} (expected 1)")

print(f"\n=== STEP 4: EXEC 3 — FAILURE without error_message ===")
v3.record_outcome(
    pack_id="test://e2e-validation",
    task_context={"task_type":"debug_auth","error_type":"credential_error","language":"python","keywords":["auth","login"],"file_path":"/src/auth.py","error_message":None},
    success=False, tokens_used=100, time_taken=3.5, agent_id="e2e-tester", session_id=None
)
print(f"After exec3 — outcomes rows: {db_count()} (expected 3), failures: {failure_count()} (expected 2)")

print(f"\n=== STEP 5: BetaPosterior check ===")
key = ("test://e2e-validation", "debug")
posteriors = v3._selector._posteriors
if key in posteriors:
    p = posteriors[key]
    print(f"  FOUND: alpha={p.alpha}, beta={p.beta}, mean={p.mean:.4f}, uncertainty={p.uncertainty:.4f}")
    print(f"  Expected: alpha>1 (1 success), beta>1 (2 failures)")
    if p.alpha > 1.0 and p.beta > 1.0:
        print(f"  Thompson Sampling UPDATE: PASS")
    else:
        print(f"  Thompson Sampling UPDATE: FAIL — posteriors not updated correctly")
else:
    print(f"  NOT FOUND — key {key} absent from posteriors")
    print(f"  Available keys (first 10): {list(posteriors.keys())[:10]}")
    print(f"  ContextualSelector UPDATE: FAIL")

print(f"\n=== STEP 6: FeedbackLoop signal check ===")
fl = v3._feedback
if hasattr(fl, '_signals'):
    print(f"  FeedbackLoop._signals: {len(fl._signals)} signals")
    for s in fl._signals:
        print(f"    - pack_id={s.pack_id} signal_type={s.signal_type} value={s.value}")
elif hasattr(fl, 'aggregator') and hasattr(fl.aggregator, '_pack_signals'):
    total = sum(len(s) for s in fl.aggregator._pack_signals.values())
    print(f"  FeedbackLoop.aggregator._pack_signals: {total} total signals")
    for k, v in fl.aggregator._pack_signals.items():
        print(f"    pack_id={k}: {len(v)} signals")
        for s in v:
            print(f"      - signal_type={s.signal_type} value={s.value}")
else:
    print(f"  FeedbackLoop has neither _signals nor aggregator._pack_signals")
    print(f"  __dict__.keys(): {list(fl.__dict__.keys())}")
    print(f"  FeedbackLoop signal recording: FAIL")

print(f"\n=== STEP 7: CRITICAL-1 — direct .record() call ===")
fl2 = v3._feedback
print(f"  hasattr(fl2, 'record'): {hasattr(fl2, 'record')}")
if hasattr(fl2, 'record'):
    try:
        fl2.record(pack_id="test://crit1", task_context={}, success=True, tokens_used=0, time_taken=0.0, agent_id="e2e")
        print(f"  CRITICAL-1: PASS — .record() succeeded without raising")
    except AttributeError as e:
        print(f"  CRITICAL-1: FAIL — AttributeError: {e}")
        import traceback; traceback.print_exc()
    except Exception as e:
        print(f"  CRITICAL-1: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
else:
    print(f"  CRITICAL-1: FAIL — FeedbackLoop has no .record method")

print(f"\n=== STEP 8: DojoPipeline ===")
try:
    from borg.dojo.pipeline import DojoPipeline
    pipeline = DojoPipeline()
    print(f"  DojoPipeline instantiated.")
    print(f"  hasattr(_feed_thompson_sampling): {hasattr(pipeline, '_feed_thompson_sampling')}")
    print(f"  hasattr(_feed_failure_memory): {hasattr(pipeline, '_feed_failure_memory')}")
    print(f"  Calling pipeline.run(days=1, auto_fix=False, report_fmt='cli', deliver_to=None)...")
    report = pipeline.run(days=1, auto_fix=False, report_fmt='cli', deliver_to=None)
    print(f"  Pipeline.run() returned. type={type(report).__name__}, len={len(report) if report else 0}")
    if report:
        print(f"  Report (first 500 chars): {report[:500]}")
    if hasattr(pipeline, '_feed_thompson_sampling'):
        print(f"  Calling _feed_thompson_sampling() directly...")
        pipeline._feed_thompson_sampling()
        print(f"  _feed_thompson_sampling(): SUCCESS")
except ImportError as e:
    print(f"  DojoPipeline ImportError: {e}")
    import traceback; traceback.print_exc()
except Exception as e:
    print(f"  DojoPipeline error: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print(f"\n=== VERDICT ===")
delta_db = db_count() - baseline_db
delta_fail = failure_count() - baseline_fail
print(f"  SQLite rows delta: {delta_db} (expected 3) — {'PASS' if delta_db == 3 else 'FAIL'}")
print(f"  Failure YAMLs delta: {delta_fail} (expected 2) — {'PASS' if delta_fail == 2 else 'FAIL'}")
print(f"  Thompson Sampling: {'PASS' if key in posteriors and posteriors[key].alpha > 1.0 else 'FAIL'}")
print(f"  FeedbackLoop signals: FAIL (see Step 6 above)")
print(f"  CRITICAL-1 .record method: {'PASS' if hasattr(fl, 'record') else 'FAIL'}")
print(f"\n{'='*70}")
print("E2E VALIDATION COMPLETE")
print(f"{'='*70}")
PYEOF
