from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')

COMM_STANDARD = REPO / 'docs' / 'EXTERNAL_COMMUNICATION_STANDARD.md'
PUBLIC_STATUS_JSON = REPO / 'docs' / 'public' / 'status.json'
PUBLIC_VALUE_JSON = REPO / 'docs' / 'public' / 'value.json'
PUBLIC_INDEX = REPO / 'docs' / 'public' / 'index.html'
PUBLIC_PROOF_INDEX = REPO / 'docs' / 'public' / 'proof' / 'index.html'
PUBLIC_PROOF_CASES = REPO / 'docs' / 'public' / 'proof' / 'case-studies.json'
PUBLIC_IMPACT_CASES = REPO / 'docs' / 'public' / 'impact' / 'case-studies.json'
SYNC_SCRIPT = REPO / 'scripts' / 'sync_public_status.py'
TELEMETRY_SCHEMA = REPO / 'eval' / 'telemetry_event_schema.json'


def test_external_comms_standard_and_public_artifacts_exist() -> None:
    assert COMM_STANDARD.exists(), 'missing docs/EXTERNAL_COMMUNICATION_STANDARD.md'
    assert PUBLIC_STATUS_JSON.exists(), 'missing docs/public/status.json'
    assert PUBLIC_VALUE_JSON.exists(), 'missing docs/public/value.json'
    assert PUBLIC_INDEX.exists(), 'missing docs/public/index.html'
    assert PUBLIC_PROOF_INDEX.exists(), 'missing docs/public/proof/index.html'
    assert PUBLIC_PROOF_CASES.exists(), 'missing docs/public/proof/case-studies.json'
    assert PUBLIC_IMPACT_CASES.exists(), 'missing docs/public/impact/case-studies.json'
    assert SYNC_SCRIPT.exists(), 'missing scripts/sync_public_status.py'
    assert TELEMETRY_SCHEMA.exists(), 'missing eval/telemetry_event_schema.json'


def test_telemetry_schema_has_required_canonical_fields() -> None:
    schema = json.loads(TELEMETRY_SCHEMA.read_text(encoding='utf-8'))
    required = set(schema.get('required', []))
    expected = {
        'event_version',
        'event_name',
        'event_time',
        'run_id',
        'agent_id',
        'task_type',
        'success',
        'latency_ms',
        'tokens_used',
        'source',
    }
    assert expected.issubset(required)
    enum_values = set(schema['properties']['source']['enum'])
    assert enum_values == {'real', 'synthetic'}


def test_public_status_matches_canonical_gate_snapshot() -> None:
    gate = json.loads((REPO / 'eval' / 'gate_run_snapshot.json').read_text(encoding='utf-8'))
    public_status = json.loads(PUBLIC_STATUS_JSON.read_text(encoding='utf-8'))

    assert public_status['ready_for_10'] == gate['ready_for_10']
    assert public_status['ready_for_100'] == gate['ready_for_100']
    assert public_status['all_pass'] == gate['all_pass']


def test_public_value_readiness_matches_gate_truth() -> None:
    gate = json.loads((REPO / 'eval' / 'gate_run_snapshot.json').read_text(encoding='utf-8'))
    public_value = json.loads(PUBLIC_VALUE_JSON.read_text(encoding='utf-8'))

    readiness = public_value.get('readiness', {})
    assert readiness.get('ready_for_10') == gate['ready_for_10']
    assert readiness.get('ready_for_100') == gate['ready_for_100']


def test_canonical_public_docs_do_not_claim_stale_no_go() -> None:
    checked = [
        REPO / 'docs' / 'VALUE_COMMUNICATION_DASHBOARD.md',
        REPO / 'docs' / 'VALUE_COMMUNICATION_DASHBOARD.html',
    ]

    for path in checked:
        text = path.read_text(encoding='utf-8').lower()
        assert 'ready_for_100=false' not in text, f'stale no-go claim in {path}'
        assert '100-user gate is currently red' not in text, f'stale red-gate claim in {path}'


def test_public_proof_payload_integrity() -> None:
    proof = json.loads(PUBLIC_PROOF_CASES.read_text(encoding='utf-8'))
    impact = json.loads(PUBLIC_IMPACT_CASES.read_text(encoding='utf-8'))
    public_index_text = PUBLIC_INDEX.read_text(encoding='utf-8')

    assert proof == impact
    roles = {s['role'] for s in proof.get('case_studies', [])}
    assert roles == {'operator', 'builder', 'executive'}
    assert 'proof/index.html' in public_index_text
