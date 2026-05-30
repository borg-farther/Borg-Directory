from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from borg.core.agent_priming import install_agent_priming, uninstall_agent_priming


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

    install_agent_priming("claude-code", target_file=target)
    target.write_text(target.read_text(encoding="utf-8").replace("BEGIN BORG AGENT PRIMING", "BEGIN TAMPERED BORG AGENT PRIMING"), encoding="utf-8")
    manifest = tmp_path / "borg-home" / "agent-priming" / "claude-code" / "manifest.json"

    with pytest.raises(ValueError, match="malformed Borg managed priming marker|managed block not found"):
        uninstall_agent_priming("claude-code")

    assert manifest.exists()
    assert "TAMPERED" in target.read_text(encoding="utf-8")


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
