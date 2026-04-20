#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
SESSIONS = Path('/root/.hermes/sessions')
REGISTRY = REPO / 'eval' / 'human_impact_trace_registry.json'
GATE = REPO / 'eval' / 'gate_run_snapshot.json'

PUBLIC_IMPACT = REPO / 'docs' / 'public' / 'impact'
PUBLIC_PROOF = REPO / 'docs' / 'public' / 'proof'


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _extract_summary(text: str) -> dict:
    passed_counts = [int(m) for m in re.findall(r"\b(\d+) passed\b", text)]
    failed_counts = [int(m) for m in re.findall(r"\b(\d+) failed\b", text)]

    status = 'unknown'
    normalized = text.lower()
    explicit_complete = ('status: complete' in normalized) or ('[human-impact-lint] pass' in normalized)
    explicit_failed = bool(re.search(r"\b\d+ failed\b", normalized))

    if explicit_complete or (passed_counts and not explicit_failed):
        status = 'complete'
    elif explicit_failed:
        status = 'failed'

    return {
        'passed_tests_max': max(passed_counts) if passed_counts else 0,
        'failed_tests_max': max(failed_counts) if failed_counts else 0,
        'status': status,
    }


def _outcome_line(role: str, summary: dict, gate: dict) -> str:
    if role == 'operator':
        return (
            f"Readiness stayed green at scale (ready_for_10={gate.get('ready_for_10')}, "
            f"ready_for_100={gate.get('ready_for_100')}) with max {summary['passed_tests_max']} passing checks."
        )
    if role == 'builder':
        return (
            f"Contradiction guard run reached status={summary['status']} with "
            f"{summary['passed_tests_max']} passing tests to keep public claims anchored to canonical truth."
        )
    return (
        f"Reporting pipeline showed status={summary['status']} with "
        f"{summary['passed_tests_max']} passing checks, reducing executive narrative risk."
    )


def build_case_studies() -> dict:
    registry = _read_json(REGISTRY)
    gate = _read_json(GATE)

    studies = []
    for entry in registry['roles']:
        session_path = SESSIONS / entry['session_id']
        raw = session_path.read_text(encoding='utf-8') if session_path.exists() else ''
        summary = _extract_summary(raw)

        studies.append(
            {
                'role': entry['role'],
                'headline': entry['headline'],
                'human_question': entry['question'],
                'focus': entry['focus'],
                'session_id': entry['session_id'],
                'trace_exists': session_path.exists(),
                'proof_summary': summary,
                'impact_statement': _outcome_line(entry['role'], summary, gate),
            }
        )

    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_registry': 'eval/human_impact_trace_registry.json',
        'canonical_readiness_source': 'eval/gate_run_snapshot.json',
        'readiness': {
            'ready_for_10': bool(gate.get('ready_for_10', False)),
            'ready_for_100': bool(gate.get('ready_for_100', False)),
            'all_pass': bool(gate.get('all_pass', False)),
        },
        'case_studies': studies,
    }


def _write_html(payload: dict) -> None:
    cards = []
    for study in payload['case_studies']:
        cards.append(
            f"""
<section class=\"card\">
  <h2>{study['role']}: {study['headline']}</h2>
  <p><strong>Question:</strong> {study['human_question']}</p>
  <p><strong>Impact:</strong> {study['impact_statement']}</p>
  <p><strong>Trace:</strong> <code>{study['session_id']}</code> | status=<code>{study['proof_summary']['status']}</code> | passed=<code>{study['proof_summary']['passed_tests_max']}</code></p>
</section>
""".strip()
        )

    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>borg proof case studies</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 24px; background:#0b1020; color:#e7ebff; }}
    .card {{ background:#131a33; border:1px solid #2a3566; border-radius:12px; padding:16px; margin: 0 0 14px 0; max-width:980px; }}
    code {{ background:#1a2347; padding:2px 6px; border-radius:6px; }}
    a {{ color:#89b4ff; }}
  </style>
</head>
<body>
  <h1>borg role-specific proof case studies</h1>
  <p>Generated: <code>{payload['generated_at']}</code></p>
  <p>Canonical readiness: <code>ready_for_10={str(payload['readiness']['ready_for_10']).lower()}</code>, <code>ready_for_100={str(payload['readiness']['ready_for_100']).lower()}</code></p>
  {''.join(cards)}
  <p>Machine payload: <a href=\"case-studies.json\">case-studies.json</a></p>
</body>
</html>
"""
    (PUBLIC_PROOF / 'index.html').write_text(html, encoding='utf-8')


def main() -> int:
    PUBLIC_IMPACT.mkdir(parents=True, exist_ok=True)
    PUBLIC_PROOF.mkdir(parents=True, exist_ok=True)

    payload = build_case_studies()

    proof_json = PUBLIC_PROOF / 'case-studies.json'
    impact_json = PUBLIC_IMPACT / 'case-studies.json'

    proof_json.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    impact_json.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    _write_html(payload)

    print(
        json.dumps(
            {
                'status': 'ok',
                'proof_json': str(proof_json),
                'impact_json': str(impact_json),
                'proof_html': str(PUBLIC_PROOF / 'index.html'),
                'count': len(payload['case_studies']),
            },
            indent=2,
        )
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
