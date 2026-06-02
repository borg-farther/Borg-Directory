from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from eval import first_10_evidence as evidence
from eval import public_self_serve_launch_gate as gate
from eval import real_user_rollout_gate as rollout
from eval import run_pypi_fresh_install_canary as canary


def _row(idx: int, *, install: bool = True, useful: bool = True, incident: bool = False) -> dict[str, object]:
    return {
        "user_id_pseudonym": f"external-user-{idx:02d}",
        "external_user_evidence_uri": f"https://evidence.borg-farther.org/first-10/{idx}",
        "consent_confirmed": True,
        "install_method": "pipx install agent-borg==9.9.9",
        "install_success": install,
        "time_to_first_rescue_minutes": 3,
        "rescue_input_redacted": "ModuleNotFoundError: No module named flask",
        "rescue_returned_action_stop_verify": True,
        "rescue_useful": useful,
        "mcp_setup_attempted": True,
        "mcp_setup_success": True,
        "no_confident_match_when_unknown": True,
        "blocker_category": "none",
        "blocker_notes_redacted": "none",
        "privacy_security_incident": incident,
        "repeat_use_within_7_days": idx <= 2,
        "outcome_recorded": True,
    }


def _scoreboard(rows: list[dict[str, object]]) -> dict[str, object]:
    data: dict[str, object] = {
        "schema_version": 1,
        "truth_policy": {
            "simulated_users_count_as_real": False,
            "internal_sessions_count_as_real": False,
            "maintainer_runs_count_as_real": False,
            "verified_external_users": 0,
            "public_self_serve_launch_allowed_before_thresholds": False,
        },
        "thresholds": {
            "min_install_successes_for_public_self_serve": 8,
            "min_useful_rescue_moments_for_public_self_serve": 6,
            "max_critical_privacy_security_failures": 0,
            "required_total_real_users": 10,
        },
        "columns": evidence.DEFAULT_COLUMNS,
        "rows": rows,
        "current_counts": {
            "real_users": 0,
            "install_successes": 0,
            "useful_rescue_moments": 0,
            "critical_privacy_security_failures": 0,
            "repeat_use_within_7_days": 0,
        },
        "current_verdict": {
            "first_10_complete": False,
            "public_self_serve_launch_gate": "BLOCKED",
            "reason": "No verified external user rows exist yet.",
        },
    }
    return evidence.scoreboard_with_derived_fields(data)


def _pypi_fixture(
    version: str = "9.9.9",
    *,
    project_urls: dict[str, str] | None = None,
    summary: str | None = None,
    keywords: str | None = None,
) -> dict[str, object]:
    return {
        "package": "agent-borg",
        "version": version,
        "summary": gate.EXPECTED_PYPI_SUMMARY if summary is None else summary,
        "keywords": gate.REQUIRED_PYPI_KEYWORD if keywords is None else keywords,
        "release_files": [
            {"filename": f"agent_borg-{version}-py3-none-any.whl", "upload_time_iso_8601": "2026-05-26T00:00:00+00:00"},
            {"filename": f"agent_borg-{version}.tar.gz", "upload_time_iso_8601": "2026-05-26T00:00:01+00:00"},
        ],
        "project_urls": project_urls if project_urls is not None else {
            "Homepage": "https://github.com/borg-farther/Borg-Directory",
            "Repository": "https://github.com/borg-farther/Borg-Directory",
            "Documentation": "https://github.com/borg-farther/Borg-Directory#readme",
            "Issues": "https://github.com/borg-farther/Borg-Directory/issues",
        },
    }


def _fresh_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_source_revision_state() -> dict[str, object]:
    return {
        "revision": "abcdef1234567890abcdef1234567890abcdef12",
        "commit_time_utc": "2026-05-25T00:00:00+00:00",
        "dirty": False,
        "available": True,
    }


def _write_cold_start_trust_snapshot(root: Path, *, passed: bool = True) -> None:
    (root / "eval" / "cold_start_trust_gate_snapshot.json").write_text(
        json.dumps({
            "passed": passed,
            "checks": [
                {"name": name, "passed": passed}
                for name in sorted(gate.REQUIRED_COLD_START_TRUST_CHECKS)
            ],
            "trust_policy": "fail closed on irrelevant first answers",
            "bad_answer_feedback_path": {
                "agent_mcp_durable_path": "call borg_record_failure(error_pattern, pack_id, phase, approach, outcome='failure') when the bad path is concrete",
                "cli_durable_path": "borg feedback-v3 --task-context ...",
                "human_path": ".github/ISSUE_TEMPLATE/bad-answer.yml",
            },
        }),
        encoding="utf-8",
    )


def _write_ops_watchdog_snapshot(root: Path, *, passed: bool = True) -> None:
    (root / "eval" / "ops_readiness_watchdog_snapshot.json").write_text(
        json.dumps({
            "passed": passed,
            "blockers": [] if passed else ["ops readiness watchdog failed"],
            "generated_at_utc": "2026-05-30T00:00:00+00:00",
            "truth_policy": "Watchdog passing means controlled first-10 ops proof is fresh and internally consistent.",
        }),
        encoding="utf-8",
    )


def _write_served_runtime_snapshot(root: Path, *, version: str = "9.9.9", passed: bool = True) -> None:
    (root / "eval" / "served_runtime_fingerprint_snapshot.json").write_text(
        json.dumps({
            "success": passed,
            "borg_version": version if passed else "9.9.8",
            "source_version": version,
            "version_matches_source": passed,
            "reload_status": "loaded_code_matches_source_behavior" if passed else "reload_or_patch_required",
            "confidence_gate_canary": {"passed": passed},
            "observe_behavior_canary": {"passed": passed, "meta_prompt_failed_closed": passed},
        }),
        encoding="utf-8",
    )


