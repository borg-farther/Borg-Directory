#!/usr/bin/env python3
"""Operator-side counterfactual replay of consented value receipts.

Answers the only question that justifies Borg: **would the agent have failed
here without Borg?** For each consented, redacted receipt (schema v2,
`replay_context`), a pinned frontier model is asked to solve the failure BLIND
(no Borg knowledge), then a pinned judge prompt compares the blind attempt to
the fix Borg actually surfaced:

  * blind attempt equivalent / independently valid  -> agent would have
    recovered alone -> NOT counterfactual
  * blind attempt wrong / would still be stuck      -> Borg's rescue was
    counterfactual value

Outputs ``counterfactual_rate`` (counterfactual / replayed) with a Wilson 95%
CI, mapped to the docs/PILOT_DECISION_PROTOCOL.md thresholds (<5% kill, >20% build,
5-20% extend).

Honesty and privacy rules:
  * OFFLINE by design for CI: ``--mock`` + the synthetic fixtures under
    tests/fixtures/ never touch the network.
  * Real receipts require ``--attest-consent`` — receipts are local-only by
    contract; the operator attests users consented to this offline replay.
  * Only the POST-REDACTION error text ever leaves the machine (and only when
    the operator runs a live replay); raw secrets were never stored.
  * Model and prompts are PINNED (MODEL_ID / PROMPT_VERSION) so runs are
    comparable across the pilot.

Stdlib-only on purpose: runs anywhere with python3, no agent-borg install
required (reads value_receipts.db directly, or a JSON export/fixture file).

Usage:
  python scripts/counterfactual_replay.py --fixtures tests/fixtures/counterfactual_receipts.json --mock
  python scripts/counterfactual_replay.py --borg-home ~/.borg --attest-consent "pilot-07 consent 2026-06-10" --mock
  ANTHROPIC_API_KEY=... python scripts/counterfactual_replay.py --receipts-file export.json --attest-consent "..."
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

MODEL_ID = "claude-opus-4-8"  # PINNED: do not float across a pilot
PROMPT_VERSION = "cfr-1.0"  # bump when either prompt below changes
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SOLVER_PROMPT = """You are an AI coding agent replaying a real (redacted) failure.
You have NO external knowledge base, NO project memory, and NO prior runs — only
this error and your own knowledge.

Environment: {env_fingerprint}
Error (redacted): {error_redacted}

State, in at most 5 lines, the exact fix you would apply on your next attempt.
If you cannot determine a concrete fix from this information, say exactly:
NO_CONCRETE_FIX
"""

JUDGE_PROMPT = """You are judging a counterfactual replay for a debugging-memory tool.

A blind agent (no tool access) proposed this fix for a redacted failure:
--- BLIND ATTEMPT ---
{blind_attempt}
--- END BLIND ATTEMPT ---

The tool had surfaced this known-good fix (class: {matched_id}):
--- SURFACED FIX ---
{fix_surfaced}
--- END SURFACED FIX ---

Would the blind agent have recovered within one retry using ONLY its own attempt?
- If the blind attempt is equivalent to the surfaced fix, or a different but
  plausibly working fix: it would have recovered.
- If the blind attempt is NO_CONCRETE_FIX, wrong, or would not resolve the
  failure: it would still be stuck.

