from __future__ import annotations

import json
import multiprocessing as mp
import os
from pathlib import Path
import queue

import pytest

from borg.core import agent_priming as agent_priming_module
from borg.core.agent_priming import install_agent_priming, uninstall_agent_priming


def _concurrent_install_worker(home: str, target: str, barrier, out) -> None:
    os.environ["BORG_HOME"] = home
    try:
        barrier.wait(10)
        result = install_agent_priming("claude-code", target_file=Path(target))
        out.put({"home": home, "target": target, "status": "ok", "manifest_target": result["manifest"]["target_file"]})
    except Exception as exc:  # pragma: no cover - exercised in subprocess
        out.put({"home": home, "target": target, "status": "err", "error": f"{type(exc).__name__}: {exc}"})


def _concurrent_host_install_worker(home: str, host: str, target: str, barrier, out) -> None:
    os.environ["BORG_HOME"] = home
    try:
        barrier.wait(10)
        result = install_agent_priming(host, target_file=Path(target))
        out.put({"host": host, "target": target, "status": "ok", "manifest_target": result["manifest"]["target_file"]})
    except Exception as exc:  # pragma: no cover - exercised in subprocess
        out.put({"host": host, "target": target, "status": "err", "error": f"{type(exc).__name__}: {exc}"})


def _codes(result: dict) -> set[str]:
    return {str(item.get("code")) for item in result.get("fallback_states", []) if isinstance(item, dict)}


