from __future__ import annotations

import re
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')


def _text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_canonical_first_user_docs_use_pypi_install() -> None:
    docs = [
        REPO / 'README.md',
        REPO / 'QUICKSTART.md',
        REPO / 'docs' / 'GETTING_STARTED.md',
        REPO / 'docs' / 'TRYING_BORG.md',
    ]
    for path in docs:
        text = _text(path)
        assert 'pip install agent-borg' in text, f'missing canonical pip install in {path}'


def test_canonical_docs_do_not_require_git_ssh_install() -> None:
    docs = [
        REPO / 'README.md',
        REPO / 'docs' / 'GETTING_STARTED.md',
    ]
    for path in docs:
        text = _text(path)
        assert 'git+ssh://git@github.com/' not in text, f'first-user blocker git+ssh remains in {path}'


def test_pypi_metadata_urls_exist_and_are_consistent() -> None:
    pyproject = _text(REPO / 'pyproject.toml')
    required_lines = [
        '[project.urls]',
        'Homepage = "https://github.com/bensargotest-sys/borg"',
        'Repository = "https://github.com/bensargotest-sys/borg"',
        'Issues = "https://github.com/bensargotest-sys/borg/issues"',
        'Documentation = "https://github.com/bensargotest-sys/borg/tree/main/docs"',
        'readme = "README.md"',
    ]
    for line in required_lines:
        assert line in pyproject


def test_docs_version_matches_package_version() -> None:
    pyproject = _text(REPO / 'pyproject.toml')
    trying = _text(REPO / 'docs' / 'TRYING_BORG.md')

    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, flags=re.MULTILINE)
    assert m, 'missing version in pyproject.toml'
    version = m.group(1)

    assert f'**agent-borg {version}**' in trying


def test_root_license_exists_for_external_users() -> None:
    license_path = REPO / 'LICENSE'
    assert license_path.exists(), 'missing root LICENSE file'
    text = _text(license_path)
    assert 'MIT License' in text
