from __future__ import annotations

from pathlib import Path
import tomllib


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_pyproject_declares_canonical_urls() -> None:
    """Distribution metadata must point to the canonical Borg home."""
    pyproject = _repo_root() / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    urls = data["project"]["urls"]

    expected = "https://github.com/borg-farther/Borg-Directory"
    assert urls["Homepage"] == expected
    assert urls["Repository"] == expected
    assert urls["Documentation"].startswith(expected)
    assert urls["Issues"].startswith(f"{expected}/issues")


def test_readme_contains_offline_onboarding_path() -> None:
    """README must document no-download onboarding for controlled environments."""
    readme = (_repo_root() / "README.md").read_text(encoding="utf-8")
    assert "--no-index --find-links" in readme
    assert "borg setup-claude --scope user --verify --fix" in readme