def _release_governance_payload(*, protected: bool = True) -> dict:
    checks = [
        "test (3.10)",
        "test (3.11)",
        "test (3.12)",
        "dependency-audit",
        "policy-check",
        "secret-scan",
        "static-security",
        "ops-readiness-watchdog",
        "old-account-reference",
    ]
    return {
        "generated_at_utc": _fresh_timestamp(),
        "repo": "borg-farther/Borg-Directory",
        "branch": "main",
        "protected": protected,
        "protection": {
            "required_status_checks": {
                "strict": protected,
                "checks": [{"context": context} for context in checks],
            },
            "required_pull_request_reviews": {
                "require_code_owner_reviews": protected,
                "required_approving_review_count": 1 if protected else 0,
                "dismiss_stale_reviews": protected,
                "require_last_push_approval": protected,
            },
            "enforce_admins": {"enabled": protected},
            "required_conversation_resolution": protected,
            "allow_force_pushes": {"enabled": False},
            "allow_deletions": {"enabled": False},
            "codeowners_errors": [],
        },
        "codeowners_errors": [],
    }


def _write_release_governance_snapshot(root: Path, *, protected: bool = True) -> None:
    (root / "eval" / "release_governance_snapshot.json").write_text(
        json.dumps(_release_governance_payload(protected=protected)),
        encoding="utf-8",
    )


def _write_release_runtime_snapshots(root: Path) -> None:
    _write_served_runtime_snapshot(root)
    _write_release_governance_snapshot(root)


def test_row_derived_evidence_rejects_forged_aggregates_with_empty_rows() -> None:
    data = _scoreboard([])
    data["truth_policy"]["verified_external_users"] = 10  # type: ignore[index]
    data["current_counts"] = {  # type: ignore[index]
        "real_users": 10,
        "install_successes": 10,
        "useful_rescue_moments": 10,
        "critical_privacy_security_failures": 0,
        "repeat_use_within_7_days": 10,
    }
    data["current_verdict"] = {"first_10_complete": True, "public_self_serve_launch_gate": "READY"}  # type: ignore[index]

    result = evidence.evaluate_scoreboard(data)

    assert result["thresholds_passed"] is False
    assert result["derived_counts"]["verified_external_users"] == 0
    assert result["stored_consistency"]["passed"] is False
    assert any(item["field"] == "truth_policy.verified_external_users" for item in result["stored_consistency"]["mismatches"])


def test_valid_first_10_rows_pass_and_sync_aggregate_fields() -> None:
    data = _scoreboard([_row(i) for i in range(1, 11)])

    result = evidence.evaluate_scoreboard(data)

    assert result["schema_valid"] is True
    assert result["thresholds_passed"] is True
    assert result["stored_consistency"]["passed"] is True
    assert result["derived_counts"]["verified_external_users"] == 10
    assert result["derived_counts"]["install_successes"] == 10
    assert result["derived_counts"]["useful_rescue_moments"] == 10


def test_invalid_rows_do_not_count_and_secrets_block_schema() -> None:
    rows = [_row(i) for i in range(1, 10)]
    rows.append(_row(10))
    rows[-1]["user_id_pseudonym"] = "external-user-01"  # duplicate
    rows[-1]["rescue_input_redacted"] = "api_key=sk-123...7890"
    data = _scoreboard(rows)

    result = evidence.evaluate_scoreboard(data)

    assert result["schema_valid"] is False
    assert "external-user-01" in result["duplicate_user_ids"]
    assert result["thresholds_passed"] is False
    assert any("unredacted secret" in reason for item in result["invalid_rows"] for reason in item["reasons"])


def test_first_10_thresholds_are_non_relaxable_policy_floors() -> None:
    data = _scoreboard([])
    data["thresholds"] = {  # type: ignore[index]
        "required_total_real_users": -1,
        "min_install_successes_for_public_self_serve": -1,
        "min_useful_rescue_moments_for_public_self_serve": -1,
        "max_critical_privacy_security_failures": 99,
    }
    data["current_verdict"] = {"first_10_complete": True, "public_self_serve_launch_gate": "READY"}  # type: ignore[index]

    result = evidence.evaluate_scoreboard(data)

    assert result["thresholds"] == {
        "required_total_real_users": 10,
        "required_install_successes": 8,
        "required_useful_rescue_moments": 6,
        "max_critical_privacy_security_failures": 0,
    }
    assert result["thresholds_passed"] is False
    assert result["public_self_serve_launch_gate"] == "BLOCKED"


def test_first_10_thresholds_never_allow_privacy_security_incidents() -> None:
    rows = [_row(i) for i in range(1, 11)]
    rows[0]["privacy_security_incident"] = True
    data = _scoreboard(rows)
    data["thresholds"]["max_critical_privacy_security_failures"] = 10  # type: ignore[index]

    result = evidence.evaluate_scoreboard(data)

    assert result["derived_counts"]["critical_privacy_security_failures"] == 1
    assert result["thresholds"]["max_critical_privacy_security_failures"] == 0
    assert result["thresholds_passed"] is False


