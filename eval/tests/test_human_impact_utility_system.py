from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')

IMPACT_OS = REPO / 'eval' / 'borg_human_impact_os.json'
IMPACT_DOC = REPO / 'docs' / 'BORG_HUMAN_IMPACT_UTILITY_SYSTEM.md'
IMPACT_PUBLIC_JSON = REPO / 'docs' / 'public' / 'impact' / 'impact.json'
IMPACT_PUBLIC_HTML = REPO / 'docs' / 'public' / 'impact' / 'index.html'
TEAM_DIR = REPO / 'docs' / '20260420-1512_human_impact_team'


def _j(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def test_human_impact_artifacts_exist() -> None:
    assert IMPACT_OS.exists(), 'missing eval/borg_human_impact_os.json'
    assert IMPACT_DOC.exists(), 'missing docs/BORG_HUMAN_IMPACT_UTILITY_SYSTEM.md'
    assert IMPACT_PUBLIC_JSON.exists(), 'missing docs/public/impact/impact.json'
    assert IMPACT_PUBLIC_HTML.exists(), 'missing docs/public/impact/index.html'


def test_team_pack_exists() -> None:
    for name in [
        'CONTEXT_DOSSIER.md',
        'RED_TEAM_REVIEW.md',
        'BLUE_TEAM_ARCHITECTURE.md',
        'GREEN_TEAM_DATA_ANALYSIS.md',
        'SKEPTIC_REVIEW.md',
        'SYNTHESIS_AND_ACTION_PLAN.md',
    ]:
        assert (TEAM_DIR / name).exists(), f'missing team artifact: {name}'


def test_impact_os_has_required_sections() -> None:
    data = _j(IMPACT_OS)
    for key in [
        'human_questions',
        'impact_answers',
        'trust_layer',
        'adoption_snapshot',
        'scorecard',
        'message_map',
        'next_actions',
    ]:
        assert key in data


def test_public_impact_consistent_with_gate_truth() -> None:
    gate = _j(REPO / 'eval' / 'gate_run_snapshot.json')
    impact = _j(IMPACT_PUBLIC_JSON)
    assert impact['readiness']['ready_for_10'] == gate['ready_for_10']
    assert impact['readiness']['ready_for_100'] == gate['ready_for_100']


def test_no_placeholder_tokens() -> None:
    text = '\n'.join([
        IMPACT_OS.read_text(encoding='utf-8').lower(),
        IMPACT_DOC.read_text(encoding='utf-8').lower(),
        IMPACT_PUBLIC_JSON.read_text(encoding='utf-8').lower(),
    ])
    for token in ['todo', 'tbd', 'placeholder', 'fixme', 'lorem']:
        assert token not in text
