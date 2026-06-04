from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from eval import public_self_serve_launch_gate as public_gate

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_GITHUB_INSTALL = "git+https://github.com/borg-farther/Borg-Directory.git@main"
REQUIRED_RESULT_NAMES = [
    "fresh_venv_create",
    "pip_install_git_source",
    "pip_direct_url_agent_borg",
    "pip_show_agent_borg",
    "borg_version",
    "borg_help",
    "borg_rescue_json",
    "borg_doctor_json",
    "borg_generate_systematic_debugging_rules",
    "borg_convert_openclaw_registry",
    "python_api_check",
]


def _current_head() -> str:
    return public_gate._git_output(["rev-parse", "HEAD"])


def _snapshot_payload(**overrides: object) -> dict[str, object]:
    head = _current_head()
    payload: dict[str, object] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "package": "agent-borg",
        "version": "9.9.9",
        "install_source": "github_source",
        "install_target": CANONICAL_GITHUB_INSTALL,
        "source_resolution": {
            "passed": True,
            "resolved_commit": head,
            "expected_commit": head,
            "commit_matches_expected": True,
            "requested_revision": "main",
        },
        "success": True,
        "checkout_import_leakage": {
            "passed": True,
            "installed_file": "/tmp/venv/lib/python/site-packages/borg/__init__.py",
        },
        "results": [{"name": name, "passed": True} for name in REQUIRED_RESULT_NAMES],
        "mcp_stdio_canary": {
            "passed": True,
            "server_info": {"name": "borg-mcp-server", "version": "9.9.9"},
            "required_tools_present": ["borg_observe", "borg_rescue", "borg_runtime_fingerprint", "error_lookup"],
            "alias_value_signal": True,
            "fingerprint_signal": True,
        },
    }
    payload.update(overrides)
    return payload


def _write_snapshot(path: Path, **overrides: object) -> None:
    path.write_text(json.dumps(_snapshot_payload(**overrides)), encoding="utf-8")


def test_github_source_install_canary_script_contract() -> None:
    """GitHub/source self-service must be proven by an executable canary."""
    script = ROOT / "eval" / "run_github_source_install_canary.py"
    assert script.exists(), "missing GitHub source-install canary"
    text = script.read_text(encoding="utf-8")

    required_tokens = [
        CANONICAL_GITHUB_INSTALL,
        "github_source_install_snapshot.json",
        "tempfile.mkdtemp",
        "runtime-cwd",
        "PYTHONPATH",
        "PYTHONNOUSERSITE",
        "PIP_CONFIG_FILE",
        "HOME",
        "BORG_HOME",
        "BORG_DIR",
        "pip_install_git_source",
        "pip_direct_url_agent_borg",
        "direct_url.json",
        "--expected-commit",
        "resolved_commit",
        "source_resolution",
        "borg_version",
        "borg_doctor_json",
        "borg_rescue_json",
        "borg_generate_systematic_debugging_rules",
        "borg_convert_openclaw_registry",
        "python_api_check",
        "mcp_stdio_canary",
        "checkout_import_leakage",
        "BORG_TEST_PACKS_DIR",
        "BORG_MAINTAINER_PACKS_DIR",
        "install_source",
        "github_source",
    ]
    for token in required_tokens:
        assert token in text


def test_public_gate_checks_github_source_snapshot_missing(tmp_path: Path) -> None:
    result = public_gate.github_source_install_check(tmp_path / "missing.json", "9.9.9")

    assert result["passed"] is False
    assert result["exists"] is False
    assert "GitHub source-install" in result["error"]


def test_public_gate_accepts_fresh_github_source_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    _write_snapshot(snapshot)

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is True
    assert result["install_source"] == "github_source"
    assert result["install_target"] == CANONICAL_GITHUB_INSTALL
    assert result["version"] == "9.9.9"
    assert result["checkout_import_leakage_passed"] is True
    assert result["source_resolution_passed"] is True
    assert result["resolved_commit"] == _current_head()
    assert result["missing_required_results"] == []


