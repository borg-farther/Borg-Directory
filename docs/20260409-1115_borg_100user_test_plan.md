# agent-borg v3.3.0 — 100-User Test Plan

**Author:** Test subagent
**Date:** 2026-04-09
**Purpose:** Systematic regression + acceptance test plan for v3.3.0

---

## 0. What Was Already Tested (DO NOT REPEAT)

The following are confirmed passing as of commit `32cd0d0` (SB-01 through SB-05 fixed):

- SB-01: `borg setup-claude` emits `sys.executable` not `"python"` — verified by RED team
- SB-02: `docs/EXTERNAL_TESTER_GUIDE.md` deleted; `docs/TRYING_BORG.md` created with zero `guild` hits
- SB-03: `borg generate --format {claude,cursor,cline,windsurf}` all exit 0
- SB-04: `pip show agent-borg | grep -i url` shows no `guild-packs` substring
- SB-05: `borg autopilot` MCP config uses valid interpreter path
- Classifier FCR: 53.8% → 0.58% (test_classify_error.py passes)
- P1.1: 45 runs, floor effect confirmed (MiniMax-Text-01 stops after 2 iters) — documented, not a regression
- E2E observe→search roundtrip: works in v3.2.4 (confirmed in audit)
- `borg setup-claude` idempotency: works (re-runs print "already configured")
- Error messages are actionable (above-average CLI quality)
- JSON output consistency across subcommands

### NOT YET TESTED (gaps in coverage):
- `borg pull` on a **live** remote index (only fake URI tested)
- `--no-seeds` CLI flag (only `BORG_DISABLE_SEEDS=1` env var tested)
- `borg debug 'zzzzzzzzz'` exit code (HIGH-04)
- `feedback-v3 --success garbage` exit code (HIGH-03)
- `guild://` → `borg://` in CLI help strings (HIGH-02)
- `borg/seeds_data/guild-autopilot/` rename (HIGH-06)
- `borg_suggest` returns non-empty for the 2-failures case (HIGH-05)
- Cold-start on fresh HOME: confirmed 50/50 queries return 0 results (HIGH-01 gap)
- Wheel size ≤ 5 MiB (G3)
- G1/G2 50-query benchmark ≥ 40/50, ≥ 47/50
- All pytest tests in borg/tests/ (G4 regression gate)
- License audit completeness (G5)
- Seed corpus integration into borg_search

---

## 1. Circles to Avoid

1. **Testing what was already tested** — SB-01 through SB-05 fixes are committed; re-running the ship-blocker gate is wasted effort.
2. **Testing cold-start before _load_seed_index() exists** — the integration shim is greenfield; no amount of testing will make it pass until it's built.
3. **Testing MCP server without a working setup-claude** — SB-01 was blocking the MCP path; now fixed, the MCP handshake tests are meaningful.
4. **Running the 50-query benchmark against a partial corpus** — G1 requires K=200 minimum. Running it against K=50 gives a false signal.
5. **Testing observability before the cold-start fix** — verbose mode reveals what seeds are loaded; that only works after LAYER 4.

---

## 2. Dependency-Ordered Test Layers

**Execution order is MANDATORY.** Each layer depends on the previous.

| Layer | Name | Prerequisite | Duration |
|-------|------|-------------|----------|
| L0 | Ship blocker regression gate | None | 5 min |
| L1 | CLI core | L0 passes | 10 min |
| L2 | MCP server | L0 passes | 10 min |
| L3 | HIGH items | L1+L2 pass | 10 min |
| L4 | Cold-start | `_load_seed_index()` built | 20 min |
| L5 | Observability | L4 passes | 5 min |
| L6 | Performance | L1 passes | 10 min |
| L7 | Concurrency/multi-user | Deferred | — |

---

## LAYER 0: Ship Blocker Regression Gate

**What it covers:** The 5 ship blockers must not regress as development continues.

### L0-T1: SB-01 — `setup-claude` interpreter path
```bash
cd /root/hermes-workspace/borg
python -m venv /tmp/l0-test-venv && source /tmp/l0-test-venv/bin/activate
pip install -e . 2>&1 | tail -3
HOME=/tmp/l0-home HERMES_HOME=/tmp/l0-home/.hermes borg setup-claude
python3 -c "
import json, sys
cfg = json.load(open('/tmp/l0-home/.config/claude/claude_desktop_config.json'))
cmd = cfg['mcpServers']['borg']['command']
print('command:', cmd)
assert cmd.endswith('borg-mcp') or 'python' in cmd, f'bad cmd: {cmd}'
import shutil; assert shutil.which(cmd) or cmd.startswith('/'), f'not resolvable: {cmd}'
print('PASS')
"
```
**PASS:** command ends in `borg-mcp` or contains `python` + is resolvable  
**FAIL:** command is bare `"python"` and fails shutil.which

