#!/usr/bin/env python3
"""
Borg V3 Feedback Loop — Full Adversarial E2E Validation
Posts results back via Telegram bot directly so they arrive in-session.
"""

import os
import sys
import sqlite3
import urllib.request
import json
from pathlib import Path

# Ensure borg is importable
_BORG_ROOT = Path("/root/hermes-workspace/borg")
sys.path.insert(0, str(_BORG_ROOT))

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
BORG_V3_DB = HERMES_HOME / ".borg" / "borg_v3.db"
FAILURES_DIR = HERMES_HOME / "borg" / "failures"
STATE_DB = HERMES_HOME / "state.db"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

lines = []

def log(msg):
    print(msg)
    lines.append(str(msg))

def send_telegram(text):
    """Send message via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)

def flush():
    msg = "\n".join(lines)
    send_telegram(msg)
    print("=" * 70, file=sys.stderr)
    print(msg, file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    lines.clear()

log("=" * 70)
log("BORG V3 FEEDBACK LOOP — ADVERSARIAL E2E VALIDATION")
log("=" * 70)
log(f"HERMES_HOME : {HERMES_HOME}")
log(f"BORG_V3_DB  : {BORG_V3_DB}")
log(f"FAILURES_DIR: {FAILURES_DIR}")
log(f"STATE_DB    : {STATE_DB}")
log("")

# ── helpers ──────────────────────────────────────────────────────────────────

def count_db_rows(db_path):
    if not Path(db_path).exists():
        return 0
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute("SELECT COUNT(*) FROM outcomes")
        return cur.fetchone()[0]

def get_posterior_alpha_beta(pack_id, category="debug"):
    try:
        from borg.core.v3_integration import BorgV3
        v3 = BorgV3()
        sel = v3._selector
        key = (pack_id, category)
        if hasattr(sel, '_posteriors') and key in sel._posteriors:
            p = sel._posteriors[key]
            return p.alpha, p.beta
    except Exception as e:
        log(f"  [WARNING] Could not read posterior: {e}")
    return None, None

def count_failure_entries(failures_dir):
    if not failures_dir.exists():
        return 0
    return sum(1 for _ in failures_dir.rglob("*.yaml"))

def snapshot(label):
    from borg.core.v3_integration import BorgV3
    v3 = BorgV3()
    db_count = count_db_rows(BORG_V3_DB)
    post_a, post_b = get_posterior_alpha_beta("test://e2e-validation", "debug")
    fail_count = count_failure_entries(FAILURES_DIR)
    fl = v3._feedback
    if hasattr(fl, '_signals'):
        fl_count = len(fl._signals)
    elif hasattr(fl, 'aggregator') and hasattr(fl.aggregator, '_pack_signals'):
        total = sum(len(s) for s in fl.aggregator._pack_signals.values())
        fl_count = total
    else:
        fl_count = "unknown"
    log(f"  SNAPSHOT {label}:")
    log(f"    outcomes table rows  : {db_count}")
    log(f"    Beta posterior (α,β) : ({post_a}, {post_b})")
    log(f"    failure_memory YAMLs : {fail_count}")
    log(f"    FeedbackLoop signals : {fl_count}")
    return {"db_rows": db_count, "posterior": (post_a, post_b), "failure_yamls": fail_count, "fl_signals": fl_count}

def run_execution(v3, pack_id, success, task_context, exec_num):
    log(f"")
    log(f"{'='*60}")
    log(f"EXECUTION {exec_num}: pack_id={pack_id!r} success={success}")
    log(f"  task_context = {task_context}")
    log(f"")
    v3.record_outcome(
        pack_id=pack_id,
        task_context=task_context,
        success=success,
        tokens_used=100,
        time_taken=3.5,
        agent_id="e2e-tester",
        session_id=None,
    )
    log(f"EXECUTION {exec_num} COMPLETE")

# ── Step 0: Baseline ─────────────────────────────────────────────────────────

log("STEP 0: BASELINE STATE")
log("-" * 40)
baseline = snapshot("BASELINE")
flush()

# ── Step 1: Execution 1 — SUCCESS ──────────────────────────────────────────

log(f"")
log(f"{'='*60}")
log("STEP 1: EXECUTION 1 — SUCCESS (no error context)")
log("-" * 40)

from borg.core.v3_integration import BorgV3
v3 = BorgV3()

run_execution(v3, "test://e2e-validation", True, {
    "task_type": "debug_auth",
    "error_type": "credential_error",
    "language": "python",
    "keywords": ["auth", "login"],
    "file_path": "/src/auth.py",
    "error_message": None,
    "phase": "apply",
}, exec_num=1)

snap1 = snapshot("POST-EXEC1")
flush()

# ── Step 2: Execution 2 — FAILURE with error context ──────────────────────

log(f"")
log(f"{'='*60}")
log("STEP 2: EXECUTION 2 — FAILURE with error_message in context")
log("-" * 40)

run_execution(v3, "test://e2e-validation", False, {
    "task_type": "debug_auth",
    "error_type": "credential_error",
    "language": "python",
    "keywords": ["auth", "login"],
    "file_path": "/src/auth.py",
    "error_message": "TypeError: 'NoneType' object has no attribute 'get' in /src/auth.py:42",
    "phase": "apply",
}, exec_num=2)

snap2 = snapshot("POST-EXEC2")
flush()

# ── Step 3: Execution 3 — FAILURE without error context ───────────────────

log(f"")
log(f"{'='*60}")
log("STEP 3: EXECUTION 3 — FAILURE without error_message")
log("-" * 40)

run_execution(v3, "test://e2e-validation", False, {
    "task_type": "debug_auth",
    "error_type": "credential_error",
    "language": "python",
    "keywords": ["auth", "login"],
    "file_path": "/src/auth.py",
    "error_message": None,
    "phase": "apply",
}, exec_num=3)

snap3 = snapshot("POST-EXEC3")
flush()

# ── Step 4: Summary table ─────────────────────────────────────────────────

log(f"")
log(f"{'='*60}")
log("STEP 4: STATE PROGRESSION SUMMARY")
log("-" * 40)
log(f"{'Metric':<25} {'Baseline':>10} {'Post-Exec1':>10} {'Post-Exec2':>10} {'Post-Exec3':>10}")
log(f"{'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
log(f"{'outcomes DB rows':<25} {baseline['db_rows']:>10} {snap1['db_rows']:>10} {snap2['db_rows']:>10} {snap3['db_rows']:>10}")
pa, pb = baseline['posterior']
log(f"{'Beta post. (α,β)':<25} {f'({pa},{pb})':>10} {str(snap1['posterior']):>10} {str(snap2['posterior']):>10} {str(snap3['posterior']):>10}")
log(f"{'failure YAMLs':<25} {baseline['failure_yamls']:>10} {snap1['failure_yamls']:>10} {snap2['failure_yamls']:>10} {snap3['failure_yamls']:>10}")
log(f"{'FL signals':<25} {str(baseline['fl_signals']):>10} {str(snap1['fl_signals']):>10} {str(snap2['fl_signals']):>10} {str(snap3['fl_signals']):>10}")
flush()

# ── Step 5: CRITICAL-1 test ───────────────────────────────────────────────

log(f"")
log(f"{'='*60}")
log("STEP 5: CRITICAL-1 — DIRECT .record() CALL ON FeedbackLoop")
log("-" * 40)

from borg.core.v3_integration import BorgV3 as BV3
v3_fresh = BV3()
fl = v3_fresh._feedback

log(f"FeedbackLoop type   : {type(fl).__name__}")
log(f"hasattr(fl, 'record'): {hasattr(fl, 'record')}")

if hasattr(fl, 'record'):
    log("Calling: fl.record(pack_id='test', task_context={...}, success=True, ...)")
    try:
        fl.record(
            pack_id="test://crit1-direct",
            task_context={"task_type": "debug", "error_message": "test error"},
            success=True,
            tokens_used=0,
            time_taken=0.0,
            agent_id="e2e-direct-test",
        )
        log("RESULT: SUCCESS — no exception raised")
    except AttributeError as e:
        log(f"RESULT: AttributeError — {e}")
        import traceback
        for line in traceback.format_exc().splitlines():
            log(f"  {line}")
    except Exception as e:
        log(f"RESULT: {type(e).__name__} — {e}")
        import traceback
        for line in traceback.format_exc().splitlines():
            log(f"  {line}")
else:
    log("SKIPPED — FeedbackLoop has no .record method (CRITICAL-1 confirmed BROKEN)")

flush()

# ── Step 6: DojoPipeline ───────────────────────────────────────────────────

log(f"")
log(f"{'='*60}")
log("STEP 6: DOJO PIPELINE — MANUAL RUN with --days 1")
log("-" * 40)

os.environ["BORG_DOJO_ENABLED"] = "true"

pipeline = None
try:
    from borg.dojo.pipeline import DojoPipeline, BORG_DOJO_ENABLED
    log(f"Import: DojoPipeline found. BORG_DOJO_ENABLED={BORG_DOJO_ENABLED}")
    pipeline = DojoPipeline()
    log(f"pipeline has _feed_thompson_sampling: {hasattr(pipeline, '_feed_thompson_sampling')}")
    log(f"pipeline has _feed_failure_memory: {hasattr(pipeline, '_feed_failure_memory')}")
    log(f"")
    log("Running pipeline.run(days=1, auto_fix=False)...")
    try:
        report = pipeline.run(days=1, auto_fix=False, report_fmt="cli", deliver_to=None)
        log(f"Pipeline.run() returned OK. report len={len(report)}")
        log(f"Report preview: {report[:300] if report else '(empty)'}")
    except Exception as e:
        log(f"Pipeline.run() RAISED: {type(e).__name__}: {e}")
        import traceback
        for line in traceback.format_exc().splitlines():
            log(f"  {line}")
except ImportError as e:
    log(f"ImportError: {e}")
    import traceback
    for line in traceback.format_exc().splitlines():
        log(f"  {line}")
except Exception as e:
    log(f"Unexpected: {type(e).__name__}: {e}")
    import traceback
    for line in traceback.format_exc().splitlines():
        log(f"  {line}")

if pipeline and hasattr(pipeline, '_feed_thompson_sampling'):
    log("")
    log("Direct call to _feed_thompson_sampling():")
    try:
        pipeline._feed_thompson_sampling()
        log("  SUCCESS — no exception")
    except ImportError as e:
        log(f"  ImportError: {e}")
        import traceback
        for line in traceback.format_exc().splitlines():
            log(f"  {line}")
    except Exception as e:
        log(f"  {type(e).__name__}: {e}")
        import traceback
        for line in traceback.format_exc().splitlines():
            log(f"  {line}")

flush()

# ── Step 7: Verdict ────────────────────────────────────────────────────────

log(f"")
log(f"{'='*60}")
log("STEP 7: VERDICT")
log("-" * 40)

path1_works = snap3["db_rows"] > baseline["db_rows"]
path2_works = snap3["posterior"] != baseline["posterior"]
path3_works = snap3["fl_signals"] not in ("unknown", -1, None) and snap3["fl_signals"] != baseline["fl_signals"]

log(f"COMPONENT                                    EXPECTED          ACTUAL          VERDICT")
log(f"{'-'*70}")
log(f"SQLite persistence (PATH-1)                  rows +3           +{snap3['db_rows']-baseline['db_rows']}            {'PASS ✓' if path1_works else 'FAIL ✗'}")
log(f"ContextualSelector Thompson (PATH-2)          α/β updated       {snap3['posterior']}      {'PASS ✓' if path2_works else 'FAIL ✗'}")
log(f"FeedbackLoop signal (PATH-3)                 signals > baseline {snap3['fl_signals']}       {'PASS ✓' if path3_works else 'FAIL ✗'}")
log(f"FailureMemory write on failure              YAML created       {snap3['failure_yamls']}             {'PASS ✓' if snap3['failure_yamls'] > 0 else 'FAIL ✗'}")
log(f"MutationEngine A/B attribution (PATH-4)     no crash          N/A (no A/B ctx)    PASS*")
log(f"DriftDetector                               no crash          in-memory         PASS*")
log(f"CRITICAL-1 (.record exists)                 no AttributeError  {hasattr(fl, 'record')}             {'PASS ✓' if hasattr(fl, 'record') else 'FAIL ✗'}")
log(f"HIGH-5 (_feed_thompson_sampling exists)    callable          {hasattr(pipeline, '_feed_thompson_sampling') if pipeline else 'N/A'}             {'PASS ✓' if hasattr(pipeline, '_feed_thompson_sampling') else 'FAIL ✗'}")

log(f"")
log(f"* = not directly verifiable without A/B test or drift event")
log(f"E2E VALIDATION COMPLETE")
flush()
