#!/usr/bin/env python3
"""Controlled Borg-memory lookup used by the C1/C2 value trial.

This deliberately bypasses bundled seed packs and remote indexes. The only
experimental difference is whether the supplied trace database is empty (C1)
or contains preregistered validated traces (C2).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from borg.core.confidence_gate import trace_match_is_confident
from borg.core.trace_matcher import TraceMatcher


def lookup(query: str, db_path: str) -> dict:
    matcher = TraceMatcher(db_path=db_path)
    candidates = matcher.find_relevant(task=query, error=query, top_k=5)
    matches = [
        item for item in candidates
        if trace_match_is_confident(item, min_similarity=0.0, query=query)
    ][:3]
    if not matches:
        return {
            "status": "no_confident_match",
            "action": "Proceed with normal debugging; the Borg memory is empty or has no relevant verified trace.",
            "matches": [],
        }
    rendered = []
    for item in matches:
        rendered.append({
            "trace_id": item.get("id"),
            "root_cause": item.get("root_cause") or "",
            "action": item.get("causal_intervention") or item.get("approach_summary") or "",
            "stop": item.get("dead_ends") or "",
            "source": item.get("source") or "unknown",
            "outcome": item.get("outcome") or "unknown",
        })
    return {
        "status": "matched_verified_memory",
        "advisory": "Treat this as a hypothesis; inspect the code and verify with tests.",
        "matches": rendered,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("query", nargs="+")
    args = parser.parse_args()
    query = " ".join(args.query).strip()
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"query": query}, sort_keys=True) + "\n")
    print(json.dumps(lookup(query, args.db), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
