#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
IMPACT = REPO / 'eval' / 'borg_human_impact_os.json'
PUBLIC_IMPACT = REPO / 'docs' / 'public' / 'impact' / 'impact.json'
CASE_STUDIES_PROOF = REPO / 'docs' / 'public' / 'proof' / 'case-studies.json'
CASE_STUDIES_IMPACT = REPO / 'docs' / 'public' / 'impact' / 'case-studies.json'
CASE_STUDIES_PROOF_HTML = REPO / 'docs' / 'public' / 'proof' / 'index.html'
GATE = REPO / 'eval' / 'gate_run_snapshot.json'


def main() -> int:
    impact = json.loads(IMPACT.read_text(encoding='utf-8'))
    public = json.loads(PUBLIC_IMPACT.read_text(encoding='utf-8'))
    gate = json.loads(GATE.read_text(encoding='utf-8'))

    required = ['human_questions', 'impact_answers', 'scorecard', 'message_map', 'next_actions']
    missing = [k for k in required if k not in impact]
    if missing:
        raise SystemExit(f"[human-impact-lint] FAIL missing keys: {missing}")

    if len(impact['human_questions']) < 5:
        raise SystemExit('[human-impact-lint] FAIL requires at least 5 human questions')

    if not CASE_STUDIES_PROOF.exists() or not CASE_STUDIES_IMPACT.exists() or not CASE_STUDIES_PROOF_HTML.exists():
        raise SystemExit('[human-impact-lint] FAIL missing case-study proof artifacts')

    case_studies = json.loads(CASE_STUDIES_PROOF.read_text(encoding='utf-8'))
    roles = {x.get('role') for x in case_studies.get('case_studies', [])}
    if roles != {'operator', 'builder', 'executive'}:
        raise SystemExit(f"[human-impact-lint] FAIL bad case-study roles: {sorted(roles)}")

    mirrored = json.loads(CASE_STUDIES_IMPACT.read_text(encoding='utf-8'))
    if case_studies != mirrored:
        raise SystemExit('[human-impact-lint] FAIL impact/proof case-study payload mismatch')

    for key in ['ready_for_10', 'ready_for_100', 'all_pass']:
        if public['readiness'][key] != gate[key]:
            raise SystemExit(f"[human-impact-lint] FAIL readiness mismatch on {key}")

    bad_tokens = ['todo', 'tbd', 'placeholder', 'fixme']
    txt = (
        json.dumps(impact).lower()
        + json.dumps(public).lower()
        + json.dumps(case_studies).lower()
    )
    for token in bad_tokens:
        if token in txt:
            raise SystemExit(f"[human-impact-lint] FAIL bad token: {token}")

    print('[human-impact-lint] PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
