from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from borg.core.pack_optimizer import (
    PackOptimizer,
    _candidate_id_from_material,
    _canonical_json,
    _privacy_artifact_from_scan,
    _prompt_artifact_from_scan,
    _sha256_ref,
    run_pack_optimizer,
    scan_candidate_text,
)
from borg.core.pack_optimizer_scoring import compare_baseline_candidate
from borg.core.pack_optimizer_schemas import OptimizerExample


REQUIRED_ARTIFACTS = {
    "candidate_pack.patch",
    "candidate_pack.preview",
    "accepted_edits.json",
    "rejected_edits.json",
    "training_manifest.json",
    "selection_score.json",
    "privacy_scan.json",
    "prompt_injection_scan.json",
    "candidate_integrity.json",
    "optimizer_run.json",
}


def _write_pack(path: Path) -> str:
    text = """
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
  evidence: Local optimizer test fixture with schema-valid workflow pack fields.
  failure_cases:
    - Missing exact failure text.
""".strip() + "\n"
    path.write_text(text, encoding="utf-8")
    return text


def _write_taskset(path: Path, *, candidate_score: float = 0.95, baseline_score: float = 0.61, hard_failures: list[str] | None = None) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "taskset_id": "systematic-debugging-selection-smoke",
                "baseline_metrics": {
                    "verified_success": baseline_score,
                    "action_stop_verify_relevance": 0.60,
                    "dead_ends_avoided": 0.20,
                    "no_confident_match_precision": 0.70,
                    "verification_quality": 0.70,
                    "token_or_tool_efficiency": 0.40,
                },
                "candidate_metrics": {
                    "verified_success": candidate_score,
                    "action_stop_verify_relevance": 0.95,
                    "dead_ends_avoided": 0.95,
                    "no_confident_match_precision": 0.95,
                    "verification_quality": 0.95,
                    "token_or_tool_efficiency": 0.80,
                },
                "hard_failures": hard_failures or [],
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


def _example(idx: int, *, helpful: bool, dead_ends: int = 0) -> OptimizerExample:
    hex_char = format(idx, "x")[-1]
    return OptimizerExample(
        example_id=f"ex-{'success' if helpful else 'failure'}-{idx}",
        pack_id="systematic-debugging",
        task_class="python:modulenotfounderror" if helpful else "unknown:no-confident-match",
        intervention_id="intervention-sha256:" + hex_char * 64,
        action_summary="Install the missing package in the active environment." if helpful else "No confident match should have been returned.",
        stop_summary="Do not reinstall Python or use sudo pip." if helpful else "Do not force weak unrelated guidance.",
        verify_summary="python -c 'import flask'" if helpful else "rerun with exact failing output",
        outcome="success" if helpful else "failure",
        helpful=helpful,
        verified=True,
        verification_exit_code=0 if helpful else 1,
        verification_output_sha256="sha256:" + hex_char * 64,
        trusted_tenant_id="tenant-identity-sha256:" + format(idx + 8, "x")[-1] * 64,
        receipt_id="outcome-sha256:" + format(idx + 12, "x")[-1] * 64,
        dead_ends_avoided=dead_ends,
    )


def _examples() -> list[OptimizerExample]:
    return [
        _example(1, helpful=True, dead_ends=2),
        _example(2, helpful=False),
        _example(3, helpful=True, dead_ends=1),
        _example(4, helpful=False),
    ]


