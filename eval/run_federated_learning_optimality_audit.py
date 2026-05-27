#!/usr/bin/env python3
"""Truth gate for whether Borg federated learning is *optimal*, not just safe.

This deliberately separates three questions that are easy to conflate:

1. Is the remote/signed registry protocol correct enough to call GO?
2. Is the mechanism proven to improve agents quickly in the real world?
3. Is the current learning loop close to Google/God-tier optimality?

The expected current answer is: protocol GO; optimality/value proof NO-GO.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def _git_context() -> Dict[str, Any]:
    def run(*args: str) -> str:
        try:
            proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=10, check=False)
            return proc.stdout.strip() if proc.returncode == 0 else ""
        except Exception:
            return ""

    status = run("status", "--short")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status),
        "dirty_files": [line for line in status.splitlines() if line],
    }


def _trace_stats(trace_db: Path | None) -> Dict[str, Any]:
    if not trace_db or not trace_db.exists():
        return {"available": False, "reason": "trace database not found"}
    try:
        conn = sqlite3.connect(f"file:{trace_db}?mode=ro", uri=True)
        cur = conn.cursor()
        tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "traces" not in tables:
            return {"available": False, "reason": "traces table not found", "path": str(trace_db)}
        total = cur.execute("SELECT COUNT(*) FROM traces").fetchone()[0]
        columns = [row[1] for row in cur.execute("PRAGMA table_info(traces)").fetchall()]
        distinct_task = None
        if "task_description" in columns:
            distinct_task = cur.execute("SELECT COUNT(DISTINCT task_description) FROM traces").fetchone()[0]
        outcomes = {}
        if "outcome" in columns:
            outcomes = dict(cur.execute("SELECT outcome, COUNT(*) FROM traces GROUP BY outcome").fetchall())
        conn.close()
        duplicate_pressure = None
        if total and distinct_task:
            duplicate_pressure = round(1.0 - (float(distinct_task) / float(total)), 4)
        return {
            "available": True,
            "path": str(trace_db),
            "total_traces": int(total),
            "distinct_task_descriptions": int(distinct_task) if distinct_task is not None else None,
            "duplicate_pressure": duplicate_pressure,
            "outcomes": outcomes,
        }
    except Exception as exc:  # pragma: no cover - defensive for local operator DB drift.
        return {"available": False, "path": str(trace_db), "reason": str(exc)}


def compile_audit(
    *,
    federated_snapshot: Path,
    first10_scoreboard: Path,
    collective_loop_snapshot: Path | None = None,
    trace_db: Path | None = None,
) -> Dict[str, Any]:
    federated = _load_json(federated_snapshot)
    collective_loop = _load_json(collective_loop_snapshot) if collective_loop_snapshot else {}
    first10 = _load_json(first10_scoreboard)
    counts = first10.get("current_counts", {}) if isinstance(first10, dict) else {}
    value_counts = first10.get("current_value_counts", {}) if isinstance(first10, dict) else {}
    trace = _trace_stats(trace_db)

    protocol_go = bool(
        federated.get("success") is True
        and federated.get("verdict") == "GO"
        and federated.get("scope") == "remote_global_federated_protocol"
        and federated.get("external_user_lift_claimed") is False
    )
    collective_loop_go = bool(
        collective_loop.get("success") is True
        and collective_loop.get("verdict") == "GO"
        and collective_loop.get("scope") == "max_value_collective_intelligence_loop_primitives"
        and str(collective_loop.get("public_external_lift", "")).startswith("NO-GO")
    )
    proof_fields = [
        federated.get("generated_at_utc"),
        federated.get("proof_provenance", {}).get("git", {}).get("commit"),
        federated.get("remote_http_signed_manifest", {}).get("manifest_hash"),
        federated.get("remote_http_signed_manifest", {}).get("atom_envelope_hash"),
        federated.get("remote_http_signed_manifest", {}).get("receipt_hash"),
        federated.get("remote_http_signed_manifest", {}).get("tombstone_hash"),
        federated.get("runtime_freshness", {}).get("fingerprint"),
        federated.get("revocation_convergence", {}).get("post_revocation_get_atom_is_none"),
        federated.get("revocation_convergence", {}).get("reimport_suppressed"),
        federated.get("adversarial_coverage", {}).get("in_tests"),
    ]
    proof_richness = sum(1 for field in proof_fields if field not in (None, False, [], {}, "")) / len(proof_fields)

    real_users = int(counts.get("real_users") or counts.get("verified_external_users") or 0)
    install_successes = int(counts.get("install_successes") or 0)
    useful_rescues = int(counts.get("useful_rescue_moments") or 0)
    critical_incidents = int(counts.get("critical_privacy_security_failures") or 0)
    measured_rows = int(value_counts.get("rows_with_measured_value") or 0)

    protocol_security_score = 8.0 if protocol_go else 2.0
    protocol_security_score += 1.0 if proof_richness >= 0.9 else 0.0
    protocol_security_score = min(protocol_security_score, 9.0)

    external_truth_score = 1.0
    if real_users >= 10 and install_successes >= 8 and useful_rescues >= 6 and critical_incidents == 0:
        external_truth_score = 7.0
    if measured_rows >= 6:
        external_truth_score = 8.0

    signal_quality_score = 5.0 if collective_loop_go else 4.0
    if trace.get("available") and trace.get("total_traces", 0) > 0:
        duplicate_pressure = trace.get("duplicate_pressure")
        if duplicate_pressure is not None and duplicate_pressure > 0.5:
            signal_quality_score = 4.0 if collective_loop_go else 3.0
        else:
            signal_quality_score = 6.0 if collective_loop_go else 5.0
    if useful_rescues >= 6:
        signal_quality_score = max(signal_quality_score, 6.0)

    routing_value_score = 6.0 if collective_loop_go else (5.0 if protocol_go else 3.0)
    if useful_rescues >= 6 and measured_rows > 0:
        routing_value_score = 7.0

    collective_learning_score = 6.0 if collective_loop_go else (4.0 if protocol_go else 2.0)
    if real_users >= 10 and useful_rescues >= 6 and measured_rows >= 6:
        collective_learning_score = 8.0

    optimality_score = min(
        protocol_security_score,
        external_truth_score + 1.0,
        signal_quality_score + 1.0,
        routing_value_score,
        collective_learning_score,
    )

    google_tier_optimal = bool(optimality_score >= 8.0 and external_truth_score >= 8.0 and collective_learning_score >= 8.0)

    resolved_internal_primitives = {
        "outcome_receipts": collective_loop_go and bool(collective_loop.get("checks", {}).get("outcome_receipts_exported")),
        "dedupe_generalization": collective_loop_go and bool(collective_loop.get("checks", {}).get("dedupe_cluster_stable")),
        "registry_computed_quorum": collective_loop_go and bool(collective_loop.get("checks", {}).get("registry_computed_quorum")),
        "payload_quorum_ignored": collective_loop_go and bool(collective_loop.get("checks", {}).get("payload_quorum_ignored")),
        "unified_scored_retrieval": collective_loop_go and bool(collective_loop.get("checks", {}).get("unified_retrieval_ranked")),
        "negative_evidence_retained": collective_loop_go and bool(collective_loop.get("checks", {}).get("negative_evidence_retained")),
        "first10_not_faked": collective_loop_go and bool(collective_loop.get("checks", {}).get("first10_not_faked")),
    }

    p0_gaps = []
    if not collective_loop_go:
        p0_gaps.extend([
            "Tie every guidance event to an outcome receipt: exact guidance shown, verification command, worked/failed result, time/tokens/dead-ends avoided.",
            "Deduplicate and generalize traces into canonical atoms before promotion; repeated seed-like traces must not inflate confidence.",
            "Compute tenant quorum from signed independent outcome receipts, not caller-supplied counts at registry ingestion time.",
            "Unify packs, traces, atoms, failure memory, negative evidence, recency, and project context into one scored retrieval/routing API.",
        ])
    if measured_rows < 6:
        p0_gaps.append("Collect consented first-10 external outcome rows with measured minutes/tokens/dead-ends impact; internal/synthetic gates must not count.")
    if real_users < 10 or install_successes < 8 or useful_rescues < 6 or critical_incidents != 0:
        p0_gaps.append("Pass row-derived first-10 public-package evidence: 10 real users, 8 installs, 6 useful rescues, 0 critical privacy/security incidents.")
    p0_gaps.extend([
        "Run the 3-condition knowledge-system evaluation: no Borg, empty Borg scaffold, seeded Borg knowledge; report pure knowledge lift separately.",
        "Operate a production hosted registry with monitoring, key rotation, backup/restore, incident response, and revocation SLO telemetry.",
        "Add transparency-log anchoring before high-trust public federation claims.",
    ])

    return {
        "schema_version": 1,
        "generated_at_utc": _utc_now(),
        "git": _git_context(),
        "verdict": {
            "google_god_tier_optimal": "GO" if google_tier_optimal else "NO-GO",
            "remote_global_federated_protocol": "GO" if protocol_go else "NO-GO",
            "effective_collective_learning": "GO" if collective_learning_score >= 8.0 else "NO-GO_REAL_WORLD_VALUE_NOT_PROVEN",
            "public_self_serve_launch": "NO-GO" if real_users < 10 or useful_rescues < 6 or critical_incidents else "GO",
            "external_user_lift": "NO-GO" if measured_rows < 6 else "GO",
        },
        "scores_0_to_10": {
            "protocol_security": round(protocol_security_score, 1),
            "proof_packet_richness": round(proof_richness * 10, 1),
            "external_truth_grounding": round(external_truth_score, 1),
            "signal_quality": round(signal_quality_score, 1),
            "routing_value_speed": round(routing_value_score, 1),
            "effective_collective_learning": round(collective_learning_score, 1),
            "overall_optimality_ceiling": round(optimality_score, 1),
        },
        "resolved_internal_primitives": resolved_internal_primitives,
        "evidence": {
            "federated_snapshot": str(federated_snapshot),
            "federated_protocol_verdict": federated.get("verdict"),
            "federated_scope": federated.get("scope"),
            "collective_loop_snapshot": str(collective_loop_snapshot) if collective_loop_snapshot else "",
            "collective_loop": {
                "verdict": collective_loop.get("verdict"),
                "scope": collective_loop.get("scope"),
                "public_external_lift": collective_loop.get("public_external_lift"),
                "success": collective_loop.get("success"),
            },
            "first10_scoreboard": str(first10_scoreboard),
            "first10_counts": {
                "real_users": real_users,
                "install_successes": install_successes,
                "useful_rescue_moments": useful_rescues,
                "critical_privacy_security_failures": critical_incidents,
                "rows_with_measured_value": measured_rows,
            },
            "trace_stats": trace,
        },
        "external_design_anchors": [
            {
                "name": "TUF",
                "lesson": "Signed metadata, file hashes, expiry, rollback/replay resistance are necessary for safe propagation.",
                "url": "https://theupdateframework.github.io/specification/latest/",
            },
            {
                "name": "Sigstore/Rekor",
                "lesson": "Transparency logs make metadata tamper-resistant/auditable; Borg does not yet implement this append-only layer.",
                "url": "https://docs.sigstore.dev/logging/overview/",
            },
            {
                "name": "SLSA provenance",
                "lesson": "Artifact metadata should say where, when, and how something was produced; Borg proof packets now need this provenance.",
                "url": "https://slsa.dev/spec/v0.1/provenance",
            },
            {
                "name": "Federated-learning Sybil/poisoning literature",
                "lesson": "Multiple identities can overpower honest clients; Borg needs outcome-derived tenant independence, not self-reported quorum.",
                "url": "https://ar5iv.labs.arxiv.org/html/1808.04866",
            },
        ],
        "p0_gaps_to_google_tier": p0_gaps,
        "hard_boundary": "Protocol GO is not evidence of maximum agent value, public adoption, or measured external lift.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit whether Borg federated learning is optimal/value-proven")
    parser.add_argument("--federated-snapshot", default=str(ROOT / "eval" / "federated_learning_gate_snapshot.json"))
    parser.add_argument("--first10-scoreboard", default=str(ROOT / "eval" / "first_10_user_scoreboard.json"))
    parser.add_argument("--collective-loop-snapshot", default=str(ROOT / "eval" / "collective_intelligence_loop_gate.json"))
    parser.add_argument("--trace-db", default="")
    parser.add_argument("--output", default=str(ROOT / "eval" / "federated_learning_optimality_audit.json"))
    args = parser.parse_args(argv)

    trace_db = Path(args.trace_db) if args.trace_db else Path.home() / ".borg" / "traces.db"
    result = compile_audit(
        federated_snapshot=Path(args.federated_snapshot),
        first10_scoreboard=Path(args.first10_scoreboard),
        collective_loop_snapshot=Path(args.collective_loop_snapshot),
        trace_db=trace_db,
    )
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"]["remote_global_federated_protocol"] == "GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
