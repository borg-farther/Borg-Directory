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
    # Simulate the published-wheel-on-user-machine condition: the hardcoded
    # maintainer-pack fallback (/root/hermes-workspace/guild-packs, 0700 and
    # absent off the dev VPS) raises EACCES on every probe. convert --all must
    # still succeed from bundled seeds.
    #
    # Patch the Path.exists/is_dir *methods*, NOT the pathlib.Path class.
    # Replacing the class (the old approach) breaks CPython's Path.__new__
    # subclass dispatch -- its `if cls is Path` identity check compares against
    # the swapped module global, so the real Path no longer redirects to
    # PosixPath. On Python <3.12 the base Path then lacks `_flavour`, and
    # pytest's own failure reporter (`Path(os.getcwd())`) crashes with an
    # INTERNALERROR that aborts the whole session and masks every other failure.
    # Patching methods keeps Path construction intact and faithfully models the
    # D-018 EACCES condition. The prefix is the guild-packs fallback only, so it
    # no longer collides with the bundled-package path resolved in borg.cli.
    import pathlib as _pathlib

    forbidden_prefix = "/root/hermes-workspace/guild-packs"
    real_exists = _pathlib.Path.exists
    real_is_dir = _pathlib.Path.is_dir

    def _deny_under_forbidden(real_method):
        def _probe(self, *args, **kwargs):
            if str(self).startswith(forbidden_prefix):
                raise PermissionError(13, "Permission denied")
            return real_method(self, *args, **kwargs)
        return _probe

    monkeypatch.setenv("BORG_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(_pathlib.Path, "exists", _deny_under_forbidden(real_exists))
    monkeypatch.setattr(_pathlib.Path, "is_dir", _deny_under_forbidden(real_is_dir))
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
