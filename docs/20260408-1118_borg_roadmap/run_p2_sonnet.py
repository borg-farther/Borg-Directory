#!/usr/bin/env python3.12
"""P2.1 Sonnet Path 1 agent-level borg A/B/C orchestrator.

Runs 15 pre-registered Django Verified tasks × 3 conditions × 1 run = 45 runs.
Replication of P1.1 (MiniMax) on claude-sonnet-4-5-20250929 for cross-model
meta-analysis.

Hard rules (from the Priority 2 subagent brief):
  * $25.00 HARD BUDGET, $24.00 ABORT
  * Honesty invariant H2: any C1/C2 run with borg_searches==0 → HALT
  * Sequential only; 45s between-run pacing; exponential backoff on 429
  * JSONL streamed per row with fsync (same schema as p1_minimax_results.jsonl)
  * Crashes logged as crash rows (success=None, error=str(e)); never fabricated

Phase A-lite seeding (new in P2):
  * 3 DIFFERENT django tasks than the 15 eval tasks, that are cached Docker
    images, are used as the seeding inputs to `borg observe`. We record a
    short trace per seeding task derived from the task problem_statement.
  * After seeding, we verify `borg search django` returns >=3 hits, then
    proceed. Otherwise HALT.
  * v3.2.4 shipped the observe→search roundtrip; we probe for it here before
    any paid API call goes out.

Imports the bulletproof runner from 20260408-1003_scope3_experiment/run_single_task.py.
"""
from __future__ import annotations
import os, sys, json, time, hashlib, traceback, subprocess
from pathlib import Path

# ── paths / config ────────────────────────────────────────────────────────────
ROOT = Path("/root/hermes-workspace/borg")
PREFLIGHT = ROOT / "docs/20260408-1003_scope3_experiment"
OUTDIR = ROOT / "docs/20260408-1118_borg_roadmap"
JSONL = OUTDIR / "p2_sonnet_results.jsonl"
LOGFILE = OUTDIR / "run_p2_sonnet.log"
WORKDIR = Path("/root/p2_workdir")
BORG_DB_SEEDED = Path("/root/p2_borg_db/seeded.sqlite")  # placeholder; real DB is ~/.borg/traces.db

BUDGET_HARD = 25.00
BUDGET_ABORT = 24.00
MAX_PER_RUN_USD = 1.50  # defensive warning threshold (Sonnet ~$0.50/run expected)
MODEL = "claude-sonnet-4-5-20250929"
BETWEEN_RUN_SLEEP = 60  # seconds — shared OAuth pacing (bumped to 60 due to heavy load)
PER_RUN_TIMEOUT = 900   # 15 min hard cap per run
# Proactive ratelimit preflight: before each run, ping /v1/messages with 1 token
# and inspect the anthropic-ratelimit-unified-5h-utilization header. If it's
# above this threshold, sleep until the reset timestamp.
RATELIMIT_PREFLIGHT_THRESHOLD = 0.70

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

# seeding tasks (different from eval set; same as P1.1 for comparability)
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

# ── ratelimit preflight probe ────────────────────────────────────────────────
def _anthropic_token() -> str:
    env = {}
    for ln in open("/root/.hermes/.env"):
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")
    return env.get("ANTHROPIC_TOKEN", "")

def ratelimit_probe() -> dict:
    """Send a 1-token ping to /v1/messages to read current ratelimit headers.
    Returns {status, util_5h, reset_5h, overage, raw_headers}.
    """
    import httpx
    token = _anthropic_token()
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "oauth-2025-04-20",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 1,
                "system": "You are Claude Code, Anthropic's official CLI for Claude.",
                "messages": [{"role": "user", "content": "."}],
            },
            timeout=30,
        )
        h = r.headers
        util_5h = float(h.get("anthropic-ratelimit-unified-5h-utilization", "0") or 0)
        reset_5h = int(h.get("anthropic-ratelimit-unified-5h-reset", "0") or 0)
        overage = h.get("anthropic-ratelimit-unified-overage-status", "unknown")
        return {
            "status": r.status_code,
            "util_5h": util_5h,
            "reset_5h": reset_5h,
            "overage": overage,
            "err": None if r.status_code == 200 else r.text[:200],
        }
    except Exception as e:
        return {"status": 0, "util_5h": None, "reset_5h": 0,
                "overage": None, "err": f"{type(e).__name__}: {e}"}