def test_optimizer_dry_run_writes_required_artifacts(tmp_path):
    pack_path = tmp_path / "systematic-debugging.workflow.yaml"
    original = _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
        max_edits=4,
    )

    assert result.success is True
    assert result.candidate_id.startswith("packopt-sha256:")
    candidate_dir = Path(result.output_dir)
    assert ":" not in candidate_dir.name
    assert result.candidate_id.replace(":", "_") == candidate_dir.name
    assert REQUIRED_ARTIFACTS.issubset({p.name for p in candidate_dir.iterdir()})
    assert pack_path.read_text(encoding="utf-8") == original

    optimizer_run = json.loads((candidate_dir / "optimizer_run.json").read_text(encoding="utf-8"))
    integrity = json.loads((candidate_dir / "candidate_integrity.json").read_text(encoding="utf-8"))
    assert optimizer_run["local_only"] is True
    assert optimizer_run["first_10_claim"] is False
    assert optimizer_run["global_promotion_allowed"] is False
    assert integrity["candidate_id"] == result.candidate_id
    assert integrity["candidate_id_material"]["train_example_ids"] == optimizer_run["train_examples_used_for_candidate"]
    assert "examples" not in optimizer_run
    assert {ex["example_id"] for ex in optimizer_run["train_examples"]} == set(optimizer_run["train_examples_used_for_candidate"])
    assert {ref["example_id"] for ref in optimizer_run["selection_example_refs"]} == set(optimizer_run["selection_examples_withheld_from_candidate"])
    assert all(set(ref) == {"example_id", "artifact_sha256"} for ref in optimizer_run["selection_example_refs"])
    assert all(set(ref) == {"example_id", "artifact_sha256"} for ref in optimizer_run["hidden_example_refs"])
    assert integrity["candidate_id_material"]["selection_evidence_sha256"] == integrity["selection_evidence_sha256"]


def test_relative_output_dir_does_not_leak_absolute_workspace_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=Path("out"),
        examples=_examples(),
        local_only=True,
    )

    assert result.output_dir.startswith("out/")
    assert str(tmp_path) not in result.output_dir
    optimizer_run = json.loads((Path(result.output_dir) / "optimizer_run.json").read_text(encoding="utf-8"))
    assert optimizer_run["output_dir"] == result.output_dir
    assert str(tmp_path) not in json.dumps(optimizer_run)


def test_optimizer_refuses_symlinked_artifact_paths(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    output_root = tmp_path / "out"
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=output_root,
        examples=_examples(),
        local_only=True,
    )
    victim = tmp_path / "victim.txt"
    victim.write_text("unchanged", encoding="utf-8")
    symlink_path = Path(result.output_dir) / "optimizer_run.json"
    symlink_path.unlink()
    symlink_path.symlink_to(victim)

    with pytest.raises(ValueError, match="symlink artifact path"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=output_root,
            examples=_examples(),
            local_only=True,
        )
    assert victim.read_text(encoding="utf-8") == "unchanged"


