> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# 20260514 Borg world-class hardening board

**file rev:** 20260514-1212 rev A  
**status:** active execution board, not a marketing claim.  
**principle:** fail closed, prove runtime, remove split-brain, no deletion before no-loss archive/diff.

## Current verified state

### Green, source/fresh-process proven

- `borg.core.confidence_gate` exists as the shared confidence/injection-safety policy.
- `borg_runtime_fingerprint` exists in canonical source and known runtime mirrors.
- Raw proof: `/root/hermes-workspace/borg/docs/20260514_BORG_RUNTIME_FINGERPRINT_VERIFICATION_RAW.md`
  - Borg targeted tests: `31 passed in 6.31s`
  - Hermes plugin tests: `9 passed in 12.02s`
  - local `runtime_fingerprint()` canary: passed
  - fresh stdio MCP exposes `borg_runtime_fingerprint`: yes
  - fresh stdio MCP `confidence_gate_canary.passed`: true

### Still stale in this active chat MCP process

The active tool session still returns stale/unrelated `PACK GUIDANCE` from `mcp_borg_observe`. This is runtime/session state, not source state. No gateway restart/kill/signal has been performed.

Read-only diagnostics: `/root/hermes-workspace/borg/docs/repo-manifest/20260514_safe_mcp_reload_diagnostics.json`

Key findings:

- configured MCP server name is `borg-mcp`, not `borg`
- `hermes mcp test borg-mcp` connects and discovers 24 tools including `borg_runtime_fingerprint`
- fresh subprocess can load the patched runtime

## New issue found during fresh canary

Fresh subprocess `borg_observe` emitted:

```text
ERROR:borg.core.embeddings:embeddings: DB read failed: no such column: causal_intervention
```

This is exactly the kind of polish issue that would make a code reviewer distrust the system. It is now fixed source-side:

- `borg/core/embeddings.py` no longer hard-requires `causal_intervention` in old trace DBs.
- It introspects `PRAGMA table_info(traces)` and includes optional columns only when present.
- `semantic_search()` now checks whether an index exists before loading the embedding model, avoiding unnecessary model load/noise when there is no usable index.
- Regression tests added: `borg/tests/test_embeddings_schema_compat.py`.
- Installed/runtime mirrors patched:
  - `/usr/local/lib/python3.12/dist-packages/borg/core/embeddings.py`
  - `/root/hermes-workspace/borg/build/lib/borg/core/embeddings.py`

## New contract issue found during full-context review

MCP `TOOLS` had duplicate `borg_generate` entries. That is not world-class: duplicate public tool names create schema/dispatch ambiguity and make downstream wrappers brittle.

Fixed:

- removed duplicate canonical `borg_generate` schema entry from `borg/integrations/mcp_server.py`
- removed duplicate build mirror entry from `build/lib/borg/integrations/mcp_server.py`
- replaced brittle tool-count test with a contract test that asserts no duplicate tool names and requires `borg_runtime_fingerprint`

Verification running as cron jobs `982ef1f42d3a` and `ec0a4853829b`:

- embeddings schema compatibility tests
- fingerprint/confidence tests
- MCP duplicate-tool contract test
- fresh stdio stale-guidance canary
- fresh stdio permission-denied positive control
- checks that `no such column: causal_intervention` is gone
- checks that fresh canary no longer loads model weights unnecessarily for stale-guidance path

## World-class code standard for Borg

A reviewer should see these properties:

1. **One source of truth**
   - canonical package source owns product behavior.
   - installed/site-packages, `guild-v2`, `guild-tools`, and `build/lib` are temporary runtime mirrors only until cutover.

2. **Fail-closed retrieval**
   - no confident match means no confident match.
   - synthetic-only or zero-real pack guidance cannot be injected as if proven.
   - stale pasted assistant output is inert text, never evidence.

3. **Runtime identity is inspectable**
   - every served MCP process can report file paths, hashes, version, `BORG_HOME`, and canary status.
   - production status never depends on guessing which file is live.

4. **Old local state is tolerated**
   - older trace DB schemas must not crash or spam logs.
   - optional columns must be optional.
   - no heavyweight model load unless there is a usable index.

5. **No-loss cleanup before deletion**
   - dirty tree is classified in `/root/hermes-workspace/borg/docs/repo-manifest/20260514_borg_no_loss_cleanup_manifest.json`.
   - 250 dirty/untracked entries are classified:
     - 201 generated-ignore
     - 22 product code
     - 18 docs
     - 8 tests
     - 1 archive-readonly

6. **External readiness is still honest**
   - internal source/fresh-process proof is strong.
   - live active session proof is not complete until MCP reload/new session picks up patched runtime.
   - broad production remains conditional until first-user evidence exists.

## Next execution gates

### Gate A — Embeddings compatibility proof

Wait for `d9a8023acdf0` raw output. Required:

- tests pass
- `STDERR_HAS_CAUSAL_ERROR=False`
- stale canary has no `PACK GUIDANCE`
- permission positive control remains useful

### Gate B — Active served MCP reload/new-session proof

Allowed only by operator-approved safe path. Acceptance:

- active served tool schema includes `borg_runtime_fingerprint`
- active served `confidence_gate_canary.passed=True`
- active stale-guidance canary returns `NO_CONFIDENT_MATCH`/no junk advice
- active permission-denied positive control still returns permission guidance

### Gate C — Cutover cleanup

Use the no-loss manifest to:

1. archive/diff generated artifacts before deletion;
2. move durable docs/tests/code into canonical source only;
3. mark runtime mirrors as generated/non-source;
4. update docs to one install/runtime story;
5. add CI checks preventing mirror-only product code.

No destructive cleanup happens before archive/diff preservation.
