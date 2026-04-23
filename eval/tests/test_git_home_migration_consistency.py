from __future__ import annotations

from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
NEW_HOME = 'https://github.com/borg-farther/Borg-Directory'
NEW_HOME_GIT = f'{NEW_HOME}.git'



def _text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_git_config_origin_and_legacy_push_lock() -> None:
    cfg = _text(REPO / '.git' / 'config')
    assert f'url = {NEW_HOME_GIT}' in cfg
    assert '[remote "legacy"]' not in cfg
    assert 'DISABLED_LEGACY_BACKUP_REMOTE' not in cfg


def test_canonical_surfaces_point_to_new_home() -> None:
    files = [
        REPO / 'pyproject.toml',
        REPO / 'docs' / 'QUICKSTART.md',
        REPO / 'docs' / 'TRYING_BORG.md',
        REPO / 'docs' / 'GETTING_STARTED.md',
    ]
    for path in files:
        text = _text(path)
        assert 'borg-farther/Borg-Directory' in text, f'new-home URL missing in {path}'

    pyproject = _text(REPO / 'pyproject.toml')
    assert f'Homepage = "{NEW_HOME}"' in pyproject
    assert f'Repository = "{NEW_HOME}"' in pyproject
    assert f'Issues = "{NEW_HOME}/issues"' in pyproject
    assert f'Documentation = "{NEW_HOME}/tree/main/docs"' in pyproject


def test_required_new_home_artifacts_exist() -> None:
    required = [
        REPO / 'docs' / '20260422-0909_NEW_HOME_PRODUCTION_CLOSURE.md',
        REPO / 'eval' / 'tests' / 'test_git_home_migration_consistency.py',
        REPO / 'eval' / 'tests' / 'test_new_home_scale_hardening_plan.py',
        REPO / 'eval' / 'tests' / 'test_new_home_readiness_contract.py',
        REPO / 'scripts' / 'new_home_readiness_gate_check.py',
        REPO / 'eval' / 'new_home_scale_hardening_plan.json',
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f'missing required new-home artifacts: {missing}'