def test_optimizer_apply_refuses_symlink_pack_target(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    link_path = tmp_path / "linked-pack.yaml"
    link_path.symlink_to(pack_path)

    with pytest.raises(ValueError, match="must not be a symlink"):
        PackOptimizer(output_root=tmp_path / "out").apply_candidate(
            result.candidate_id,
            pack_path=link_path,
            taskset_path=taskset,
            examples=_examples(),
            scope="local",
        )


def test_prebuilt_optimizer_examples_are_sanitized_before_artifact_write(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples()
    examples[0] = replace(examples[0], action_summary="RAW_USER_CHAT_SENTINEL private terminal transcript should be redacted")

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=examples,
        local_only=True,
        max_edits=4,
    )

    optimizer_run = (Path(result.output_dir) / "optimizer_run.json").read_text(encoding="utf-8")
    assert "RAW_USER_CHAT_SENTINEL" not in optimizer_run
    assert "[REDACTED_RAW_TRAJECTORY]" in optimizer_run


def test_optimizer_rejects_duplicate_example_ids_before_split(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples()
    examples[1] = replace(examples[1], example_id=examples[0].example_id)

    with pytest.raises(ValueError, match="duplicate_example_id"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=examples,
            local_only=True,
            max_edits=4,
        )


def test_optimizer_rejects_duplicate_receipt_ids_before_split(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples()
    examples[1] = replace(examples[1], receipt_id=examples[0].receipt_id)

    with pytest.raises(ValueError, match="duplicate_receipt_id"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=examples,
            local_only=True,
            max_edits=4,
        )


def test_optimizer_rejects_duplicate_intervention_ids_before_split(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples()
    examples[1] = replace(examples[1], intervention_id=examples[0].intervention_id)

    with pytest.raises(ValueError, match="duplicate_intervention_id"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=examples,
            local_only=True,
            max_edits=4,
        )


def test_optimizer_rejects_malformed_selection_taskset(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "empty-taskset.json"
    taskset.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="selection taskset requires"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=_examples(),
            local_only=True,
            max_edits=4,
        )


def test_optimizer_rejects_pack_level_first10_or_global_claims(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    original = _write_pack(pack_path)
    pack_path.write_text(original + "claim_boundary_notes: |\n  first_10_claim: true\n  global_promotion_allowed: true\n  public_lift_claim: true\n", encoding="utf-8")
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    with pytest.raises(ValueError, match="first-10|global promotion"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=_examples(),
            local_only=True,
            max_edits=4,
        )


def test_optimizer_requires_train_selection_and_hidden_split(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples() + [_example(5, helpful=True), _example(6, helpful=False)]

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=examples,
        local_only=True,
    )

    manifest = json.loads((Path(result.output_dir) / "training_manifest.json").read_text(encoding="utf-8"))
    assert manifest["train_example_ids"]
    assert manifest["selection_example_ids"]
    assert manifest["hidden_example_ids"]
    assert set(manifest["train_example_ids"]).isdisjoint(manifest["selection_example_ids"])
    assert set(manifest["train_example_ids"]).isdisjoint(manifest["hidden_example_ids"])
    assert "selection withheld from proposal" in manifest["split_method"]


def test_selection_examples_are_withheld_from_candidate_receipts(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples()

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=examples,
        local_only=True,
    )

    candidate_dir = Path(result.output_dir)
    manifest = json.loads((candidate_dir / "training_manifest.json").read_text(encoding="utf-8"))
    accepted = json.loads((candidate_dir / "accepted_edits.json").read_text(encoding="utf-8"))
    selection_receipts = {ex.receipt_id for ex in examples if ex.example_id in set(manifest["selection_example_ids"])}
    accepted_receipts = {rid for edit in accepted["edits"] for rid in edit["supporting_receipt_ids"]}
    assert accepted_receipts.isdisjoint(selection_receipts)


def test_optimizer_rejects_candidate_without_strict_selection_improvement(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset, candidate_score=0.40, baseline_score=0.70)

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )

    assert result.success is False
    score = json.loads((Path(result.output_dir) / "selection_score.json").read_text(encoding="utf-8"))
    rejected = json.loads((Path(result.output_dir) / "rejected_edits.json").read_text(encoding="utf-8"))
    accepted = json.loads((Path(result.output_dir) / "accepted_edits.json").read_text(encoding="utf-8"))
    assert score["recommendation"] == "reject"
    assert "selection_score_not_strictly_better" in score["hard_failures"]
    assert rejected["candidate_id"] == result.candidate_id
    assert rejected["rejections"]
    assert all(item["created_at"].endswith("Z") for item in rejected["rejections"])
    assert all(item["prevent_repeat_key"].startswith("sha256:") for item in rejected["rejections"])
    assert accepted["edits"] == []


def test_optimizer_apply_local_requires_accepted_candidate(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    original = _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )

    optimizer = PackOptimizer(output_root=tmp_path / "out")
    applied = optimizer.apply_candidate(result.candidate_id, pack_path=pack_path, taskset_path=taskset, examples=_examples(), scope="local")

    assert applied["success"] is True
    assert applied["scope"] == "local"
    assert pack_path.read_text(encoding="utf-8") != original
    assert "Borg local pack optimizer candidate" in pack_path.read_text(encoding="utf-8")


def test_optimizer_manual_review_requires_source_verification(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )

    optimizer = PackOptimizer(output_root=tmp_path / "out")
    artifact_only = optimizer.inspect_candidate(result.candidate_id)
    assert artifact_only["source_verified"] is False
    assert artifact_only["manual_review_eligibility"] == "source_verification_required"

    verified = optimizer.verify_candidate_against_sources(
        result.candidate_id,
        pack_path=pack_path,
        taskset_path=taskset,
        examples=_examples(),
    )
    assert verified["source_verified"] is True
    assert verified["manual_review_eligibility"] == "eligible_for_manual_review"


def test_optimizer_rejects_schema_invalid_workflow_pack(tmp_path):
    pack_path = tmp_path / "invalid-pack.yaml"
    pack_path.write_text("type: workflow_pack\nid: systematic-debugging\nproblem_class: debugging\n", encoding="utf-8")
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    with pytest.raises(ValueError, match="workflow pack schema validation|workflow pack proof validation"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=_examples(),
            local_only=True,
        )


def test_optimizer_inspect_rejects_accepted_edit_tampering(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    accepted_path = Path(result.output_dir) / "accepted_edits.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted["edits"][0]["supporting_receipt_ids"] = ["outcome-sha256:" + "f" * 64]
    accepted["edits"][0]["rationale"] = "tampered manual-review evidence"
    accepted_path.write_text(json.dumps(accepted, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="edits artifact hash"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_moving_accepted_edits_to_rejected_buffer(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    candidate_dir = Path(result.output_dir)
    accepted_path = candidate_dir / "accepted_edits.json"
    rejected_path = candidate_dir / "rejected_edits.json"
    integrity_path = candidate_dir / "candidate_integrity.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    assert accepted["edits"]
    rejected["rejections"] = accepted["edits"]
    accepted["edits"] = []
    accepted_path.write_text(json.dumps(accepted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rejected_path.write_text(json.dumps(rejected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    integrity["accepted_edits_sha256"] = _sha256_ref(_canonical_json(accepted))
    integrity["rejected_edits_sha256"] = _sha256_ref(_canonical_json(rejected))
    integrity_path.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="eligible candidate must have accepted edits|rejected edit artifact shape mismatch"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_top_level_accepted_buffer_metadata_forgery(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    candidate_dir = Path(result.output_dir)
    accepted_path = candidate_dir / "accepted_edits.json"
    integrity_path = candidate_dir / "candidate_integrity.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted["source_verified"] = True
    accepted["reviewer_attestation"] = "source_verified_by_admin"
    accepted_path.write_text(json.dumps(accepted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    integrity["accepted_edits_sha256"] = _sha256_ref(_canonical_json(accepted))
    integrity_path.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="accepted_edits artifact shape mismatch"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_top_level_rejected_buffer_metadata_forgery(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset, candidate_score=0.40, baseline_score=0.70)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    candidate_dir = Path(result.output_dir)
    rejected_path = candidate_dir / "rejected_edits.json"
    integrity_path = candidate_dir / "candidate_integrity.json"
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    rejected["source_verified"] = True
    rejected["reviewer_attestation"] = "source_verified_by_admin"
    rejected_path.write_text(json.dumps(rejected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    integrity["rejected_edits_sha256"] = _sha256_ref(_canonical_json(rejected))
    integrity_path.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="rejected_edits artifact shape mismatch"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_self_consistent_extra_accepted_edit_metadata(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    candidate_dir = Path(result.output_dir)
    accepted_path = candidate_dir / "accepted_edits.json"
    integrity_path = candidate_dir / "candidate_integrity.json"
    accepted = json.loads(accepted_path.read_text(encoding="utf-8"))
    accepted["edits"][0]["reviewer_attestation"] = "source_verified_by_admin"
    accepted_path.write_text(json.dumps(accepted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    integrity["accepted_edits_sha256"] = _sha256_ref(_canonical_json(accepted))
    integrity_path.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="accepted edit artifact shape mismatch"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_self_consistent_rejected_edit_metadata_forgery(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset, candidate_score=0.40, baseline_score=0.70)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    candidate_dir = Path(result.output_dir)
    rejected_path = candidate_dir / "rejected_edits.json"
    integrity_path = candidate_dir / "candidate_integrity.json"
    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
    assert rejected["rejections"]
    rejected["rejections"][0]["reason"] = "forged: safe to retry globally"
    rejected_path.write_text(json.dumps(rejected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    integrity["rejected_edits_sha256"] = _sha256_ref(_canonical_json(rejected))
    integrity_path.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="rejected edit reason metadata mismatch"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_full_selection_or_hidden_ref_artifact_tampering(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    optimizer_run_path = Path(result.output_dir) / "optimizer_run.json"
    optimizer_run = json.loads(optimizer_run_path.read_text(encoding="utf-8"))
    optimizer_run["selection_example_refs"][0]["raw_artifact"] = {"example_id": "leaked-selection", "outcome": "success"}
    optimizer_run_path.write_text(json.dumps(optimizer_run, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="selection example refs must be ref-only"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_rejects_full_hidden_ref_artifact_tampering(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    examples = _examples() + [_example(5, helpful=True), _example(6, helpful=False)]
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=examples,
        local_only=True,
    )
    optimizer_run_path = Path(result.output_dir) / "optimizer_run.json"
    optimizer_run = json.loads(optimizer_run_path.read_text(encoding="utf-8"))
    assert optimizer_run["hidden_example_refs"]
    optimizer_run["hidden_example_refs"][0]["raw_artifact"] = {"example_id": "leaked-hidden", "outcome": "success"}
    optimizer_run_path.write_text(json.dumps(optimizer_run, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hidden example refs must be ref-only"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_inspect_rejects_illegal_claim_tampering(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    manifest_path = Path(result.output_dir) / "training_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["first_10_claim"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="first-10"):
        PackOptimizer(output_root=tmp_path / "out").inspect_candidate(result.candidate_id)


def test_optimizer_apply_rejects_self_consistent_forged_rewrite(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    baseline = _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )

    original_dir = Path(result.output_dir)
    integrity = json.loads((original_dir / "candidate_integrity.json").read_text(encoding="utf-8"))
    material = dict(integrity["candidate_id_material"])
    selection_evidence = integrity["selection_evidence"]
    forged_preview = baseline + "\n# Borg local pack optimizer candidate — local-only, not global promotion.\noptimizer_candidate_notes:\n  - \"arbitrary forged rewrite\"\n"
    material["candidate_pack_sha256"] = _sha256_ref(forged_preview)
    forged_id = _candidate_id_from_material(material)
    forged_dir = tmp_path / "out" / forged_id.replace(":", "_")
    forged_dir.mkdir()

    for name in REQUIRED_ARTIFACTS:
        source = original_dir / name
        target = forged_dir / name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    patch_text = "".join([
        "--- systematic-debugging.baseline\n",
        "+++ systematic-debugging.candidate\n",
        "+# forged diff placeholder\n",
    ])
    (forged_dir / "candidate_pack.preview").write_text(forged_preview, encoding="utf-8")
    (forged_dir / "candidate_pack.patch").write_text(patch_text, encoding="utf-8")
    scan = scan_candidate_text(forged_preview)
    score = compare_baseline_candidate(
        {
            "baseline_metrics": selection_evidence["baseline_metrics"],
            "candidate_metrics": selection_evidence["candidate_metrics"],
            "controls": selection_evidence["controls"],
            "hard_failures": selection_evidence["hard_failures"],
        },
        forged_id,
    ).to_artifact()
    integrity.update(
        {
            "candidate_id": forged_id,
            "candidate_id_material": material,
            "candidate_pack_sha256": _sha256_ref(forged_preview),
            "stored_preview_sha256": _sha256_ref(forged_preview),
            "patch_sha256": _sha256_ref(patch_text),
        }
    )
    optimizer_run = json.loads((forged_dir / "optimizer_run.json").read_text(encoding="utf-8"))
    optimizer_run.update({"candidate_id": forged_id, "candidate_pack_sha256": _sha256_ref(forged_preview), "stored_preview_sha256": _sha256_ref(forged_preview)})
    accepted = json.loads((forged_dir / "accepted_edits.json").read_text(encoding="utf-8"))
    accepted["candidate_id"] = forged_id
    for edit in accepted.get("edits", []):
        edit["after_hash"] = _sha256_ref(forged_preview)
    rejected = json.loads((forged_dir / "rejected_edits.json").read_text(encoding="utf-8"))
    rejected["candidate_id"] = forged_id
    privacy = _privacy_artifact_from_scan(forged_id, scan)
    prompt = _prompt_artifact_from_scan(forged_id, scan)
    (forged_dir / "candidate_integrity.json").write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (forged_dir / "optimizer_run.json").write_text(json.dumps(optimizer_run, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (forged_dir / "selection_score.json").write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (forged_dir / "accepted_edits.json").write_text(json.dumps(accepted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (forged_dir / "rejected_edits.json").write_text(json.dumps(rejected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (forged_dir / "privacy_scan.json").write_text(json.dumps(privacy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (forged_dir / "prompt_injection_scan.json").write_text(json.dumps(prompt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    optimizer = PackOptimizer(output_root=tmp_path / "out")
    with pytest.raises(ValueError, match="deterministic optimizer output|target baseline diff|reproducible|edits artifact hash"):
        optimizer.apply_candidate(forged_id, pack_path=pack_path, taskset_path=taskset, examples=_examples(), scope="local")


def test_optimizer_apply_requires_existing_target_and_matching_baseline(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )

    optimizer = PackOptimizer(output_root=tmp_path / "out")
    with pytest.raises(FileNotFoundError, match="must already exist"):
        optimizer.apply_candidate(result.candidate_id, pack_path=tmp_path / "missing-pack.yaml", taskset_path=taskset, examples=_examples(), scope="local")

    pack_path.write_text(pack_path.read_text(encoding="utf-8") + "# local drift\n", encoding="utf-8")
    with pytest.raises(ValueError, match="baseline"):
        optimizer.apply_candidate(result.candidate_id, pack_path=pack_path, taskset_path=taskset, examples=_examples(), scope="local")


def test_optimizer_rejects_score_swapped_candidate_bundle(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )
    assert result.success is True

    score_path = Path(result.output_dir) / "selection_score.json"
    score = json.loads(score_path.read_text(encoding="utf-8"))
    score.update({"recommendation": "eligible_for_manual_review", "hard_failures": [], "candidate_score": 0.10, "score_delta": -0.51})
    score_path.write_text(json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    optimizer = PackOptimizer(output_root=tmp_path / "out")
    with pytest.raises(ValueError, match="selection score"):
        optimizer.apply_candidate(result.candidate_id, pack_path=pack_path, taskset_path=taskset, examples=_examples(), scope="local")


def test_optimizer_rejects_forged_or_path_traversal_candidate(tmp_path):
    optimizer = PackOptimizer(output_root=tmp_path / "out")
    fake_dir = tmp_path / "fakecandidate"
    fake_dir.mkdir()
    (fake_dir / "selection_score.json").write_text('{"recommendation":"eligible_for_manual_review"}', encoding="utf-8")
    (fake_dir / "candidate_pack.preview").write_text("malicious", encoding="utf-8")

    with pytest.raises(ValueError, match="candidate_id"):
        optimizer.inspect_candidate(str(fake_dir))
    with pytest.raises(ValueError, match="candidate_id"):
        optimizer.apply_candidate("../fakecandidate", pack_path=tmp_path / "pack.yaml", taskset_path=tmp_path / "taskset.json", examples=[], scope="local")


def test_optimizer_does_not_allow_too_many_edits_and_honors_bound(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)

    with pytest.raises(ValueError, match="max_edits"):
        run_pack_optimizer(
            pack_id="systematic-debugging",
            pack_path=pack_path,
            taskset_path=taskset,
            output_root=tmp_path / "out",
            examples=_examples(),
            local_only=True,
            max_edits=0,
        )

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "bounded",
        examples=_examples(),
        local_only=True,
        max_edits=2,
    )
    accepted = json.loads((Path(result.output_dir) / "accepted_edits.json").read_text(encoding="utf-8"))
    assert len(accepted["edits"]) <= 2
    assert {edit["op"] for edit in accepted["edits"]} <= {"add_antipattern", "add_verification_step", "tighten_no_confident_match_rule", "tighten_stop_rule"}
    assert all(edit["expected_metric_impact"] for edit in accepted["edits"])
