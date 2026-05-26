# Borg always-current runtime and federated learning plan

Date: 2026-05-26
Source repo: `https://github.com/borg-farther/Borg-Directory`
Current source/package target: `agent-borg==3.3.14`

## Executive verdict

Borg's local package path is current, but a long-lived served MCP process can still execute stale in-memory code after source/PyPI have moved on. The production solution is not "trust files on disk"; it is an always-current runtime gate that compares the loaded process to a signed approved-runtime manifest and fails closed when stale.

Borg's learning loop has real local primitives: failure memory, V3 outcomes, feedback, telemetry, aggregator reports, signed learning atoms, privacy scanning, prompt-injection scanning, local atom storage, and local revocation. That is not yet the same as global/federated propagation. A Google-grade solution needs signed sanitized atoms, tenant isolation, remote ingestion receipts, quorum-based promotion, signed manifests, client pull verification, and revocation propagation.

## Problem 1: served runtime freshness

### Current failure mode

A Borg MCP process may be started by Hermes, Cursor, Claude, Smithery, Docker, or another MCP host. Once that process imports Borg, Python keeps the module objects in memory. Updating the git repo or publishing a new PyPI package does not update the already-running process.

That creates split-brain states:

- source checkout: current
- PyPI latest: current
- fresh `borg-mcp` stdio process: current
- long-lived hosted/served MCP process: stale

Disk hashes are not sufficient proof. A stale process can report file paths that now point at updated files while still executing old imported functions and old import-time constants.

### Production invariant

Every user-connected Borg flow must be one of these two states:

1. `CURRENT_AND_ALLOWED_TO_SERVE`
   - loaded Borg version equals approved version
   - package metadata agrees
   - source version agrees when running from source
   - loaded function hashes match expected runtime contract
   - behavior canaries pass
   - fingerprint schema is current
2. `STALE_OR_UNKNOWN_FAIL_CLOSED`
   - only fingerprint/upgrade-instruction tools are allowed
   - all guidance/learning/write tools are blocked with explicit upgrade instructions

There is no third state where stale Borg is allowed to keep serving advice.

## Always-current runtime architecture

### 1. Approved-runtime manifest

Create a signed manifest for each promoted release:

```json
{
  "schema_version": 1,
  "package": "agent-borg",
  "approved_version": "3.3.14",
  "git_commit": "50e943eff7efebf0ed1b84f7bee52b9d275970fd",
  "pypi_wheel_sha256": "...",
  "mcp_tool_schema_sha256": "...",
  "loaded_function_hashes": {
    "borg.integrations.mcp_server.call_tool": "...",
    "borg.integrations.mcp_server.borg_observe": "...",
    "borg.core.confidence_gate.guidance_is_safe_to_inject": "..."
  },
  "denylisted_versions": ["3.3.7"],
  "valid_after": "2026-05-26T00:00:00Z",
  "expires_after": "2026-06-02T00:00:00Z",
  "upgrade_command": "pipx upgrade agent-borg || pip install -U agent-borg",
  "signature": "ed25519:..."
}
```

The manifest is the control-plane truth. Do not use mutable git branch names or local files as the final authority for served runtime readiness.

### 2. Shared `FreshnessGate`

Every Borg entrypoint should call one shared gate:

- `borg`
- `borg-doctor`
- `borg-mcp`
- `borg-http`
- any Hermes plugin/Borg wrapper
- any Smithery/Docker hosted runtime

The gate returns:

```json
{
  "allowed_to_serve": false,
  "current_version": "3.3.7",
  "approved_version": "3.3.14",
  "reason": "stale served MCP process",
  "safe_tools": ["borg_runtime_fingerprint", "borg_upgrade_instructions"],
  "blocked_tools": "all guidance, learning, publish, pull, feedback, and write tools"
}
```

### 3. MCP fail-closed mode

If stale or unknown:

- `initialize` still succeeds and exposes stale status.
- `tools/list` exposes only:
  - `borg_runtime_fingerprint`
  - `borg_upgrade_instructions`