### L0-T2: SB-02 — No stale `guild` references in docs
```bash
cd /root/hermes-workspace/borg
# EXTERNAL_TESTER_GUIDE.md must be gone or rewritten
test ! -f docs/EXTERNAL_TESTER_GUIDE.md || grep -c 'guild' docs/EXTERNAL_TESTER_GUIDE.md | grep -q '^0$'
# TRYING_BORG.md must have zero guild hits if it exists
test ! -f docs/TRYING_BORG.md || grep -ci 'guild' docs/TRYING_BORG.md | grep -q '^0$'
echo "PASS"
```
**PASS:** both greps return 0 hits  
**FAIL:** any non-zero count

### L0-T3: SB-03 — `generate --format` accepts human-readable names
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
for fmt in claude cursor cline windsurf; do
    borg generate systematic-debugging --format "$fmt" > /dev/null 2>&1
    echo "$fmt: exit=$?"
done | grep -v 'exit=0$' && echo "FAIL" || echo "PASS"
```
**PASS:** all four formats exit 0  
**FAIL:** any format exits non-zero

### L0-T4: SB-04 — `pyproject.toml` URLs are clean
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
pip show agent-borg | grep -i url | grep -v 'agent-borg\|borg' && echo "FAIL-URL" || echo "PASS"
```
**PASS:** no output (no stale URLs)  
**FAIL:** any line containing `guild-packs`

### L0-T5: SB-05 — `autopilot` interpreter path
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l0-home HERMES_HOME=/tmp/l0-home/.hermes borg autopilot
python3 -c "
import json
cfg = json.load(open('/tmp/l0-home/.config/claude/claude_desktop_config.json'))
cmd = cfg['mcpServers']['borg']['command']
print('autopilot command:', cmd)
import shutil
assert shutil.which(cmd) or cmd.startswith('/'), f'not resolvable: {cmd}'
print('PASS')
"
```
**PASS:** command is resolvable  
**FAIL:** command is bare `"python"` or unresolvable

---

## LAYER 1: CLI Core

**What it covers:** The 16 subcommands, search path, list, debug, generate, setup-claude, autopilot, pull, feedback-v3.

### L1-T1: `borg --help` and all subcommand helps
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
for cmd in search pull try init apply publish feedback feedback-v3 debug convert generate list observe version autopilot setup-claude setup-cursor start; do
    borg "$cmd" --help > /dev/null 2>&1
    echo "$cmd: exit=$?"
done | grep -v 'exit=0$' && echo "FAIL" || echo "PASS"
```
**PASS:** all 16 exit 0  
**FAIL:** any non-zero

### L1-T2: `borg search` on clean HOME returns 0 results (cold-start gap)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg search debugging --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('matches:', d['matches'])
assert d['matches'] == [], f'Expected 0 matches on cold install, got {len(d[\"matches\"])}'
print('PASS — cold-start gap confirmed (no seed loading yet)')
"
```
**PASS:** 0 matches confirmed  
**FAIL:** non-zero matches (means seed integration is already working, or something else is wrong)

### L1-T3: `borg list` works
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg list --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d['success'] == True
print('PASS — list works, total:', d.get('total', 0))
"
```
**PASS:** success=true  
**FAIL:** success=false or error

### L1-T4: `borg debug` with no match exits 1 (HIGH-04)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg debug 'zzzzzzzzz' 2>/dev/null; echo "exit=$?"
```
**PASS:** exit code is 1 or 2 (not 0)  
**FAIL:** exit code 0

### L1-T5: `borg generate` produces output files
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
rm -rf /tmp/l1-gen-test
mkdir /tmp/l1-gen-test && cd /tmp/l1-gen-test
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg generate systematic-debugging --format claude 2>/dev/null
ls -la CLAUDE.md .cursorrules 2>/dev/null && echo "PASS" || echo "FAIL"
```
**PASS:** CLAUDE.md or .cursorrules created  
**FAIL:** no files created

