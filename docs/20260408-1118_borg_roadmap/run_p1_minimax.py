#!/usr/bin/env python3.12
"""P1.1 MiniMax Path 1 agent-level borg A/B/C orchestrator.

Runs 15 pre-registered Django Verified tasks × 3 conditions × 1 run = 45 runs.

Hard rules:
  * $5.00 HARD BUDGET, $4.00 ABORT
  * Honesty invariant: any C1/C2 run with borg_searches==0 → HALT, experiment INVALIDATED
  * JSONL streamed per row with fsync
  * Crashes logged as crash rows (success=None, error=str(e)); never fabricated

Imports the bulletproof runner from 20260408-1003_scope3_experiment/run_single_task.py.
"""
from __future__ import annotations
import os, sys, json, time, hashlib, traceback, random, subprocess
from pathlib import Path

# ── paths / config ────────────────────────────────────────────────────────────
ROOT = Path("/root/hermes-workspace/borg")
PREFLIGHT = ROOT / "docs/20260408-1003_scope3_experiment"
OUTDIR = ROOT / "docs/20260408-1118_borg_roadmap"
JSONL = OUTDIR / "p1_minimax_results.jsonl"
LOGFILE = OUTDIR / "run_p1_minimax.log"
WORKDIR = Path("/root/p1_workdir")
BORG_DB_SEEDED = Path("/root/p1_borg_db/seeded.sqlite")  # placeholder

BUDGET_HARD = 5.00
BUDGET_ABORT = 4.00
MAX_PER_RUN_USD = 0.20
MODEL = "minimax-text-01"

sys.path.insert(0, str(PREFLIGHT))
from run_single_task import run_single_task, append_jsonl  # noqa: E402

# ── pre-registered tasks (roadmap Appendix A) ─────────────────────────────────
PRE_REGISTERED = [
    "django__django-10554",
    "django__django-11138",
    "django__django-11400",
    "django__django-12708",
    "django__django-12754",
    "django__django-13212",
    "django__django-13344",
    "django__django-14631",
    "django__django-15128",
    "django__django-15252",
    "django__django-15503",
    "django__django-15957",
    "django__django-16263",
    "django__django-16560",
    "django__django-16631",
]

# seeding tasks (different from eval set — all cached)
SEEDING_TASKS = [
    "django__django-10973",
    "django__django-11087",
    "django__django-11265",
]

CONDITIONS = ["C0_no_borg", "C1_borg_empty", "C2_borg_seeded"]

# ── logging ───────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())

# ── task loading ──────────────────────────────────────────────────────────────
def load_tasks(task_ids: list[str]) -> dict[str, dict]:
    log(f"loading {len(task_ids)} tasks from SWE-bench Verified")
    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    wanted = set(task_ids)
    out: dict[str, dict] = {}
    for r in ds:
        if r["instance_id"] in wanted:
            out[r["instance_id"]] = dict(r)
    missing = wanted - set(out.keys())
    if missing:
        raise RuntimeError(f"tasks missing from dataset: {missing}")
    return out

# ── latin square condition order ──────────────────────────────────────────────
def latin_square_order(task_idx: int) -> list[str]:
    """Cycle conditions to balance ordering across tasks."""
    base = list(CONDITIONS)
    shift = task_idx % 3
    return base[shift:] + base[:shift]

def fixed_seed(task_id: str, condition: str) -> int:
    h = hashlib.sha256(f"{task_id}|{condition}".encode()).digest()
    return int.from_bytes(h[:4], "big") % (2**31 - 1)

