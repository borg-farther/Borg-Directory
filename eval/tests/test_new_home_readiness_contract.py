from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')


def _text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_no_false_pass_contract_required_files_exist() -> None:
    required = [
        REPO / 'docs' / '20260422-0909_NEW_HOME_PRODUCTION_CLOSURE.md',
        REPO / 'eval' / 'tests' / 'test_git_home_migration_consistency.py',
        REPO / 'eval' / 'tests' / 'test_new_home_scale_hardening_plan.py',
        REPO / 'scripts' / 'new_home_readiness_gate_check.py',
        REPO / 'eval' / 'new_home_scale_hardening_plan.json',
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f'cannot claim readiness; missing: {missing}'


def test_git_remote_contract_locked() -> None:
    cfg = _text(REPO / '.git' / 'config')
    assert 'url = https://github.com/borg-farther/Borg-Directory.git' in cfg
    assert '[remote "legacy"]' not in cfg
    assert 'DISABLED_LEGACY_BACKUP_REMOTE' not in cfg


def test_canonical_docs_contract_uses_new_home() -> None:
    canonical_files = [
        REPO / 'pyproject.toml',
        REPO / 'docs' / 'QUICKSTART.md',
        REPO / 'docs' / 'TRYING_BORG.md',
        REPO / 'docs' / 'GETTING_STARTED.md',
    ]
    for path in canonical_files:
        text = _text(path)
        assert 'borg-farther/Borg-Directory' in text, f'new-home URL missing in canonical file: {path}'


def test_machine_plan_is_json_and_complete() -> None:
    plan = json.loads(_text(REPO / 'eval' / 'new_home_scale_hardening_plan.json'))
    assert plan.get('status') == 'complete'
