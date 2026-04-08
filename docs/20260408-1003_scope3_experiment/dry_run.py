#!/usr/bin/env python3.12
"""Dry-run orchestrator for Scope 3 preflight. Streams JSONL, hard $5 cap."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from run_single_task import run_single_task, append_jsonl

OUT = Path("/root/hermes-workspace/borg/docs/20260408-1003_scope3_experiment")
JSONL = OUT / "dry_runs.jsonl"
BUDGET_HARD = 5.00
BUDGET_ABORT = 4.00

TASK_ID = "django__django-15695"  # smallest test_patch, 1 FAIL_TO_PASS, cached

def load_task(tid):
    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    for r in ds:
        if r["instance_id"] == tid: return dict(r)
    raise RuntimeError(f"task {tid} not in dataset")

def existing_cost():
    if not JSONL.exists(): return 0.0
    total = 0.0
    for ln in open(JSONL):
        try: total += json.loads(ln).get("llm_cost_usd", 0.0)
        except: pass
    return total

def run(task, cond, model, seed, label):
    current = existing_cost()
    print(f"\n=== [{label}] {model} {cond} (spent so far ${current:.4f}) ===", flush=True)
    if current >= BUDGET_ABORT:
        print(f"ABORT: spent=${current:.4f} >= ${BUDGET_ABORT}"); return None
    t0=time.time()
    try:
        rec = run_single_task(task, cond, model, seed, None, "/tmp/runs", timeout=600)
    except AssertionError as e:
        rec = {"FATAL_ASSERTION": str(e), "model": model, "condition": cond}
        print("ASSERTION:", e)
    rec["label"] = label
    append_jsonl(str(JSONL), rec)
    dt = time.time()-t0
    print(f"  -> success={rec.get('success')} cost=${rec.get('llm_cost_usd',0):.4f} "
          f"tokens={rec.get('tokens_used',0)} borg={rec.get('borg_searches',0)} "
          f"iter={rec.get('iterations',0)} time={dt:.0f}s "
          f"skipped={rec.get('skipped')} err={rec.get('error')}", flush=True)
    return rec

def main():
    task = load_task(TASK_ID)
    print(f"task: {TASK_ID}  FAIL_TO_PASS: {task['FAIL_TO_PASS'][:120]}")

    plan = [
        ("4a_sonnet_C0", "C0_no_borg", "claude-sonnet-4-5-20250929", 42),
        ("4b_gemini_C0", "C0_no_borg", "gemini-2.0-flash",           42),
        ("4c_minimax_C0","C0_no_borg", "minimax-text-01",            42),
        ("4d_sonnet_C1", "C1_borg_empty","claude-sonnet-4-5-20250929",42),
    ]
    # Substitute GPT only if quota works — tested earlier: it doesn't. Skip.
    for label, cond, model, seed in plan:
        run(task, cond, model, seed, label)
        if existing_cost() >= BUDGET_ABORT:
            print("Hard budget abort triggered."); break

    print(f"\nTotal spent: ${existing_cost():.4f}")

if __name__=="__main__": main()
