from __future__ import annotations

import json
from pathlib import Path

from borg.core.pack_optimizer import run_pack_optimizer
from borg.core.pack_optimizer_rejections import RejectedEditMemory
from tests.optimizer.test_pack_optimizer_contract import _examples, _write_pack, _write_taskset


def _ops(candidate_dir: Path, filename: str) -> list[str]:
    data = json.loads((candidate_dir / filename).read_text(encoding="utf-8"))
    key = "edits" if filename == "accepted_edits.json" else "rejections"
    return [item["op"] for item in data[key]]


def test_rejected_edit_memory_skips_repeated_candidate_ops(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    memory_path = tmp_path / "rejected-edits.jsonl"
    memory = RejectedEditMemory(memory_path)
    memory.record_rejection(
        pack_id="systematic-debugging",
        op="tighten_no_confident_match_rule",
        anchor="NO_CONFIDENT_MATCH",
        reason="prior selection regression",
        candidate_id="packopt-sha256:" + "0" * 64,
        supporting_receipt_ids=["outcome-sha256:" + "1" * 64],
    )

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
        rejected_memory_path=memory_path,
    )

    candidate_dir = Path(result.output_dir)
    assert result.success is True
    assert "tighten_no_confident_match_rule" not in _ops(candidate_dir, "accepted_edits.json")
    assert "Tighten NO_CONFIDENT_MATCH" not in (candidate_dir / "candidate_pack.preview").read_text(encoding="utf-8")
    optimizer_run = json.loads((candidate_dir / "optimizer_run.json").read_text(encoding="utf-8"))
    assert optimizer_run["rejected_memory_consulted"] is True
    assert optimizer_run["rejected_memory_skipped_edits"][0]["op"] == "tighten_no_confident_match_rule"
    assert "prior selection regression" in optimizer_run["rejected_memory_skipped_edits"][0]["reason"]


def test_failed_selection_candidates_are_persisted_to_rejected_edit_memory(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset, hard_failures=["selection_score_regression"])
    memory_path = tmp_path / "rejected-edits.jsonl"

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
        rejected_memory_path=memory_path,
    )

    assert result.success is False
    records = RejectedEditMemory(memory_path).list_rejections(pack_id="systematic-debugging")
    assert records
    assert {record["reason"] for record in records} == {"selection_score_regression"}
    assert all(record["candidate_id"] == result.candidate_id for record in records)
    assert all(record["prevent_repeat_key"].startswith("rejected-edit-sha256:") for record in records)


def test_all_rejected_memory_skipped_edits_blocks_noop_candidate(tmp_path):
    pack_path = tmp_path / "pack.yaml"
    _write_pack(pack_path)
    taskset = tmp_path / "taskset.json"
    _write_taskset(taskset)
    memory_path = tmp_path / "rejected-edits.jsonl"
    memory = RejectedEditMemory(memory_path)
    for op, anchor in (
        ("tighten_no_confident_match_rule", "NO_CONFIDENT_MATCH"),
        ("add_verification_step", "VERIFY"),
        ("tighten_stop_rule", "STOP"),
    ):
        memory.record_rejection(
            pack_id="systematic-debugging",
            op=op,
            anchor=anchor,
            reason="prior selection regression",
            candidate_id="packopt-sha256:" + "2" * 64,
        )

    result = run_pack_optimizer(
        pack_id="systematic-debugging",
        pack_path=pack_path,
        taskset_path=taskset,
        output_root=tmp_path / "out",
        examples=_examples(),
        local_only=True,
        rejected_memory_path=memory_path,
    )

    candidate_dir = Path(result.output_dir)
    preview = (candidate_dir / "candidate_pack.preview").read_text(encoding="utf-8")
    assert result.success is False
    assert result.recommendation == "reject"
    assert "all_candidate_edits_previously_rejected" in result.hard_failures
    assert "optimizer_candidate_notes" not in preview
    assert _ops(candidate_dir, "accepted_edits.json") == []