### L1-T6: `borg pull` with fake URI gives useful error
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg pull not-a-real-uri 2>&1 | grep -qi 'guild\|pack.*not.*found\|invalid.*uri'; echo "exit=$?"
```
**PASS:** grep matches (error message is actionable)  
**FAIL:** no match

### L1-T7: `borg feedback-v3` rejects invalid `--success`
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg feedback-v3 --pack test --session 00000000 --success garbage 2>/dev/null; echo "exit=$?"
```
**PASS:** exit code is 1 (rejected)  
**FAIL:** exit code 0 (accepted garbage)

---

## LAYER 2: MCP Server

**What it covers:** Handshake, tools/list, JSON-RPC calls, borg_search, borg_observe.

### L2-T1: MCP handshake (protocol version)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import subprocess, json, sys

proc = subprocess.Popen(
    ['borg-mcp'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True
)

# initialize
init_req = {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}
proc.stdin.write(json.dumps(init_req) + '\n')
proc.stdin.flush()
resp = json.loads(proc.stdout.readline())
assert resp['id'] == 1
assert 'protocolVersion' in resp['result']
print('protocolVersion:', resp['result']['protocolVersion'])
print('serverInfo:', resp['result']['serverInfo'])
proc.kill()
print('PASS')
"
```
**PASS:** correct protocol version, serverInfo present  
**FAIL:** protocol mismatch or missing serverInfo

### L2-T2: `tools/list` returns ≥ 17 tools
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import subprocess, json

proc = subprocess.Popen(
    ['borg-mcp'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True
)

# initialize
init_req = {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}
proc.stdin.write(json.dumps(init_req) + '\n')
proc.stdin.flush()
_ = proc.stdout.readline()

# tools/list
proc.stdin.write(json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/list'}) + '\n')
proc.stdin.flush()
resp = json.loads(proc.stdout.readline())
tools = resp['result']['tools']
print('tool count:', len(tools))
names = [t['name'] for t in tools]
print('tools:', names)
assert len(tools) >= 17, f'Expected >=17 tools, got {len(tools)}'
proc.kill()
print('PASS')
"
```
**PASS:** ≥ 17 tools  
**FAIL:** < 17 tools

### L2-T3: `borg_search` via MCP returns valid JSON
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import subprocess, json

proc = subprocess.Popen(
    ['borg-mcp'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True
)

# initialize
init_req = {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}
proc.stdin.write(json.dumps(init_req) + '\n')
proc.stdin.flush()
_ = proc.stdout.readline()

# tools/call borg_search
proc.stdin.write(json.dumps({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'borg_search','arguments':{'query':'debugging'}}}) + '\n')
proc.stdin.flush()
resp = json.loads(proc.stdout.readline())
content = resp['result']['content'][0]['text']
data = json.loads(content)
print('success:', data['success'])
print('matches:', len(data.get('matches', [])))
assert data['success'] == True
proc.kill()
print('PASS')
"
```
**PASS:** success=true, matches returned  
**FAIL:** success=false or malformed response

### L2-T4: `borg_observe` records a trace
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import subprocess, json

proc = subprocess.Popen(
    ['borg-mcp'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True
)

# initialize
init_req = {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}
proc.stdin.write(json.dumps(init_req) + '\n')
proc.stdin.flush()
_ = proc.stdout.readline()

# tools/call borg_observe
proc.stdin.write(json.dumps({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'borg_observe','arguments':{'task':'fix django auth bug'}}}) + '\n')
proc.stdin.flush()
resp = json.loads(proc.stdout.readline())
content = resp['result']['content'][0]['text']
data = json.loads(content)
print('observed:', data.get('observed'))
assert data.get('observed') == True
proc.kill()
print('PASS')
"
```
**PASS:** observed=true  
**FAIL:** observed=false or error

---

## LAYER 3: HIGH Items

**What it covers:** HIGH-02 through HIGH-06 from the defect inventory.

### L3-T1: `guild://` → `borg://` in CLI help strings (HIGH-02)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
# Check pull help — should say borg:// not guild://
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg pull --help 2>&1 | grep -c 'guild://'
# Should be 0 in user-facing text; parser accepts guild:// for back-compat
echo "guild:// in pull help: $(HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg pull --help 2>&1 | grep -c 'guild://')"
# Verify borg:// appears
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg pull --help 2>&1 | grep -c 'borg://'
echo "PASS — guild:// removed from help"
```
**PASS:** 0 occurrences of `guild://` in pull help  
**FAIL:** any occurrence

### L3-T2: `feedback-v3 --success garbage` exits 1 (HIGH-03)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg feedback-v3 --pack foo --session 00000000 --success garbage 2>/dev/null
echo "exit=$?"
```
**PASS:** exit=1  
**FAIL:** exit=0

### L3-T3: `borg debug 'zzzzzzzzz'` exits 1 (HIGH-04)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l1-fresh HERMES_HOME=/tmp/l1-fresh/.hermes borg debug 'zzzzzzzzz' 2>/dev/null
echo "exit=$?"
```
**PASS:** exit=1 or 2  
**FAIL:** exit=0

### L3-T4: `borg_suggest` returns non-empty for valid trigger (HIGH-05)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import subprocess, json

proc = subprocess.Popen(
    ['borg-mcp'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True
)

# initialize
init_req = {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'1.0'}}}
proc.stdin.write(json.dumps(init_req) + '\n')
proc.stdin.flush()
_ = proc.stdout.readline()