def test_public_gate_rejects_github_source_snapshot_without_commit_binding(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    _write_snapshot(snapshot, source_resolution={"passed": False})

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is False
    assert result["source_resolution_passed"] is False


def test_public_gate_rejects_github_source_snapshot_resolved_to_old_non_ancestor_sha(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    old_sha = "a" * 40
    _write_snapshot(
        snapshot,
        source_resolution={
            "passed": True,
            "resolved_commit": old_sha,
            "expected_commit": old_sha,
            "commit_matches_expected": True,
            "requested_revision": "main",
        },
    )

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is False
    assert result["source_resolution_passed"] is False
    assert result["source_commit_honesty"]["reason"] == "resolved_commit_not_ancestor_of_head"


def test_public_gate_rejects_github_source_snapshot_with_unrelated_source_changes_since_commit(tmp_path: Path, monkeypatch) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    old_sha = "b" * 40
    _write_snapshot(
        snapshot,
        source_resolution={
            "passed": True,
            "resolved_commit": old_sha,
            "expected_commit": old_sha,
            "commit_matches_expected": True,
            "requested_revision": "main",
        },
    )
    monkeypatch.setattr(
        public_gate,
        "_source_commit_is_honest_for_current_head",
        lambda commit: {
            "passed": False,
            "resolved_commit": commit,
            "head": _current_head(),
            "reason": "ancestor_has_source_or_non_generated_changes",
            "non_generated_paths_since_resolved": ["borg/cli.py"],
        },
    )

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is False
    assert result["source_commit_honesty"]["non_generated_paths_since_resolved"] == ["borg/cli.py"]


def test_public_gate_accepts_github_source_snapshot_from_ancestor_when_only_generated_artifacts_changed(tmp_path: Path, monkeypatch) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    old_sha = "c" * 40
    _write_snapshot(
        snapshot,
        source_resolution={
            "passed": True,
            "resolved_commit": old_sha,
            "expected_commit": old_sha,
            "commit_matches_expected": True,
            "requested_revision": "main",
        },
    )
    monkeypatch.setattr(
        public_gate,
        "_source_commit_is_honest_for_current_head",
        lambda commit: {
            "passed": True,
            "resolved_commit": commit,
            "head": _current_head(),
            "reason": "ancestor_with_only_generated_artifacts",
            "changed_paths_since_resolved": ["eval/github_source_install_snapshot.json"],
        },
    )

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is True
    assert result["source_commit_honesty"]["reason"] == "ancestor_with_only_generated_artifacts"


def test_public_gate_rejects_incomplete_github_source_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    _write_snapshot(snapshot, results=[{"name": "pip_install_git_source", "passed": True}])

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is False
    assert "borg_version" in result["missing_required_results"]
    assert "mcp_stdio_jsonrpc" not in result["missing_required_results"]


def test_public_gate_rejects_non_canonical_git_source_snapshot(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    _write_snapshot(snapshot, install_target="git+file:///tmp/borg-checkout")

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is False
    assert result["canonical_install_target"] is False


def test_public_gate_rejects_checkout_import_leakage_inside_repo(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    _write_snapshot(
        snapshot,
        checkout_import_leakage={
            "passed": True,
            "installed_file": str(ROOT / "borg" / "__init__.py"),
        },
    )

    result = public_gate.github_source_install_check(snapshot, "9.9.9", max_snapshot_age_hours=24.0)

    assert result["passed"] is False
    assert result["checkout_import_leakage_passed"] is False


def test_public_gate_rejects_wrong_git_source_snapshot_version(tmp_path: Path) -> None:
    snapshot = tmp_path / "github_source_install_snapshot.json"
    _write_snapshot(snapshot, version="9.9.8")

    result = public_gate.github_source_install_check(snapshot, "9.9.9")

    assert result["passed"] is False
    assert result["version"] == "9.9.8"
    assert result["expected_version"] == "9.9.9"


def test_self_service_watchdog_workflow_runs_canonical_github_source_canary_before_public_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "self-service-watchdog.yml").read_text(encoding="utf-8")

    assert "python eval/run_github_source_install_canary.py" in workflow
    assert "git+file://${GITHUB_WORKSPACE}" not in workflow
    assert "git+https://github.com/${GITHUB_REPOSITORY}.git@${GITHUB_SHA}" in workflow
    assert "--expected-commit \"${GITHUB_SHA}\"" in workflow
    assert "GitHub source canary failed; continuing" in workflow
    assert workflow.index("python eval/run_pypi_fresh_install_canary.py") < workflow.index("python eval/run_github_source_install_canary.py")
    assert workflow.index("python eval/run_github_source_install_canary.py") < workflow.index("python eval/public_self_serve_launch_gate.py")


def test_ops_watchdog_tracks_github_source_snapshot_as_proof_artifact() -> None:
    watchdog = (ROOT / "eval" / "ops_readiness_watchdog.py").read_text(encoding="utf-8")

    assert "eval/github_source_install_snapshot.json" in watchdog
    assert "python eval/run_github_source_install_canary.py" in watchdog
    assert "github_source_current" in watchdog


def test_proof_dashboard_lists_github_source_install_evidence() -> None:
    dashboard = (ROOT / "scripts" / "build_borg_proof_dashboard.py").read_text(encoding="utf-8")

    assert "eval/github_source_install_snapshot.json" in dashboard
    assert "github_source_install_canary" in dashboard
    assert "github_source_green" in dashboard
