"""Mechanics test for the Borg readiness/acceptance harness
(``eval/borg_readiness_harness.py``).

Asserts the harness runs, returns a well-formed machine-readable report, and that
every launch-gate whose implementation is already on ``main`` passes. The four
fix-gated checks (documented-API confidence gate D-006, redaction count D-015,
federation kill-switch #27, value legibility #10) go green once their PRs merge;
this test deliberately does not require them, so it is green before and after.
"""

from __future__ import annotations

import os

from eval.borg_readiness_harness import CHECKS, run_harness

# Gates whose code is on main today; these must always pass.
_ALWAYS_GREEN = {
    "local_day_one",
    "matcher_honesty",
    "injection_scoring",
    "crypto_sign_verify_failclosed",
    "convergence_atom_ingest",
}


def _run_isolated():
    """Run the harness without leaking its per-check BORG_HOME mutation."""
    saved = os.environ.get("BORG_HOME")
    try:
        return run_harness()
    finally:
        if saved is None:
            os.environ.pop("BORG_HOME", None)
        else:
            os.environ["BORG_HOME"] = saved


def test_harness_report_is_well_formed() -> None:
    report = _run_isolated()
    assert report["harness"] == "borg_readiness"
    assert len(report["checks"]) == len(CHECKS)
    for check in report["checks"]:
        assert {"name", "gate", "passed", "detail"} <= set(check)
        assert isinstance(check["passed"], bool)
    summary = report["summary"]
    assert summary["total"] == len(report["checks"])
    assert summary["passed"] + summary["failed"] == summary["total"]
    assert report["passed"] == (summary["failed"] == 0)


def test_main_present_gates_pass() -> None:
    by_name = {c["name"]: c for c in _run_isolated()["checks"]}
    for name in _ALWAYS_GREEN:
        assert by_name[name]["passed"], f"{name} must pass on main: {by_name[name]['detail']}"
