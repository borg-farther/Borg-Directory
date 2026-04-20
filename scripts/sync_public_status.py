#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path('/root/hermes-workspace/borg')
EVAL = REPO / 'eval'
PUBLIC = REPO / 'docs' / 'public'


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    PUBLIC.mkdir(parents=True, exist_ok=True)

    gate = _read_json(EVAL / 'gate_run_snapshot.json')
    value = _read_json(EVAL / 'value_communication_dashboard.json')

    status_payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source': 'eval/gate_run_snapshot.json',
        'snapshot_timestamp': gate.get('timestamp'),
        'ready_for_10': bool(gate.get('ready_for_10', False)),
        'ready_for_100': bool(gate.get('ready_for_100', False)),
        'all_pass': bool(gate.get('all_pass', False)),
        'scoreboard_gates': gate.get('scoreboard_gates', {}),
    }

    value_payload = {
        **value,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'readiness': {
            **value.get('readiness', {}),
            'ready_for_10': bool(gate.get('ready_for_10', False)),
            'ready_for_100': bool(gate.get('ready_for_100', False)),
            'all_pass': bool(gate.get('all_pass', False)),
            'source': 'eval/gate_run_snapshot.json',
        },
    }

    (PUBLIC / 'status.json').write_text(json.dumps(status_payload, indent=2), encoding='utf-8')
    (PUBLIC / 'value.json').write_text(json.dumps(value_payload, indent=2), encoding='utf-8')

    public_index = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>agent-borg public status</title>
  <style>
    body {{ font-family: Inter, system-ui, sans-serif; margin: 24px; background:#0b1020; color:#e7ebff; }}
    .card {{ background:#131a33; border:1px solid #2a3566; border-radius:12px; padding:16px; max-width:920px; }}
    a {{ color:#89b4ff; }}
    .ok {{ color:#6ee7b7; }}
    .bad {{ color:#fca5a5; }}
    code {{ background:#1a2347; padding:2px 6px; border-radius:6px; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>agent-borg public status</h1>
    <p>Generated: <code>{status_payload['generated_at']}</code></p>
    <p>Snapshot: <code>{status_payload.get('snapshot_timestamp')}</code></p>
    <ul>
      <li>ready_for_10: <strong class=\"{'ok' if status_payload['ready_for_10'] else 'bad'}\">{str(status_payload['ready_for_10']).lower()}</strong></li>
      <li>ready_for_100: <strong class=\"{'ok' if status_payload['ready_for_100'] else 'bad'}\">{str(status_payload['ready_for_100']).lower()}</strong></li>
      <li>all_pass: <strong class=\"{'ok' if status_payload['all_pass'] else 'bad'}\">{str(status_payload['all_pass']).lower()}</strong></li>
    </ul>
    <h3>machine artifacts</h3>
    <ul>
      <li><a href=\"status.json\">status.json</a></li>
      <li><a href=\"value.json\">value.json</a></li>
      <li><a href=\"value-dashboard/index.html\">value dashboard</a></li>
      <li><a href=\"impact/index.html\">impact page</a></li>
      <li><a href=\"proof/index.html\">proof case studies</a></li>
    </ul>
  </div>
</body>
</html>
"""
    (PUBLIC / 'index.html').write_text(public_index, encoding='utf-8')

    print(json.dumps({'status': 'ok', 'status_path': str(PUBLIC / 'status.json'), 'value_path': str(PUBLIC / 'value.json')}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