def test_first_10_evidence_uri_must_be_real_https_and_secret_free() -> None:
    rows = [_row(i) for i in range(1, 11)]
    rows[0]["external_user_evidence_uri"] = "https://evidence.example.test/borg/1"
    rows[1]["external_user_evidence_uri"] = "http://evidence.borg-farther.org/first-10/2"
    rows[2]["external_user_evidence_uri"] = "https://evidence.borg-farther.org/first-10/3?" + "tok" + "en=abc123"

    result = evidence.evaluate_scoreboard(_scoreboard(rows))

    assert result["schema_valid"] is False
    reasons = [reason for item in result["invalid_rows"] for reason in item["reasons"]]
    assert reasons.count("missing valid https external_user_evidence_uri") >= 3
    assert any("external_user_evidence_uri appears to contain an unredacted secret" in reason for reason in reasons)


def test_first_10_secret_scan_covers_all_string_fields() -> None:
    rows = [_row(i) for i in range(1, 11)]
    rows[0]["install_method"] = "pipx install agent-borg==9.9.9 " + "pass" + "word=abc123"

    result = evidence.evaluate_scoreboard(_scoreboard(rows))

    assert result["schema_valid"] is False
    assert any("install_method appears to contain an unredacted secret" in reason for item in result["invalid_rows"] for reason in item["reasons"])