Reply with EXACTLY one line:
VERDICT: WOULD_HAVE_SOLVED
or
VERDICT: WOULD_HAVE_BEEN_STUCK
"""

KILL_THRESHOLD = 0.05  # docs/PILOT_DECISION_PROTOCOL.md: below -> kill
BUILD_THRESHOLD = 0.20  # docs/PILOT_DECISION_PROTOCOL.md: above -> build

_Z95 = 1.959963984540054


def wilson_ci(successes: int, n: int, z: float = _Z95) -> Tuple[float, float]:
    """Wilson score 95% interval for a binomial proportion. (0.0, 1.0) when n=0."""
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def protocol_reading(counterfactual: int, n: int) -> str:
    """Map the Wilson CI onto the pilot decision thresholds (conservative: a
    zone is only called when the WHOLE interval sits inside it)."""
    if n == 0:
        return "no-data"
    lo, hi = wilson_ci(counterfactual, n)
    if hi < KILL_THRESHOLD:
        return "kill"
    if lo > BUILD_THRESHOLD:
        return "build"
    return "extend"


# ----------------------------------------------------------------- receipt I/O


def load_receipts_from_db(borg_home: Path) -> List[Dict[str, Any]]:
    db = borg_home / "value_receipts.db"
    if not db.exists():
        raise SystemExit(f"no value_receipts.db under {borg_home} — nothing to replay")
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(rescue_receipts)")}
    if "replay_context" not in cols:
        conn.close()
        raise SystemExit(
            "value_receipts.db is schema v1 (no replay_context column). "
            "Upgrade agent-borg so rescues record replayable receipts, then re-run."
        )
    rows = [
        dict(r)
        for r in conn.execute(
            "SELECT id, created_at, problem_class, confidence, provenance, trigger, "
            "trigger_n, coverage_class, replay_context FROM rescue_receipts "
            "WHERE matched = 1 ORDER BY id"
        )
    ]
    conn.close()
    for row in rows:
        try:
            row["replay_context"] = json.loads(row.get("replay_context") or "{}")
        except json.JSONDecodeError:
            row["replay_context"] = {}
    return rows


def load_receipts_from_file(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text())
    receipts = data["receipts"] if isinstance(data, dict) and "receipts" in data else data
    if not isinstance(receipts, list):
        raise SystemExit(f"{path}: expected a JSON list of receipts (or {{'receipts': [...]}})")
    return receipts


# ----------------------------------------------------------------- model calls


def _anthropic_call(prompt: str, *, max_tokens: int, api_key: str) -> str:
    body = json.dumps(
        {
            "model": MODEL_ID,
            "max_tokens": max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read())
    return "".join(b.get("text", "") for b in payload.get("content", []))


def _mock_verdict(receipt: Dict[str, Any]) -> str:
    """Deterministic offline verdict: fixtures may pin it via receipt['mock'];
    otherwise it is derived from a stable hash of the redacted error text."""
    pinned = (receipt.get("mock") or {}).get("judge", "")
    if pinned in ("WOULD_HAVE_SOLVED", "WOULD_HAVE_BEEN_STUCK"):
        return pinned
    err = (receipt.get("replay_context") or {}).get("error_redacted", "")
    digest = hashlib.sha256(err.encode("utf-8", "ignore")).hexdigest()
    return "WOULD_HAVE_BEEN_STUCK" if int(digest[:2], 16) % 2 else "WOULD_HAVE_SOLVED"


def replay_one(receipt: Dict[str, Any], *, mock: bool, api_key: str = "") -> Dict[str, Any]:
    ctx = receipt.get("replay_context") or {}
    error_redacted = (ctx.get("error_redacted") or "").strip()
    if not error_redacted:
        return {"id": receipt.get("id"), "skipped": "no_replay_context"}

    if mock:
        verdict = _mock_verdict(receipt)
        blind_attempt = "(mock mode: no model call)"
    else:
        blind_attempt = _anthropic_call(
            SOLVER_PROMPT.format(
                env_fingerprint=ctx.get("env_fingerprint", "?"),
                error_redacted=error_redacted,
            ),
            max_tokens=512,
            api_key=api_key,
        )
        judge_out = _anthropic_call(
            JUDGE_PROMPT.format(
                blind_attempt=blind_attempt.strip()[:2000],
                matched_id=ctx.get("matched_id", "?"),
                fix_surfaced=(ctx.get("fix_surfaced") or "(none recorded)")[:2000],
            ),
            max_tokens=64,
            api_key=api_key,
        )
        verdict = (
            "WOULD_HAVE_BEEN_STUCK" if "WOULD_HAVE_BEEN_STUCK" in judge_out else
            "WOULD_HAVE_SOLVED" if "WOULD_HAVE_SOLVED" in judge_out else
            "UNPARSEABLE"
        )

    return {
        "id": receipt.get("id"),
        "problem_class": receipt.get("problem_class", "unknown"),
        "coverage_class": receipt.get("coverage_class", "unknown"),
        "trigger": receipt.get("trigger", "unknown"),
        "verdict": verdict,
        "counterfactual": verdict == "WOULD_HAVE_BEEN_STUCK",
        "blind_attempt_chars": len(blind_attempt),
    }


# ------------------------------------------------------------------------ main


def run(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--borg-home", type=Path, help="read consented receipts from this BORG_HOME")
    src.add_argument("--receipts-file", type=Path, help="read consented receipts from a JSON export")
    src.add_argument("--fixtures", type=Path, help="synthetic CI fixtures (no consent needed, implies offline data)")
    ap.add_argument("--mock", action="store_true", help="no network: deterministic mock verdicts (CI mode)")
    ap.add_argument("--attest-consent", default="", metavar="TEXT",
                    help="REQUIRED for real receipts: who consented and when (recorded in the report)")
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--out", type=Path, help="also write the JSON report here")
    args = ap.parse_args(argv)

    real_source = args.borg_home or args.receipts_file
    if real_source and not args.attest_consent.strip():
        ap.error("real receipts need --attest-consent \"<who consented, when>\" — "
                 "receipts are local-only by contract; replay only with user consent")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not args.mock and not api_key:
        ap.error("live replay needs ANTHROPIC_API_KEY (or pass --mock for the offline CI mode)")

    if args.borg_home:
        receipts = load_receipts_from_db(args.borg_home.expanduser())
    else:
        receipts = load_receipts_from_file((args.receipts_file or args.fixtures).expanduser())
    receipts = receipts[: max(0, args.limit)]

    results = [replay_one(r, mock=args.mock, api_key=api_key) for r in receipts]
    replayed = [r for r in results if "skipped" not in r]
    skipped = len(results) - len(replayed)
    unparseable = sum(1 for r in replayed if r["verdict"] == "UNPARSEABLE")
    judged = [r for r in replayed if r["verdict"] != "UNPARSEABLE"]
    counterfactual = sum(1 for r in judged if r["counterfactual"])
    n = len(judged)
    rate = (counterfactual / n) if n else 0.0
    lo, hi = wilson_ci(counterfactual, n)

    report = {
        "schema": "counterfactual-replay-report/1",
        "model_id": MODEL_ID,
        "prompt_version": PROMPT_VERSION,
        "mock": bool(args.mock),
        "consent_attestation": args.attest_consent.strip(),
        "receipts_total": len(results),
        "skipped_no_context": skipped,
        "unparseable_verdicts": unparseable,
        "replayed": n,
        "counterfactual_count": counterfactual,
        "counterfactual_rate": round(rate, 4),
        "wilson_ci_95": [round(lo, 4), round(hi, 4)],
        "protocol_reading": protocol_reading(counterfactual, n),
        "thresholds": {"kill_below": KILL_THRESHOLD, "build_above": BUILD_THRESHOLD},
        "per_receipt": results,
    }
    if args.out:
        args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(
        f"counterfactual_rate = {counterfactual}/{n} = {rate:.1%} "
        f"(Wilson 95% CI {lo:.1%}-{hi:.1%}) -> {report['protocol_reading']}"
        + (" [MOCK — not evidence]" if args.mock else ""),
        file=sys.stderr,
    )
    return report


if __name__ == "__main__":
    try:
        run()
    except urllib.error.URLError as exc:  # operator-friendly network failure
        raise SystemExit(f"model call failed: {exc}")
