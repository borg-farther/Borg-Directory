"""Release packaging contract tests for first-user PyPI readiness."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_core_dependencies_are_minimal_and_ml_is_optional():
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    deps = data['project'].get('dependencies', [])
    assert deps == ['pyyaml>=6.0']
    optional = data['project'].get('optional-dependencies', {})
    assert any('sentence-transformers' in dep for dep in optional['embeddings'])
    assert all('sentence-transformers' not in dep for dep in deps)
    assert all('torch' not in dep.lower() for dep in deps)


def test_version_consistent_and_above_broken_332_line():
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    version = data['project']['version']
    init = (ROOT / 'borg' / '__init__.py').read_text()
    assert f'__version__ = "{version}"' in init
    assert tuple(map(int, version.split('.'))) >= (3, 3, 3)


def test_public_entrypoints_and_day_one_commands_are_declared():
    data = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    scripts = data['project']['scripts']
    assert scripts['borg'] == 'borg.cli:main'
    assert scripts['borg-mcp'] == 'borg.integrations.mcp_server:main'
    assert scripts['borg-doctor'] == 'borg.cli.doctor:run_doctor'

    cli = (ROOT / 'borg' / 'cli.py').read_text()
    assert 'sub.add_parser("rescue"' in cli
    assert 'sub.add_parser("first-10"' in cli
    assert '_cmd_rescue' in cli
    assert '_cmd_first_10' in cli

    doctor = (ROOT / 'borg' / 'cli' / 'doctor.py').read_text()
    assert 'def run_doctor' in doctor
