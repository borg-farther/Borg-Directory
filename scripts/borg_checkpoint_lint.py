#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "eval" / "borg_telegram_checkpoint_contract.json"
DOC_PATH = ROOT / "docs" / "BORG_TELEGRAM_CHECKPOINT_STANDARD.md"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def lint() -> int:
    errors: list[str] = []

    if not CONTRACT_PATH.exists():
        errors.append(f"missing contract: {CONTRACT_PATH}")
    if not DOC_PATH.exists():
        errors.append(f"missing doc: {DOC_PATH}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        return 1

    contract = _load_json(CONTRACT_PATH)
    doc_text = DOC_PATH.read_text(encoding="utf-8")

    for line in contract.get("required_lines", []):
        if line not in doc_text:
            errors.append(f"doc missing required checkpoint line: {line}")

    risk_map = contract.get("risk_to_checkpoint_count", {})
    expected_risk = {"low": 1, "medium": 2, "high": 4}
    if risk_map != expected_risk:
        errors.append(
            f"risk_to_checkpoint_count mismatch: expected {expected_risk}, got {risk_map}"
        )

    defaults = contract.get("estimation_defaults", {})
    for key in (
        "avg_seconds_per_tool_call",
        "usd_per_million_tokens_low",
        "usd_per_million_tokens_high",
    ):
        if key not in defaults:
            errors.append(f"missing estimation default: {key}")

    block_re = re.compile(
        r"\[borg checkpoint\]\n"
        r"phase:\s+(investigate|decide|execute|verify)\n"
        r"borg used:\s+(yes|no)\s+\(source:\s+(borg|guild|none),\s+confidence:\s+(high|medium|low)\)\n"
        r"what changed:\s+.+\n"
        r"estimated save:\s+.+\n"
        r"next step:\s+.+",
        re.IGNORECASE,
    )
    if not block_re.search(doc_text):
        errors.append("doc does not contain a fully valid example checkpoint block")

    if errors:
        print("FAIL: borg checkpoint lint")
        for e in errors:
            print(f" - {e}")
        return 1

    print("PASS: borg checkpoint lint")
    return 0


if __name__ == "__main__":
    raise SystemExit(lint())
