from __future__ import annotations

from pathlib import Path
import re
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_runtime_version_matches_pyproject() -> None:
    root = _root()
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    init_text = (root / "borg" / "__init__.py").read_text(encoding="utf-8")
    runtime = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", init_text)
    assert runtime, "borg/__init__.py must define __version__"
    assert runtime.group(1) == project


def test_root_license_exists_for_first_user_distribution() -> None:
    license_path = _root() / "LICENSE"
    text = license_path.read_text(encoding="utf-8")
    assert "MIT License" in text
    assert "Permission is hereby granted" in text


def test_ci_optional_dependency_groups_exist() -> None:
    data = tomllib.loads((_root() / "pyproject.toml").read_text(encoding="utf-8"))
    optional = data["project"]["optional-dependencies"]
    assert "dev" in optional
    assert "all" in optional
