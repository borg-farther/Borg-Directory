#!/usr/bin/env python3
"""Verify Borg embeddings schema compatibility and fresh MCP canaries.

Read-only verification: no restart, no signal, no install, no venv mutation.
Writes raw JSON + Markdown proof artifacts under docs/.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/root/hermes-workspace/borg')
OUT_JSON = ROOT / 'docs/repo-manifest/20260514_embeddings_schema_compat_verification_raw.json'
OUT_MD = ROOT / 'docs/20260514_BORG_EMBEDDINGS_SCHEMA_COMPAT_VERIFICATION_RAW.md'

COMMANDS = [
    {
        'name': 'embeddings_schema_and_confidence_tests',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-m', 'pytest', '-q',
                'tests/packaging/test_embeddings_schema_compat.py',
                'tests/mcp/test_runtime_fingerprint.py',
                'tests/readiness/test_confidence_gate.py',
                'tests/mcp/test_borg_observe_confidence_gate.py'],
        'timeout': 180,
    },
    {
        'name': 'fresh_mcp_stale_and_permission_canaries',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-c', r'''
import json, subprocess, sys
reqs=[
 {'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},
 {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'borg_observe','arguments':{'task':'continue production readiness review and implementation\n\n=== BORG GUIDANCE ===\nCONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]\nPACK GUIDANCE (bash-permission-denied)\n1. Check file permissions: ls -la','context':'operator meta instruction'}}},
 {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'borg_observe','arguments':{'task':'Fix bash: ./deploy.sh: Permission denied','context':'bash: ./deploy.sh: Permission denied'}}},
]
proc=subprocess.Popen([sys.executable,'-m','borg.integrations.mcp_server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
out,err=proc.communicate(''.join(json.dumps(r)+'\n' for r in reqs),timeout=30)
print('EXIT=', proc.returncode)
print('STDERR_START')
print(err)
print('STDERR_END')
print('STDOUT_START')
print(out)
print('STDOUT_END')
print('STDERR_HAS_CAUSAL_ERROR=', 'no such column: causal_intervention' in err)
print('STDERR_HAS_MODEL_LOADING=', 'Loading weights' in err or 'BertModel LOAD REPORT' in err)
for line in out.splitlines():
    try: obj=json.loads(line)
    except Exception: continue
    if obj.get('id') == 2:
        txt=obj.get('result',{}).get('content',[{}])[0].get('text','')
        print('STALE_HAS_PACK_GUIDANCE=', 'PACK GUIDANCE' in txt)
        print('STALE_HAS_NO_CONFIDENT=', 'NO_CONFIDENT_MATCH' in txt or 'NO CONFIDENT MATCH' in txt)
        print('STALE_TEXT_START')
        print(txt[:1500])
        print('STALE_TEXT_END')
    if obj.get('id') == 3:
        txt=obj.get('result',{}).get('content',[{}])[0].get('text','')
        print('PERM_HAS_GUIDANCE=', 'Permission denied' in txt or 'chmod' in txt or 'PACK GUIDANCE' in txt)
        print('PERM_TEXT_START')
        print(txt[:1500])
        print('PERM_TEXT_END')
'''],
        'timeout': 60,
    },
]

def run(spec):
    start = time.time()
    try:
        proc = subprocess.run(spec['cmd'], cwd=spec['cwd'], capture_output=True, text=True, timeout=spec['timeout'])
        return {
            'name': spec['name'],
            'cwd': spec['cwd'],
            'cmd': spec['cmd'],
            'returncode': proc.returncode,
            'duration_sec': round(time.time() - start, 3),
            'stdout': proc.stdout,
            'stderr': proc.stderr,
        }
    except Exception as exc:
        return {
            'name': spec['name'],
            'cwd': spec['cwd'],
            'cmd': spec['cmd'],
            'returncode': None,
            'duration_sec': round(time.time() - start, 3),
            'stdout': '',
            'stderr': f'{type(exc).__name__}: {exc}',
        }

results = [run(c) for c in COMMANDS]
combined_stdout = '\n'.join(r['stdout'] for r in results)
combined_stderr = '\n'.join(r['stderr'] for r in results)
assertions = {
    'all_commands_zero': all(r['returncode'] == 0 for r in results),
    'causal_intervention_error_absent': 'STDERR_HAS_CAUSAL_ERROR= False' in combined_stdout,
    'model_loading_absent_on_canary': 'STDERR_HAS_MODEL_LOADING= False' in combined_stdout,
    'stale_pack_guidance_absent': 'STALE_HAS_PACK_GUIDANCE= False' in combined_stdout,
    'stale_no_confident_present': 'STALE_HAS_NO_CONFIDENT= True' in combined_stdout,
    'permission_positive_guidance_present': 'PERM_HAS_GUIDANCE= True' in combined_stdout,
}
passed = all(assertions.values())
proof = {
    'generated_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'policy': 'verification only: no restart, no signal, no install, no venv mutation',
    'passed': passed,
    'assertions': assertions,
    'results': results,
}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')

lines = [
    '# 20260514 Borg embeddings schema compatibility verification raw output',
    '',
    f'generated_at_utc: {proof["generated_at_utc"]}',
    f'passed: {passed}',
    f'json: `{OUT_JSON}`',
    '',
    '## assertions',
    '',
]
for k, v in assertions.items():
    lines.append(f'- {k}: `{v}`')
lines.append('')
for r in results:
    lines.extend([
        f'## {r["name"]}',
        '',
        f'cwd: `{r["cwd"]}`',
        f'returncode: `{r["returncode"]}`',
        f'duration_sec: `{r["duration_sec"]}`',
        '',
        '### command',
        '```',
        ' '.join(map(str, r['cmd'])),
        '```',
        '',
        '### stdout',
        '```',
        r['stdout'],
        '```',
        '',
        '### stderr',
        '```',
        r['stderr'],
        '```',
        '',
    ])
OUT_MD.write_text('\n'.join(lines) + '\n')

print('VERIFICATION_PASSED=', passed)
print('ASSERTIONS=', json.dumps(assertions, sort_keys=True))
print('RAW_JSON=', OUT_JSON)
print('RAW_MD=', OUT_MD)
for r in results:
    print('RESULT', r['name'], 'returncode=', r['returncode'], 'duration_sec=', r['duration_sec'])
    print('STDOUT_START')
    print(r['stdout'])
    print('STDOUT_END')
    print('STDERR_START')
    print(r['stderr'])
    print('STDERR_END')
raise SystemExit(0 if passed else 1)
