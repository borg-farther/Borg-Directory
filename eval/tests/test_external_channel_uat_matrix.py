from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
MATRIX = REPO / 'eval' / 'external_channel_uat_matrix.json'
DOC = REPO / 'docs' / 'EXTERNAL_CHANNEL_UAT.md'

REQUIRED_CHANNELS = {'telegram', 'discord', 'public_web', 'github_repo'}


def _j(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def test_matrix_and_doc_exist() -> None:
    assert MATRIX.exists(), 'missing eval/external_channel_uat_matrix.json'
    assert DOC.exists(), 'missing docs/EXTERNAL_CHANNEL_UAT.md'


def test_matrix_has_required_channels_and_overall_pass() -> None:
    data = _j(MATRIX)
    assert data.get('overall_status') == 'pass'
    channels = data.get('channels', {})
    assert REQUIRED_CHANNELS.issubset(set(channels.keys()))


def test_each_channel_is_independent_and_passing_with_existing_proof() -> None:
    data = _j(MATRIX)
    channels = data['channels']

    for name in REQUIRED_CHANNELS:
        item = channels[name]
        assert item.get('enabled') is True, f'{name} not enabled'
        assert item.get('independent') is True, f'{name} not marked independent'
        assert item.get('uat_status') == 'pass', f'{name} not pass'

        proofs = item.get('proof_artifacts', [])
        assert proofs, f'{name} has empty proof_artifacts'
        for rel in proofs:
            path = REPO / rel
            assert path.exists(), f'{name} missing proof artifact: {rel}'


def test_discord_standard_references_discord_source() -> None:
    text = (REPO / 'docs' / 'BORG_DISCORD_CHECKPOINT_STANDARD.md').read_text(encoding='utf-8').lower()
    assert 'source: discord' in text
    assert '[borg checkpoint]' in text
