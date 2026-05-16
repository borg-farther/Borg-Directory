"""Tests for centralized Borg storage path resolution."""

from pathlib import Path

from borg.core import dirs


class TestBorgPathResolution:
    def test_default_is_home_dot_borg_guild(self, monkeypatch):
        monkeypatch.delenv("BORG_HOME", raising=False)
        monkeypatch.delenv("BORG_DIR", raising=False)
        assert dirs.get_borg_home() == Path.home() / ".borg"
        assert dirs.get_borg_dir() == Path.home() / ".borg" / "guild"
        assert dirs.get_trace_db_path() == Path.home() / ".borg" / "traces.db"
        assert dirs.get_v3_db_path() == Path.home() / ".borg" / "borg_v3.db"

    def test_borg_home_isolates_all_storage(self, monkeypatch, tmp_path):
        home = tmp_path / "borg-home"
        monkeypatch.setenv("BORG_HOME", str(home))
        monkeypatch.delenv("BORG_DIR", raising=False)
        assert dirs.get_borg_home() == home
        assert dirs.get_borg_dir() == home / "guild"
        assert dirs.get_trace_db_path() == home / "traces.db"
        assert dirs.get_v3_db_path() == home / "borg_v3.db"
        assert dirs.get_atom_db_path() == home / "atoms.db"
        assert dirs.get_failure_memory_dir() == home / "failures"

    def test_borg_dir_env_var_backcompat_isolation(self, monkeypatch, tmp_path):
        custom = tmp_path / "legacy-root"
        monkeypatch.delenv("BORG_HOME", raising=False)
        monkeypatch.setenv("BORG_DIR", str(custom))
        assert dirs.get_borg_home() == custom
        assert dirs.get_borg_dir() == custom
        assert dirs.get_trace_db_path() == custom / "traces.db"
        assert dirs.get_v3_db_path() == custom / "borg_v3.db"

    def test_env_vars_expand_tilde(self, monkeypatch):
        monkeypatch.setenv("BORG_HOME", "~/my-borg")
        monkeypatch.delenv("BORG_DIR", raising=False)
        assert dirs.get_borg_home() == Path("~/my-borg").expanduser()
        assert dirs.get_borg_dir() == Path("~/my-borg").expanduser() / "guild"

    def test_borg_dir_env_var_overrides_borg_home_for_workflows(self, monkeypatch, tmp_path):
        home = tmp_path / "home"
        workflow = tmp_path / "workflow"
        monkeypatch.setenv("BORG_HOME", str(home))
        monkeypatch.setenv("BORG_DIR", str(workflow))
        assert dirs.get_borg_home() == home
        assert dirs.get_borg_dir() == workflow

    def test_paths_summary_is_machine_readable(self, monkeypatch, tmp_path):
        home = tmp_path / "borg-home"
        monkeypatch.setenv("BORG_HOME", str(home))
        monkeypatch.delenv("BORG_DIR", raising=False)
        summary = dirs.get_paths_summary()
        assert summary["borg_home"] == str(home)
        assert summary["borg_dir"] == str(home / "guild")
        assert summary["trace_db_path"] == str(home / "traces.db")
        assert summary["v3_db_path"] == str(home / "borg_v3.db")
        assert summary["guild_db_path"] == str(home / "guild" / "guild.db")
