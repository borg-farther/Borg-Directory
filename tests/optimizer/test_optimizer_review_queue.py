from __future__ import annotations

import json
from pathlib import Path

import pytest

from borg.core.optimizer_review_queue import build_review_packet
from borg.core.pack_optimizer import run_pack_optimizer
from tests.optimizer.test_pack_optimizer_contract import _examples, _write_pack, _write_taskset


def test_optimizer_review_packet_requires_source_verification_before_eligibility(tmp_path):
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

    artifact_only = build_review_packet(Path(result.output_dir))

    assert artifact_only["schema_version"] == "1.0"
    assert artifact_only["candidate_id"] == result.candidate_id
    assert artifact_only["source_verified"] is False
    assert artifact_only["manual_review_eligibility"] == "source_verification_required"
    assert artifact_only["decision"] == "source_verification_required"
    assert artifact_only["first_10_claim"] is False
    assert artifact_only["global_promotion_allowed"] is False
    assert artifact_only["diff"]["patch_sha256"].startswith("sha256:")
    assert artifact_only["score"]["score_delta"] == result.score_delta
    assert artifact_only["safety"]["privacy_blocked"] is False
    assert artifact_only["safety"]["prompt_injection_blocked"] is False
    assert artifact_only["edits"]["accepted_count"] > 0
    assert artifact_only["edits"]["rejected_count"] == 0
    assert "Run source-bound inspect" in artifact_only["next_actions"][0]

    source_verified = build_review_packet(Path(result.output_dir), source_verified=True)

    assert source_verified["source_verified"] is True
    assert source_verified["manual_review_eligibility"] == "eligible_for_manual_review"
    assert source_verified["decision"] == "awaiting_maintainer_review"
    assert "Confirm source-bound inspect/apply was run" in source_verified["reviewer_checklist"]


def test_optimizer_review_packet_for_rejected_candidate_is_not_eligible(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset, hard_failures=["unsafe_command_regression"])
    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
    )

    packet = build_review_packet(Path(result.output_dir), source_verified=True)

    assert result.success is False
    assert packet["manual_review_eligibility"] == "blocked"
    assert packet["decision"] == "reject"
    assert packet["edits"]["accepted_count"] == 0
    assert packet["edits"]["rejected_count"] > 0
    assert "unsafe_command_regression" in packet["score"]["hard_failures"]


def test_optimizer_review_packet_rejects_patch_and_preview_symlinks(tmp_path):
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
    outside = tmp_path / "outside.txt"
    outside.write_text("do not hash me\n", encoding="utf-8")

    (candidate_dir / "candidate_pack.patch").unlink()
    (candidate_dir / "candidate_pack.patch").symlink_to(outside)

    with pytest.raises(ValueError, match="must not be a symlink"):
        build_review_packet(candidate_dir, source_verified=True)
