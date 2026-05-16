# Production Closure Fast Rerun — 2026-05-15

## Overall Status

PASS

## Blockers

None found in this rerun.

## Command Results

### 1. Rescue / runtime fingerprint / embeddings schema compatibility

Command:

```bash
python -m pytest -q borg/tests/test_rescue.py borg/tests/test_runtime_fingerprint.py borg/tests/test_embeddings_schema_compat.py
```

stdout:

```text
............                                                             [100%]
12 passed in 0.19s
```

stderr:

```text

```

rc: `0`

Status: PASS

### 2. Security hardening / confidence gate / first-10 readiness

Command:

```bash
python -m pytest -q eval/tests/test_security_hardening_baseline.py borg/tests/test_confidence_gate.py borg/tests/test_borg_observe_confidence_gate.py borg/tests/test_first_10_readiness.py
```

stdout:

```text
.....................................                                    [100%]
37 passed in 7.50s
```

stderr:

```text

```

rc: `0`

Status: PASS

### 3. borg_observe confidence/staleness smoke check

Command:

```bash
python - <<'PY'
from borg.integrations import mcp_server
for name,kw in [('unrelated',dict(task='continue Borg readiness/get it there: fix borg_observe irrelevant guidance/runtime mismatch and proceed toward first-user readiness',context='python borg mcp runtime readiness')),('permission',dict(task='Fix bash: ./deploy.sh: Permission denied',context='bash permission denied chmod'))]:
 out=mcp_server.borg_observe(**kw)
 print('---',name,'---')
 print(out[:1200])
 print('NO_CONFIDENT=', 'NO_CONFIDENT_MATCH' in out or 'NO CONFIDENT MATCH' in out)
 print('STALE=', 'Plugin directory ~/.hermes/plugins/' in out or 'BORG_HOME env var' in out or 'PACK GUIDANCE (python-type-error)' in out)
 print('PERMISSION=', 'Permission denied' in out or 'chmod' in out or 'PACK GUIDANCE (bash-permission-denied)' in out)
PY
```

stdout:

```text
--- unrelated ---
ACTION: proceed with normal debugging for python; Borg has no proven cache hit.

STOP: do not force a weak or unrelated pack onto this task.

VERIFY: collect the exact failing command/output and rerun borg_observe or borg_rescue only if new evidence appears.

CONFIDENCE: BORG [NO CONFIDENT MATCH] -- no relevant traces, synthetic hits, or pack matches.

NO_CONFIDENT_MATCH: No confident Borg match for python.
Borg found no relevant real traces, synthetic hits, or exact pack class match.
Proceed with normal reasoning; do not treat Borg as evidence for this task.
After resolving: call borg_rate(helpful=True) only if Borg guidance was actually useful.
NO_CONFIDENT= True
STALE= False
PERMISSION= False
--- permission ---
VERIFY: execute the pack's first checkpoint, then rerun the exact failing command

CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]

------------------------------------------------------------
PACK GUIDANCE (bash-permission-denied)
1. Check file permissions: ls -la <file>
2. Add execute permission: chmod +x <script.sh>
3. For directories: chmod +x <directory>
4. Check ownership: ls -ln <file>
5. Run as appropriate user: sudo <command>
6. For SSH keys: chmod 600 ~/.ssh/id_rsa
------------------------------------------------------------
NO_CONFIDENT= False
STALE= False
PERMISSION= True
```

stderr:

```text

```

rc: `0`

Status: PASS

## Readiness Notes

- Unrelated readiness/runtime prompt correctly returned `NO_CONFIDENT_MATCH` and did not emit stale guidance.
- Bash permission-denied prompt correctly returned permission/chmod pack guidance.
- No stale plugin/BORG_HOME/python-type-error guidance detected.
