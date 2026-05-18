#!/usr/bin/env python3
"""Run Borg runtime fingerprint verification and persist raw outputs.

No restart, no signal, no install, no venv mutation. This script only runs
read-only test/smoke commands and writes a proof artifact.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/root/hermes-workspace/borg')
HERMES = Path('/root/.hermes/hermes-agent')
OUT_JSON = ROOT / 'docs/repo-manifest/20260514_runtime_fingerprint_verification_raw.json'
OUT_MD = ROOT / 'docs/20260514_BORG_RUNTIME_FINGERPRINT_VERIFICATION_RAW.md'

COMMANDS = [
    {
        'name': 'borg_pytest_confidence_runtime_first10',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-m', 'pytest', '-q',
                'tests/readiness/test_confidence_gate.py',
                'tests/mcp/test_borg_observe_confidence_gate.py',
                'tests/mcp/test_runtime_fingerprint.py',
                'tests/readiness/test_first_10_readiness.py'],
        'timeout': 180,
    },
    {
        'name': 'hermes_plugin_guidance_filter_pytest',
        'cwd': str(HERMES),
        'cmd': [sys.executable, '-m', 'pytest', '-q', 'tests/test_borg_auto_trace_guidance_filter.py'],
        'timeout': 180,
    },
    {
        'name': 'local_import_and_call_tool_fingerprint_smoke',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-c', r'''
import json
from borg.core.runtime_fingerprint import runtime_fingerprint
from borg.integrations import mcp_server
fp = runtime_fingerprint()
print('LOCAL_FP_SUCCESS=', fp.get('success'))
print('LOCAL_FP_CANARY_PASSED=', fp.get('confidence_gate_canary', {}).get('passed'))
print('LOCAL_FP_RELOAD_STATUS=', fp.get('reload_status'))
print('LOCAL_FP_BORG_HOME=', fp.get('borg_home'))
print('LOCAL_FP_MCP_PATH=', fp.get('modules', {}).get('borg.integrations.mcp_server', {}).get('path'))
print('LOCAL_FP_MCP_SHA256=', fp.get('modules', {}).get('borg.integrations.mcp_server', {}).get('sha256'))
print('LOCAL_FP_CONFIDENCE_PATH=', fp.get('modules', {}).get('borg.core.confidence_gate', {}).get('path'))
print('LOCAL_FP_CONFIDENCE_SHA256=', fp.get('modules', {}).get('borg.core.confidence_gate', {}).get('sha256'))
print('LOCAL_FP_RUNTIME_PATH=', fp.get('modules', {}).get('borg.core.runtime_fingerprint', {}).get('path'))
print('LOCAL_FP_RUNTIME_SHA256=', fp.get('modules', {}).get('borg.core.runtime_fingerprint', {}).get('sha256'))
parsed = json.loads(mcp_server.call_tool('borg_runtime_fingerprint', {}))
print('CALL_TOOL_SUCCESS=', parsed.get('success'))
print('CALL_TOOL_CANARY_PASSED=', parsed.get('confidence_gate_canary', {}).get('passed'))
print('CALL_TOOL_RELOAD_STATUS=', parsed.get('reload_status'))
print('CALL_TOOL_MCP_PATH=', parsed.get('modules', {}).get('borg.integrations.mcp_server', {}).get('path'))
print('TOOL_SCHEMA_HAS_FP=', any(t.get('name') == 'borg_runtime_fingerprint' for t in mcp_server.TOOLS))
'''],
        'timeout': 60,
    },
    {
        'name': 'needle_scan_all_known_paths',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-c', r'''
from pathlib import Path
needles = ['borg_runtime_fingerprint', 'confidence_gate_canary', 'runtime_fingerprint_json']
paths = [
'/root/hermes-workspace/borg/borg/integrations/mcp_server.py',
'/usr/local/lib/python3.12/dist-packages/borg/integrations/mcp_server.py',
'/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py',
'/home/user/guild-tools/borg/integrations/mcp_server.py',
'/root/hermes-workspace/borg/borg/core/runtime_fingerprint.py',
'/usr/local/lib/python3.12/dist-packages/borg/core/runtime_fingerprint.py',
'/root/hermes-workspace/guild-v2/borg/core/runtime_fingerprint.py',
'/home/user/guild-tools/borg/core/runtime_fingerprint.py',
'/root/hermes-workspace/borg/build/lib/borg/core/runtime_fingerprint.py',
]
for p in paths:
    text = Path(p).read_text()
    print('NEEDLE', p, {n: (n in text) for n in needles}, 'bytes=', len(text))
'''],
        'timeout': 60,
    },
    {
        'name': 'fresh_stdio_mcp_fingerprint_canary',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-c', r'''
import json, subprocess, sys
reqs = [
 {'jsonrpc':'2.0','id':1,'method':'initialize','params':{}},
 {'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}},
 {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'borg_runtime_fingerprint','arguments':{}}},
]
proc = subprocess.Popen([sys.executable, '-m', 'borg.integrations.mcp_server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdin = ''.join(json.dumps(r)+'\n' for r in reqs)
out, err = proc.communicate(stdin, timeout=25)
print('FRESH_MCP_EXIT=', proc.returncode)
print('FRESH_MCP_STDERR_START')
print(err)
print('FRESH_MCP_STDERR_END')
print('FRESH_MCP_STDOUT_START')
print(out)
print('FRESH_MCP_STDOUT_END')
for line in out.splitlines():
    try:
        obj = json.loads(line)
    except Exception:
        continue
    if obj.get('id') == 2:
        names = [t.get('name') for t in obj.get('result', {}).get('tools', [])]
        print('FRESH_MCP_SCHEMA_HAS_FP=', 'borg_runtime_fingerprint' in names)
    if obj.get('id') == 3:
        txt = obj.get('result', {}).get('content', [{}])[0].get('text', '')
        parsed = json.loads(txt)
        print('FRESH_MCP_CALL_SUCCESS=', parsed.get('success'))
        print('FRESH_MCP_CANARY_PASSED=', parsed.get('confidence_gate_canary', {}).get('passed'))
        print('FRESH_MCP_RELOAD_STATUS=', parsed.get('reload_status'))
        print('FRESH_MCP_PATH=', parsed.get('modules', {}).get('borg.integrations.mcp_server', {}).get('path'))
'''],
        'timeout': 60,
    },
    {
        'name': 'no_loss_manifest_generation',
        'cwd': str(ROOT),
        'cmd': [sys.executable, '-c', r'''
import json, subprocess, time
from pathlib import Path
root = Path('/root/hermes-workspace/borg')
proc = subprocess.run(['git','status','--porcelain=v1','-z'], cwd=root, capture_output=True, text=False)
raw = proc.stdout.decode('utf-8', 'replace')
entries = []
parts = [p for p in raw.split('\0') if p]
for item in parts:
    if len(item) < 4:
        continue
    status = item[:2]
    path = item[3:]
    p = path
    if p.startswith('build/lib/') or p.startswith('dist/') or p.endswith(('.egg-info', '.pyc')) or '/__pycache__/' in p:
        classification = 'generated_ignore'; reason = 'generated build/dist/cache artifact; not source of truth'
    elif p.startswith('docs/repo-manifest/'):
        classification = 'commit_doc'; reason = 'cleanup/source-of-truth audit artifact'
    elif p.startswith('docs/') or p in {'README.md','PROJECT_STATUS.md','GO_NO_GO_DECISION.md','LOAD_TEST_REPORT_10.md','LOAD_TEST_REPORT_100.md','LOAD_TEST_REPORT_1000.md','UAT_RESULTS.md'}:
        classification = 'commit_doc'; reason = 'documentation/readiness/proof artifact'
    elif p.startswith('tests/') or p.startswith('eval/tests/') or '/tests/' in p:
        classification = 'commit_test'; reason = 'test coverage or verification artifact'
    elif p.startswith('borg/') or p.startswith('scripts/') or p.startswith('eval/') or p == 'pyproject.toml':
        classification = 'commit_product_code'; reason = 'product/runtime/eval source under canonical repo'
    elif p.startswith('tmp_'):
        classification = 'archive_readonly'; reason = 'temporary audit output; archive before possible deletion'
    else:
        classification = 'review_required'; reason = 'not matched by automatic classifier; human review required before deletion/commit'
    entries.append({'status': status, 'path': p, 'classification': classification, 'reason': reason})
summary = {}
for e in entries:
    summary[e['classification']] = summary.get(e['classification'], 0) + 1
manifest = {'schema_version': 1, 'generated_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'repo': str(root), 'command': 'git status --porcelain=v1 -z', 'returncode': proc.returncode, 'policy': 'no deletion, move, or commit from this manifest alone; archive/diff first', 'summary': summary, 'entries': entries}
out = root / 'docs/repo-manifest/20260514_borg_no_loss_cleanup_manifest.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print('MANIFEST_PATH=', out)
print('GIT_STATUS_RETURN_CODE=', proc.returncode)
print('ENTRY_COUNT=', len(entries))
print('SUMMARY=', json.dumps(summary, sort_keys=True))
print('GIT_STATUS_STDERR=', proc.stderr.decode('utf-8', 'replace'))
'''],
        'timeout': 60,
    },
]

def run_command(spec):
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

results = [run_command(c) for c in COMMANDS]
passed = all(r['returncode'] == 0 for r in results)
proof = {
    'generated_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'policy': 'verification only: no restart, no signal, no install, no venv mutation',
    'passed': passed,
    'results': results,
}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')

lines = []
lines.append('# 20260514 Borg runtime fingerprint verification raw output')
lines.append('')
lines.append(f'generated_at_utc: {proof["generated_at_utc"]}')
lines.append(f'passed: {passed}')
lines.append(f'json: `{OUT_JSON}`')
lines.append('')
for r in results:
    lines.append(f'## {r["name"]}')
    lines.append('')
    lines.append(f'cwd: `{r["cwd"]}`')
    lines.append(f'returncode: `{r["returncode"]}`')
    lines.append(f'duration_sec: `{r["duration_sec"]}`')
    lines.append('')
    lines.append('### command')
    lines.append('```')
    lines.append(' '.join(map(str, r['cmd'])))
    lines.append('```')
    lines.append('')
    lines.append('### stdout')
    lines.append('```')
    lines.append(r['stdout'])
    lines.append('```')
    lines.append('')
    lines.append('### stderr')
    lines.append('```')
    lines.append(r['stderr'])
    lines.append('```')
    lines.append('')
OUT_MD.write_text('\n'.join(lines) + '\n')
print('VERIFICATION_PASSED=', passed)
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
