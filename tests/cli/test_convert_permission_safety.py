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

    # Patch the existence PROBES, not the Path constructor. Replacing the
    # `pathlib.Path` module global with a plain function breaks pathlib's
    # internal `cls is Path` identity check inside Path.__new__ on py3.10/3.11:
    # any later Path(...) construction skips the redirect to PosixPath, hits the
    # bare Path class (which has no `_flavour`), and raises AttributeError. That
    # corrupted construction fires inside pytest's own report/teardown/atexit
    # machinery and crashed the whole session (cacheprovider Path._flavour
    # teardown crash). Patching the bound methods keeps Path a real class, so
    # monkeypatch restores it cleanly and unrelated Path() calls stay intact.
    forbidden_prefix = "/root/hermes-workspace"
    real_exists = _pathlib.Path.exists
    real_is_dir = _pathlib.Path.is_dir

    def fake_exists(self, *args, **kwargs):
        if str(self).startswith(forbidden_prefix):
            raise PermissionError(13, "Permission denied")
        return real_exists(self, *args, **kwargs)

    def fake_is_dir(self, *args, **kwargs):
        if str(self).startswith(forbidden_prefix):
            raise PermissionError(13, "Permission denied")
        return real_is_dir(self, *args, **kwargs)

    monkeypatch.setenv("BORG_HOME", str(tmp_path / "home"))
    # borg.cli probes the hardcoded /root/... fallback via Path.exists(); make
    # exactly that probe raise EACCES, the way an untraversable dir does.
    monkeypatch.setattr(_pathlib.Path, "exists", fake_exists)
    monkeypatch.setattr(_pathlib.Path, "is_dir", fake_is_dir)
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
