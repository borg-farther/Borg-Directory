# 20260514 Borg runtime fingerprint + canary proof

**file rev:** 20260514-1117 rev A  
**scope:** runtime identity proof for Borg MCP confidence-gate rollout.  
**status:** source/fresh-process verification running via cron job `68e8869059b6`; live served MCP reload not performed.

## Why this exists

Borg previously leaked unrelated `PACK GUIDANCE` into operator/meta tasks after source files had been patched. That means a production operator cannot trust source edits alone; Borg needs a read-only runtime fingerprint that proves exactly what code a served MCP process is running.

## Implemented artifacts

### Canonical source

- `/root/hermes-workspace/borg/borg/core/runtime_fingerprint.py`
- `/root/hermes-workspace/borg/borg/tests/test_runtime_fingerprint.py`
- `/root/hermes-workspace/borg/borg/integrations/mcp_server.py`
  - adds `borg_runtime_fingerprint` schema entry
  - adds `borg_runtime_fingerprint()` handler
  - dispatches `call_tool('borg_runtime_fingerprint', {})`

### Defensive runtime/mirror copies

- `/usr/local/lib/python3.12/dist-packages/borg/core/runtime_fingerprint.py`
- `/usr/local/lib/python3.12/dist-packages/borg/integrations/mcp_server.py`
- `/root/hermes-workspace/guild-v2/borg/core/runtime_fingerprint.py`
- `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py`
- `/home/user/guild-tools/borg/core/runtime_fingerprint.py`
- `/home/user/guild-tools/borg/integrations/mcp_server.py`
- `/root/hermes-workspace/borg/build/lib/borg/core/runtime_fingerprint.py`

## Fingerprint fields

`borg_runtime_fingerprint` returns:

- `pid`
- Python executable/version
- current working directory
- `BORG_HOME`
- Borg package version
- loaded module paths + sha256/mtime/size for:
  - `borg`
  - `borg.integrations.mcp_server`
  - `borg.core.confidence_gate`
  - `borg.core.runtime_fingerprint`
- first `sys.path` entries
- `confidence_gate_canary`
- `reload_status`

## Canary contract

The canary passes only if all are true:

1. pasted `=== BORG GUIDANCE === ... PACK GUIDANCE (bash-permission-denied)` is stripped before classification.
2. pasted stale permission guidance does **not** count as a real permission signal.
3. unrelated permission guidance is unsafe to inject.
4. synthetic/zero-real pack guidance is unsafe to inject.
5. a real permission-denied task remains a positive control and is allowed.

Expected key fields:

```text
confidence_gate_canary.passed = True
confidence_gate_canary.stale_guidance_stripped = True
confidence_gate_canary.stale_permission_match = False
confidence_gate_canary.stale_permission_safe = False
confidence_gate_canary.synthetic_pack_safe = False
confidence_gate_canary.real_permission_positive_control_safe = True
reload_status = loaded_code_has_confidence_gate
```

## Verification job

Raw terminal verification is running as cron job:

```text
68e8869059b6 borg-complete-fingerprint-verification-20260514
```

It runs:

1. Borg confidence-gate + runtime-fingerprint pytest set.
2. Hermes plugin guidance-filter pytest set.
3. Local import fingerprint smoke.
4. MCP `call_tool('borg_runtime_fingerprint', {})` smoke.
5. Needle scan across canonical, installed runtime, guild-v2, guild-tools, and build/lib.
6. Fresh stdio MCP subprocess call to prove a newly loaded server exposes the fingerprint tool and canary.

## Live served MCP state

No gateway/MCP process reload, restart, kill, or signal has been performed.

Current live `mcp_borg_observe` calls still return unrelated stale guidance, which is expected until the served process reloads. Therefore:

- source files: patched
- installed runtime files: patched
- fresh-process behavior: pending cron proof
- live served MCP behavior: **not claimed fixed yet**

## Reload gate

Only after raw verification passes should an operator-approved reload happen. Post-reload acceptance requires:

1. served `borg_runtime_fingerprint` exists in MCP tool list.
2. served fingerprint module path points to the intended runtime.
3. served `confidence_gate_canary.passed = True`.
4. stale-guidance `borg_observe` canary returns `NO_CONFIDENT_MATCH` or no injected advice.
5. real `./deploy.sh: Permission denied` positive control remains allowed.

## Next permanent gate

After served reload proof, continue to P0.3 no-loss cleanup manifest: classify every dirty/untracked path and remove source-of-truth ambiguity without deleting anything before archive/diff capture.
