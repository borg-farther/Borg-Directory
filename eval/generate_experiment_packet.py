#!/usr/bin/env python3
"""Generate an integrity-aware experiment decision packet for Borg×AutoAgent.

Outputs a JSON packet used by readiness gates.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

try:
    # Package-style imports (pytest, module execution)
    from eval.autoagent_harbor_bridge import verify_provenance_manifest
    from eval.instrumentation_schema import DB_PATH, load_experiment
except ModuleNotFoundError:
    # Script-style imports (python eval/generate_experiment_packet.py)
    from autoagent_harbor_bridge import verify_provenance_manifest
    from instrumentation_schema import DB_PATH, load_experiment


def _rate(records: list[Any], pred) -> float:
    if not records:
        return 0.0
    return sum(1 for r in records if pred(r)) / len(records)


def _mean(records: list[Any], getter) -> float:
    vals = [float(getter(r)) for r in records]
    return mean(vals) if vals else 0.0


def _diff_ci_95(p1: float, n1: int, p2: float, n2: int) -> tuple[float, float]:
    if n1 <= 0 or n2 <= 0:
        return (0.0, 0.0)
    se = math.sqrt((p1 * (1 - p1) / n1) + (p2 * (1 - p2) / n2))
    margin = 1.96 * se
    d = p2 - p1
    return (d - margin, d + margin)


def _load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_pair(job_dir: Path | None, manifest_path: Path | None) -> dict[str, Any]:
    if not job_dir or not manifest_path:
        return {"provided": False, "ok": False, "errors": ["missing_job_or_manifest"]}
    if not job_dir.exists() or not manifest_path.exists():
        return {"provided": True, "ok": False, "errors": ["missing_path"]}
    manifest = _load_manifest(manifest_path)
    ok, errors = verify_provenance_manifest(job_dir, manifest)
    return {"provided": True, "ok": bool(ok), "errors": errors}


def _verify_from_instrumentation_db(experiment_id: str, arm: str) -> dict[str, Any]:
    control, treatment = load_experiment(experiment_id)
    records = control if arm == "control" else treatment
    if not records:
        return {
            "provided": True,
            "ok": False,
            "errors": [f"no_{arm}_records_for_experiment"],
            "source": "instrumentation_db",
            "record_count": 0,
        }
    return {
        "provided": True,
        "ok": True,
        "errors": [],
        "source": "instrumentation_db",
        "record_count": len(records),
    }


def _latest_experiment_id_from_db() -> str:
    db_path = Path(DB_PATH)
    if not db_path.exists():
        raise ValueError(f"No instrumentation DB at {db_path}")

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT experiment_id FROM task_records "
            "WHERE experiment_id IS NOT NULL AND experiment_id != '' "
            "ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()

    if not row or not row[0]:
        raise ValueError("No experiment_id rows found in instrumentation DB")
    return str(row[0])


def _resolve_experiment_id(explicit_id: str | None) -> str:
    if explicit_id and explicit_id.strip():
        return explicit_id.strip()
    return _latest_experiment_id_from_db()


def build_packet(
    experiment_id: str,
    control_verify: dict[str, Any],
    treatment_verify: dict[str, Any],
) -> dict[str, Any]:
    control, treatment = load_experiment(experiment_id)

    n_control = len(control)
    n_treatment = len(treatment)

    c_completion = _rate(control, lambda r: int(r.completion_status) == 2)
    t_completion = _rate(treatment, lambda r: int(r.completion_status) == 2)
    c_severe = _rate(control, lambda r: bool(r.severe_failure))
    t_severe = _rate(treatment, lambda r: bool(r.severe_failure))

    success_lift = t_completion - c_completion
    severe_failure_delta = t_severe - c_severe
    completion_ci95 = _diff_ci_95(c_completion, n_control, t_completion, n_treatment)

    suspicious_control = sum(
        1
        for r in control
        if int(r.completion_status) == 2 and int(r.tool_call_count) == 0 and not bool(r.trace_retrieved)
    )
    suspicious_treatment = sum(
        1
        for r in treatment
        if int(r.completion_status) == 2 and int(r.tool_call_count) == 0 and not bool(r.trace_retrieved)
    )
    suspicious_total = suspicious_control + suspicious_treatment

    synthetic_evidence = "synthetic" in experiment_id.lower()

    provenance_ok = (
        control_verify.get("provided")
        and treatment_verify.get("provided")
        and control_verify.get("ok")
        and treatment_verify.get("ok")
    )

    integrity_pass = bool(
        provenance_ok
        and not synthetic_evidence
        and suspicious_total == 0
    )

    policy_pass = bool(
        success_lift >= 0.05
        and severe_failure_delta <= 0.01
        and integrity_pass
        and completion_ci95[0] > 0.0
    )

    decision = "SHIP" if policy_pass else ("HOLD" if integrity_pass else "KILL")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_id": experiment_id,
        "samples": {"control": n_control, "treatment": n_treatment},
        "metrics": {
            "control_completion_rate": c_completion,
            "treatment_completion_rate": t_completion,
            "success_lift": success_lift,
            "completion_lift_ci95": {"low": completion_ci95[0], "high": completion_ci95[1]},
            "control_severe_failure_rate": c_severe,
            "treatment_severe_failure_rate": t_severe,
            "severe_failure_delta": severe_failure_delta,
            "control_tokens_mean": _mean(control, lambda r: r.tokens_total),
            "treatment_tokens_mean": _mean(treatment, lambda r: r.tokens_total),
        },
        "integrity": {
            "synthetic_evidence": synthetic_evidence,
            "provenance": {
                "control": control_verify,
                "treatment": treatment_verify,
                "pass": provenance_ok,
            },
            "anomalies": {
                "high_reward_no_edit_total": suspicious_total,
                "high_reward_no_edit_control": suspicious_control,
                "high_reward_no_edit_treatment": suspicious_treatment,
            },
            "pass": integrity_pass,
        },
        "policy": {
            "success_lift_min": 0.05,
            "severe_failure_delta_max": 0.01,
            "ci_low_must_be_gt_zero": True,
            "pass": policy_pass,
        },
        "decision": decision,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Borg AutoAgent experiment packet")
    ap.add_argument("--experiment-id", default="", help="Experiment id; if omitted, auto-select latest id from instrumentation DB")
    ap.add_argument("--control-job-dir")
    ap.add_argument("--control-manifest")
    ap.add_argument("--treatment-job-dir")
    ap.add_argument("--treatment-manifest")
    ap.add_argument("--output", default="/root/hermes-workspace/borg/eval/experiment_packet.json")
    args = ap.parse_args()

    control_verify = _verify_pair(
        Path(args.control_job_dir) if args.control_job_dir else None,
        Path(args.control_manifest) if args.control_manifest else None,
    )
    treatment_verify = _verify_pair(
        Path(args.treatment_job_dir) if args.treatment_job_dir else None,
        Path(args.treatment_manifest) if args.treatment_manifest else None,
    )

    resolved_experiment_id = _resolve_experiment_id(args.experiment_id)

    if control_verify.get("provided") is False:
        control_verify = _verify_from_instrumentation_db(resolved_experiment_id, "control")
    if treatment_verify.get("provided") is False:
        treatment_verify = _verify_from_instrumentation_db(resolved_experiment_id, "treatment")

    packet = build_packet(resolved_experiment_id, control_verify, treatment_verify)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(str(out))
    print(
        json.dumps(
            {
                "experiment_id": resolved_experiment_id,
                "decision": packet["decision"],
                "integrity_pass": packet["integrity"]["pass"],
            }
        )
    )
    return 0 if packet["decision"] == "SHIP" else 1


if __name__ == "__main__":
    raise SystemExit(main())