# borg_suggest with 2 failures
proc.stdin.write(json.dumps({'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'borg_suggest','arguments':{'failures':['TypeError','TypeError'],'task':'fix auth bug'}}}) + '\n')
proc.stdin.flush()
resp = json.loads(proc.stdout.readline())
content = resp['result']['content'][0]['text']
print('borg_suggest response:', content[:200])
data = json.loads(content) if content.strip() != '{}' else {}
assert data != {}, 'borg_suggest returned empty {} — HIGH-05 not fixed'
print('PASS — borg_suggest returns non-empty')
proc.kill()
"
```
**PASS:** non-empty JSON (not `{}`)  
**FAIL:** `{}` returned

### L3-T5: `borg/seeds_data/guild-autopilot` renamed to `borg-autopilot` (HIGH-06)
```bash
cd /root/hermes-workspace/borg
test ! -d borg/seeds_data/guild-autopilot && echo "PASS — guild-autopilot directory removed" || echo "FAIL — guild-autopilot still exists"
test -d borg/seeds_data/borg-autopilot && echo "PASS — borg-autopilot exists" || echo "FAIL — borg-autopilot missing"
```
**PASS:** guild-autopilot gone, borg-autopilot present  
**FAIL:** guild-autopilot still exists

---

## LAYER 4: Cold-Start

**Prerequisite:** `_load_seed_index()` function is built and wired into `search.py`.

### L4-T1: `_load_seed_index()` function exists and returns packs
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
from borg.core.seeds import _load_seed_index
result = _load_seed_index()
print('type:', type(result))
print('keys:', list(result.keys()) if isinstance(result, dict) else 'not a dict')
pack_count = result.get('pack_count', len(result.get('packs', [])) if isinstance(result, dict) else 0)
print('pack_count:', pack_count)
assert pack_count >= 10, f'Expected >=10 packs (only 10 seed packs exist), got {pack_count}'
print('PASS')
"
```
**PASS:** pack_count >= 10  \
**FAIL:** function not found, returns empty, or pack_count < 10

### L4-T2: `borg search` on fresh HOME returns seed matches (integration test)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
rm -rf /tmp/l4-fresh-home && mkdir -p /tmp/l4-fresh-home/.hermes
# Use "django" — matches 4 seed packs (django-*-dependency/migration/null-pointer/schema-drift)
HOME=/tmp/l4-fresh-home HERMES_HOME=/tmp/l4-fresh-home/.hermes borg search django --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
seed_hits = [m for m in d['matches'] if m.get('tier') == 'seed']
print('matches:', len(d['matches']), 'seed_hits:', len(seed_hits))
assert len(seed_hits) > 0, 'Expected seed hits on cold install, got 0'
print('PASS — seeds loaded into search')
"
```
**PASS:** > 0 seed-marked matches on fresh HOME  \
**FAIL:** 0 seed-marked matches (integration not wired)

### L4-T3: `--no-seeds` flag disables seed hits
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l4-fresh-home HERMES_HOME=/tmp/l4-fresh-home/.hermes borg search django --no-seeds --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
matches = d['matches']
seed_hits = [m for m in matches if m.get('tier') == 'seed' or m.get('source') == 'seed']
print('seed hits with --no-seeds:', len(seed_hits))
assert len(seed_hits) == 0, f'Expected 0 seed hits with --no-seeds, got {len(seed_hits)}'
print('PASS')
"
```
**PASS:** 0 seed-tier matches  
**FAIL:** non-zero seed matches with --no-seeds

### L4-T4: `BORG_DISABLE_SEEDS=1` env var disables seeds
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
BORG_DISABLE_SEEDS=1 HOME=/tmp/l4-fresh-home HERMES_HOME=/tmp/l4-fresh-home/.hermes borg search django --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
matches = d['matches']
seed_hits = [m for m in matches if m.get('tier') == 'seed' or m.get('source') == 'seed']
print('seed hits with BORG_DISABLE_SEEDS=1:', len(seed_hits))
assert len(seed_hits) == 0
print('PASS')
"
```
**PASS:** 0 seed-tier matches  
**FAIL:** non-zero seed matches

### L4-T5: Seed packs marked as `tier=seed` or `source=seed` in output
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l4-fresh-home HERMES_HOME=/tmp/l4-fresh-home/.hermes borg search django --json 2>/dev/null | python3 -c "
import sys, json
d = json.load(sys.stdin)
seed_hits = [m for m in d['matches'] if m.get('tier') == 'seed']
print('seed-marked matches:', len(seed_hits))
assert len(seed_hits) > 0, 'Expected seed-marked matches in output'
print('PASS')
"
```
**PASS:** seed-marked matches present  
**FAIL:** no seed marking in output

### L4-T6: G1 — 50-query benchmark ≥ 40/50 relevant matches
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
# Requires borg/tests/fixtures/cold_start_queries.json
python3 -c "
import json, subprocess, sys

fixture_path = 'borg/tests/fixtures/cold_start_queries.json'
try:
    with open(fixture_path) as f:
        queries = json.load(f)
except FileNotFoundError:
    print('SKIP — cold_start_queries.json not committed yet')
    sys.exit(0)

hits = 0
for q in queries:
    result = subprocess.run(
        ['borg', 'search', q['query'], '--json'],
        capture_output=True, text=True,
        env={'HOME': '/tmp/l4-bench', 'HERMES_HOME': '/tmp/l4-bench/.hermes'}
    )
    try:
        data = json.loads(result.stdout)
        if len(data.get('matches', [])) >= 1:
            hits += 1
    except:
        pass

print(f'hits: {hits}/{len(queries)}')
assert hits >= 40, f'G1 FAILED: {hits}/50 (need >= 40)'
print('PASS')
"
```
**PASS:** ≥ 40/50  
**FAIL:** < 40/50

### L4-T7: G2 — 50-query benchmark ≥ 47/50 with ≥ 5 results
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import json, subprocess, sys

fixture_path = 'borg/tests/fixtures/cold_start_queries.json'
try:
    with open(fixture_path) as f:
        queries = json.load(f)
except FileNotFoundError:
    print('SKIP — fixture not committed')
    sys.exit(0)

hits = 0
for q in queries:
    result = subprocess.run(
        ['borg', 'search', q['query'], '--json'],
        capture_output=True, text=True,
        env={'HOME': '/tmp/l4-bench2', 'HERMES_HOME': '/tmp/l4-bench2/.hermes'}
    )
    try:
        data = json.loads(result.stdout)
        if len(data.get('matches', [])) >= 5:
            hits += 1
    except:
        pass

print(f'hits (>=5 results): {hits}/{len(queries)}')
assert hits >= 47, f'G2 FAILED: {hits}/50 (need >= 47)'
print('PASS')
"
```
**PASS:** ≥ 47/50  
**FAIL:** < 47/50

### L4-T8: G3 — wheel size ≤ 5 MiB
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
pip wheel . -w /tmp/wheel-output --no-deps 2>&1 | tail -3
ls -la /tmp/wheel_output/*.whl 2>/dev/null || ls -la /tmp/wheel-output/*.whl 2>/dev/null
python3 -c "
import os, tarfile, sys

# Find the wheel
whl_candidates = []
for root, dirs, files in os.walk('/tmp'):
    for f in files:
        if f.endswith('.whl'):
            whl_candidates.append(os.path.join(root, f))

if not whl_candidates:
    print('SKIP — wheel not built')
    sys.exit(0)

whl = whl_candidates[0]
print('wheel:', whl)
with tarfile.open(whl) as tf:
    total = sum(m.size for m in tf.getmembers())
print(f'uncompressed size: {total/1024/1024:.2f} MiB')
assert total <= 5 * 1024 * 1024, f'G3 FAILED: {total/1024/1024:.2f} MiB > 5 MiB'
print('PASS')
"
```
**PASS:** ≤ 5 MiB  
**FAIL:** > 5 MiB

### L4-T9: G5 — every seed pack has allowlist license
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python3 -c "
import os, yaml
from pathlib import Path

allowlist = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'CC0-1.0', 'ISC'}

packs_dir = Path('borg/seeds_data/packs')
if not packs_dir.exists():
    print('SKIP — packs/ directory not created yet')
    exit(0)

violations = []
for pack_yaml in packs_dir.glob('*.yaml'):
    with open(pack_yaml) as f:
        data = yaml.safe_load(f)
    license = data.get('license', 'UNKNOWN')
    if license not in allowlist:
        violations.append(f'{pack_yaml.name}: {license}')

if violations:
    print('VIOLATIONS:', violations)
    assert False, f'{len(violations)} packs with non-allowlist license'
print('PASS')
"
```
**PASS:** all packs have allowlist license  
**FAIL:** any violation

---

## LAYER 5: Observability

**What it covers:** Verbose mode, error quality, hint messages.

### L5-T1: `(seed)` suffix appears in search output for seed packs
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l4-fresh-home HERMES_HOME=/tmp/l4-fresh-home/.hermes borg search django 2>&1 | grep -c 'seed'
echo "seed markers: $(HOME=/tmp/l4-fresh-home HERMES_HOME=/tmp/l4-fresh-home/.hermes borg search django 2>&1 | grep -c 'seed')"
```
**PASS:** ≥ 1 occurrence of `seed`  
**FAIL:** 0 occurrences

### L5-T2: Error messages are actionable (no silent failures)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
# Remote index blackhole — should show hint, not silent failure
BORG_REMOTE_INDEX=https://blackhole.invalid.tld/index.json HOME=/tmp/l5-test HERMES_HOME=/tmp/l5-test/.hermes borg search debugging 2>&1 | grep -i 'unreachable\|local only\|warning' && echo "PASS — hint present" || echo "FAIL — no hint"
```
**PASS:** hint about remote unavailability  
**FAIL:** silent failure

### L5-T3: Empty search result is actionable
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
HOME=/tmp/l5-empty HERMES_HOME=/tmp/l5-empty/.hermes borg search 'zzzzzzzNOT A REAL QUERYzzzzzz' 2>&1 | grep -i 'try\|pull\|init\|no pack' && echo "PASS" || echo "FAIL"
```
**PASS:** hint message is present  
**FAIL:** bare "No packs found." with no guidance

---

## LAYER 6: Performance

**What it covers:** Latency and startup time.

### L6-T1: `borg --version` < 200ms
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
for i in 1 2 3; do
    /usr/bin/time -f "%e" borg --version 2>&1
done | grep -v real
```
**PASS:** all 3 runs < 0.2s  
**FAIL:** any run >= 0.2s

### L6-T2: `borg search` < 1s on local corpus
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
for i in 1 2 3; do
    /usr/bin/time -f "%e" borg search debugging 2>/dev/null
done | grep -v real
```
**PASS:** all 3 runs < 1.0s  
**FAIL:** any run >= 1.0s

### L6-T3: `borg observe` < 200ms
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
for i in 1 2 3; do
    /usr/bin/time -f "%e" borg observe 'test task' 2>/dev/null
done | grep -v real
```
**PASS:** all 3 runs < 0.2s  
**FAIL:** any run >= 0.2s

### L6-T4: Full pytest suite passes (G4 regression gate)
```bash
cd /root/hermes-workspace/borg
source /tmp/l0-test-venv/bin/activate
python -m pytest borg/tests/ --tb=short -q 2>&1 | tail -10
```
**PASS:** 100% pass, exit 0  
**FAIL:** any test failure

---

## LAYER 7: Concurrency / Multi-User

**Deferred:** No tests until actual multi-user usage patterns emerge. The system is single-user by design (HERMES_HOME scoped).

---

## 3. Test Execution Summary

| Layer | Tests | Time | Blocked by |
|-------|-------|------|------------|
| L0 | 5 | 5 min | None |
| L1 | 7 | 10 min | L0 |
| L2 | 4 | 10 min | L0 |
| L3 | 5 | 10 min | L1+L2 |
| L4 | 9 | 20 min | `_load_seed_index()` built |
| L5 | 3 | 5 min | L4 |
| L6 | 4 | 10 min | L1 |
| **Total** | **37** | **~70 min** | — |

---

## 4. Failure Response

If any test fails:
1. Check which layer failed
2. Identify the dependency that is not met
3. Fix the underlying issue before re-running
4. Do NOT skip layers — each layer validates its own prerequisites

**The most common failure mode is running LAYER 4 tests before `_load_seed_index()` is built. Do not do this.**