- any other `tools/call` returns:

```json
{
  "success": false,
  "error": "Borg MCP runtime is stale",
  "current_version": "3.3.7",
  "approved_version": "3.3.14",
  "action": [
    "Stop using this MCP session for Borg guidance",
    "Upgrade/restart the Borg MCP runtime under operator supervision"
  ],
  "verify": [
    "Run borg_runtime_fingerprint",
    "Confirm version_matches_source=true",
    "Confirm observe_behavior_canary.passed=true"
  ]
}
```

Agents must not restart or reload the Hermes gateway themselves. The stale process should make the problem visible and safe.

### 4. Host-side MCP registration gate

MCP hosts should not register a Borg server just because handshake succeeds. The host should call `borg_runtime_fingerprint` before exposing tools and require:

- `success=true`
- `schema_version >= required_schema_version`
- `borg_version == approved_version`
- `source_version == approved_version` when source mode is used
- `version_matches_source=true`
- `loaded_function_hashes` present
- confidence/observe behavior canaries pass

If this fails, the host marks Borg unhealthy and exposes only upgrade instructions.

### 5. Immutable served deployments

For production served Borg, avoid mutable workspace paths:

- good: `/opt/borg/releases/3.3.14/bin/borg-mcp`
- good: container digest with `agent-borg==3.3.14`
- bad: `python -m borg.integrations.mcp_server` from an arbitrary mutable checkout
- bad: long-lived Hermes MCP process with no cutover canary

Promotion should be atomic:

1. build immutable release
2. run local package canaries
3. start candidate process
4. run fingerprint and behavior canaries
5. atomically route traffic to candidate
6. keep old process only for rollback, and old process fails closed if asked to serve after manifest changes

### 6. Runtime freshness gates to add

Required executable gates:

- `eval/served_runtime_freshness_gate.py`
  - compares a fingerprint JSON to approved manifest
  - fails stale versions, missing schema fields, missing behavior canaries, mutable production paths, and old tool schemas
- `tests/mcp/test_served_runtime_freshness_gate.py`
  - stale `3.3.7` fixture must fail
  - disk-current/process-stale fixture must fail
  - current `3.3.14` fixture must pass
- deployment-config guard
  - Docker/Smithery/hosted configs must not pin stale `agent-borg` or stale MCP tool counts
  - configs must prefer `borg-mcp` console script over unpinned `python -m borg...`

## Problem 2: global/federated learning propagation

### Current reality

Working local primitives:

- `borg_record_failure` / `borg_recall` local failure memory
- `borg_feedback` and V3 outcome storage
- local aggregator report generation
- local telemetry with opt-in structural events
- signed sanitized learning atom primitives
- privacy and prompt-injection scan primitives
- local atom store and tombstone/revocation support
- GitHub PR/outbox publish path

Not yet proven:

- user A learns something
- sanitized learning leaves A safely
- global/org registry ingests it
- user B on a clean install retrieves it
- bad/revoked learning disappears everywhere
- independent tenants can promote learning without Sybil/self-vote pollution

## Federated learning architecture

### 1. Learning atom as the only shared unit

Raw traces, raw prompts, raw source, screenshots, env vars, and tool outputs never leave the tenant by default. Shared artifacts must be minimized learning atoms:

```json
{
  "atom_id": "sha256:...",
  "scope": "local|org|global_candidate|global",
  "problem_signature": "normalized, redacted failure shape",
  "worked_approach": "short actionable guidance",
  "wrong_approaches": ["dead-end to avoid"],
  "verification": "what proved the approach worked",
  "source_receipt": "redacted evidence URI/hash",
  "privacy_scan": "pass",
  "prompt_injection_scan": "pass",
  "author_pseudonym": "tenant-HMAC pseudonym",
  "signature": "ed25519:..."
}
```

### 2. Ingestion service

A real collective network needs a remote/staging ingestion service with fail-closed validation:

