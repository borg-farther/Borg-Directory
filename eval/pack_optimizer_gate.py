#!/usr/bin/env python3
"""Executable gate for Borg's local-only pack optimizer.

This gate is intentionally conservative: it proves candidate artifacts are
complete, local-only, privacy-scanned, prompt-injection-scanned, and selected by
strict local metrics.  It does not claim first-10 or public/self-serve lift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from borg.core.pack_optimizer import PackOptimizer, REQUIRED_ARTIFACTS, load_examples_file, run_pack_optimizer  # noqa: E402

_SECRETISH_RE = re.compile(r"(?i)(sk-[a-z0-9_-]{16,}|gh[pousr]_[a-z0-9_]{16,}|xox[baprs]-[a-z0-9-]{16,}|password\s*=\s*\S+|token\s*=\s*\S+)")
_RAW_SENTINELS = ("RAW_USER_CHAT", "RAW_TOOL_OUTPUT", "BEGIN RAW", "raw_user_chat", "raw_tool_output")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_leak_failures(candidate_dir: Path) -> list[str]:
    failures: list[str] = []
    for path in candidate_dir.iterdir():
        if path.is_file() and path.suffix in {".json", ".patch", ".preview", ""}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(sentinel in text for sentinel in _RAW_SENTINELS):
                failures.append(f"raw_trajectory_sentinel:{path.name}")
            if _SECRETISH_RE.search(text):
                failures.append(f"secretish_token:{path.name}")
    return failures


def _verify_candidate(
    candidate_id: str,
    output_dir: str | Path,
    *,
    pack_file: str | Path,
    taskset: str | Path,
    examples_file: str | Path,
) -> dict[str, Any]:
    optimizer = PackOptimizer(output_root=output_dir)
    examples = load_examples_file(examples_file)
    data = optimizer.verify_candidate_against_sources(
        candidate_id,
        pack_path=pack_file,
        taskset_path=taskset,
        examples=examples,
        scope="local",
    )
    candidate_dir = Path(data["output_dir"])
    try:
        display_output_dir = str(candidate_dir.relative_to(ROOT))
    except ValueError:
        display_output_dir = str(candidate_dir)
    missing = [name for name in REQUIRED_ARTIFACTS if not (candidate_dir / name).exists()]
    score = data["selection_score"]
    privacy = data["privacy_scan"]
    injection = data["prompt_injection_scan"]
    run = data["optimizer_run"]
    failures: list[str] = []
    failures.extend(f"missing_artifact:{name}" for name in missing)
    if score.get("recommendation") != "eligible_for_manual_review":
        failures.append("selection_not_eligible")
    if privacy.get("blocked"):
        failures.append("privacy_scan_blocked")
    if injection.get("blocked"):
        failures.append("prompt_injection_scan_blocked")
    if not run.get("local_only"):
        failures.append("not_local_only")
    if run.get("first_10_claim") is not False:
        failures.append("first_10_claim_not_false")
    if run.get("global_promotion_allowed") is not False:
        failures.append("global_promotion_allowed_not_false")
    if data.get("source_verified") is not True:
        failures.append("source_verification_required")
    failures.extend(_artifact_leak_failures(candidate_dir))
    return {
        "success": not failures,
        "gate": "pack_optimizer",
        "candidate_id": candidate_id,
        "output_dir": display_output_dir,
        "recommendation": data.get("manual_review_eligibility") or score.get("recommendation"),
        "score_delta": score.get("score_delta"),
        "hard_failures": score.get("hard_failures", []),
        "gate_failures": failures,
        "first_10_claim": False,
        "global_promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Borg local pack optimizer gate")
    parser.add_argument("--candidate", default=None, help="Existing candidate id to inspect")
    parser.add_argument("--pack", default="systematic-debugging", help="Pack id for candidate generation")
    parser.add_argument("--pack-file", default="eval/tasksets/systematic_debugging_pack.yaml", help="Pack file path used to generate the local candidate")
    parser.add_argument("--taskset", default="eval/tasksets/systematic_debugging_selection.json", help="Selection taskset JSON")
    parser.add_argument("--examples-file", default="eval/tasksets/systematic_debugging_examples.json", help="Sanitized examples JSON")
    parser.add_argument("--collective-db", default=None, help="Optional collective learning DB path")
    parser.add_argument("--output-dir", default="eval/pack_optimizer", help="Candidate artifact root")
    parser.add_argument("--snapshot", default="eval/pack_optimizer_gate_snapshot.json", help="Gate snapshot path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    args = parser.parse_args()

    try:
        if args.candidate:
            candidate_id = args.candidate
        else:
            examples = load_examples_file(args.examples_file) if args.examples_file else None
            result = run_pack_optimizer(
                pack_id=args.pack,
                taskset_path=args.taskset,
                pack_path=args.pack_file,
                output_root=args.output_dir,
                examples=examples,
                collective_db_path=args.collective_db,
                local_only=True,
                max_edits=4,
            )
            candidate_id = result.candidate_id
        gate = _verify_candidate(
            candidate_id,
            args.output_dir,
            pack_file=args.pack_file,
            taskset=args.taskset,
            examples_file=args.examples_file,
        )
    except Exception as exc:  # Fail closed for gate use.
        gate = {
            "success": False,
            "gate": "pack_optimizer",
            "candidate_id": args.candidate or "",
            "error": str(exc),
            "type": type(exc).__name__,
            "first_10_claim": False,
            "global_promotion_allowed": False,
        }

    snapshot = Path(args.snapshot)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(gate, indent=2, sort_keys=True))
    else:
        print(f"pack_optimizer_gate: {'PASS' if gate.get('success') else 'FAIL'}")
        print(f"candidate_id: {gate.get('candidate_id', '')}")
        if gate.get("gate_failures"):
            print("gate_failures:")
            for failure in gate["gate_failures"]:
                print(f"  - {failure}")
        if gate.get("error"):
            print(f"error: {gate['error']}")
    return 0 if gate.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
