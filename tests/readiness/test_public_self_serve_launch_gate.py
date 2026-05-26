from __future__ import annotations

import json
from pathlib import Path

from eval import first_10_evidence as evidence
from eval import public_self_serve_launch_gate as gate
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
        "project_urls": project_urls if project_urls is not None else {
            "Homepage": "https://github.com/borg-farther/Borg-Directory",
            "Repository": "https://github.com/borg-farther/Borg-Directory",
            "Documentation": "https://github.com/borg-farther/Borg-Directory#readme",
            "Issues": "https://github.com/borg-farther/Borg-Directory/issues",
        },
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


def test_pypi_latest_check_requires_source_version_and_urls() -> None:
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
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(1, incident=True)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
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
    (tmp_path / "eval").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
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
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
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
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path, passed=False)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": True, "blockers": [], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
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
    (tmp_path / "eval").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "agent-borg"\nversion = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("pipx install agent-borg==9.9.9\nPublic self-serve launch: NO-GO until evidence.\n", encoding="utf-8")
    (tmp_path / "eval" / "first_10_user_scoreboard.json").write_text(json.dumps(_scoreboard([_row(i) for i in range(1, 11)])), encoding="utf-8")
    (tmp_path / "eval" / "first_user_release_gate_snapshot.json").write_text(json.dumps({"success": True, "results": [{"name": "ok", "passed": True}]}), encoding="utf-8")
    _write_cold_start_trust_snapshot(tmp_path)
    monkeypatch.setattr(gate, "self_service_ops_check", lambda: {"passed": False, "blockers": ["bad-answer intake missing"], "rollout_policy": "test"})
    (tmp_path / "eval" / "pypi_fresh_install_snapshot.json").write_text(
        json.dumps({
            "success": True,
            "version": "9.9.9",
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