def wait_if_needed() -> None:
    """Check the 5h bucket; if utilization > threshold, sleep until reset."""
    probe = ratelimit_probe()
    log(f"  ratelimit probe: status={probe['status']} "
        f"util_5h={probe['util_5h']} overage={probe['overage']} "
        f"err={probe['err']}")
    if probe["status"] == 200 and probe["util_5h"] is not None \
            and probe["util_5h"] >= RATELIMIT_PREFLIGHT_THRESHOLD:
        reset_ts = probe["reset_5h"]
        if reset_ts > 0:
            now = time.time()
            wait = max(30, int(reset_ts - now) + 30)  # +30s grace
            wait = min(wait, 3 * 3600)  # never sleep more than 3h
            log(f"  5h bucket at {probe['util_5h']*100:.1f}%, "
                f"sleeping {wait}s until reset")
            time.sleep(wait)
    if probe["status"] == 429:
        # hard rate-limited right now; sleep a moderate amount
        log("  429 on probe, sleeping 300s")
        time.sleep(300)

# ── Phase A-lite seeding (v3.2.4-specific: observe→search roundtrip) ─────────
def _first_sentence(text: str, maxlen: int = 140) -> str:
    if not text:
        return ""
    t = " ".join(text.strip().split())
    # Try first full sentence
    for sep in (". ", "\n"):
        if sep in t:
            t = t.split(sep, 1)[0]
            break
    return t[:maxlen]

def phase_a_lite_seeding(tasks: dict[str, dict] | None = None) -> dict:
    """Lite seeding: `borg observe` a short trace per seeding task, then
    verify `borg search django` returns ≥3 hits. Fast, free, no LLM calls.
    """
    log("== Phase A-lite seeding (v3.2.4 observe→search roundtrip) ==")
    if tasks is None:
        tasks = load_tasks(SEEDING_TASKS)
    seeded_ids: list[str] = []
    for tid in SEEDING_TASKS:
        task = tasks.get(tid)
        if task is None:
            log(f"  SEED SKIP {tid}: not in dataset")
            continue
        problem = task.get("problem_statement", "") or ""
        summary = _first_sentence(problem, 140) or f"fix django bug {tid}"
        desc = f"Fix {tid}: {summary}"
        try:
            r = subprocess.run(
                ["borg", "observe", desc,
                 "--context", f"SWE-bench Verified task {tid}",
                 "--agent", "p2_sonnet_seeder"],
                capture_output=True, text=True, timeout=30,
            )
            out = (r.stdout or r.stderr).strip()
            log(f"  OBSERVE {tid}: rc={r.returncode} {out[:160]}")
            if r.returncode == 0:
                seeded_ids.append(tid)
            # Append a metadata row to JSONL for audit
            append_jsonl(str(JSONL), {
                "phase": "seeding",
                "task_id": tid,
                "condition": "borg_observe",
                "model": "n/a (borg CLI)",
                "success": None,
                "seeding_desc": desc,
                "borg_observe_rc": r.returncode,
                "borg_observe_out": out[:400],
            })
        except Exception as e:
            log(f"  OBSERVE {tid} CRASH: {type(e).__name__}: {e}")
            append_jsonl(str(JSONL), {
                "phase": "seeding",
                "task_id": tid,
                "condition": "borg_observe",
                "model": "n/a (borg CLI)",
                "success": None,
                "error": f"{type(e).__name__}: {e}",
            })

    # Verification: borg search django must return ≥3 trace hits
    try:
        r = subprocess.run(
            ["borg", "search", "django"],
            capture_output=True, text=True, timeout=30,
        )
        search_out = (r.stdout or "")
        log("borg search 'django' (head 15):")
        for ln in search_out.splitlines()[:15]:
            log(f"  {ln}")
        hit_lines = [ln for ln in search_out.splitlines() if ln.startswith("trace:")]
        n_hits = len(hit_lines)
        log(f"  trace hits counted: {n_hits}")
        verified = n_hits >= 3
    except Exception as e:
        log(f"  borg search probe CRASH: {e}")
        search_out = ""
        n_hits = 0
        verified = False

    result = {
        "seeded_tasks": seeded_ids,
        "n_seeded": len(seeded_ids),
        "n_search_hits": n_hits,
        "verified": verified,
    }
    log(f"phase_a_lite_seeding result: {result}")
    return result

