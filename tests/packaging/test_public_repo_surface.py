from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOT_FILES = {
    ".dockerignore",
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "Dockerfile",
    "index.json",
    "LICENSE",
    "README.md",
    "pyproject.toml",
}

ALLOWED_ROOT_DIRS = {
    ".githooks",
    ".github",
    "benchmarks",
    "borg",
    "deploy",
    "docs",
    "eval",
    "examples",
    "scripts",
    "tests",
}

ROOT_SCRIPT_RE = re.compile(
    r"^(audit|check|debug|inspect|measure|cleanup|verify|run)_.*\.(py|sh)$"
)


def _git_ls_files() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:  # pragma: no cover - non-git sdists
        pytest.skip(f"git tracked-file inventory unavailable: {exc}")
    return [line for line in result.stdout.splitlines() if line]


def test_public_root_contains_only_package_surface() -> None:
    """The GitHub root should look like an installable package, not a scratchpad."""
    tracked = _git_ls_files()

    root_files = sorted(path for path in tracked if "/" not in path)
    root_dirs = sorted({path.split("/", 1)[0] for path in tracked if "/" in path})

    assert root_files == sorted(ALLOWED_ROOT_FILES)
    assert root_dirs == sorted(ALLOWED_ROOT_DIRS)


def test_generated_and_internal_artifacts_are_not_tracked_at_root() -> None:
    tracked = _git_ls_files()
    root_files = [path for path in tracked if "/" not in path]

    assert ".coverage" not in root_files
    assert not any(path.endswith(".pdf") for path in root_files)
    assert not any(path.startswith("test_") and path.endswith(".py") for path in root_files)
    assert not any(ROOT_SCRIPT_RE.match(path) for path in root_files)


def test_archive_has_a_public_boundary_note() -> None:
    archive_readme = (ROOT / "docs" / "archive" / "README.md").read_text(encoding="utf-8")
    assert "not the current first-user product surface" in archive_readme
    assert "root-pdfs/" in archive_readme
    assert "root-scripts/" in archive_readme
    assert "root-tests/" in archive_readme


def test_public_first_user_docs_have_no_unrendered_placeholders() -> None:
    for relative_path in [
        "docs/QUICKSTART.md",
        "docs/TRYING_BORG.md",
        "docs/ONBOARDING.md",
    ]:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "{PRIMING_PARAGRAPH}" not in text
        assert "borg_rescue" in text
        assert "borg_observe" in text
