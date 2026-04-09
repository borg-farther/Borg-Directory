#!/usr/bin/env python3.12
"""
Cross-model classifier benchmark (P5 exploratory).

For each of the 173 rows in error_corpus.jsonl, collect 4 predictions:
  a) borg v3.2.4: classify_error() from borg.core.pack_taxonomy
  b) gemini_zero: Gemini 2.0 Flash zero-shot on the same 12-class label set
  c) gemini_ctx:  Gemini 2.0 Flash with richer context / refuse instructions
  d) null:        the trivial classifier that always returns UNKNOWN

Stream results to classifier_benchmark_results.jsonl (resumable — skips any
already-written ids). Uses 4s sleeps between Gemini calls (15 rpm free tier).

Correctness vocabulary (same as docs/20260408-0623_classifier_prd/run_baseline.py):
  correct           = actual == expected
  silent_miss       = actual is None and expected is None         (good, never fires on this corpus)
  false_confident   = actual is not None and actual != expected   (BAD)
  correct_no_match  = actual is None and expected is not None     (honest miss)

Gemini normalisation:
  - strip/lowercase output
  - UNKNOWN / empty / anything outside the 12-class vocabulary -> None
  - an exception or total refusal -> errored=True (counted separately from wrong)
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "20260408-0623_classifier_prd" / "error_corpus.jsonl"
OUT = HERE / "classifier_benchmark_results.jsonl"

# -- Borg classifier ---------------------------------------------------------
sys.path.insert(0, str(HERE.parent.parent))  # /root/hermes-workspace/borg
from borg.core.pack_taxonomy import classify_error  # noqa: E402

BORG_CLASSES = [
    "circular_dependency",
    "null_pointer_chain",
    "missing_foreign_key",
    "migration_state_desync",
    "import_cycle",
    "race_condition",
    "configuration_error",
    "type_mismatch",
    "missing_dependency",
    "timeout_hang",
    "schema_drift",
    "permission_denied",
]
BORG_CLASSES_SET = set(BORG_CLASSES)

# -- Gemini ------------------------------------------------------------------
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai  # noqa: E402

GEMINI_KEY = Path("/root/.hermes/secrets/google_api_key").read_text().strip()
genai.configure(api_key=GEMINI_KEY)
GEMINI_MODEL_NAME = "gemini-2.0-flash"
GEMINI_MODEL = genai.GenerativeModel(GEMINI_MODEL_NAME)
GEMINI_SLEEP = 4.1  # seconds between calls (15 rpm = 4s, +0.1 safety)
# API latency is already ~7s per call so running the two Gemini variants in
# parallel and then sleeping just enough to respect 15 req/min keeps us safe.
GEMINI_POST_ROW_SLEEP = 1.0  # min ≈ 8s total per row of 2 calls -> ~15 rpm

ZERO_SHOT_PROMPT = (
    "Given this error, output ONLY one of these labels with no explanation: "
    + ", ".join(BORG_CLASSES)
    + ", or UNKNOWN if it does not fit any of these or is non-Python.\n\n"
      "Error:\n{err}\n\nLabel:"
)

CTX_PROMPT = (
    "You are a strict error classifier. Borg's problem_class taxonomy "
    "contains exactly these 12 labels (all Python/Django oriented):\n"
    + "\n".join(f"  - {c}" for c in BORG_CLASSES)
    + "\n\nRules:\n"
      "1. If the error is not Python/Django (Rust, Go, JS/TS, shell, Docker, "
         "k8s, etc.), output exactly: UNKNOWN\n"
      "2. If the error is Python/Django but does not cleanly fit any of the "
         "12 labels, output exactly: UNKNOWN\n"
      "3. Otherwise output exactly one label from the list above.\n"
      "4. Output ONLY the label, no explanation, no punctuation, no code fences.\n\n"
      "Error:\n{err}\n\nLabel:"
)


def _parse_gemini(text: Optional[str]) -> Tuple[Optional[str], bool]:
    """Return (prediction_or_none, errored_flag).

    errored=True  -> model output was not parseable into the label set.
    prediction=None, errored=False -> model answered UNKNOWN (honest refusal).
    prediction=<label>, errored=False -> valid label.
    """
    if text is None:
        return None, True
    t = text.strip().strip("`").strip()
    # Sometimes the model says "Label: foo" — peel that off.
    if ":" in t and len(t.splitlines()) <= 2:
        last = t.splitlines()[-1]
        if ":" in last:
            last = last.split(":", 1)[1].strip()
        t = last
    t = t.strip(" .,'\"`\n")
    low = t.lower()
    if not low:
        return None, True
    if low == "unknown":
        return None, False
    # exact match against taxonomy
    if low in BORG_CLASSES_SET:
        return low, False
    # tolerate the model listing one label amongst other words
    for c in BORG_CLASSES:
        if c in low:
            return c, False
    return None, True


def _call_gemini(prompt: str, err: str, max_retries: int = 3) -> Tuple[Optional[str], bool, Optional[str]]:
    """Call Gemini with bounded retries. Returns (pred, errored, raw_text)."""
    full = prompt.format(err=err[:4000])  # cap very long errors
    last_exc = None
    for attempt in range(max_retries):
        try:
            resp = GEMINI_MODEL.generate_content(
                full,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 20,
                },
            )
            raw = None
            try:
                raw = resp.text
            except Exception:
                # candidate may exist but text accessor can raise
                if resp.candidates:
                    parts = getattr(resp.candidates[0].content, "parts", None) or []
                    raw = "".join(getattr(p, "text", "") for p in parts)
            pred, errored = _parse_gemini(raw)
            return pred, errored, raw
        except Exception as e:
            last_exc = e
            msg = str(e)
            # Rate-limit / quota — back off longer
            if "429" in msg or "quota" in msg.lower() or "exhaust" in msg.lower():
                time.sleep(30 * (attempt + 1))
            else:
                time.sleep(2 * (attempt + 1))
    return None, True, f"EXC:{type(last_exc).__name__}:{str(last_exc)[:160]}"


def load_corpus() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in CORPUS.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_existing() -> Dict[str, Dict[str, Any]]:
    """Resume: read any rows already written."""
    out: Dict[str, Dict[str, Any]] = {}
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                out[row["id"]] = row
            except Exception:
                continue
    return out


def write_row(row: Dict[str, Any]) -> None:
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    corpus = load_corpus()
    existing = load_existing()
    print(f"[bench] corpus={len(corpus)}  already_done={len(existing)}")
    print(f"[bench] output -> {OUT}")
    t0 = time.time()
    gemini_calls = 0
    gemini_errors = 0

    for i, r in enumerate(corpus, 1):
        rid = r["id"]
        if rid in existing:
            # still count any previous errors from stored row
            prev = existing[rid]
            gemini_errors += int(prev.get("gemini_zero_errored", False))
            gemini_errors += int(prev.get("gemini_ctx_errored", False))
            gemini_calls += 2
            continue

        expected = r.get("expected_problem_class")
        text = r["text"]

        # a) borg
        borg_pred = classify_error(text)

        # b)+c) gemini zero-shot and ctx in parallel (2 of the 15 rpm budget)
        row_start = time.time()
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_zero = pool.submit(_call_gemini, ZERO_SHOT_PROMPT, text)
            f_ctx = pool.submit(_call_gemini, CTX_PROMPT, text)
            zero_pred, zero_err, zero_raw = f_zero.result()
            ctx_pred, ctx_err, ctx_raw = f_ctx.result()
        gemini_calls += 2
        if zero_err:
            gemini_errors += 1
        if ctx_err:
            gemini_errors += 1
        # Pacing: 2 calls per row, want <=15 rpm -> >=8s per row
        elapsed_row = time.time() - row_start
        if elapsed_row < 8.0:
            time.sleep(8.0 - elapsed_row)
        else:
            time.sleep(GEMINI_POST_ROW_SLEEP)

        # d) null baseline: always refuse
        null_pred = None

        row = {
            "id": rid,
            "language": r.get("language"),
            "framework": r.get("framework"),
            "family": r.get("family"),
            "expected_problem_class": expected,
            "text": text[:500],
            "borg_pred": borg_pred,
            "gemini_zero_pred": zero_pred,
            "gemini_zero_errored": zero_err,
            "gemini_zero_raw": zero_raw[:200] if zero_raw else None,
            "gemini_ctx_pred": ctx_pred,
            "gemini_ctx_errored": ctx_err,
            "gemini_ctx_raw": ctx_raw[:200] if ctx_raw else None,
            "null_pred": null_pred,
        }
        write_row(row)

        elapsed = time.time() - t0
        if i % 5 == 0 or i == len(corpus):
            print(
                f"[bench] {i}/{len(corpus)}  "
                f"borg={borg_pred}  gem0={zero_pred}  gemctx={ctx_pred}  "
                f"elapsed={elapsed:.0f}s  gem_err={gemini_errors}"
            )

    print(f"[bench] done. gemini_calls={gemini_calls} gemini_errors={gemini_errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
