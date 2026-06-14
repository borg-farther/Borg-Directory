"""CI gate for the reproducible matcher recall/precision harness (issue #9).

These tests replace the prior un-gated, hand-asserted "recall 0.57" prose. They
make three guarantees on every commit:

  1. PRECISION IS A HARD FLOOR — the matcher is never confidently wrong
     (precision == 1.0, fp == 0). A change that introduces a confident-wrong
     match fails CI.
  2. RECALL CANNOT SILENTLY REGRESS — overall recall stays at or above the
     committed baseline snapshot. Improvements are allowed (refresh the
     snapshot); regressions fail.
  3. THE NUMBER CANNOT BE GAMED BY DELETING HARD CASES — the labelled set keeps
     a minimum size and keeps conversational cases (the issue #9 gap).
"""

from __future__ import annotations

import json
import os

import pytest

from eval import recall_harness


def _snapshot():
    with open(recall_harness.SNAPSHOT_PATH) as fh:
        return json.load(fh)


def test_harness_is_deterministic():
    assert recall_harness.run() == recall_harness.run()


def test_precision_is_a_hard_floor_never_confidently_wrong():
    report = recall_harness.run()
    assert report["overall"]["fp"] == 0, (
        "matcher produced a confident-wrong match (false positive); "
        "precision is the safety invariant and must stay perfect"
    )
    assert report["overall"]["precision"] == 1.0


def test_recall_does_not_regress_below_baseline():
    report = recall_harness.run()
    baseline = _snapshot()
    assert report["overall"]["recall"] >= baseline["overall"]["recall"], (
        f"overall recall regressed: {report['overall']['recall']} "
        f"< baseline {baseline['overall']['recall']} — refresh the snapshot only "
        f"if recall went UP"
    )


def test_conversational_gap_is_measured_and_not_hidden():
    report = recall_harness.run()
    # The whole point of the harness: conversational phrasing is reported as its
    # own number so the issue #9 gap can never be averaged away. We assert the
    # bucket exists and is populated, not a specific value.
    assert "conversational" in report["by_phrasing"]
    conv = report["by_phrasing"]["conversational"]
    assert conv["tp"] + conv["fn"] >= 10, "too few conversational should-match cases to measure the gap"


def test_labelled_set_minimum_size_and_composition():
    report = recall_harness.run()
    assert report["case_count"] >= 30, "labelled set must keep >=30 cases (no gaming by deletion)"
    assert report["control_count"] >= 5, "must keep should-not-match controls for precision/FP discipline"


def test_snapshot_is_in_sync_with_metrics():
    # Guards against a stale committed baseline drifting from the live harness.
    report = recall_harness.run()
    baseline = _snapshot()
    assert report["case_count"] == baseline["case_count"]
    assert report["overall"]["precision"] == baseline["overall"]["precision"]
