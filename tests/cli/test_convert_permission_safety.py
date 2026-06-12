"""D-018: `borg convert --all` crashed with PermissionError for every non-root
user of the published wheel — the maintainer-pack fallback paths live under
/root (0700 everywhere), and on Python 3.12 Path.exists()/is_dir() RAISE
PermissionError for paths under an untraversable directory instead of
returning False. Unreadable fallback dirs must mean "not there", never a crash."""

from __future__ import annotations

import sys
from pathlib import Path

from borg.cli import main
from borg.core.dirs import safe_dir_exists


class _ForbiddenPath:
    """Mimics a path under untraversable /root on py3.12: stat raises EACCES."""

    def exists(self):
        raise PermissionError(13, "Permission denied")

    def is_dir(self):
        raise PermissionError(13, "Permission denied")


def test_safe_dir_exists_swallows_eacces():
    assert safe_dir_exists(_ForbiddenPath()) is False
    assert safe_dir_exists(Path("/nonexistent/nowhere")) is False


def test_convert_all_survives_forbidden_fallback_dir(tmp_path, monkeypatch, capsys):
    # Simulate the published-wheel-on-user-machine condition: every probe of
    # the hardcoded /root/... fallback raises EACCES (as it does for any
    # non-root user). convert --all must still succeed from bundled seeds.
    import pathlib as _pathlib

    real_path_cls = _pathlib.Path

    def fake_path(*args, **kwargs):
        if args and str(args[0]).startswith("/root/hermes-workspace"):
            return _ForbiddenPath()
        return real_path_cls(*args, **kwargs)

    monkeypatch.setenv("BORG_HOME", str(tmp_path / "home"))
    # borg.cli does `import pathlib` at function scope, so patch the module
    # global; the fake delegates everything except the forbidden prefix.
    monkeypatch.setattr(_pathlib, "Path", fake_path)
    monkeypatch.setattr(sys, "argv", [
        "borg", "convert", ".", "--format", "openclaw", "--all",
        "--output", str(tmp_path / "openclaw"),
    ])
    code = main()
    out = capsys.readouterr()
    assert "Permission denied" not in out.err, out.err
    assert code == 0, out.err
    assert "Converted" in out.out
    assert (tmp_path / "openclaw" / "SKILL.md").exists()


def test_convert_all_works_from_clean_home(tmp_path, monkeypatch, capsys):
    # The canary contract: clean home, bundled seeds only, expected files exist.
    monkeypatch.setenv("BORG_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(sys, "argv", [
        "borg", "convert", ".", "--format", "openclaw", "--all",
        "--output", str(tmp_path / "openclaw"),
    ])
    assert main() == 0
    for rel in ("SKILL.md", "references/pack-index.md", "references/packs/systematic-debugging.md"):
        assert (tmp_path / "openclaw" / rel).exists(), rel
