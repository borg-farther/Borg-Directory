from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
SESSIONS = Path('/root/.hermes/sessions')

REGISTRY = REPO / 'eval' / 'human_impact_trace_registry.json'
PROOF_JSON = REPO / 'docs' / 'public' / 'proof' / 'case-studies.json'
IMPACT_JSON = REPO / 'docs' / 'public' / 'impact' / 'case-studies.json'
PROOF_HTML = REPO / 'docs' / 'public' / 'proof' / 'index.html'
IMPACT_HTML = REPO / 'docs' / 'public' / 'impact' / 'index.html'
PUBLIC_INDEX = REPO / 'docs' / 'public' / 'index.html'


def _j(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def test_case_study_artifacts_exist() -> None:
    assert REGISTRY.exists(), 'missing eval/human_impact_trace_registry.json'
    assert PROOF_JSON.exists(), 'missing docs/public/proof/case-studies.json'
    assert IMPACT_JSON.exists(), 'missing docs/public/impact/case-studies.json'
    assert PROOF_HTML.exists(), 'missing docs/public/proof/index.html'


def test_case_study_roles_are_complete() -> None:
    payload = _j(PROOF_JSON)
    roles = {x['role'] for x in payload['case_studies']}
    assert roles == {'operator', 'builder', 'executive'}


def test_case_study_sessions_exist_and_have_signal() -> None:
    payload = _j(PROOF_JSON)
    for study in payload['case_studies']:
        session_path = SESSIONS / study['session_id']
        assert session_path.exists(), f"missing session trace: {study['session_id']}"
        summary = study['proof_summary']
        assert summary['status'] in {'complete', 'failed', 'unknown'}
        assert isinstance(summary['passed_tests_max'], int)
        assert summary['passed_tests_max'] >= 0


def test_impact_and_proof_payloads_match() -> None:
    assert _j(PROOF_JSON) == _j(IMPACT_JSON)


def test_public_pages_link_case_studies() -> None:
    impact_html = IMPACT_HTML.read_text(encoding='utf-8')
    proof_html = PROOF_HTML.read_text(encoding='utf-8')
    public_html = PUBLIC_INDEX.read_text(encoding='utf-8')

    assert 'case-studies.json' in impact_html
    assert '/proof case studies' in impact_html
    assert 'borg role-specific proof case studies' in proof_html.lower()
    assert 'proof/index.html' in public_html
