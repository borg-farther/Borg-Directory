# Borg roadmap — first-user value and safe rollout

File rev: `20260504-1129 rev A`

## Current rollout state

- Package/runtime version: `3.3.1`
- Canonical repo: `https://github.com/borg-farther/Borg-Directory`
- Current local readiness decision: **GO for controlled rollout**
- Machine snapshot: `eval/uat_scoreboard_snapshot.json`
- 1000 logical-user local gate: **passed** (`success_rate=1.0`, `failures=0`, `p95_ms=0.582`, `p99_ms=0.614`)

Honest boundary: this proves install/runtime/security/local soak gates. It does **not** prove statistically significant agent-level outcome lift or real external-user network effects.

## What Borg should be on day one

Borg should be the thing an agent checks before it wastes the user's money rediscovering a known failure mode.

Day-one success means:

1. A fresh user can install and verify it in one command path.
2. An agent can call `borg_observe` / `borg.check()` and get useful, bounded guidance.
3. Unsafe shared memory cannot leak secrets or inject instructions into the agent.
4. The product tells the truth about what is proven and what is not.
5. Every rollout claim has a machine-readable gate behind it.

## P0 — done / must stay green

- [x] Version consistency gate: `pyproject.toml`, `borg/__init__.py`, `build/lib/borg/__init__.py` all `3.3.1`.
- [x] First-user setup surface: README uses `pip install agent-borg` and `borg setup-claude --scope user --verify --fix`.
- [x] Runtime doctor: `borg-doctor` entrypoint restored and emits runtime fingerprint.
- [x] Security docs/gate: root `LICENSE`, security baseline, privacy model, prompt injection threat model, revocation/deletion docs.
- [x] Learning atoms: schema validation, privacy scan, prompt-injection firewall, tenant pseudonyms, signing/verification path.
- [x] V2 pack compatibility: apply/schema/proof gates accept V2 `structure[]` as well as V1 `phases[]`.
- [x] Local 10/100/1000 logical-user readiness gate: green as of `2026-05-04T11:24:00Z`.
- [x] Top-level public API no longer placeholder: `borg.check()` delegates to real search and has regression tests.

## P0 — watch like a hawk

1. **Claim hygiene**
   - Never market statistical agent-level lift until the A/B gate is significant and reproducible.
   - Keep DeFi/network/federation claims labeled as designed/prototype unless backed by live external data.

2. **First-user smoke test from clean env**
   - Required before every public push: fresh venv, `pip install agent-borg`, `borg setup-claude --scope user --verify --fix`, `borg-doctor`, `borg search`, `borg observe`/MCP handshake.

3. **Public distribution authenticity**
   - Ed25519 primitives and atom signatures exist; universal pack-signature enforcement remains optional/backward-compatible. If marketing says “signed packs,” the pull/apply path must enforce or explicitly report signature state.

## P1 — next permanent product upgrades

1. **Agent-visible auto-observe by default**
   - Make every supported agent integration call observe before technical fixes without user prompt edits.
   - Gate: install → first `borg_observe` in <60 seconds.

2. **External first-user loop**
   - One non-us user completes: install → observe/search → apply guidance → rate/record outcome.
   - Gate: captured log + privacy-safe atom + user-visible saved time.

3. **A/B utility proof**
   - Continue strict binary gates: 10-user first, then 100-user.
   - Required outcome: reduced redundant exploration or improved task success with no negative transfer.

4. **Pack-signature UX**
   - Add explicit CLI/MCP fields: `signature_state=verified|unsigned|invalid|unavailable`.
   - Invalid signatures must fail closed for global/trusted sources.

5. **Distribution resilience**
   - Remove single-point GitHub assumptions from runtime fetch path.
   - Add cache/offline bundle fallback and machine-readable source provenance.

## P2 — scale after proof, not before

- Reputation-gated promotion and anti-Sybil controls wired into public publish/search ranking.
- Dashboard for pack/atom helpfulness, revocations, confidence drift, and false-confidence rate.
- Private org Borgs with tenant-isolated atom stores and export/delete controls.
- Navigation cache only when surfaced in CLI/MCP and evaluated against real tasks.

## Decision rule

Borg is ready to push wider only when the live scoreboard says so. No vibes, no vanity metrics, no stale roadmap claims.
