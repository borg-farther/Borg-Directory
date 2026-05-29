from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import borg.cli as cli_module


def capture_main(args: list[str]) -> tuple[int, str, str]:
    sys.argv = ["borg"] + args
    captured_out = ""
    captured_err = ""

    def fake_stdout_write(s):
        nonlocal captured_out
        captured_out += str(s)

    def fake_stderr_write(s):
        nonlocal captured_err
        captured_err += str(s)

    try:
        with patch.object(sys, "stdout", MagicMock(wraps=sys.stdout, write=fake_stdout_write)), patch.object(
            sys, "stderr", MagicMock(wraps=sys.stderr, write=fake_stderr_write)
        ):
            code = cli_module.main()
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1

    return code, captured_out, captured_err


def _write_pack(path: Path) -> None:
    path.write_text(
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
  evidence: Local optimizer CLI fixture with schema-valid workflow pack fields.
  failure_cases:
    - Missing exact failure text.
""".strip()
        + "\n",
        encoding="utf-8",
    )


def _write_taskset(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "taskset_id": "cli-smoke",
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
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_examples_file(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "examples": [
                    {
                        "example_id": "cli-success",
                        "pack_id": "systematic-debugging",
                        "task_class": "python:modulenotfounderror",
                        "intervention_id": "intervention-sha256:" + "1" * 64,
                        "guidance": {
                            "ACTION": "Install the missing package in the active environment.",
                            "STOP": "Do not use sudo pip.",
                            "VERIFY": "python -c 'import flask'",
                        },
                        "outcome": "success",
                        "helpful": True,
                        "verified": True,
                        "verification_exit_code": 0,
                        "verification_output_sha256": "sha256:" + "a" * 64,
                        "trusted_tenant_id": "tenant-identity-sha256:" + "b" * 64,
                        "receipt_id": "outcome-sha256:" + "c" * 64,
                    },
                    {
                        "example_id": "cli-failure",
                        "pack_id": "systematic-debugging",
                        "task_class": "unknown:no-confident-match",
                        "intervention_id": "intervention-sha256:" + "2" * 64,
                        "guidance": {
                            "ACTION": "No confident match should have been returned.",
                            "STOP": "Do not force weak guidance.",
                            "VERIFY": "rerun with exact failure output",
                        },
                        "outcome": "failure",
                        "helpful": False,
                        "verified": True,
                        "verification_exit_code": 1,
                        "verification_output_sha256": "sha256:" + "d" * 64,
                        "trusted_tenant_id": "tenant-identity-sha256:" + "e" * 64,
                        "receipt_id": "outcome-sha256:" + "f" * 64,
                    },
                    {
                        "example_id": "cli-success-2",
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
                        "example_id": "cli-failure-2",
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
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_optimize_pack_cli_dry_run_json(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    taskset = tmp_path / "taskset.json"
    examples_file = tmp_path / "examples.json"
    output_root = tmp_path / "pack_optimizer"
    _write_pack(pack_path)
    _write_taskset(taskset)
    _write_examples_file(examples_file)

    code, out, err = capture_main(
        [
            "optimize-pack",
            "systematic-debugging",
            "--taskset",
            str(taskset),
            "--pack-file",
            str(pack_path),
            "--examples-file",
            str(examples_file),
            "--output-dir",
            str(output_root),
            "--local-only",
            "--json",
        ]
    )

    data = json.loads(out)
    assert code == 0
    assert data["success"] is True
    assert data["candidate_id"].startswith("packopt-sha256:")
    assert data["local_only"] is True
    assert Path(data["output_dir"]).exists()
    assert err == ""


def test_optimize_pack_cli_default_loads_bundled_workflow_pack_uri_id(tmp_path):
    taskset = tmp_path / "taskset.json"
    examples_file = tmp_path / "examples.json"
    output_root = tmp_path / "pack_optimizer"
    _write_taskset(taskset)
    _write_examples_file(examples_file)

    code, out, err = capture_main(
        [
            "optimize-pack",
            "systematic-debugging",
            "--taskset",
            str(taskset),
            "--examples-file",
            str(examples_file),
            "--output-dir",
            str(output_root),
            "--local-only",
            "--json",
        ]
    )

    data = json.loads(out)
    assert code == 0
    assert data["success"] is True
    assert data["candidate_id"].startswith("packopt-sha256:")
    assert err == ""


def test_optimize_pack_cli_inspect_and_global_apply_block(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    taskset = tmp_path / "taskset.json"
    examples_file = tmp_path / "examples.json"
    output_root = tmp_path / "pack_optimizer"
    _write_pack(pack_path)
    _write_taskset(taskset)
    _write_examples_file(examples_file)

    code, out, err = capture_main(
        [
            "optimize-pack",
            "systematic-debugging",
            "--taskset",
            str(taskset),
            "--pack-file",
            str(pack_path),
            "--examples-file",
            str(examples_file),
            "--output-dir",
            str(output_root),
            "--local-only",
            "--json",
        ]
    )
    assert code == 0
    candidate_id = json.loads(out)["candidate_id"]

    code, out, err = capture_main(["optimize-pack", "inspect", candidate_id, "--output-dir", str(output_root), "--json"])
    inspected = json.loads(out)
    assert code == 0
    assert inspected["candidate_id"] == candidate_id
    assert inspected["selection_score"]["recommendation"] == "eligible_for_manual_review"
    assert inspected["source_verified"] is False
    assert inspected["manual_review_eligibility"] == "source_verification_required"

    code, out, err = capture_main([
        "optimize-pack",
        "inspect",
        candidate_id,
        "--pack-file",
        str(pack_path),
        "--taskset",
        str(taskset),
        "--examples-file",
        str(examples_file),
        "--output-dir",
        str(output_root),
        "--json",
    ])
    source_verified = json.loads(out)
    assert code == 0
    assert source_verified["source_verified"] is True
    assert source_verified["manual_review_eligibility"] == "eligible_for_manual_review"

    code, out, err = capture_main(
        ["optimize-pack", "apply", candidate_id, "--pack-file", str(pack_path), "--output-dir", str(output_root), "--scope", "global", "--json"]
    )
    blocked = json.loads(out)
    assert code == 1
    assert blocked["success"] is False
    assert "local-only" in blocked["error"]

    code, out, err = capture_main(["optimize-pack", "apply", candidate_id, "--output-dir", str(output_root), "--json"])
    missing_pack_file = json.loads(out)
    assert code == 1
    assert missing_pack_file["success"] is False
    assert "--pack-file" in missing_pack_file["error"]


def test_optimize_pack_cli_accepts_top_level_examples_list(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    taskset = tmp_path / "taskset.json"
    examples_file = tmp_path / "examples.json"
    output_root = tmp_path / "pack_optimizer"
    _write_pack(pack_path)
    _write_taskset(taskset)
    _write_examples_file(examples_file)
    payload = json.loads(examples_file.read_text(encoding="utf-8"))
    examples_file.write_text(json.dumps(payload["examples"], indent=2) + "\n", encoding="utf-8")

    code, out, err = capture_main(
        [
            "optimize-pack",
            "systematic-debugging",
            "--taskset",
            str(taskset),
            "--pack-file",
            str(pack_path),
            "--examples-file",
            str(examples_file),
            "--output-dir",
            str(output_root),
            "--json",
        ]
    )

    data = json.loads(out)
    assert code == 0
    assert data["success"] is True
    assert err == ""