def test_docs_claim_guard_catches_stale_pins_and_unsupported_ship_claims(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "pipx install agent-borg==3.3.3\n"
        "decision: SHIP\n"
        "completion lift: +65%\n"
        "statistically significant agent-level lift: not claimed\n"
        "**Ready to share Git now?** YES, supervised only\n"
        "version_package pyproject=3.3.1 runtime=3.3.1\n"
        "ready_for_10=True; ready_for_1000=True\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard([Path("README.md")], "9.9.9", public_evidence_ready=False)

    assert result["passed"] is False
    kinds = {violation["kind"] for violation in result["violations"]}
    assert "stale agent-borg pin" in kinds
    assert "unqualified SHIP decision claim" in kinds
    assert "completion-lift claim without external evidence" in kinds
    assert "stale Git-sharing YES claim" in kinds
    assert "stale proof-dashboard version metric" in kinds
    assert "unqualified logical-load readiness claim" in kinds
    assert "statistically significant external/agent lift claim" not in kinds


def test_docs_claim_guard_blocks_controlled_beta_go_until_package_canary_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "docs" / "VALUE_COMMUNICATION_DASHBOARD.md"
    doc.parent.mkdir()
    doc.write_text(
        "Ready for **controlled first-10 beta sharing**:\n"
        "controlled first-10 PyPI beta infrastructure: **GO** — PyPI latest, "
        "fresh-install, stdio MCP, docs claim guard, and security gates are green\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("docs/VALUE_COMMUNICATION_DASHBOARD.md")],
        "9.9.9",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is False
    assert any(v["kind"] == "controlled first-10 package GO before PyPI canary" for v in result["violations"])


def test_docs_claim_guard_blocks_markdown_stale_package_no_go_after_canary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "**Status:** controlled first-10 public-package beta infrastructure is "
        "**NO-GO for this source revision** until PyPI latest, fresh-install, "
        "and stdio MCP canaries pass for that exact version.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "9.9.9",
        public_evidence_ready=False,
        package_evidence_ready=True,
    )

    assert result["passed"] is False
    assert any(v["kind"] == "stale package NO-GO after PyPI canary" for v in result["violations"])


def test_docs_claim_guard_blocks_broader_stale_package_blockers_after_canary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "docs" / "README.md"
    doc.parent.mkdir()
    doc.write_text(
        "Controlled first-10 public-package beta infrastructure: NO-GO for `agent-borg==9.9.9` "
        "until GitHub main, PyPI latest, fresh-install, stdio MCP, and proof dashboards are green.\n"
        "controlled first-10 PyPI beta infrastructure: NO-GO for `agent-borg==9.9.9` until the package/proof chain is green.\n"
        "Current package path status: `agent-borg==9.9.9` is not yet published/canaried as the current PyPI package.\n"
        "production PyPI/latest, fresh-install, and stdio MCP canaries are not current for this version.\n"
        "decision: controlled first-10 beta invites may not start until PyPI latest and fresh-install are green.\n"
        "source/local release-candidate only\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("docs/README.md")],
        "9.9.9",
        public_evidence_ready=False,
        package_evidence_ready=True,
    )

    assert result["passed"] is False
    kinds = {violation["kind"] for violation in result["violations"]}
    assert "stale controlled-beta package blocker after PyPI canary" in kinds
    assert "stale package-proof-chain blocker after PyPI canary" in kinds
    assert "stale unpublished package-path status after PyPI canary" in kinds
    assert "stale PyPI/fresh-install blocker after PyPI canary" in kinds
    assert "stale invite-start blocker after PyPI canary" in kinds
    assert "stale source/local-only wording after PyPI canary" in kinds


def test_docs_claim_guard_allows_release_control_blockers_after_package_canary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "docs" / "READINESS.md"
    doc.parent.mkdir()
    doc.write_text(
        "Controlled first-10 beta: **NO-GO right now**. `agent-borg==9.9.9` "
        "package/fresh-install/local stdio MCP proof is green, but release controls are red: "
        "the served runtime fingerprint is stale and GitHub `main` is unprotected.\n"
        "Public waitlist / narrow beta: **0 testers may proceed** until served-runtime freshness, "
        "release-governance, ops/watchdog, proof-dashboard, cold-start trust, and source/local "
        "first-user gates are all green; then the first-10 evidence contract caps the cohort at 10.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("docs/READINESS.md")],
        "9.9.9",
        public_evidence_ready=False,
        package_evidence_ready=True,
    )

    assert result["passed"] is True
    assert result["violations"] == []


def test_docs_claim_guard_blocks_known_package_beta_contradictions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "Package infrastructure is green for **controlled first-10 public-package beta**:\n"
        "Ready to invite up to 10 controlled public-package beta testers.\n"
        "Published controlled-beta package line: `agent-borg==9.9.9`; production PyPI upload and fresh-install + stdio MCP canary are green.\n"
        "Public waitlist / narrow beta: **CONDITIONAL GO for controlled first-10 only**.\n"
        "controlled first-10 beta invites may start with consented evidence capture.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "9.9.9",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is False
    kinds = {violation["kind"] for violation in result["violations"]}
    assert "controlled beta package infrastructure green before PyPI canary" in kinds
    assert "ready-to-invite claim before PyPI canary" in kinds
    assert "published controlled-beta package line before PyPI canary" in kinds
    assert "production PyPI canary green before PyPI canary" in kinds
    assert "controlled first-10 conditional GO before PyPI canary" in kinds
    assert "controlled beta invites-may-start before PyPI canary" in kinds


def test_docs_claim_guard_allows_explicit_same_version_drift_blocker_before_canary(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "docs" / "READINESS.md"
    doc.parent.mkdir()
    doc.write_text(
        "Local first-user gate is green for source `agent-borg==9.9.9`. "
        "PyPI latest/fresh-install/stdio MCP proof is not current for this source revision.\n"
        "decision: package proof is not current for `agent-borg==9.9.9`; "
        "controlled first-10 beta must wait for a new immutable package version.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("docs/READINESS.md")],
        "9.9.9",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is True
    assert result["violations"] == []


def test_docs_claim_guard_allows_honest_stale_pypi_latest_before_next_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "`agent-borg==3.3.15` is published on PyPI, but that artifact is stale; "
        "this branch targets `agent-borg==3.3.16`.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "3.3.16",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is True
    assert result["violations"] == []


def test_docs_claim_guard_blocks_stale_pypi_latest_after_package_evidence_is_green(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "`agent-borg==3.3.15` is published on PyPI, but that artifact is stale; "
        "this branch targets `agent-borg==3.3.16`.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "3.3.16",
        public_evidence_ready=False,
        package_evidence_ready=True,
    )

    assert result["passed"] is False
    assert any(v["kind"] == "stale agent-borg pin" for v in result["violations"])


def test_docs_claim_guard_still_blocks_stale_install_command_before_next_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "`agent-borg==3.3.15` is published on PyPI, but that artifact is stale; "
        "this branch targets `agent-borg==3.3.16`.\n"
        "pipx install agent-borg==3.3.15\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "3.3.16",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is False
    assert any(v["kind"] == "stale agent-borg pin" for v in result["violations"])


def test_docs_claim_guard_blocks_stale_install_commands_with_flags_and_alt_tools(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "`agent-borg==3.3.15` is published on PyPI, but that artifact is stale; "
        "this branch targets `agent-borg==3.3.16`.\n"
        "python -m pip install --upgrade --no-cache-dir agent-borg==3.3.15\n"
        "uv tool install --force agent-borg==3.3.15\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "3.3.16",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is False
    assert [v["kind"] for v in result["violations"]].count("stale agent-borg pin") == 2


def test_docs_claim_guard_requires_explicit_stale_label_for_old_package_reference(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "`agent-borg==3.3.15` is published on PyPI; this branch targets `agent-borg==3.3.16`.\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "3.3.16",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    assert result["passed"] is False
    assert any(v["kind"] == "stale agent-borg pin" for v in result["violations"])


def test_docs_claim_guard_does_not_allow_historical_banner_on_current_claim_doc(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    doc = tmp_path / "README.md"
    doc.write_text(
        "Historical/internal — not current product documentation.\n"
        "pipx install agent-borg==3.3.15\n",
        encoding="utf-8",
    )

    result = gate.docs_claim_guard(
        [Path("README.md")],
        "3.3.16",
        public_evidence_ready=False,
        package_evidence_ready=False,
    )

    kinds = {v["kind"] for v in result["violations"]}
    assert result["passed"] is False
    assert "current claim doc marked historical" in kinds
    assert "stale agent-borg pin" in kinds


def test_pypi_latest_check_requires_source_version_and_urls(monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "source_revision_state",
        lambda: {
            "revision": "abcdef1234567890abcdef1234567890abcdef12",
            "commit_time_utc": "2026-05-25T00:00:00+00:00",
            "dirty": False,
            "available": True,
        },
    )
    result = gate.pypi_latest_check(
        "9.9.9",
        fetch_network=False,
        pypi_data=_pypi_fixture(),
    )
    assert result["passed"] is True

    wrong_urls = gate.pypi_latest_check(
        "9.9.9",
        fetch_network=False,
        pypi_data=_pypi_fixture(project_urls={
            "Homepage": "https://example.com",
            "Repository": "https://example.com/repo",
            "Documentation": "https://example.com/docs",
            "Issues": "https://example.com/issues",
        }),
    )
    assert wrong_urls["passed"] is False
    assert wrong_urls["url_mismatches"]["Homepage"]["expected"] == "https://github.com/borg-farther/Borg-Directory"

    stale = gate.pypi_latest_check(
        "9.9.9",
        fetch_network=False,
        pypi_data={"package": "agent-borg", "version": "9.9.8", "project_urls": {}},
    )
    assert stale["passed"] is False


def test_pypi_latest_check_fails_when_same_version_upload_predates_source_revision(monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "source_revision_state",
        lambda: {
            "revision": "abcdef1234567890abcdef1234567890abcdef12",
            "commit_time_utc": "2026-05-31T10:27:07+00:00",
        },
    )

    result = gate.pypi_latest_check(
        "9.9.9",
        fetch_network=False,
        pypi_data=_pypi_fixture() | {
            "release_files": [
                {"filename": "agent_borg-9.9.9-py3-none-any.whl", "upload_time_iso_8601": "2026-05-28T17:50:29.231332+00:00"},
                {"filename": "agent_borg-9.9.9.tar.gz", "upload_time_iso_8601": "2026-05-28T17:50:31.032755+00:00"},
            ],
        },
    )

    assert result["passed"] is False
    assert result["source_upload_alignment"]["passed"] is False
    assert result["source_upload_alignment"]["failure_kind"] == "same_version_pypi_upload_predates_source_revision"
    assert "PyPI release upload predates current source revision" in result["source_upload_alignment"]["detail"]


def test_pypi_latest_check_fails_if_any_release_file_predates_source_revision(monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "source_revision_state",
        lambda: {
            "revision": "abcdef1234567890abcdef1234567890abcdef12",
            "commit_time_utc": "2026-05-31T10:27:07+00:00",
            "dirty": False,
            "available": True,
        },
    )

    result = gate.pypi_latest_check(
        "9.9.9",
        fetch_network=False,
        pypi_data=_pypi_fixture() | {
            "release_files": [
                {"filename": "agent_borg-9.9.9-py3-none-any.whl", "upload_time_iso_8601": "2026-05-28T17:50:29+00:00"},
                {"filename": "agent_borg-9.9.9.tar.gz", "upload_time_iso_8601": "2026-06-01T00:00:00+00:00"},
            ],
        },
    )

    assert result["passed"] is False
    alignment = result["source_upload_alignment"]
    assert alignment["passed"] is False
    assert alignment["failure_kind"] == "same_version_pypi_upload_predates_source_revision"
    assert alignment["oldest_release_upload_time_utc"] == "2026-05-28T17:50:29+00:00"
    assert alignment["stale_release_files"] == ["agent_borg-9.9.9-py3-none-any.whl"]


def test_pypi_latest_check_fails_closed_without_release_file_timestamps(monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "source_revision_state",
        lambda: {
            "revision": "abcdef1234567890abcdef1234567890abcdef12",
            "commit_time_utc": "2026-05-25T00:00:00+00:00",
            "dirty": False,
            "available": True,
        },
    )

    result = gate.pypi_latest_check(
        "9.9.9",
        fetch_network=False,
        pypi_data=_pypi_fixture() | {"release_files": [{"filename": "agent_borg-9.9.9-py3-none-any.whl"}]},
    )

    assert result["passed"] is False
    assert result["source_upload_alignment"]["passed"] is False
    assert result["source_upload_alignment"]["failure_kind"] == "missing_release_upload_timestamp"


def test_pypi_latest_check_fails_when_source_worktree_is_dirty(monkeypatch) -> None:
    monkeypatch.setattr(
        gate,
        "source_revision_state",
        lambda: {
            "revision": "abcdef1234567890abcdef1234567890abcdef12+dirty",
            "commit_time_utc": "2026-05-25T00:00:00+00:00",
            "dirty": True,
            "available": True,
        },
    )

    result = gate.pypi_latest_check("9.9.9", fetch_network=False, pypi_data=_pypi_fixture())

    assert result["passed"] is False
    assert result["source_upload_alignment"]["failure_kind"] == "source_worktree_dirty"


def test_pypi_fresh_install_check_requires_current_timestamp(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    path = eval_dir / "pypi_fresh_install_snapshot.json"

    def write_snapshot(generated_at: str | None) -> dict:
        payload: dict[str, object] = {
            "success": True,
            "version": "9.9.9",
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True},
        }
        if generated_at is not None:
            payload["generated_at_utc"] = generated_at
        path.write_text(json.dumps(payload), encoding="utf-8")
        return gate.pypi_fresh_install_check(path, "9.9.9")

    monkeypatch.setattr(gate, "_age_hours", lambda value: None)
    missing = write_snapshot(None)
    assert missing["passed"] is False
    assert missing["freshness"]["failure_kind"] == "missing_timestamp"

    monkeypatch.setattr(gate, "_age_hours", lambda value: 48.0)
    stale = write_snapshot("stale")
    assert stale["passed"] is False
    assert stale["freshness"]["failure_kind"] == "stale_timestamp"

    monkeypatch.setattr(gate, "_age_hours", lambda value: -1.0)
    future = write_snapshot("future")
    assert future["passed"] is False
    assert future["freshness"]["failure_kind"] == "future_timestamp"

    monkeypatch.setattr(gate, "_age_hours", lambda value: 1.0)
    fresh = write_snapshot("fresh")
    assert fresh["passed"] is True
    assert fresh["freshness"]["passed"] is True


def test_first_10_issue_form_not_measured_basis_does_not_invalidate_unmeasured_rows() -> None:
    row = _row(1)
    row.update({
        "savings_counterfactual_basis": "not-measured",
        "dead_end_avoided_confirmed": "unknown",
        "user_confirmed_value": "unknown",
    })

    result = evidence.evaluate_scoreboard(_scoreboard([row]))

    assert result["schema_valid"] is True
    assert result["invalid_rows"] == []
    assert result["derived_value"]["rows_with_measured_value"] == 0


def test_first_10_issue_form_savings_basis_aliases_are_normalized() -> None:
    row = _row(1)
    row.update({
        "baseline_minutes_without_borg": 30,
        "actual_minutes_with_borg": 10,
        "net_minutes_saved": 20,
        "savings_counterfactual_basis": "timer-before-after",
        "dead_end_avoided_confirmed": True,
        "user_confirmed_value": True,
    })

    result = evidence.evaluate_scoreboard(_scoreboard([row]))

    assert result["schema_valid"] is True
    assert result["invalid_rows"] == []
    assert result["derived_value"]["counterfactual_basis_counts"] == {"same_user_before_after": 1}


def test_public_gate_pauses_controlled_first_10_when_privacy_security_incident_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(1, incident=True)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    _write_ops_watchdog_snapshot(tmp_path)
    _write_release_runtime_snapshots(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True},
        }),
        encoding="utf-8",
    )

    snapshot = gate.compile_gate(fetch_network=False, pypi_data=_pypi_fixture())

    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["gates"]["privacy_security_incident_pause"]["passed"] is False
    assert any("privacy/security incident" in blocker for blocker in snapshot["blockers"])


def test_public_self_serve_gate_passes_only_when_all_artifacts_and_real_rows_pass(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (tmp_path / "eval").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    _write_ops_watchdog_snapshot(tmp_path)
    _write_release_runtime_snapshots(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True, "server_info": {"name": "borg-mcp-server", "version": "9.9.9"}},
        }),
        encoding="utf-8",
    )

    snapshot = gate.compile_gate(
        fetch_network=False,
        pypi_data=_pypi_fixture(),
    )

    assert snapshot["ready_for_public_self_serve_launch"] is True
    assert snapshot["max_recommended_real_users_now"] == 100


def test_public_self_serve_gate_blocks_empty_evidence_even_when_infra_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    _write_ops_watchdog_snapshot(tmp_path)
    _write_release_runtime_snapshots(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True},
        }),
        encoding="utf-8",
    )

    snapshot = gate.compile_gate(
        fetch_network=False,
        pypi_data=_pypi_fixture(),
    )

    assert snapshot["ready_for_controlled_first_10_beta"] is True
    assert snapshot["ready_for_public_self_serve_launch"] is False
    assert snapshot["max_recommended_real_users_now"] == 10
    assert any("first-10 external-user evidence" in blocker for blocker in snapshot["blockers"])


