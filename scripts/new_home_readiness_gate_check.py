#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')


def exists(rel: str) -> bool:
    return (REPO / rel).exists()


def read(rel: str) -> str:
    return (REPO / rel).read_text(encoding='utf-8')


def main() -> None:
    checks = {}

    cfg = read('.git/config')
    checks['origin_new_home'] = 'url = https://github.com/borg-farther/Borg-Directory.git' in cfg
    checks['legacy_remote_removed'] = '[remote "legacy"]' not in cfg
    checks['legacy_push_disabled'] = 'pushurl = DISABLED_LEGACY_BACKUP_REMOTE' not in cfg

    required_files = [
        'docs/20260422-0909_NEW_HOME_PRODUCTION_CLOSURE.md',
        'eval/tests/test_git_home_migration_consistency.py',
        'eval/tests/test_new_home_scale_hardening_plan.py',
        'eval/tests/test_new_home_readiness_contract.py',
        'eval/new_home_scale_hardening_plan.json',
    ]
    checks['required_files_present'] = all(exists(p) for p in required_files)

    canonical_files = [
        'pyproject.toml',
        'docs/TRYING_BORG.md',
        'docs/QUICKSTART.md',
        'docs/GETTING_STARTED.md',
    ]
    checks['legacy_url_absent_from_canonical_files'] = all(
        'borg-farther/Borg-Directory' in read(p) for p in canonical_files
    )

    status = 'pass' if all(checks.values()) else 'fail'

    print(
        json.dumps(
            {
                'status': status,
                'checks': checks,
                'required_files': required_files,
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
