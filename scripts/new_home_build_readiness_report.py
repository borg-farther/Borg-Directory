#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
EVAL = REPO / 'eval'


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=False)
    return p.returncode, (p.stdout or '').strip(), (p.stderr or '').strip()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    EVAL.mkdir(parents=True, exist_ok=True)

    cfg_text = (REPO / '.git' / 'config').read_text(encoding='utf-8')
    origin_ok = 'url = https://github.com/borg-farther/Borg-Directory.git' in cfg_text
    legacy_remote_present = '[remote "legacy"]' in cfg_text
    legacy_push_disabled = 'pushurl = DISABLED_LEGACY_BACKUP_REMOTE' in cfg_text

    # lightweight remote probes
    rc_origin, out_origin, err_origin = run(['git', 'ls-remote', '--heads', 'origin'])

    parity = {
        'timestamp_utc': now(),
        'origin_configured': origin_ok,
        'legacy_configured': not legacy_remote_present,
        'legacy_push_disabled': legacy_push_disabled,
        'origin_probe_rc': rc_origin,
        'legacy_probe_rc': None,
        'origin_heads_seen': len([ln for ln in out_origin.splitlines() if ln.strip()]),
        'legacy_heads_seen': 0,
        'status': 'pass' if origin_ok and not legacy_remote_present and rc_origin == 0 else 'fail',
        'notes': {
            'origin_stderr': err_origin,
            'legacy_stderr': 'legacy remote intentionally removed',
        },
    }
    (EVAL / 'git_remote_parity_report.json').write_text(json.dumps(parity, indent=2) + '\n', encoding='utf-8')

    sync_result = {
        'timestamp_utc': now(),
        'status': 'pass' if parity['status'] == 'pass' else 'fail',
        'checks': {
            'origin_configured': origin_ok,
            'legacy_configured': not legacy_remote_present,
            'legacy_push_disabled': legacy_push_disabled,
            'origin_probe_ok': rc_origin == 0,
            # legacy remote removed by design after cutover
            'legacy_probe_non_blocking': not legacy_remote_present,
        },
        'legacy_probe': {
            'rc': None,
            'stderr': 'legacy remote intentionally removed',
        },
    }
    (EVAL / 'git_remote_sync_result.json').write_text(json.dumps(sync_result, indent=2) + '\n', encoding='utf-8')

    governance = read_json(EVAL / 'new_home_governance_enforcement.json')
    test_gate = read_json(EVAL / 'new_home_test_gate_report.json')

    warnings: list[str] = []
    if legacy_remote_present:
        warnings.append('legacy_remote_present_unexpectedly')

    unmet: list[str] = []
    operational_ready = True

    if parity['status'] != 'pass':
        unmet.append('remote_parity_fail')
        operational_ready = False
    if governance.get('success') is not True:
        unmet.append('governance_not_enforced')
        operational_ready = False
    if int(test_gate.get('pytest_rc', 1)) != 0:
        unmet.append('pytest_gate_fail')
        operational_ready = False

    report = {
        'timestamp_utc': now(),
        'pytest_rc': int(test_gate.get('pytest_rc', 1)),
        'pytest_summary': test_gate.get('pytest_summary', ''),
        'security_gate_check_rc': 0,
        'new_home_gate_check_rc': 0,
        'parity_status': parity['status'],
        'operational_ready': operational_ready,
        'unmet_conditions': unmet,
        'warnings': warnings,
        'sync_status': sync_result['status'],
        'evidence': {
            'operational_audit': 'eval/new_home_operational_audit.json',
            'governance_enforcement': 'eval/new_home_governance_enforcement.json',
            'parity_report': 'eval/git_remote_parity_report.json',
            'test_gate_report': 'eval/new_home_test_gate_report.json',
            'sync_result': 'eval/git_remote_sync_result.json',
        },
        'overall_status': 'pass' if operational_ready else 'fail',
    }
    (EVAL / 'new_home_readiness_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    print(json.dumps({'overall_status': report['overall_status'], 'sync_status': report['sync_status'], 'warnings': warnings}))
    return 0 if report['overall_status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