def test_public_self_serve_gate_blocks_when_cold_start_trust_snapshot_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path, passed=False)
    _write_ops_watchdog_snapshot(tmp_path)
    _write_release_runtime_snapshots(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True},
        }),
        encoding="utf-8",
    )

    snapshot = gate.compile_gate(fetch_network=False, pypi_data=_pypi_fixture())

    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["ready_for_public_self_serve_launch"] is False
    assert snapshot["gates"]["cold_start_trust_hardening"]["passed"] is False
    assert any("cold-start trust" in blocker for blocker in snapshot["blockers"])


def test_public_self_serve_gate_blocks_when_self_service_ops_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    _write_ops_watchdog_snapshot(tmp_path)
    _write_release_runtime_snapshots(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": False, "blockers": ["bad-answer intake missing"], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True, "server_info": {"name": "borg-mcp-server", "version": "9.9.9"}},
        }),
        encoding="utf-8",
    )

    snapshot = gate.compile_gate(fetch_network=False, pypi_data=_pypi_fixture())

    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["ready_for_public_self_serve_launch"] is False
    assert snapshot["gates"]["self_service_ops_readiness"]["passed"] is False
    assert "bad-answer intake missing" in snapshot["blockers"]


def test_public_self_serve_gate_blocks_when_ops_watchdog_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (tmp_path / "eval").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    _write_ops_watchdog_snapshot(tmp_path, passed=False)
    _write_release_runtime_snapshots(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True, "server_info": {"name": "borg-mcp-server", "version": "9.9.9"}},
        }),
        encoding="utf-8",
    )

    snapshot = gate.compile_gate(fetch_network=False, pypi_data=_pypi_fixture())

    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["ready_for_public_self_serve_launch"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["gates"]["ops_readiness_watchdog"]["passed"] is False
    assert any("ops readiness watchdog failed" in blocker for blocker in snapshot["blockers"])


def _write_public_gate_happy_fixture(root: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gate, "ROOT", root)
    monkeypatch.setattr(gate, "CURRENT_CLAIM_DOCS", [Path("README.md")])
    monkeypatch.setattr(gate, "source_revision_state", _clean_source_revision_state)
    (root / "eval").mkdir()
    (root / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (root / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (root / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (root / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(root)
    _write_ops_watchdog_snapshot(root)
    _write_release_runtime_snapshots(root)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (root / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True, "server_info": {"name": "borg-mcp-server", "version": "9.9.9"}},
        }),
        encoding="utf-8",
    )


def test_public_self_serve_gate_blocks_when_served_runtime_is_stale(tmp_path: Path, monkeypatch) -> None:
    _write_public_gate_happy_fixture(tmp_path, monkeypatch)
    _write_served_runtime_snapshot(tmp_path, passed=False)

    snapshot = gate.compile_gate(fetch_network=False, pypi_data=_pypi_fixture())

    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["gates"]["served_runtime_freshness"]["passed"] is False
    assert any("reload_status" in blocker or "borg_version" in blocker for blocker in snapshot["blockers"])


def test_public_self_serve_gate_blocks_when_release_governance_fails(tmp_path: Path, monkeypatch) -> None:
    _write_public_gate_happy_fixture(tmp_path, monkeypatch)
    _write_release_governance_snapshot(tmp_path, protected=False)

    snapshot = gate.compile_gate(fetch_network=False, pypi_data=_pypi_fixture())

    assert snapshot["ready_for_controlled_first_10_beta"] is False
    assert snapshot["gates"]["release_governance"]["passed"] is False
    assert any("main branch is not protected" in blocker for blocker in snapshot["blockers"])


def test_release_governance_check_prefers_live_github_over_stale_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    (tmp_path / "eval").mkdir()
    _write_release_governance_snapshot(tmp_path, protected=False)
    monkeypatch.setattr(gate.release_governance_gate, "fetch_live_branch_payload", lambda repo, branch: _release_governance_payload(protected=True))
    monkeypatch.setattr(gate.release_governance_gate, "fetch_codeowners_errors", lambda repo, ref=None: [])

    live = gate.release_governance_check(fetch_network=True)
    snapshot = gate.release_governance_check(fetch_network=False)

    assert live["passed"] is True
    assert live["source"] == "github_api"
    assert snapshot["passed"] is False
    assert snapshot["source"] == "snapshot"


def test_release_governance_check_accepts_evaluated_snapshot_without_double_evaluating(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    (tmp_path / "eval").mkdir()
    evaluated = {
        "schema_version": 1,
        "passed": True,
        "blockers": [],
        "protected": True,
        "required_checks_expected": gate.release_governance_gate.DEFAULT_REQUIRED_CHECKS,
        "required_checks_observed": gate.release_governance_gate.DEFAULT_REQUIRED_CHECKS,
        "strict_required_status_checks": True,
        "codeowners_review_required": True,
        "required_approving_review_count": 1,
        "dismiss_stale_reviews": True,
        "require_last_push_approval": True,
        "enforce_admins": True,
        "required_conversation_resolution": True,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "bypass_allowances": [],
        "codeowners_errors_checked": True,
        "codeowners_error_count": 0,
        "codeowners_errors": [],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo": "borg-farther/Borg-Directory",
        "branch": "main",
        "source": "github_api",
    }
    (tmp_path / "eval" / "release_governance_snapshot.json").write_text(json.dumps(evaluated), encoding="utf-8")

    snapshot = gate.release_governance_check(fetch_network=False)

    assert snapshot["passed"] is True
    assert snapshot["blockers"] == []
    assert snapshot["source"] == "snapshot"


def test_release_governance_check_rejects_incomplete_green_evaluated_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    (tmp_path / "eval").mkdir()
    evaluated = {
        "schema_version": 1,
        "passed": True,
        "blockers": [],
        "protected": True,
        "required_checks_observed": ["test (3.11)"],
        "source": "github_api",
    }
    (tmp_path / "eval" / "release_governance_snapshot.json").write_text(json.dumps(evaluated), encoding="utf-8")

    snapshot = gate.release_governance_check(fetch_network=False)

    assert snapshot["passed"] is False
    assert any("required checks" in blocker or "CODEOWNERS" in blocker for blocker in snapshot["blockers"])


def _write_rollout_fixture(root: Path, *, watchdog_passed: bool) -> None:
    (root / "eval").mkdir(exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    (root / "borg").mkdir(exist_ok=True)
    (root / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (root / "borg" / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
    for rel in [
        "eval/security_hardening_baseline.json",
        "docs/SECURITY_HARDENING_BASELINE.md",
        "docs/PRIVACY_MODEL.md",
        "docs/PROMPT_INJECTION_THREAT_MODEL.md",
        "scripts/security_gate_check.py",
        ".github/workflows/security-gates.yml",
    ]:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if path.suffix == ".json" else "ok\n", encoding="utf-8")
    (root / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    for users in [10, 100]:
        (root / "eval" / f"load_{users}_snapshot.json").write_text(json.dumps({"passed": True, "users": users}), encoding="utf-8")
    (root / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
            "generated_at_utc": _fresh_timestamp(),
            "results": [{"name": "install", "passed": True}],
            "mcp_stdio_canary": {"passed": True},
        }),
        encoding="utf-8",
    )
    (root / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([])), encoding="utf-8")
    _write_ops_watchdog_snapshot(root, passed=watchdog_passed)
    _write_release_runtime_snapshots(root)


def test_real_user_rollout_gate_blocks_controlled_beta_when_ops_watchdog_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rollout, "ROOT", tmp_path)
    monkeypatch.setattr(rollout.public_gate, "ROOT", tmp_path)
    monkeypatch.setattr(rollout.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(rollout.public_gate, "pypi_latest_check", lambda expected, fetch_network=True: {"passed": True, "version": expected})
    monkeypatch.setattr(rollout.public_gate.release_governance_gate, "fetch_live_branch_payload", lambda repo, branch: _release_governance_payload(protected=True))
    monkeypatch.setattr(rollout.public_gate.release_governance_gate, "fetch_codeowners_errors", lambda repo, ref=None: [])
    monkeypatch.setattr(rollout.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    _write_rollout_fixture(tmp_path, watchdog_passed=False)

    snapshot = rollout.compile_rollout_gate()

    assert snapshot["ready_for_10_controlled_beta"] is False
    assert snapshot["max_recommended_real_users_now"] == 0
    assert snapshot["self_service_ops_gate"]["passed"] is False
    assert snapshot["self_service_ops_gate"]["ops_readiness_watchdog"]["passed"] is False
    assert any("ops readiness watchdog failed" in blocker for blocker in snapshot["blockers"])


def test_real_user_rollout_gate_allows_controlled_beta_only_when_ops_watchdog_passes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rollout, "ROOT", tmp_path)
    monkeypatch.setattr(rollout.public_gate, "ROOT", tmp_path)
    monkeypatch.setattr(rollout.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(rollout.public_gate, "pypi_latest_check", lambda expected, fetch_network=True: {"passed": True, "version": expected})
    monkeypatch.setattr(rollout.public_gate.release_governance_gate, "fetch_live_branch_payload", lambda repo, branch: _release_governance_payload(protected=True))
    monkeypatch.setattr(rollout.public_gate.release_governance_gate, "fetch_codeowners_errors", lambda repo, ref=None: [])
    monkeypatch.setattr(rollout.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    _write_rollout_fixture(tmp_path, watchdog_passed=True)

    snapshot = rollout.compile_rollout_gate()

    assert snapshot["ready_for_10_controlled_beta"] is True
    assert snapshot["ready_for_100_real_users"] is False
    assert snapshot["max_recommended_real_users_now"] == 10
    assert snapshot["self_service_ops_gate"]["ops_readiness_watchdog"]["passed"] is True
    assert any("first-10 external-user evidence" in blocker for blocker in snapshot["blockers"])


def test_real_user_rollout_gate_blocks_controlled_beta_when_release_controls_fail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(rollout, "ROOT", tmp_path)
    monkeypatch.setattr(rollout.public_gate, "ROOT", tmp_path)
    monkeypatch.setattr(rollout.public_gate, "source_version", lambda: "9.9.9")
    monkeypatch.setattr(rollout.public_gate, "pypi_latest_check", lambda expected, fetch_network=True: {"passed": True, "version": expected})
    monkeypatch.setattr(rollout.public_gate.release_governance_gate, "fetch_live_branch_payload", lambda repo, branch: _release_governance_payload(protected=True))
    monkeypatch.setattr(rollout.public_gate.release_governance_gate, "fetch_codeowners_errors", lambda repo, ref=None: [])
    monkeypatch.setattr(rollout.self_service_ops_gate, "compile_gate", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    _write_rollout_fixture(tmp_path, watchdog_passed=True)
    _write_served_runtime_snapshot(tmp_path, passed=False)

    snapshot = rollout.compile_rollout_gate()

    assert snapshot["ready_for_10_controlled_beta"] is False
    assert snapshot["release_controls_gate"]["passed"] is False
    assert any("reload_status" in blocker or "borg_version" in blocker for blocker in snapshot["blockers"])

def test_pypi_fresh_install_canary_fails_closed_when_release_not_on_pypi(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run_cmd(name, cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(name)
        if name == "fresh_venv_create":
            return canary.CommandResult(name, list(cmd), 0, True, "", "", 0.0, "exit=0")
        if name == "pip_install_agent_borg":
            return canary.CommandResult(name, list(cmd), 1, False, "", "ERROR: No matching distribution found", 0.0, "exit=1")
        raise AssertionError(f"unexpected command after failed install: {name}")

    monkeypatch.setattr(canary, "run_cmd", fake_run_cmd)

    snapshot = canary.run_canary("9.9.9")

    assert snapshot["success"] is False
    assert calls == ["fresh_venv_create", "pip_install_agent_borg"]
    install_result = snapshot["results"][1]
    assert "--isolated" in install_result["command"]
    assert "--index-url" in install_result["command"]
    assert "https://pypi.org/simple" in install_result["command"]
    assert snapshot["mcp_stdio_canary"]["detail"] == "not run because PyPI install failed"


def test_pypi_mcp_canary_accepts_installed_package_runtime_fingerprint(monkeypatch) -> None:
    fingerprint_payload = {
        "success": True,
        "borg_version": "9.9.9",
        "source_version": None,
        "version_matches_source": False,
        "loaded_function_hashes": {
            "borg.core.confidence_gate.trace_match_is_confident": {"sha256": "abc"},
            "borg.integrations.mcp_server.borg_observe": {"sha256": "def"},
        },
        "observe_behavior_canary": {
            "passed": True,
            "meta_prompt_failed_closed": True,
        },
        "confidence_gate_canary": {"passed": True},
    }
    responses = [
        {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "borg-mcp-server", "version": "9.9.9"}}},
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "error_lookup"}, {"name": "borg_runtime_fingerprint"}, {"name": "borg_observe"}]}},
        {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"text": "ACTION\nSTOP\nVERIFY"}]}},
        {"jsonrpc": "2.0", "id": 4, "result": {"content": [{"text": json.dumps(fingerprint_payload)}]}},
    ]
    stdout = "\n".join(json.dumps(response) for response in responses) + "\n"

    def fake_run_cmd(name, cmd, **kwargs):  # type: ignore[no-untyped-def]
        return canary.CommandResult(name, list(cmd), 0, True, stdout, "", 0.0, "exit=0")

    monkeypatch.setattr(canary, "run_cmd", fake_run_cmd)

    result = canary.mcp_stdio_canary(Path("/tmp/borg-mcp"), {}, "9.9.9")

    assert result["passed"] is True
    assert result["fingerprint_signal"] is True
    assert result["server_info"] == {"name": "borg-mcp-server", "version": "9.9.9"}
    assert result["fingerprint_summary"]["borg_version"] == "9.9.9"
    assert result["fingerprint_summary"]["source_version"] is None
    assert result["fingerprint_summary"]["version_matches_source"] is False
    assert result["fingerprint_summary"]["reload_status"] is None