# ── Phase A-lite seeding ──────────────────────────────────────────────────────
def phase_a_lite_seed(tasks: dict[str, dict]) -> None:
    log("== Phase A-lite seeding ==")
    seed_ran = 0
    for tid in SEEDING_TASKS:
        if tid not in tasks:
            log(f"  SEEDING: {tid} not in dataset, skipping")
            continue
        log(f"  SEEDING RUN: {tid} (C2_borg_seeded)")
        try:
            rec = run_single_task(
                tasks[tid],
                "C2_borg_seeded",
                MODEL,
                fixed_seed(tid, "SEEDING"),
                str(BORG_DB_SEEDED),
                str(WORKDIR),
                timeout=900,
            )
            rec["phase"] = "seeding"
            append_jsonl(str(JSONL), rec)
            seed_ran += 1
            log(f"    seeded: success={rec.get('success')} "
                f"borg_searches={rec.get('borg_searches')} "
                f"cost=${rec.get('llm_cost_usd',0):.4f} "
                f"iters={rec.get('iterations')}")
        except AssertionError as e:
            # This would only fire if the seeding run did zero borg searches.
            # Honesty invariant applies to treatment runs, so we LOG it but
            # do not abort yet — the eval runs are the gated population.
            log(f"    ASSERTION (seeding): {e}")
            crash = {
                "phase": "seeding", "task_id": tid, "condition": "C2_borg_seeded",
                "model": MODEL, "success": None,
                "error": f"AssertionError: {str(e)[:400]}",
            }
            append_jsonl(str(JSONL), crash)
        except Exception as e:
            log(f"    CRASH (seeding): {type(e).__name__}: {str(e)[:200]}")
            crash = {
                "phase": "seeding", "task_id": tid, "condition": "C2_borg_seeded",
                "model": MODEL, "success": None,
                "error": f"{type(e).__name__}: {str(e)[:400]}",
                "traceback": traceback.format_exc()[-1200:],
            }
            append_jsonl(str(JSONL), crash)
    log(f"seeding done: {seed_ran}/{len(SEEDING_TASKS)} runs attempted")

    # Dump borg DB state to log for verification
    try:
        r = subprocess.run(["borg", "search", "django"], capture_output=True, text=True, timeout=15)
        log("borg search 'django' (head 10):")
        for ln in (r.stdout or r.stderr).splitlines()[:10]:
            log(f"  {ln}")
    except Exception as e:
        log(f"borg search probe failed: {e}")

