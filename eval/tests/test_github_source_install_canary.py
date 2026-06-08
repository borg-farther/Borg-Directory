from __future__ import annotations

import json

from eval import run_github_source_install_canary as canary


def test_resolve_remote_commit_accepts_direct_sha_without_ls_remote_success(monkeypatch):
    sha = "a" * 40

    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "not found"

    monkeypatch.setattr(canary.subprocess, "run", lambda *args, **kwargs: FakeProc())

    result = canary.resolve_remote_commit("https://github.com/borg-farther/Borg-Directory.git", sha)

    assert result["passed"] is True
    assert result["commit_id"] == sha
    assert result["assumed_direct_sha"] is True


def test_mcp_stdio_canary_requires_fingerprint_signal(monkeypatch, tmp_path):
    borg_mcp = tmp_path / "borg-mcp"
    borg_mcp.write_text("stub")
    payload = {
        "success": True,
        "borg_version": "1.2.3",
        "source_version": "1.2.3",
        "version_matches_source": True,
        "reload_status": "loaded_code_matches_source_behavior",
        "confidence_gate_canary": {"passed": True},
        "observe_behavior_canary": {"passed": True, "meta_prompt_failed_closed": True},
        "loaded_function_hashes": {"borg.integrations.mcp_server.borg_observe": {"sha256": "x"}},
    }
    responses = [
        {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "borg-mcp-server", "version": "1.2.3"}}},
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "borg_rescue"}, {"name": "borg_observe"}, {"name": "borg_runtime_fingerprint"}]}},
        {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"text": "ACTION\nSTOP\nVERIFY"}]}},
        {"jsonrpc": "2.0", "id": 4, "result": {"content": [{"text": json.dumps(payload)}]}},
    ]

    def fake_run_cmd(name, cmd, **kwargs):
        return canary.CommandResult(
            name=name,
            command=list(cmd),
            returncode=0,
            passed=True,
            stdout="\n".join(json.dumps(item) for item in responses) + "\n",
            stderr="",
            duration_s=0.01,
            detail="exit=0",
        )

    monkeypatch.setattr(canary, "run_cmd", fake_run_cmd)

    result = canary.mcp_stdio_canary(borg_mcp, {}, "1.2.3")

    assert result["passed"] is True
    assert result["required_tools_present"] == ["borg_observe", "borg_rescue", "borg_runtime_fingerprint"]


def test_mcp_stdio_canary_accepts_installed_package_runtime_fingerprint(monkeypatch, tmp_path):
    borg_mcp = tmp_path / "borg-mcp"
    borg_mcp.write_text("stub")
    payload = {
        "success": True,
        "borg_version": "1.2.3",
        "source_version": None,
        "version_matches_source": False,
        "reload_status": "reload_or_patch_required",
        "confidence_gate_canary": {"passed": True},
        "observe_behavior_canary": {"passed": True, "meta_prompt_failed_closed": True},
        "loaded_function_hashes": {"borg.integrations.mcp_server.borg_observe": {"sha256": "x"}},
    }
    responses = [
        {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "borg-mcp-server", "version": "1.2.3"}}},
        {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "borg_rescue"}, {"name": "borg_observe"}, {"name": "borg_runtime_fingerprint"}]}},
        {"jsonrpc": "2.0", "id": 3, "result": {"content": [{"text": "ACTION\nSTOP\nVERIFY"}]}},
        {"jsonrpc": "2.0", "id": 4, "result": {"content": [{"text": json.dumps(payload)}]}},
    ]

    def fake_run_cmd(name, cmd, **kwargs):
        return canary.CommandResult(
            name=name,
            command=list(cmd),
            returncode=0,
            passed=True,
            stdout="\n".join(json.dumps(item) for item in responses) + "\n",
            stderr="",
            duration_s=0.01,
            detail="exit=0",
        )

    monkeypatch.setattr(canary, "run_cmd", fake_run_cmd)

    result = canary.mcp_stdio_canary(borg_mcp, {}, "1.2.3")

    assert result["passed"] is True
    assert result["fingerprint_signal"] is True
    assert result["fingerprint_summary"]["installed_package_signal"] is True


def test_installed_distribution_probe_rejects_non_vcs_direct_url(monkeypatch, tmp_path):
    fake = canary.CommandResult(
        name="python_distribution_probe",
        command=["python", "-c", "..."],
        returncode=0,
        passed=True,
        stdout=json.dumps({
            "version": "1.2.3",
            "dist_version": "1.2.3",
            "file": str(tmp_path / "site-packages" / "borg" / "__init__.py"),
            "direct_url": {"url": "https://example.invalid/archive.zip"},
        }),
        stderr="",
        duration_s=0.01,
        detail="exit=0",
    )
    monkeypatch.setattr(canary, "run_cmd", lambda *args, **kwargs: fake)

    result = canary.installed_distribution_probe(tmp_path / "bin" / "python", "1.2.3")

    assert result["passed"] is False
