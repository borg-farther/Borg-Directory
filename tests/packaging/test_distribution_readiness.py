from __future__ import annotations

from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


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


def test_packaged_seed_data_includes_markdown_files() -> None:
    """Fresh wheels must include the bundled markdown seed corpus used by borg rescue/debug."""
    pyproject = _repo_root() / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    package_data = data["tool"]["setuptools"]["package-data"]["borg"]
    assert "seeds_data/*.md" in package_data
    assert "seeds_data/*/*.md" in package_data
    assert (_repo_root() / "borg" / "seeds_data" / "systematic-debugging.md").exists()
    assert (_repo_root() / "borg" / "seeds_data" / "borg" / "SKILL.md").exists()


def test_borg_install_entrypoint_is_safe_alias() -> None:
    """The legacy borg-install script must not wire users to stale removed commands."""
    data = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert scripts["borg-install"] == "borg.cli.install:main"

    install_py = (_repo_root() / "borg" / "cli" / "install.py").read_text(encoding="utf-8")
    assert "setup-claude --scope user --verify --fix" in install_py
    assert '"serve"' not in install_py


def test_base_install_keeps_sentence_transformers_optional() -> None:
    """Day-one install must not require the heavy embedding stack unless opted in."""
    data = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    base_deps = data["project"].get("dependencies", [])
    assert not any(dep.startswith("sentence-transformers") for dep in base_deps)
    assert any(dep.startswith("sentence-transformers") for dep in data["project"]["optional-dependencies"]["semantic"])


def test_first_user_release_gate_script_exists() -> None:
    """Production readiness must be decided by an executable gate, not by docs alone."""
    gate = _repo_root() / "eval" / "run_first_user_release_gate.py"
    text = gate.read_text(encoding="utf-8")
    assert "borg rescue" in text
    assert "borg-doctor" in text
    assert "guild://hermes/systematic-debugging" in text
    assert "first_user_release_gate_snapshot.json" in text