# ── main loop ─────────────────────────────────────────────────────────────────
def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    WORKDIR.mkdir(parents=True, exist_ok=True)
    BORG_DB_SEEDED.parent.mkdir(parents=True, exist_ok=True)

    if JSONL.exists():
        # Resume-safe? For now we start fresh for a clean experiment.
        # But keep a backup.
        backup = JSONL.with_suffix(f".jsonl.bak.{int(time.time())}")
        JSONL.rename(backup)
        log(f"existing JSONL backed up to {backup.name}")

    log("== P1.1 MiniMax Path 1 orchestrator starting ==")
    log(f"model={MODEL}")
    log(f"tasks={len(PRE_REGISTERED)} conditions={len(CONDITIONS)} runs={len(PRE_REGISTERED)*3}")
    log(f"jsonl={JSONL}")
    log(f"budget_hard=${BUDGET_HARD} budget_abort=${BUDGET_ABORT}")

    # load all tasks (eval + seeding)
    all_ids = list(PRE_REGISTERED) + [t for t in SEEDING_TASKS if t not in PRE_REGISTERED]
    tasks = load_tasks(all_ids)
    log(f"loaded {len(tasks)} task records from HF dataset")

    # Phase A-lite seeding first
    phase_a_lite_seed(tasks)

    # Main 45-run loop
    total_cost = 0.0
    n_done = 0
    n_success = 0
    n_skipped = 0
    n_crashed = 0
    per_cond = {c: {"done": 0, "success": 0, "skipped": 0, "crashed": 0} for c in CONDITIONS}
    budget_aborted = False
    invariant_fired = False

    log("== Main experiment: 45 runs ==")
    for ti, task_id in enumerate(PRE_REGISTERED):
        order = latin_square_order(ti)
        log(f"-- task {ti+1}/15 {task_id}: order={order}")
        for ci, condition in enumerate(order):
            run_label = f"run {n_done+1}/45 [{task_id} / {condition}]"
            if total_cost >= BUDGET_ABORT:
                log(f"BUDGET ABORT: total_cost=${total_cost:.4f} >= ${BUDGET_ABORT}")
                budget_aborted = True
                break

            log(f"START {run_label}")
            seed = fixed_seed(task_id, condition)
            borg_db = str(BORG_DB_SEEDED) if condition == "C2_borg_seeded" else None
            t_start = time.time()
            try:
                rec = run_single_task(
                    tasks[task_id],
                    condition,
                    MODEL,
                    seed,
                    borg_db,
                    str(WORKDIR),
                    timeout=900,
                )
                rec["phase"] = "eval"
                rec["cumulative_cost_usd_before"] = round(total_cost, 6)
                append_jsonl(str(JSONL), rec)
                run_cost = rec.get("llm_cost_usd", 0.0) or 0.0
                total_cost += run_cost
                n_done += 1
                per_cond[condition]["done"] += 1

                if rec.get("skipped"):
                    n_skipped += 1
                    per_cond[condition]["skipped"] += 1
                    log(f"  SKIPPED: {rec.get('skip_reason')}")
                elif rec.get("success"):
                    n_success += 1
                    per_cond[condition]["success"] += 1
                elif rec.get("error"):
                    # counted as done (completed cleanly, just failed/errored)
                    pass

                if run_cost > MAX_PER_RUN_USD:
                    log(f"  WARNING: per-run cost ${run_cost:.4f} > ${MAX_PER_RUN_USD}")

                log(f"DONE {run_label}: success={rec.get('success')} "
                    f"borg_searches={rec.get('borg_searches',0)} "
                    f"iters={rec.get('iterations',0)} "
                    f"tokens={rec.get('tokens_used',0)} "
                    f"cost=${run_cost:.5f} "
                    f"total=${total_cost:.4f} "
                    f"dt={time.time()-t_start:.1f}s")

            except AssertionError as e:
                # Honesty invariant violation
                log(f"HONESTY INVARIANT VIOLATED: {e}")
                invariant_fired = True
                crash = {
                    "phase": "eval", "task_id": task_id, "condition": condition,
                    "model": MODEL, "seed": seed, "success": None,
                    "borg_searches": 0,
                    "error": f"HONESTY_INVARIANT: {str(e)[:400]}",
                    "traceback": traceback.format_exc()[-1500:],
                }
                append_jsonl(str(JSONL), crash)
                n_done += 1
                n_crashed += 1
                per_cond[condition]["done"] += 1
                per_cond[condition]["crashed"] += 1
                # record then halt
                break
            except Exception as e:
                log(f"CRASH {run_label}: {type(e).__name__}: {str(e)[:300]}")
                crash = {
                    "phase": "eval", "task_id": task_id, "condition": condition,
                    "model": MODEL, "seed": seed, "success": None,
                    "error": f"{type(e).__name__}: {str(e)[:400]}",
                    "traceback": traceback.format_exc()[-1500:],
                    "time_seconds": round(time.time() - t_start, 2),
                }
                append_jsonl(str(JSONL), crash)
                n_done += 1
                n_crashed += 1
                per_cond[condition]["done"] += 1
                per_cond[condition]["crashed"] += 1

            if n_done % 10 == 0:
                log(f"PROGRESS: {n_done}/45 done, success={n_success}, "
                    f"skipped={n_skipped}, crashed={n_crashed}, cost=${total_cost:.4f}")

        if budget_aborted or invariant_fired:
            break

    log("== DONE ==")
    log(f"runs_completed={n_done}/45 "
        f"success={n_success} skipped={n_skipped} crashed={n_crashed} "
        f"total_cost=${total_cost:.4f}")
    for c, v in per_cond.items():
        log(f"  {c}: done={v['done']} success={v['success']} "
            f"skipped={v['skipped']} crashed={v['crashed']}")
    log(f"budget_aborted={budget_aborted} invariant_fired={invariant_fired}")

    summary = {
        "n_done": n_done,
        "n_success": n_success,
        "n_skipped": n_skipped,
        "n_crashed": n_crashed,
        "per_condition": per_cond,
        "total_cost_usd": round(total_cost, 4),
        "budget_aborted": budget_aborted,
        "invariant_fired": invariant_fired,
    }
    with open(OUTDIR / "p1_minimax_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    return 2 if invariant_fired else (0 if n_done else 1)

if __name__ == "__main__":
    sys.exit(main())
