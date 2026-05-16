import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_evidence_contract import BenchmarkEvidenceError, validate_benchmark_evidence


def test_permits_honest_no_valid_evidence_status():
    verdict = validate_benchmark_evidence(
        {
            "status": "NO_VALID_EVIDENCE",
            "reason": "Only zero-token/zero-duration control artifact exists.",
            "frontier_better_than_proven": False,
        }
    )
    assert verdict["valid"] is True
    assert verdict["status"] == "NO_VALID_EVIDENCE"
    assert verdict["frontier_better_than_proven"] is False


def test_rejects_zero_token_zero_duration_artifact_as_evidence():
    with pytest.raises(BenchmarkEvidenceError) as exc:
        validate_benchmark_evidence(
            {
                "success": False,
                "duration_seconds": 0.0,
                "tokens_used": 0,
                "token_delta": 0,
                "claim": "Borg is better than frontier models",
            }
        )
    message = str(exc.value)
    assert "positive duration" in message
    assert "positive token" in message
    assert "frontier/better-than claim lacks controlled evidence" in message


def test_rejects_null_delta_metrics():
    with pytest.raises(BenchmarkEvidenceError) as exc:
        validate_benchmark_evidence(
            {
                "success_delta": None,
                "duration_seconds": 12.5,
                "tokens_used": 1000,
            }
        )
    assert "delta metrics are present but all null" in str(exc.value)


def test_accepts_controlled_frontier_claim_with_required_metrics():
    verdict = validate_benchmark_evidence(
        {
            "claim": "Borg outperforms frontier baseline on this controlled benchmark",
            "matched_tasks": ["T1", "T2"],
            "randomized": True,
            "frontier_baseline": "frontier-agent-x",
            "confidence_interval": [0.02, 0.15],
            "success_delta": 0.08,
            "duration_seconds": 123.4,
            "tokens_used": 45678,
            "rows": [
                {"task_id": "T1", "arm": "control", "success": True},
                {"task_id": "T1", "arm": "treatment", "success": True},
            ],
        }
    )
    assert verdict["frontier_better_than_proven"] is True


def test_accepts_paired_rows_with_explicit_token_unavailable_marker():
    verdict = validate_benchmark_evidence(
        {
            "rows": [
                {"task_id": "T1", "arm": "control", "success": False, "latency_seconds": 3.0},
                {"task_id": "T1", "arm": "treatment", "success": True, "latency_seconds": 2.0},
            ],
            "duration_seconds": 5.0,
            "tokens_metric_status": "not_measured",
            "success_delta": 1.0,
        }
    )
    assert verdict["status"] == "VALID_EVIDENCE"


def test_rejects_non_unavailable_token_status_without_token_count():
    with pytest.raises(BenchmarkEvidenceError) as exc:
        validate_benchmark_evidence(
            {
                "rows": [
                    {"task_id": "T1", "arm": "control", "success": False, "latency_seconds": 3.0},
                    {"task_id": "T1", "arm": "treatment", "success": True, "latency_seconds": 2.0},
                ],
                "duration_seconds": 5.0,
                "tokens_metric_status": "measured",
                "success_delta": 1.0,
            }
        )
    assert "missing positive token metric" in str(exc.value)


def test_rejects_unpaired_control_and_treatment_rows_on_different_tasks():
    with pytest.raises(BenchmarkEvidenceError) as exc:
        validate_benchmark_evidence(
            {
                "rows": [
                    {"task_id": "T1", "arm": "control", "success": False, "latency_seconds": 3.0},
                    {"task_id": "T2", "arm": "treatment", "success": True, "latency_seconds": 2.0},
                ],
                "duration_seconds": 5.0,
                "tokens_metric_status": "not_measured",
            }
        )
    assert "missing success/success_delta/paired-row evidence" in str(exc.value)


def test_cli_reports_invalid_json_artifact(tmp_path):
    artifact = tmp_path / "bad.json"
    artifact.write_text(json.dumps({"success": False, "duration_seconds": 0, "tokens_used": 0}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "benchmark_evidence_contract.py"), str(artifact)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 1
    assert '"valid": false' in proc.stdout


def test_existing_benchmark_audit_is_explicitly_not_frontier_proof():
    audit = ROOT / "eval" / "20260515_benchmark_evidence_audit.json"
    assert audit.exists()
    text = audit.read_text(encoding="utf-8", errors="replace").lower()
    assert "frontier_better_than_proven" in text or "no controlled frontier" in text or "no_valid_evidence" in text
    assert "duration_seconds=0.0" in text or "zero" in text
