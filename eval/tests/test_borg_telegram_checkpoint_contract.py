from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path('/root/hermes-workspace/borg')
CONTRACT = ROOT / 'eval' / 'borg_telegram_checkpoint_contract.json'
DOC = ROOT / 'docs' / 'BORG_TELEGRAM_CHECKPOINT_STANDARD.md'
LINTER = ROOT / 'scripts' / 'borg_checkpoint_lint.py'


def test_contract_exists_and_has_required_keys() -> None:
    assert CONTRACT.exists(), 'missing borg telegram checkpoint contract'
    data = json.loads(CONTRACT.read_text(encoding='utf-8'))
    required = {
        'version',
        'required_lines',
        'phase_values',
        'source_values',
        'confidence_values',
        'risk_to_checkpoint_count',
        'estimation_defaults',
    }
    assert required.issubset(data.keys())


def test_doc_exists_and_mentions_checkpoint_standard() -> None:
    assert DOC.exists(), 'missing checkpoint standard doc'
    text = DOC.read_text(encoding='utf-8')
    assert '[borg checkpoint]' in text
    assert 'Mechanism Selection (by risk)' in text


def test_linter_passes() -> None:
    result = subprocess.run(
        ['python3', str(LINTER)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS: borg checkpoint lint' in result.stdout