# ── main loop ─────────────────────────────────────────────────────────────────
def run_eval_loop(tasks: dict[str, dict]) -> dict:
    total_cost = 0.0
    n_done = 0
    n_success = 0
    n_skipped = 0
    n_crashed = 0
    n_429_backoffs = 0
    per_cond = {c: {"done": 0, "success": 0, "skipped": 0, "crashed": 0} for c in CONDITIONS}
    budget_aborted = False
    invariant_fired = False

    log("== P2.1 Main 45-run eval loop ==")
    log(f"between-run sleep = {BETWEEN_RUN_SLEEP}s")

    # Much longer backoff schedule — shared OAT with 5h window pressure.
    # 2min → 5min → 15min → 30min → 60min → give up
    backoff_schedule = [120, 300, 900, 1800, 3600]

    for ti, task_id in enumerate(PRE_REGISTERED):
        order = latin_square_order(ti)
        log(f"-- task {ti+1}/15 {task_id}: order={order}")
        for ci, condition in enumerate(order):
            run_label = f"run {n_done+1}/45 [{task_id} / {condition}]"
            if total_cost >= BUDGET_ABORT:
                log(f"BUDGET ABORT: cumulative cost=${total_cost:.4f} >= ${BUDGET_ABORT}")
                budget_aborted = True
                break

            log(f"START {run_label}")
            seed = fixed_seed(task_id, condition)
            borg_db = str(BORG_DB_SEEDED) if condition == "C2_borg_seeded" else None

            # Preflight: check the 5h bucket and sleep to reset if above threshold.
            wait_if_needed()

            attempt = 0
            rec = None
            t_start = time.time()
            while True:
                try:
                    rec = run_single_task(
                        tasks[task_id],
                        condition,
                        MODEL,
                        seed,
                        borg_db,
                        str(WORKDIR),
                        timeout=PER_RUN_TIMEOUT,
                    )
                except AssertionError:
                    raise  # Honesty invariant — propagate
                except Exception as e:
                    # Non-LLM exception (docker, precheck, etc) → outer handler
                    raise

                # The runner catches LLM-call HTTPStatusError internally and
                # records it as rec["error"]="llm_call_failed: HTTPStatusError 429".
                # We need to detect this and retry with exponential backoff.
                err = (rec.get("error") or "") if isinstance(rec, dict) else ""
                is_429 = ("429" in err) or ("rate_limit" in err.lower())
                is_llm_call_failure = err.startswith("llm_call_failed")
                # Only retry on LLM-call failures, and only on 429 / rate limit.
                # Other llm_call_failed errors (e.g. timeout) just get logged once.
                if is_llm_call_failure and is_429:
                    n_429_backoffs += 1
                    if attempt < len(backoff_schedule):
                        wait = backoff_schedule[attempt]
                        log(f"  429 BACKOFF attempt={attempt+1} sleep={wait}s "
                            f"(rec.error={err[:200]})")
                        time.sleep(wait)
                        attempt += 1
                        continue
                    else:
                        log(f"  429 BACKOFF EXHAUSTED after {attempt} retries; "
                            f"recording as failed run and continuing")
                # non-429 or retries exhausted → commit this rec
                break

            try:
                if rec is None:
                    raise RuntimeError("run_single_task returned None unexpectedly")

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

                if run_cost > MAX_PER_RUN_USD:
                    log(f"  WARNING: per-run cost ${run_cost:.4f} > ${MAX_PER_RUN_USD}")

                log(f"DONE {run_label}: success={rec.get('success')} "
                    f"borg_searches={rec.get('borg_searches', 0)} "
                    f"iters={rec.get('iterations', 0)} "
                    f"tokens={rec.get('tokens_used', 0)} "
                    f"cost=${run_cost:.5f} "
                    f"cumulative=${total_cost:.4f} "
                    f"dt={time.time()-t_start:.1f}s")

            except AssertionError as e:
                # Honesty invariant violation — write report and HALT
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
                # write invariant violation report
                invariant_report = OUTDIR / "P2_INVARIANT_VIOLATION.md"
                with open(invariant_report, "w") as f:
                    f.write(f"# P2 Honesty Invariant Violation\n\n"
                            f"At {time.strftime('%Y-%m-%d %H:%M:%S')}, run\n\n"
                            f"- task_id: `{task_id}`\n- condition: `{condition}`\n"
                            f"- seed: `{seed}`\n- model: `{MODEL}`\n\n"
                            f"reported `borg_searches == 0` under a treatment condition, "
                            f"which violates the pre-registered H2 invariant. The experiment "
                            f"is HALTED per roadmap R_HALT_SILENT_TREATMENT.\n\n"
                            f"```\n{e}\n```\n")
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

            if n_done % 5 == 0:
                log(f"PROGRESS: {n_done}/45 done, success={n_success}, "
                    f"skipped={n_skipped}, crashed={n_crashed}, "
                    f"429_backoffs={n_429_backoffs}, "
                    f"cumulative_cost=${total_cost:.4f}")

            # between-run pacing (except after the final run)
            if not (ti == len(PRE_REGISTERED) - 1 and ci == len(order) - 1):
                log(f"  sleep {BETWEEN_RUN_SLEEP}s (OAuth pacing)")
                time.sleep(BETWEEN_RUN_SLEEP)

        if budget_aborted or invariant_fired:
            break

    return {
        "n_done": n_done,
        "n_success": n_success,
        "n_skipped": n_skipped,
        "n_crashed": n_crashed,
        "per_condition": per_cond,
        "total_cost_usd": round(total_cost, 4),
        "budget_aborted": budget_aborted,
        "invariant_fired": invariant_fired,
        "n_429_backoffs": n_429_backoffs,
    }


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    WORKDIR.mkdir(parents=True, exist_ok=True)
    BORG_DB_SEEDED.parent.mkdir(parents=True, exist_ok=True)

    if JSONL.exists():
        backup = JSONL.with_suffix(f".jsonl.bak.{int(time.time())}")
        JSONL.rename(backup)
        log(f"existing JSONL backed up to {backup.name}")

    log("== P2.1 Sonnet Path 1 orchestrator starting ==")
    log(f"model={MODEL}")
    log(f"tasks={len(PRE_REGISTERED)} conditions={len(CONDITIONS)} runs={len(PRE_REGISTERED)*3}")
    log(f"jsonl={JSONL}")
    log(f"budget_hard=${BUDGET_HARD} budget_abort=${BUDGET_ABORT}")

    # Load all tasks (eval + seeding) in one shot
    all_ids = list(PRE_REGISTERED) + [t for t in SEEDING_TASKS if t not in PRE_REGISTERED]
    tasks = load_tasks(all_ids)
    log(f"loaded {len(tasks)} task records from HF dataset")

    # Phase A-lite seeding: observe→search roundtrip via the borg CLI
    seed_result = phase_a_lite_seeding(tasks)
    if not seed_result["verified"]:
        log("SEEDING FAILED VERIFICATION. HALTING before eval runs.")
        block_report = OUTDIR / "P2_SEEDING_FAILURE.md"
        with open(block_report, "w") as f:
            f.write("# P2 Phase A-lite Seeding Verification Failure\n\n"
                    f"`borg search django` returned only "
                    f"{seed_result['n_search_hits']} hits (required ≥3).\n\n"
                    "v3.2.4 observe→search roundtrip is not live in production. "
                    "HALTED before any paid eval runs.\n")
        return 3

    eval_summary = run_eval_loop(tasks)

    log("== DONE ==")
    for k, v in eval_summary.items():
        log(f"  {k}={v}")

    summary = {
        "seeding": seed_result,
        "eval": eval_summary,
        "model": MODEL,
        "budget_hard_usd": BUDGET_HARD,
        "budget_abort_usd": BUDGET_ABORT,
    }
    with open(OUTDIR / "p2_sonnet_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    log(f"summary written to {OUTDIR/'p2_sonnet_summary.json'}")

    if eval_summary["invariant_fired"]:
        return 2
    if eval_summary["n_done"] == 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
