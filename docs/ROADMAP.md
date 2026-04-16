# Borg Roadmap

Source of truth for launch gates, invariants, design review state, and phase scope. Updated 2026-04-16 (v3.4.0-honest).

## Project thesis

Borg is an **open commons for agent error-recovery traces**, delivered as an MCP server. Agents query before burning tool calls on known errors; Borg surfaces what worked in prior sessions. The thesis is that recovery knowledge is more valuable shared than siloed per-agent, and that a read-through cache architecture beats per-agent memory for this class of problem.

## Current status (2026-04-16)

| Layer | State |
|---|---|
| DB | 172 organic in `traces`, 156 non-organic in `seed_traces`, invariants I3/I4 live |
| Retrieval | Tiered: organic first, synthetic fallback, `source_tier` labelled |
| Write path | `save_trace` rejects non-organic sources with `ValueError` |
| MCP server | `borg_observe` / `borg_rate` / `borg_status` live; no rate limiting yet |
| Bench harness | Not built. All public performance claims pending. |
| PII gate | Live, zero offenders on real data |

## Five Invariants

| # | Invariant | Status | Blocker if red |
|---|---|---|---|
| I1 | First query hits in <30s on fresh install | Pending Phase 1 harness | Launch |
| I2 | README performance numbers reproducible from `borg-bench` | Pending Phase 1 harness | Launch |
| I3 | `traces` and `seed_traces` architecturally separate | **LIVE** |  |
| I4 | PII never ships | **LIVE** |  |
| I5 | Exported traces validate against `BORG_TRACE_FORMAT_v1` | Pending JSON schema | Phase 2 |

## Launch Gates (G1G10)

All must be green before public launch.

| # | Gate | Status |
|---|---|---|
| G1 | All 5 invariants passing in CI | I3, I4 green; I1/I2/I5 pending |
| G2 | `borg-bench` harness built with WILD-200 held-out set | Not started |
| G3 | Published performance numbers reproducible from G2 harness | Pending G2 |
| G4 | Prompt-injection sanitizer on retrieval output path | Not started (B1) |
| G5 | Rate limiting on MCP server | Not started (M6) |
| G6 | Invited beta with 3 external users, 1 week stable | Not started |
| G7 | `BORG_TRACE_FORMAT_v1` JSON schema published | Not started |
| G8 | Trust schema (agent_reputation) populated + used in retrieval | Tables exist, unused |
| G9 | Dead-end re-ranker live in retrieval | Not started |
| G10 | MCP tool rename (`borg_observe`  `error_lookup`) with alias | Not started (this roadmap) |

## Design Review State

From Borg_Spec_Adversarial_Review.md (2026-04-15) + post-Phase-0 updates.

**Blockers (B1B4):**

- **B1  Prompt injection via stored trace text.** Borg feeds trace content back to agents. A malicious trace could inject instructions. **Not fixed.** Needs sanitization layer on retrieval output. Pre-launch blocker.
- **B2  Unfalsifiable I2.** "README numbers reproducible from bench" was unfalsifiable as written. **Resolved**  Build Spec v2 now specifies exact WILD-200 methodology.
- **B3  WILD-50 / PII bootstrapping contradiction.** Held-out real traffic eval requires real user traces, but PII gate blocks committing them to repo. **Resolved in spec**  WILD-50 split into PUBLIC (sanitized, committed) and PRIVATE (runs locally, never committed). Implementation pending Phase 1.
- **B4  `intervention_type` backfill.** Column `causal_intervention` exists but 172 organic traces have no backfill schedule. **Plan pending** (see `docs/backfill_plan.md`).

**High-severity (H1H3)  all closed:**

- H1 Hook firing verified live in production (9 stderr markers in 33s, 2026-04-16).
- H2 Pattern ordering corrected (specific `EADDRINUSE`/`ENOMEM` before generic `\w+Error`).
- H3 FTS5 injection prevented via `_sanitize_fts()`.

**Medium-severity (M1M6):**

- M1 Playground CORS  Phase 2, not blocking.
- M2 DB context managers  deferred to Phase 1.
- M3 Source-tier labelling  **resolved** (Phase 0 Day 2).
- M4 Trigger reintroduction with `OLD.id`  Phase 1.
- M5 Seed audit (credibility risk: 156/328 synthetic with some passed off)  **resolved in Phase 0** via real/synthetic separation.
- M6 Rate limiting on MCP server  launch gate G5.

## Phase scope

### Phase 0  Data hygiene (shipped v3.4.0-honest, 2026-04-16)

Done:
- Real/synthetic table split
- Write-path guard (I3)
- Tiered retrieval with `source_tier`
- 4 live invariant tests
- Honest README, prior claims withdrawn
- Migration log + state snapshot

### Phase 1  Launch-ready (6 weeks, not started)

Critical path:
1. `borg-bench` harness with WILD-200 held-out set ( G2, G3, I1, I2)
2. Prompt injection sanitizer on retrieval ( G4, B1)
3. Rate limiting on MCP server ( G5, M6)
4. MCP tool rename `borg_observe`  `error_lookup` with 90-day alias ( G10)
5. `BORG_TRACE_FORMAT_v1` JSON schema + I5 test ( G7, I5)
6. Trust schema wiring in retrieval ranker ( G8)
7. Dead-end re-ranker ( G9)
8. Invited beta 3 external users ( G6)

Nice-to-have:
- Reintroduce `cascade_delete_trace_index` trigger with `OLD.id` fix (M4)
- DB context managers refactor (M2)
- `causal_intervention` backfill execution (B4)

### Phase 2  Public launch (after all G1G10 green)

- Public GitHub announcement
- PyPI publish under final name (pending G10)
- Playground CORS fix (M1)
- Trace format adoption outreach to agent-framework maintainers
- Governance model (single-maintainer  transition plan)

## Non-goals (explicit)

- **Not** a universal agent memory. Borg is scoped to error-recovery traces only.
- **Not** claiming per-agent personalization. Trust schema exists but Phase 1 scope is collective reputation, not per-user.
- **Not** building our own agent framework. Borg is a read-through cache that any framework can wire up via MCP.

## Bus factor

Single maintainer. No redundancy. If this matters to a downstream user, fork.
