from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
PLAN_PATH = REPO / 'eval' / 'new_home_scale_hardening_plan.json'


def test_plan_file_exists_and_valid_json() -> None:
    assert PLAN_PATH.exists(), f'missing plan: {PLAN_PATH}'
    json.loads(PLAN_PATH.read_text(encoding='utf-8'))


def test_plan_has_required_hard_gates_and_artifacts() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding='utf-8'))

    assert plan.get('status') == 'complete'
    gates = {g['id']: g for g in plan.get('hard_gates', [])}
    expected_gate_ids = {
        'remote-parity',
        'migration-consistency-tests',
        'security-baseline',
        'first-user-readiness',
    }
    assert expected_gate_ids.issubset(set(gates.keys()))

    # only enforce artifact existence for local-repo artifacts
    local_artifacts = [
        Path(gates['migration-consistency-tests']['proof_artifact']),
        Path('eval/tests/test_first_user_external_readiness.py'),
    ]
    missing = [str(REPO / p) for p in local_artifacts if not (REPO / p).exists()]
    assert not missing, f'missing local proof artifacts: {missing}'


def test_plan_points_to_new_home_active_repo() -> None:
    plan = json.loads(PLAN_PATH.read_text(encoding='utf-8'))
    active = plan['repo']['active']
    assert active == 'https://github.com/borg-farther/Borg-Directory.git'
    assert plan['operating_model']['write_target'] == 'origin_only'
    assert plan['operating_model']['legacy_policy'] == 'read_only_archive'
