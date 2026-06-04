from __future__ import annotations

import argparse
from pathlib import Path


def test_openclaw_all_convert_uses_bundled_packs_when_maintainer_path_is_inaccessible(monkeypatch, tmp_path, capsys) -> None:
    """Clean installs must not depend on AB's /root/hermes-workspace guild-packs checkout.

    GitHub Actions exposed a real first-user failure: `borg convert --format openclaw
    --all` tried to probe `/root/hermes-workspace/guild-packs/packs` and failed with
    PermissionError instead of using the packaged seed packs shipped in the wheel.
    """
    import borg.cli as cli
    import borg.core.uri as uri

    empty_borg_home = tmp_path / "isolated-borg-home"
    empty_borg_home.mkdir()
    output_dir = tmp_path / "openclaw"

    monkeypatch.setattr(uri, "get_available_pack_names", lambda: [])
    monkeypatch.setattr(cli, "get_borg_dir", lambda: empty_borg_home)
    monkeypatch.delenv("BORG_TEST_PACKS_DIR", raising=False)
    monkeypatch.delenv("BORG_MAINTAINER_PACKS_DIR", raising=False)

    original_is_dir = Path.is_dir

    def guarded_is_dir(self: Path) -> bool:
        if self.as_posix() == "/root/hermes-workspace/guild-packs/packs":
            raise AssertionError("clean source installs must not probe maintainer-only guild-packs path")
        return original_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", guarded_is_dir)

    convert_cmd = getattr(cli, "_cmd_convert")
    rc = convert_cmd(argparse.Namespace(format="openclaw", all=True, output=str(output_dir), path="."))
    captured = capsys.readouterr()

    assert rc == 0, captured.err
    assert "Converted" in captured.out
    assert (output_dir / "SKILL.md").is_file()
    assert (output_dir / "references" / "pack-index.md").is_file()
    assert (output_dir / "references" / "packs" / "systematic-debugging.md").is_file()
