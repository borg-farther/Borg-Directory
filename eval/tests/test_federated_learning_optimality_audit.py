from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_federated_learning_optimality_audit_splits_protocol_go_from_value_no_go(tmp_path):
    collective = tmp_path / "collective.json"
    collective_proc = subprocess.run(
        [sys.executable, "eval/run_collective_intelligence_loop_gate.py", "--output", str(collective)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert collective_proc.returncode == 0, collective_proc.stderr + collective_proc.stdout

    federated = tmp_path / "federated.json"
    federated_proc = subprocess.run(
        [sys.executable, "eval/run_federated_learning_gate.py", "--output", str(federated)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert federated_proc.returncode == 0, federated_proc.stderr + federated_proc.stdout

    output = tmp_path / "optimality.json"
    proc = subprocess.run(
        [
            sys.executable,
            "eval/run_federated_learning_optimality_audit.py",
            "--federated-snapshot",
            str(federated),
            "--collective-loop-snapshot",
            str(collective),
            "--output",
            str(output),
            "--trace-db",
            str(tmp_path / "missing-traces.db"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["verdict"]["remote_global_federated_protocol"] == "GO"
    assert data["verdict"]["google_god_tier_optimal"] == "NO-GO"
    assert data["verdict"]["effective_collective_learning"] == "NO-GO_REAL_WORLD_VALUE_NOT_PROVEN"
    assert data["verdict"]["public_self_serve_launch"] == "NO-GO"
    assert data["verdict"]["external_user_lift"] == "NO-GO"
    assert data["evidence"]["first10_counts"]["real_users"] == 0
    assert data["evidence"]["first10_counts"]["useful_rescue_moments"] == 0
    assert data["scores_0_to_10"]["protocol_security"] >= 8.0
    assert data["scores_0_to_10"]["external_truth_grounding"] <= 1.0
    assert data["scores_0_to_10"]["overall_optimality_ceiling"] < 8.0
    assert data["evidence"]["collective_loop"]["verdict"] == "GO"
    assert data["evidence"]["collective_loop"]["public_external_lift"].startswith("NO-GO")
    assert data["resolved_internal_primitives"]["outcome_receipts"] is True
    assert data["resolved_internal_primitives"]["unified_scored_retrieval"] is True
    assert all("Tie every guidance event" not in gap for gap in data["p0_gaps_to_google_tier"])
    assert len(data["p0_gaps_to_google_tier"]) >= 3
    assert "Protocol GO is not evidence" in data["hard_boundary"]


def test_federated_learning_optimality_audit_does_not_claim_external_lift_with_empty_rows(tmp_path):
    federated = {
        "success": True,
        "verdict": "GO",
        "scope": "remote_global_federated_protocol",
        "external_user_lift_claimed": False,
        "generated_at_utc": "2026-05-26T21:15:00Z",
        "proof_provenance": {"git": {"commit": "abc"}},
        "remote_http_signed_manifest": {
            "manifest_hash": "m",
            "atom_envelope_hash": "a",
            "receipt_hash": "r",
            "tombstone_hash": "t",
        },
        "runtime_freshness": {"fingerprint": {"success": True}},
        "revocation_convergence": {"post_revocation_get_atom_is_none": True, "reimport_suppressed": True},
        "adversarial_coverage": {"in_tests": ["unsigned_manifest_rejected"]},
    }
    scoreboard = {
        "current_counts": {
            "real_users": 0,
            "install_successes": 0,
            "useful_rescue_moments": 0,
            "critical_privacy_security_failures": 0,
        },
        "current_value_counts": {"rows_with_measured_value": 0},
    }
    fed_path = tmp_path / "fed.json"
    score_path = tmp_path / "score.json"
    out_path = tmp_path / "out.json"
    fed_path.write_text(json.dumps(federated), encoding="utf-8")
    score_path.write_text(json.dumps(scoreboard), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "eval/run_federated_learning_optimality_audit.py",
            "--federated-snapshot",
            str(fed_path),
            "--first10-scoreboard",
            str(score_path),
            "--trace-db",
            str(tmp_path / "missing.db"),
            "--output",
            str(out_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["verdict"]["remote_global_federated_protocol"] == "GO"
    assert data["verdict"]["external_user_lift"] == "NO-GO"
    assert data["verdict"]["google_god_tier_optimal"] == "NO-GO"
    assert data["scores_0_to_10"]["proof_packet_richness"] == 10.0