def test_agent_priming_install_dry_run_writes_nothing_and_reports_manifest_plan(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"

    result = install_agent_priming("claude-code", target_file=target, dry_run=True)

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["changed"] is True
    assert result["operation"] == "install"
    assert result["target_file"] == str(target)
    assert result["manifest_path"].endswith("agent-priming/claude-code/manifest.json")
    assert "DRY_RUN_NO_WRITE" in _codes(result)
    assert not target.exists()
    assert not (tmp_path / "borg-home").exists()


def test_agent_priming_install_rejects_target_manifest_same_path_even_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"

    with pytest.raises(ValueError, match="manifest path must differ from target file"):
        install_agent_priming("claude-code", target_file=target, manifest_path=target, dry_run=True)

    assert not target.exists()


def test_agent_priming_install_appends_managed_block_without_clobbering_user_text_and_uninstalls_only_block(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    target.write_text("# user-authored project rules\nkeep this line\n", encoding="utf-8")

    install = install_agent_priming("claude-code", target_file=target)

    assert install["success"] is True
    assert install["changed"] is True
    assert install["created_file"] is False
    assert install["operation"] == "install"
    text = target.read_text(encoding="utf-8")
    assert text.startswith("# user-authored project rules\nkeep this line\n")
    assert "BEGIN BORG AGENT PRIMING" in text
    assert "install_id=" in text
    assert "borg_observe" in text
    manifest_path = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1.0"
    assert manifest["host"] == "claude-code"
    assert manifest["target_file"] == str(target)
    assert manifest["manifest_path"] == str(manifest_path)
    assert os.path.isabs(manifest["target_file"])
    assert os.path.isabs(manifest["manifest_path"])
    assert manifest["mode"] == "managed_block"
    assert manifest["created_file"] is False
    assert manifest["install_id"]
    assert manifest["manifest_hmac_sha256"].startswith("sha256:")

    uninstall = uninstall_agent_priming("claude-code")

    assert uninstall["success"] is True
    assert uninstall["changed"] is True
    assert target.read_text(encoding="utf-8") == "# user-authored project rules\nkeep this line\n"
    assert not manifest_path.exists()


def test_agent_priming_install_is_idempotent_for_existing_managed_block(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "AGENTS.md"

    first = install_agent_priming("codex", target_file=target)
    manifest = tmp_path / "borg-home" / "agent-priming" / "codex" / "manifest.json"
    first_manifest_text = manifest.read_text(encoding="utf-8")
    second = install_agent_priming("codex", target_file=target)

    assert first["success"] is True
    assert first["changed"] is True
    assert second["success"] is True
    assert second["changed"] is False
    assert second["status"] == "already_installed"
    assert manifest.read_text(encoding="utf-8") == first_manifest_text
    assert target.read_text(encoding="utf-8").count("BEGIN BORG AGENT PRIMING") == 1


def test_agent_priming_reinstall_same_target_allows_verified_prompt_update(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "AGENTS.md"
    target.write_text("# user rules\n", encoding="utf-8")

    first = install_agent_priming("codex", target_file=target)
    before = target.read_text(encoding="utf-8")
    assert first["status"] == "appended_managed_block"

    original_builder = agent_priming_module.build_agent_priming_candidate

    def upgraded_candidate(host="generic"):
        candidate = dict(original_builder(host))
        candidate["prompt"] = candidate["prompt"] + "- Keep Borg fallback provenance visible after local seed or lexical fallback results.\n"
        candidate["prompt_sha256"] = agent_priming_module._sha256_ref(candidate["prompt"])
        candidate["score"] = agent_priming_module.score_agent_priming(candidate["prompt"])
        candidate["recommendation"] = "eligible_for_host_rules_review"
        return candidate

    monkeypatch.setattr(agent_priming_module, "build_agent_priming_candidate", upgraded_candidate)

    second = install_agent_priming("codex", target_file=target)

    assert second["success"] is True
    assert second["changed"] is True
    assert second["status"] == "updated_managed_block"
    after = target.read_text(encoding="utf-8")
    assert after.startswith("# user rules\n")
    assert after.count("BEGIN BORG AGENT PRIMING") == 1
    assert "Keep Borg fallback provenance visible" in after
    assert after != before
    updated_match = agent_priming_module._find_host_block(after, "codex")
    assert updated_match is not None
    assert second["manifest"]["managed_block_sha256"] == agent_priming_module._sha256_ref(updated_match.group(0))

    uninstall_agent_priming("codex")

    assert target.read_text(encoding="utf-8") == "# user rules\n"



def test_agent_priming_default_manifest_rejects_second_target_without_orphaning_first(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    first = tmp_path / "project-a" / "CLAUDE.md"
    second = tmp_path / "project-b" / "CLAUDE.md"
    first.parent.mkdir()
    second.parent.mkdir()

    install_agent_priming("claude-code", target_file=first)
    manifest = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"
    before_first = first.read_text(encoding="utf-8")
    before_manifest = manifest.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="manifest target mismatch"):
        install_agent_priming("claude-code", target_file=second)

    assert first.read_text(encoding="utf-8") == before_first
    assert manifest.read_text(encoding="utf-8") == before_manifest
    assert not second.exists()

    uninstall_agent_priming("claude-code")

    assert not manifest.exists()
    assert "BEGIN BORG AGENT PRIMING" not in (first.read_text(encoding="utf-8") if first.exists() else "")
    assert not second.exists()


def test_agent_priming_concurrent_default_manifest_install_does_not_orphan_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    targets = [tmp_path / "project-a" / "CLAUDE.md", tmp_path / "project-b" / "CLAUDE.md"]
    for target in targets:
        target.parent.mkdir()
    barrier = mp.Barrier(2)
    out = mp.Queue()
    processes = [
        mp.Process(target=_concurrent_install_worker, args=(str(tmp_path / "borg-home"), str(target), barrier, out))
        for target in targets
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert all(process.exitcode == 0 for process in processes)

    rows = []
    for _ in processes:
        try:
            rows.append(out.get(timeout=5))
        except queue.Empty:  # pragma: no cover - diagnostic assertion path
            pytest.fail("concurrent install worker did not report a result")

    ok_rows = [row for row in rows if row["status"] == "ok"]
    err_rows = [row for row in rows if row["status"] == "err"]
    assert len(ok_rows) == 1, rows
    assert len(err_rows) == 1, rows
    assert "manifest target mismatch" in err_rows[0]["error"]

    manifest = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"
    assert manifest.exists()
    installed_target = Path(ok_rows[0]["target"])
    blocked_target = Path(err_rows[0]["target"])
    assert json.loads(manifest.read_text(encoding="utf-8"))["target_file"] == str(installed_target)
    assert installed_target.read_text(encoding="utf-8").count("BEGIN BORG AGENT PRIMING") == 1
    assert not blocked_target.exists()

    uninstall_agent_priming("claude-code")

    assert not manifest.exists()
    for target in targets:
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        assert "BEGIN BORG AGENT PRIMING" not in text


def test_agent_priming_concurrent_first_installs_share_one_hmac_key(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    hosts = ["claude-code", "codex"]
    targets = {host: tmp_path / host / "AGENTS.md" for host in hosts}
    for target in targets.values():
        target.parent.mkdir()
    barrier = mp.Barrier(2)
    out = mp.Queue()
    processes = [
        mp.Process(
            target=_concurrent_host_install_worker,
            args=(str(tmp_path / "borg-home"), host, str(targets[host]), barrier, out),
        )
        for host in hosts
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert all(process.exitcode == 0 for process in processes)

    rows = []
    for _ in processes:
        try:
            rows.append(out.get(timeout=5))
        except queue.Empty:  # pragma: no cover - diagnostic assertion path
            pytest.fail("concurrent install worker did not report a result")
    assert all(row["status"] == "ok" for row in rows), rows

    key_path = tmp_path / "borg-home" / "agent-priming" / ".manifest-hmac-key"
    key_text = key_path.read_text(encoding="utf-8")
    assert key_text.strip()

    for host in hosts:
        manifest = tmp_path / "borg-home" / "agent-priming" / host / "manifest.json"
        assert manifest.exists()
        assert json.loads(manifest.read_text(encoding="utf-8"))["target_file"] == str(targets[host])
        # Idempotent reinstall validates the manifest HMAC with the shared key.
        again = install_agent_priming(host, target_file=targets[host])
        assert again["status"] == "already_installed"

    assert key_path.read_text(encoding="utf-8") == key_text

    for host in hosts:
        uninstall_agent_priming(host)
        text = targets[host].read_text(encoding="utf-8") if targets[host].exists() else ""
        assert "BEGIN BORG AGENT PRIMING" not in text


def test_agent_priming_concurrent_different_hosts_same_target_preserves_both_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    hosts = ["claude-code", "codex"]
    target = tmp_path / "shared" / "AGENTS.md"
    target.parent.mkdir()
    target.write_text("# shared user rules\n", encoding="utf-8")
    barrier = mp.Barrier(2)
    out = mp.Queue()
    processes = [
        mp.Process(
            target=_concurrent_host_install_worker,
            args=(str(tmp_path / "borg-home"), host, str(target), barrier, out),
        )
        for host in hosts
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert all(process.exitcode == 0 for process in processes)

    rows = []
    for _ in processes:
        try:
            rows.append(out.get(timeout=5))
        except queue.Empty:  # pragma: no cover - diagnostic assertion path
            pytest.fail("concurrent host install worker did not report a result")
    assert all(row["status"] == "ok" for row in rows), rows

    text = target.read_text(encoding="utf-8")
    assert text.startswith("# shared user rules\n")
    assert text.count("BEGIN BORG AGENT PRIMING") == 2
    for host in hosts:
        assert f"host={host}" in text
        manifest = tmp_path / "borg-home" / "agent-priming" / host / "manifest.json"
        assert manifest.exists()
        assert json.loads(manifest.read_text(encoding="utf-8"))["target_file"] == str(target)

    uninstall_agent_priming("claude-code")
    after_first_uninstall = target.read_text(encoding="utf-8")
    assert "host=claude-code" not in after_first_uninstall
    assert "host=codex" in after_first_uninstall

    uninstall_agent_priming("codex")
    assert target.read_text(encoding="utf-8") == "# shared user rules\n"


def test_agent_priming_concurrent_cross_home_same_target_preserves_both_blocks(tmp_path, monkeypatch):
    hosts = ["claude-code", "codex"]
    homes = {"claude-code": tmp_path / "home-a", "codex": tmp_path / "home-b"}
    target = tmp_path / "shared" / "AGENTS.md"
    target.parent.mkdir()
    target.write_text("# shared user rules\n", encoding="utf-8")
    barrier = mp.Barrier(2)
    out = mp.Queue()
    processes = [
        mp.Process(
            target=_concurrent_host_install_worker,
            args=(str(homes[host]), host, str(target), barrier, out),
        )
        for host in hosts
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert all(process.exitcode == 0 for process in processes)

    rows = []
    for _ in processes:
        try:
            rows.append(out.get(timeout=5))
        except queue.Empty:  # pragma: no cover - diagnostic assertion path
            pytest.fail("cross-home concurrent host install worker did not report a result")
    assert all(row["status"] == "ok" for row in rows), rows

    text = target.read_text(encoding="utf-8")
    assert text.startswith("# shared user rules\n")
    assert text.count("BEGIN BORG AGENT PRIMING") == 2
    for host in hosts:
        assert f"host={host}" in text
        manifest = homes[host] / "agent-priming" / host / "manifest.json"
        assert manifest.exists()
        assert json.loads(manifest.read_text(encoding="utf-8"))["target_file"] == str(target)

    monkeypatch.setenv("BORG_HOME", str(homes["claude-code"]))
    uninstall_agent_priming("claude-code")
    after_first_uninstall = target.read_text(encoding="utf-8")
    assert "host=claude-code" not in after_first_uninstall
    assert "host=codex" in after_first_uninstall

    monkeypatch.setenv("BORG_HOME", str(homes["codex"]))
    uninstall_agent_priming("codex")
    assert target.read_text(encoding="utf-8") == "# shared user rules\n"



def test_agent_priming_cross_home_same_host_same_target_requires_local_manifest(tmp_path, monkeypatch):
    target = tmp_path / "shared" / "AGENTS.md"
    target.parent.mkdir()
    target.write_text("# shared user rules\n", encoding="utf-8")
    first_home = tmp_path / "home-a"
    second_home = tmp_path / "home-b"

    monkeypatch.setenv("BORG_HOME", str(first_home))
    first = install_agent_priming("claude-code", target_file=target)
    first_manifest = first_home / "agent-priming" / "claude-code" / "manifest.json"
    assert first["status"] == "appended_managed_block"
    assert first_manifest.exists()

    monkeypatch.setenv("BORG_HOME", str(second_home))
    with pytest.raises(ValueError, match="cross-profile adoption"):
        install_agent_priming("claude-code", target_file=target)

    assert target.read_text(encoding="utf-8").count("BEGIN BORG AGENT PRIMING") == 1
    assert not (second_home / "agent-priming" / "claude-code" / "manifest.json").exists()

    monkeypatch.setenv("BORG_HOME", str(first_home))
    uninstall_agent_priming("claude-code")
    assert target.read_text(encoding="utf-8") == "# shared user rules\n"



def test_agent_priming_concurrent_cross_home_same_host_same_target_allows_single_owner(tmp_path, monkeypatch):
    homes = [tmp_path / "home-a", tmp_path / "home-b"]
    target = tmp_path / "shared" / "AGENTS.md"
    target.parent.mkdir()
    target.write_text("# shared user rules\n", encoding="utf-8")
    barrier = mp.Barrier(2)
    out = mp.Queue()
    processes = [
        mp.Process(target=_concurrent_install_worker, args=(str(home), str(target), barrier, out))
        for home in homes
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(15)
    for process in processes:
        if process.is_alive():
            process.terminate()
            process.join(5)
    assert all(process.exitcode == 0 for process in processes)

    rows = []
    for _ in processes:
        try:
            rows.append(out.get(timeout=5))
        except queue.Empty:  # pragma: no cover - diagnostic assertion path
            pytest.fail("cross-home same-host install worker did not report a result")

    ok_rows = [row for row in rows if row["status"] == "ok"]
    err_rows = [row for row in rows if row["status"] == "err"]
    assert len(ok_rows) == 1, rows
    assert len(err_rows) == 1, rows
    assert "cross-profile adoption" in err_rows[0]["error"]

    text = target.read_text(encoding="utf-8")
    assert text.startswith("# shared user rules\n")
    assert text.count("BEGIN BORG AGENT PRIMING") == 1
    assert "host=claude-code" in text

    owner_home = Path(ok_rows[0]["home"])
    losing_home = Path(err_rows[0]["home"])
    assert (owner_home / "agent-priming" / "claude-code" / "manifest.json").exists()
    assert not (losing_home / "agent-priming" / "claude-code" / "manifest.json").exists()

    monkeypatch.setenv("BORG_HOME", str(owner_home))
    uninstall_agent_priming("claude-code")
    assert target.read_text(encoding="utf-8") == "# shared user rules\n"



def test_agent_priming_idempotent_install_rejects_tampered_existing_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "AGENTS.md"
    install_agent_priming("codex", target_file=target)
    manifest = tmp_path / "borg-home" / "agent-priming" / "codex" / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["target_file"] = str(tmp_path / "other.md")
    manifest.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest hmac mismatch|manifest target mismatch"):
        install_agent_priming("codex", target_file=target)

    assert target.read_text(encoding="utf-8").count("BEGIN BORG AGENT PRIMING") == 1


def test_agent_priming_idempotent_install_missing_hmac_key_fails_without_recreating_key(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "AGENTS.md"
    install_agent_priming("codex", target_file=target)
    key_path = tmp_path / "borg-home" / "agent-priming" / ".manifest-hmac-key"
    manifest = tmp_path / "borg-home" / "agent-priming" / "codex" / "manifest.json"
    before_target = target.read_text(encoding="utf-8")
    before_manifest = manifest.read_text(encoding="utf-8")
    key_path.unlink()

    with pytest.raises(ValueError, match="manifest hmac key missing"):
        install_agent_priming("codex", target_file=target)

    assert not key_path.exists()
    assert target.read_text(encoding="utf-8") == before_target
    assert manifest.read_text(encoding="utf-8") == before_manifest


def test_agent_priming_install_rejects_malformed_existing_borg_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    target.write_text(
        "# user\n<!-- BEGIN BORG AGENT PRIMING host=claude-code prompt_sha256=sha256:bad -->\nstale\n<!-- END BORG AGENT PRIMING -->\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="malformed Borg managed priming marker"):
        install_agent_priming("claude-code", target_file=target)

    assert target.read_text(encoding="utf-8").count("BORG AGENT PRIMING") == 2


def test_agent_priming_uninstall_rejects_mismatched_expected_target(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    other = tmp_path / "OTHER.md"
    install_agent_priming("claude-code", target_file=target)

    with pytest.raises(ValueError, match="target file mismatch"):
        uninstall_agent_priming("claude-code", target_file=other)

    assert "BEGIN BORG AGENT PRIMING" in target.read_text(encoding="utf-8")


def test_agent_priming_install_with_relative_target_uninstalls_original_after_chdir(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    project_a = tmp_path / "a"
    project_b = tmp_path / "b"
    project_a.mkdir()
    project_b.mkdir()
    monkeypatch.chdir(project_a)

    install = install_agent_priming("claude-code", target_file="CLAUDE.md")
    manifest_path = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"

    monkeypatch.chdir(project_b)
    (project_b / "CLAUDE.md").write_text("# unrelated user file\n", encoding="utf-8")
    uninstall = uninstall_agent_priming("claude-code", manifest_path=manifest_path)

    assert install["target_file"] == str(project_a / "CLAUDE.md")
    assert uninstall["target_file"] == str(project_a / "CLAUDE.md")
    assert not (project_a / "CLAUDE.md").exists()
    assert (project_b / "CLAUDE.md").read_text(encoding="utf-8") == "# unrelated user file\n"


def test_agent_priming_install_rolls_back_target_and_hmac_key_when_manifest_write_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    target.write_text("# original\n", encoding="utf-8")
    manifest_parent_file = tmp_path / "not-a-dir"
    manifest_parent_file.write_text("not a directory", encoding="utf-8")
    key_path = tmp_path / "borg-home" / "agent-priming" / ".manifest-hmac-key"

    with pytest.raises((FileExistsError, NotADirectoryError, ValueError, OSError)):
        install_agent_priming("claude-code", target_file=target, manifest_path=manifest_parent_file / "manifest.json")

    assert target.read_text(encoding="utf-8") == "# original\n"
    assert "BEGIN BORG AGENT PRIMING" not in target.read_text(encoding="utf-8")
    assert not key_path.exists()


def test_agent_priming_uninstall_deletes_file_only_when_borg_created_it(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "borg-only.md"

    install = install_agent_priming("generic", target_file=target)
    assert install["created_file"] is True
    assert target.exists()

    uninstall = uninstall_agent_priming("generic")

    assert uninstall["success"] is True
    assert uninstall["removed_target_file"] is True
    assert not target.exists()


def test_agent_priming_uninstall_dry_run_and_unpull_leave_files_intact(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    install_agent_priming("claude-code", target_file=target)
    before = target.read_text(encoding="utf-8")

    dry = uninstall_agent_priming("claude-code", dry_run=True)

    assert dry["dry_run"] is True
    assert dry["changed"] is True
    assert target.read_text(encoding="utf-8") == before
    assert "DRY_RUN_NO_WRITE" in _codes(dry)

    final = uninstall_agent_priming("claude-code")
    assert final["changed"] is True
    assert not target.exists()


def test_agent_priming_uninstall_rolls_back_target_when_manifest_unlink_fails(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    target.write_text("# user\n", encoding="utf-8")
    install_agent_priming("claude-code", target_file=target)
    manifest = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"
    before = target.read_text(encoding="utf-8")
    original_unlink = Path.unlink

    def fail_manifest_unlink(self, *args, **kwargs):
        if self == manifest:
            raise PermissionError("simulated manifest unlink failure")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_manifest_unlink)

    with pytest.raises(PermissionError, match="simulated manifest unlink failure"):
        uninstall_agent_priming("claude-code")

    assert target.read_text(encoding="utf-8") == before
    assert manifest.exists()


def test_agent_priming_refuses_symlink_target_manifest_and_parent_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    real_target = tmp_path / "real.md"
    symlink_target = tmp_path / "linked.md"
    real_target.write_text("safe\n", encoding="utf-8")
    symlink_target.symlink_to(real_target)

    with pytest.raises(ValueError, match="symlink"):
        install_agent_priming("claude-code", target_file=symlink_target)

    manifest_real = tmp_path / "manifest-real.json"
    manifest_link = tmp_path / "manifest-link.json"
    manifest_real.write_text("{}", encoding="utf-8")
    manifest_link.symlink_to(manifest_real)
    with pytest.raises(ValueError, match="symlink"):
        install_agent_priming("claude-code", target_file=tmp_path / "CLAUDE.md", manifest_path=manifest_link)

    real_dir = tmp_path / "real-dir"
    real_dir.mkdir()
    linked_dir = tmp_path / "linked-dir"
    linked_dir.symlink_to(real_dir, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        install_agent_priming("claude-code", target_file=linked_dir / "CLAUDE.md")

    manifest_lock_parent = tmp_path / "borg-home" / "agent-priming" / "claude-code"
    manifest_lock_parent.mkdir(parents=True)
    manifest_lock = manifest_lock_parent / ".manifest.json.lock"
    manifest_lock.symlink_to(real_target)
    with pytest.raises(ValueError, match="symlink"):
        install_agent_priming("claude-code", target_file=tmp_path / "CLAUDE.md")
    manifest_lock.unlink()

    hmac_lock_parent = tmp_path / "borg-home" / "agent-priming"
    hmac_lock = hmac_lock_parent / ".manifest-hmac-key.lock"
    hmac_lock.symlink_to(real_target)
    with pytest.raises(ValueError, match="symlink"):
        install_agent_priming("codex", target_file=tmp_path / "AGENTS.md")


def test_agent_priming_uninstall_rejects_forged_manifest_without_local_hmac(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "victim.md"
    real = install_agent_priming("claude-code", target_file=tmp_path / "real.md")
    victim_text = (tmp_path / "real.md").read_text(encoding="utf-8")
    target.write_text(victim_text, encoding="utf-8")
    forged_manifest = tmp_path / "forged.json"
    forged = dict(real["manifest"])
    forged["target_file"] = str(target)
    forged["manifest_path"] = str(forged_manifest)
    forged["created_file"] = True
    forged.pop("manifest_hmac_sha256", None)
    forged_manifest.write_text(json.dumps(forged), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest hmac"):
        uninstall_agent_priming("claude-code", manifest_path=forged_manifest)

    assert target.exists()
    assert "BEGIN BORG AGENT PRIMING" in target.read_text(encoding="utf-8")


def test_agent_priming_uninstall_fails_closed_when_managed_block_body_or_marker_was_tampered(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    install_agent_priming("claude-code", target_file=target)
    target.write_text(target.read_text(encoding="utf-8").replace("borg_observe", "borg_guess"), encoding="utf-8")

    with pytest.raises(ValueError, match="managed block hash mismatch"):
        uninstall_agent_priming("claude-code")

    with pytest.raises(ValueError, match="managed block hash mismatch"):
        install_agent_priming("claude-code", target_file=target)

    marker_target = tmp_path / "AGENTS.md"
    install_agent_priming("codex", target_file=marker_target)
    marker_target.write_text(
        marker_target.read_text(encoding="utf-8").replace("BEGIN BORG AGENT PRIMING", "BEGIN TAMPERED BORG AGENT PRIMING"),
        encoding="utf-8",
    )
    manifest = tmp_path / "borg-home" / "agent-priming" / "codex" / "manifest.json"

    with pytest.raises(ValueError, match="malformed Borg managed priming marker|managed block not found"):
        uninstall_agent_priming("codex")

    assert manifest.exists()
    assert "TAMPERED" in marker_target.read_text(encoding="utf-8")


def test_agent_priming_uninstall_fails_closed_when_extra_malformed_borg_marker_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "borg-home"))
    target = tmp_path / "CLAUDE.md"
    install_agent_priming("claude-code", target_file=target)
    manifest = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"
    before = target.read_text(encoding="utf-8")
    target.write_text(
        before
        + "\n<!-- BEGIN BORG AGENT PRIMING host=claude-code prompt_sha256=sha256:stale -->\nstale local instruction\n",
        encoding="utf-8",
    )
    tampered = target.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="malformed Borg managed priming marker"):
        uninstall_agent_priming("claude-code")

    assert target.read_text(encoding="utf-8") == tampered
    assert manifest.exists()
