from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_pack_optimizer_gate_runs_local_candidate_and_writes_snapshot(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    taskset = tmp_path / "taskset.json"
    examples = tmp_path / "examples.json"
    output_root = tmp_path / "out"
    snapshot = tmp_path / "snapshot.json"

    pack_path.write_text(
        """
type: workflow_pack
version: "1.0"
id: systematic-debugging
problem_class: debugging
mental_model: Reproduce, isolate, fix, then verify the exact failing command.
required_inputs:
  - name: error_message
    type: string
    description: Exact failing command output or traceback.
phases:
  - name: observe
    description: Return ACTION STOP VERIFY when a concrete failure exists.
    checkpoint: Failure evidence is reproduced before fixing.
  - name: confidence
    description: Return NO_CONFIDENT_MATCH when evidence is weak.
    checkpoint: Weak or unrelated guidance is rejected.
escalation_rules:
  - condition: Failure cannot be reproduced locally.
    action: Stop and report the exact missing evidence.
provenance:
  confidence: tested
  evidence: Local optimizer gate fixture with schema-valid workflow pack fields.
  failure_cases:
    - Missing exact failure text.
""".strip()
        + "\n",
        encoding="utf-8",
    )
    taskset.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "taskset_id": "gate-smoke",
                "baseline_metrics": {
                    "verified_success": 0.50,
                    "action_stop_verify_relevance": 0.50,
                    "dead_ends_avoided": 0.10,
                    "no_confident_match_precision": 0.60,
                    "verification_quality": 0.60,
                    "token_or_tool_efficiency": 0.30,
                },
                "candidate_metrics": {
                    "verified_success": 0.80,
                    "action_stop_verify_relevance": 0.80,
                    "dead_ends_avoided": 0.40,
                    "no_confident_match_precision": 0.90,
                    "verification_quality": 0.90,
                    "token_or_tool_efficiency": 0.50,
                },
                "controls": {
                    "unrelated_task_regression": False,
                    "no_confident_match_regression": False,
                    "unsafe_command_regression": False,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    examples.write_text(
        json.dumps(
            {
                "examples": [
                    {
                        "example_id": "gate-success",
                        "pack_id": "systematic-debugging",
                        "task_class": "python:modulenotfounderror",
                        "intervention_id": "intervention-sha256:" + "1" * 64,
                        "guidance": {"ACTION": "Install Flask", "STOP": "Do not use sudo pip", "VERIFY": "python -c 'import flask'"},
                        "outcome": "success",
                        "helpful": True,
                        "verified": True,
                        "verification_exit_code": 0,
                        "verification_output_sha256": "sha256:" + "a" * 64,
                        "trusted_tenant_id": "tenant-identity-sha256:" + "b" * 64,
                        "receipt_id": "outcome-sha256:" + "c" * 64,
                    },
                    {
                        "example_id": "gate-failure",
                        "pack_id": "systematic-debugging",
                        "task_class": "unknown:no-confident-match",
                        "intervention_id": "intervention-sha256:" + "2" * 64,
                        "guidance": {"ACTION": "No confident match", "STOP": "Do not force guidance", "VERIFY": "rerun exact failure"},
                        "outcome": "failure",
                        "helpful": False,
                        "verified": True,
                        "verification_exit_code": 1,
                        "verification_output_sha256": "sha256:" + "d" * 64,
                        "trusted_tenant_id": "tenant-identity-sha256:" + "e" * 64,
                        "receipt_id": "outcome-sha256:" + "f" * 64,
                    },
                    {
                        "example_id": "gate-success-2",
                        "pack_id": "systematic-debugging",
                        "task_class": "python:importerror",
                        "intervention_id": "intervention-sha256:" + "3" * 64,
                        "guidance": {"ACTION": "Install dependency", "STOP": "Do not reinstall Python", "VERIFY": "pytest"},
                        "outcome": "success",
                        "helpful": True,
                        "verified": True,
                        "verification_exit_code": 0,
                        "verification_output_sha256": "sha256:" + "3" * 64,
                        "trusted_tenant_id": "tenant-identity-sha256:" + "4" * 64,
                        "receipt_id": "outcome-sha256:" + "5" * 64,
                    },
                    {
                        "example_id": "gate-failure-2",
                        "pack_id": "systematic-debugging",
                        "task_class": "unknown:no-confident-match",
                        "intervention_id": "intervention-sha256:" + "6" * 64,
                        "guidance": {"ACTION": "No confident match", "STOP": "Do not force weak guidance", "VERIFY": "pytest"},
                        "outcome": "failure",
                        "helpful": False,
                        "verified": True,
                        "verification_exit_code": 1,
                        "verification_output_sha256": "sha256:" + "6" * 64,
                        "trusted_tenant_id": "tenant-identity-sha256:" + "7" * 64,
                        "receipt_id": "outcome-sha256:" + "8" * 64,
                    },
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "eval/pack_optimizer_gate.py",
            "--pack",
            "systematic-debugging",
            "--pack-file",
            str(pack_path),
            "--taskset",
            str(taskset),
            "--examples-file",
            str(examples),
            "--output-dir",
            str(output_root),
            "--snapshot",
            str(snapshot),
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    data = json.loads(result.stdout)
    assert data["success"] is True
    assert data["gate"] == "pack_optimizer"
    assert data["recommendation"] == "eligible_for_manual_review"
    assert snapshot.exists()
    snapshot_data = json.loads(snapshot.read_text(encoding="utf-8"))
    assert snapshot_data["candidate_id"] == data["candidate_id"]
    assert snapshot_data["first_10_claim"] is False
    assert snapshot_data["global_promotion_allowed"] is False

    candidate_gate = subprocess.run(
        [
            sys.executable,
            "eval/pack_optimizer_gate.py",
            "--candidate",
            data["candidate_id"],
            "--pack-file",
            str(pack_path),
            "--taskset",
            str(taskset),
            "--examples-file",
            str(examples),
            "--output-dir",
            str(output_root),
            "--snapshot",
            str(tmp_path / "candidate-snapshot.json"),
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert candidate_gate.returncode == 0, candidate_gate.stderr + candidate_gate.stdout
    assert json.loads(candidate_gate.stdout)["success"] is True

    tampered_pack = tmp_path / "tampered-pack.yaml"
    tampered_pack.write_text(pack_path.read_text(encoding="utf-8") + "# local drift\n", encoding="utf-8")
    forged_gate = subprocess.run(
        [
            sys.executable,
            "eval/pack_optimizer_gate.py",
            "--candidate",
            data["candidate_id"],
            "--pack-file",
            str(tampered_pack),
            "--taskset",
            str(taskset),
            "--examples-file",
            str(examples),
            "--output-dir",
            str(output_root),
            "--snapshot",
            str(tmp_path / "forged-snapshot.json"),
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert forged_gate.returncode == 1
    forged = json.loads(forged_gate.stdout)
    assert forged["success"] is False
    assert "baseline" in forged["error"]
