from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
SCRIPT = REPO / 'scripts' / 'google_tier_uat_runner.py'
SNAPSHOT = REPO / 'eval' / 'google_tier_uat_snapshot.json'
SCOREBOARD = REPO / 'eval' / 'google_tier_uat_scoreboard.json'
PLAN = REPO / 'eval' / 'google_tier_uat_plan.json'


def _run_uat() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def test_google_tier_plan_exists_and_declares_critical_gates() -> None:
    assert PLAN.exists(), f'missing plan: {PLAN}'
    plan = _read_json(PLAN)
    gate_ids = {g['id'] for g in plan.get('hard_gates', [])}
    assert {
        'git-home-cutover',
        'governance-enforcement',
        'readiness-contract',
        'test-gate',
        'scale-gates',
        'utility-and-savings',
        'anti-theater-artifacts',
    }.issubset(gate_ids)


def test_google_tier_uat_runner_emits_snapshot_and_passes() -> None:
    proc = _run_uat()
    assert proc.returncode == 0, (
        'google-tier UAT runner failed\n'
        f'stdout:\n{proc.stdout}\n\n'
        f'stderr:\n{proc.stderr}\n'
    )

    assert SNAPSHOT.exists(), f'missing snapshot: {SNAPSHOT}'
    assert SCOREBOARD.exists(), f'missing scoreboard: {SCOREBOARD}'

    snapshot = _read_json(SNAPSHOT)
    scoreboard = _read_json(SCOREBOARD)

    assert snapshot.get('overall_status') == 'pass'
    assert snapshot.get('decision') == 'GO'
    assert scoreboard.get('overall_status') == 'pass'
    assert scoreboard.get('decision') == 'GO'

    checks = snapshot.get('checks', [])
    check_map = {c['id']: c for c in checks}
    for check_id in (
        'git-home-cutover',
        'governance-enforcement',
        'readiness-contract',
        'test-gate',
        'scale-gates',
        'utility-and-savings',
        'anti-theater-artifacts',
    ):
        assert check_id in check_map, f'missing check: {check_id}'
        assert check_map[check_id]['passed'] is True, f'failed check: {check_id}'


def test_canonical_decision_docs_are_consistent() -> None:
    _run_uat()

    project_status = (REPO / 'PROJECT_STATUS.md').read_text(encoding='utf-8')
    go_no_go = (REPO / 'GO_NO_GO_DECISION.md').read_text(encoding='utf-8')
    uat_results = (REPO / 'UAT_RESULTS.md').read_text(encoding='utf-8')

    assert 'decision: **GO**' in project_status
    assert 'verdict: **GO**' in go_no_go
    assert 'decision: **GO**' in uat_results
    assert '**PASS**' in project_status
    assert '**PASS**' in go_no_go
    assert '**PASS**' in uat_results