- verify signature and key identity
- validate schema
- run privacy/secrets scan
- run prompt-injection scan
- reject raw traces and private data
- issue signed acceptance/rejection receipt
- quarantine risky atoms
- write append-only ingestion log

### 3. Promotion pipeline

Learning should move through states:

`local -> org_candidate -> org -> global_candidate -> global -> revoked`

Promotion requires:

- independent tenant quorum
- reputation-weighted support
- duplicate/similar atom clustering
- negative feedback/downranking
- human review for high-risk domains
- signed promotion decision

Same tenant, same machine, same key, or same operator must not count as independent support.

### 4. Distribution path

Clients pull signed manifests, not raw databases:

```text
borg sync --channel global --since <cursor>
  -> fetch signed manifest
  -> verify manifest signature
  -> fetch atom envelopes
  -> verify atom signatures
  -> check tombstones
  -> apply local policy
  -> store locally
```

Retrieval still uses Borg's confidence gate and retrieval firewall. A global atom is historical advice, not truth.

### 5. Revocation path

Revocation must propagate like learning:

- signed tombstone published
- client sync imports tombstone
- tombstone suppresses local search/retrieval
- re-import of the same atom fails
- public manifest exposes revocation cursor

### 6. Proof gates for real propagation

Minimum end-to-end test before claiming global/federated propagation:

1. Fresh user A installs `agent-borg` with isolated `BORG_HOME`.
2. A records a real redacted miss/success.
3. A distills/signs an atom.
4. Staging registry ingests it and returns a signed receipt.
5. Fresh user B installs from scratch with empty `BORG_HOME`.
6. B syncs from registry.
7. B's `borg rescue` or `borg recall` surfaces the learning with `ACTION / STOP / VERIFY`.
8. Registry publishes a tombstone.
9. B syncs again.
10. B can no longer retrieve the atom.

Artifacts required:

- A's redacted source issue URI
- atom ID and atom JSON hash
- privacy scan receipt
- prompt-injection scan receipt
- signed ingestion receipt
- B's clean install command/output
- B's before/after recall output hashes
- tombstone hash
- post-revocation retrieval failure proof

## First implementation slice

Do not start with full internet federation. Start with one controlled staging registry:

1. **Runtime freshness P0**
   - implement `FreshnessGate`
   - add served-runtime gate and stale fixture tests
   - require deployment configs to match pyproject/manifest
2. **Staging propagation P0**
   - create local/staging registry directory format:
     - `manifest.json`
     - `atoms/<atom_id>.json`
     - `tombstones/<atom_id>.json`
     - `receipts/<receipt_id>.json`
   - add `borg atom publish --registry <url_or_path>` and `borg atom sync --registry <url_or_path>` or equivalent non-public commands
   - sign every atom and manifest
   - prove A -> registry -> B -> revoke path in CI using temp dirs
3. **First-10 evidence integration P1**
   - when a first-10 row contains a bad answer or useful rescue, require `outcome_recorded=true`
   - link the row to a local learning record or signed atom receipt
   - run one clean-user reuse proof before claiming collective learning works for beta
4. **Global rollout P2**
   - remote hosted ingestion service
   - org/global scopes
   - key registry
   - transparency log
   - promotion quorum
   - abuse throttling

## Hard stop criteria

Pause invites or block served channel if any are true:

- served runtime version is behind approved manifest
- fingerprint schema missing required fields
- behavior canary fails
- deployment config pins stale version
- any privacy/security incident appears in first-10 rows
- a shared atom contains raw prompt/source/env/secrets
- sync accepts unsigned/tampered atom
- revocation/tombstone does not suppress retrieval
- same tenant can self-promote global learning

## Bottom line

For the current controlled beta, local CLI and local stdio MCP can continue. The served Hermes MCP channel must stay excluded until fingerprint/cutover proves current code. Global/federated learning should not be claimed until Borg has a signed atom ingestion/sync/revocation proof across at least two clean external environments.
