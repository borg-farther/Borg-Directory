from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import yaml


def _load_cli_module():
    module_path = Path(__file__).resolve().parents[2] / "borg" / "cli.py"
    spec = importlib.util.spec_from_file_location("borg_cli_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_builtin_packs():
    return getattr(_load_cli_module(), "_load_builtin_packs")()


def _pack_names(packs):
    names: set[str] = set()
    for pack in packs:
        pack_id = str(pack.get("id") or pack.get("name") or "")
        names.add(pack_id.rsplit("/", 1)[-1] if "/" in pack_id else pack_id)
    return names


def test_load_builtin_packs_uses_bundled_seed_packs(monkeypatch):
    monkeypatch.delenv("BORG_TEST_PACKS_DIR", raising=False)

    packs = _load_builtin_packs()
    pack_names = _pack_names(packs)

    assert "systematic-debugging" in pack_names
    assert len(pack_names) == 11
    assert len(pack_names) == len(packs)


def test_load_builtin_packs_only_uses_external_pack_dir_when_explicit(monkeypatch, tmp_path):
    extra_dir = tmp_path / "extra-packs"
    extra_dir.mkdir()
    (extra_dir / "operator-only.yaml").write_text(
        yaml.safe_dump(
            {
                "id": "operator-only-test-pack",
                "name": "Operator Only Test Pack",
                "type": "workflow_pack",
                "phases": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("BORG_TEST_PACKS_DIR", raising=False)
    assert "operator-only-test-pack" not in _pack_names(_load_builtin_packs())

    monkeypatch.setenv("BORG_TEST_PACKS_DIR", os.fspath(extra_dir))
    assert "operator-only-test-pack" in _pack_names(_load_builtin_packs())


def test_package_entrypoint_context_resolves_bundled_seed_packs(monkeypatch):
    """Entry-point imports execute cli.py from borg/cli/__init__.py."""
    monkeypatch.delenv("BORG_TEST_PACKS_DIR", raising=False)
    sys.modules.pop("borg.cli", None)

    import borg.cli as cli

    assert Path(cli.__file__).name == "__init__.py"
    pack_names = _pack_names(getattr(cli, "_load_builtin_packs")())
    assert "systematic-debugging" in pack_names
