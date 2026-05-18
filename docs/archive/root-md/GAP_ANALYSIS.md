# AI Guild v2 — Gap Analysis Report
## Spec: `/root/hermes-workspace/specs/ai-guild-design-doc-v2.0.md`
## Code: `/root/hermes-workspace/guild-v2/`
## Date: 2026-03-27

---

## EXECUTIVE SUMMARY

The spec is **significantly outdated** and was written when the project had ~162 tests. The codebase now has **603 passing tests** — nearly 4x the spec's stated count. Most core infrastructure exists and works, but the spec massively overstates what's actually built in several major areas: the reputation/economics engine, the coordinator pattern, and the adoption/incentive mechanisms. The architecture is technically sound but **heavily over-engineered for zero users**.

---

## PART 1: WHAT SPEC SAYS SHOULD EXIST THAT DOESN'T

### 1.1 MCP Tool: `guild_submit` (listed as tool #5)
- **Spec (line 511):** `guild_submit — feedback_handler — Submit feedback on a used pack`
- **Reality:** The 7th MCP tool is `guild_feedback`, not `guild_submit`. `guild_feedback` generates a feedback draft from an execution session. It does NOT actually submit feedback to the guild repository — that workflow is incomplete.
- **Impact:** Minor. The feedback generation exists; the submission to GitHub via the full workflow is incomplete.

### 1.2 CLI Wrapper (M2 transport)
- **Spec (line 499):** `CLI — M2 — Local — hermes guild try/pull/apply/publish/search shell commands wrapping core engine`
- **Reality:** CLI wrapper does NOT exist as shell commands. Only the MCP server interface exists.
- **Impact:** Medium. MCP is the primary transport, so this is deferrable.

### 1.3 Discord Bot Transport (M2)
- **Spec (line 498):** `Discord — M2 — Bidirectional — File attachments, Notifications for new packs`
- **Reality:** Discord bot transport does NOT exist.
- **Impact:** Low. Marked M2, not required for Phase 1-2.

### 1.4 SDK / REST API (M3)
- **Spec (line 500):** `SDK — M3 — Programmatic — Python/TypeScript SDK`
- **Reality:** Does NOT exist.
- **Impact:** Low. Marked M3, far future.

### 1.5 Coordinator Bot (Automated)
- **Spec (Section 5):** Fully automated coordinator bot that mediates GitHub operations for external agents, with credential isolation, validation enforcement, rate limiting, branch management, PR formatting, outbox management, and audit trail.
- **Reality:** `publish.py` has `create_github_pr()` which uses `gh CLI` directly. There is NO automated coordinator bot. The "coordinator" described in the spec (Section 5.3 table with 8 responsibilities) does not exist as a separate service.
- **Impact:** HIGH. The coordinator is a core architectural piece for external agent support. Currently, pack publication requires direct `gh` CLI access.

### 1.6 `guild convert` Tool (Phase 3)
- **Spec (line 1487):** `guild convert tool: import from CLAUDE.md, .cursorrules, SKILL.md`
- **Reality:** Does NOT exist. Only `guild_init` (scaffold new) and `guild_init --from-skill` conversion exist in `search.py`.
- **Impact:** Medium. Part of the supply-side growth engine.

### 1.7 Pack Analytics Dashboard
- **Spec (line 1510):** `Pack analytics dashboard for operators`
- **Reality:** Does NOT exist.
- **Impact:** Low. Operator-facing, Phase 4.

### 1.8 Ecosystem Health Dashboard
- **Spec (line 709-718):** `health_score = weighted_sum(active_contributors/total_members, avg_pack_quality_trend, ...)` with below-threshold notifications.
- **Reality:** Does NOT exist.
- **Impact:** Low. Phase 4+, governance layer.

### 1.9 Private Guild Support
- **Spec (line 1511):** `Private guild support (company-internal knowledge exchange)`
- **Reality:** Does NOT exist.
- **Impact:** Low. Phase 4 enterprise.

### 1.10 Guild-to-Guild Pack Sharing Protocol
- **Spec (line 1512):** `Guild-to-guild pack sharing protocol (with proof gate requirements)`
- **Reality:** Does NOT exist.
- **Impact:** Low. Phase 4 federation.

### 1.11 Confidence Decay Enforcement in Workflow
- **Spec (line 400):** `Confidence decay: packs auto-downgrade if not re-validated within TTL (guessed=30d, tested=90d, validated=365d)`
- **Reality:** `check_confidence_decay()` exists in `proof_gates.py` and is called in search/try/pull, but does NOT block pack usage. It's advisory only.
- **Impact:** Medium. The decay exists but doesn't enforce usage restrictions.

### 1.12 Risk-Proportional Approval
- **Spec (line 1488):** `Risk-proportional approval: auto-approve low-risk packs, require review for high-risk`
- **Reality:** Does NOT exist. All packs require the same `__approval__` checkpoint.
- **Impact:** Low. Phase 3.

### 1.13 Adoption Count (Weighted by Operator Diversity)
- **Spec (line 408):** `Adoption count (weighted by operator diversity)` as a trust signal
- **Reality:** Does NOT exist as a displayed metric anywhere.
- **Impact:** Low.

### 1.14 Sandbox Constraints
- **Spec (line 354):** `Sandbox constraints (spec'd, enforcement in progress): path restrictions, network scope, credential access`
- **Reality:** NOT implemented. No sandboxing.
- **Impact:** Medium. Security gap.

### 1.15 Auto-Suggest Prototype (Phase 2)
- **Spec (line 1463):** `Auto-suggest prototype: agent detects struggle → suggests relevant pack`
- **Reality:** `check_for_suggestion()` and `classify_task()` exist in `search.py` but appear minimal/stub. `suggest_packs()` in `semantic_search.py` exists but requires embeddings.
- **Impact:** Medium. This is the key demand-side growth mechanism.

---

## PART 2: WHAT EXISTS IN CODE THAT SPEC DOESN'T MENTION

### 2.1 SQLite Store (`guild/db/store.py`)
- Full SQLite-based persistent store with schema migrations, FTS5 full-text search, pack and feedback CRUD — NOT mentioned in the spec at all.
- The spec describes file-based JSONL execution logs but not a SQLite store.

### 2.2 Embeddings System (`guild/db/embeddings.py`)
- `EmbeddingEngine` for vector storage and similarity search — completely absent from spec.
- Spec's semantic search (Phase 4, line 1508) is mentioned as M3 but the actual implementation is more mature than the spec suggests.

### 2.3 Semantic Search Engine (`guild/core/semantic_search.py`)
- Full hybrid search with semantic/text/hybrid modes, reranking, and pack suggestions — this is Phase 4 in spec but Phase 1-2 in implementation.

### 2.4 Analytics Module (`guild/db/analytics.py`)
- `GuildAnalytics` for computing engagement metrics, second-pack activation, contributor conversion — NOT in spec at all, despite the spec having an entire Metrics Framework section.

### 2.5 Reputation Engine (`guild/db/reputation.py`)
- Full `ReputationEngine` with contribution scoring, access tiers, free-rider detection, inactivity decay — the spec describes this in extensive game-theoretic detail (Section 2) but the actual implementation is a shadow of the spec. The spec describes Beta reputation, EigenTrust, SybilGuard, Bayesian Truth Serum, Shapley attribution — NONE are implemented. What exists is a simplified contribution counter.

### 2.6 Schema Module (`guild/core/schema.py`)
- `parse_workflow_pack`, `validate_pack`, `collect_text_fields`, `parse_skill_frontmatter`, `sections_to_phases` — all exist but not documented as standalone modules in the spec.

### 2.7 MCP Server Has 7 Tools
- Spec line 497 says 7 tools registered, but lists only 6 by name (missing `guild_submit`). MCP has 7: `guild_search`, `guild_pull`, `guild_try`, `guild_init`, `guild_apply`, `guild_publish`, `guild_feedback`.

### 2.8 Test Count: 603 (vs spec's 162)
- Spec was written at 162 tests. Code now has 603 tests.
- This means the spec is severely stale.

### 2.9 `guild_feedback` Tool
- The MCP server exposes `guild_feedback` for generating feedback drafts from execution sessions. Not mentioned in spec's tool list.

### 2.10 FTS5 Full-Text Search
- `GuildStore.search_packs()` uses SQLite FTS5 for full-text search. Not mentioned in spec.

---

## PART 3: SPEC REQUIREMENTS IMPLEMENTED DIFFERENTLY

### 3.1 Pack Storage Path
- **Spec (line 259):** `Save to ~/.hermes/guild/{name}/pack.yaml (spec target: ~/.hermes/skills/{domain}/{name}.yaml)`
- **Code:** `~/.hermes/guild/{name}/pack.yaml` — matches the parenthetical, NOT the primary spec.
- **Status:** Partial. The `~/.hermes/skills/` path variant was the intended target but not implemented.

### 3.2 Feedback Generation
- **Spec (line 297-301):** Feedback should include: `before`, `after`, `what_changed`, `why_it_worked`, `evidence`, `where_to_reuse`, `failure_cases`, `execution_log_hash`
- **Code (`_generate_feedback` in `apply.py`):** Returns only `before`, `after`, `evidence`, `schema_version`, `type`. Missing: `what_changed`, `why_it_worked`, `where_to_reuse`, `failure_cases`.
- **Status:** PARTIAL. Basic fields exist; most complex fields missing.

### 3.3 Proof Gate Validation — Different File Locations
- **Spec (line 330):** `guild publish <path>` validates proof gates → safety scan → privacy scan → GitHub PR
- **Code (`publish.py`):** Validates proof gates → safety scan → privacy scan (in that order) ✓ CORRECT
- BUT: `guild_init` in search.py does NOT validate proof gates before returning the scaffold — the user could create an invalid pack.

### 3.4 Confidence Decay TTL Values
- **Spec (line 1486):** `guessed=30d, tested=90d, validated=365d`
- **Code (`proof_gates.py`):** `validated=365, tested=180, inferred=90, guessed=30`
- **Status:** **DIFFERENT.** Spec says tested=90d, code has tested=180d (twice as long). Spec is missing `inferred=90d` tier entirely.

### 3.5 Retry Logic
- **Spec (line 285):** `FAIL: retry once → FAIL again → skip with log entry`
- **Code (`apply.py` line 409):** Same behavior ✓

### 3.6 Rate Limit
- **Spec (line 220, 456):** Max 3 publishes per agent per day, max 10 feedback/day
- **Code (`publish.py`):** Max 3 publishes/day ✓. No feedback rate limit implemented.
- **Status:** PARTIAL.

### 3.7 Feedback Requires `execution_log_hash`
- **Spec (line 220-221):** `Feedback must include execution_log_hash`
- **Code (`_validate_feedback_gates`):** Enforced ✓
- **BUT:** The code in `apply.py` `_generate_feedback` does NOT include `execution_log_hash` in the generated feedback dict. It's left to the caller to add it.
- **Status:** PARTIAL. Validation enforces it; generation doesn't produce it.

### 3.8 Trust Tier Computation
- **Spec (line 313-315):** CORE = maintained by project, highest trust; VALIDATED = community packs passed gates; COMMUNITY = published with proof gates
- **Code (`compute_pack_tier`):** CORE requires `author_agent starts with 'agent://hermes'` which is a much narrower definition than "project-maintained." VALIDATED requires `confidence in ('tested', 'validated')` — but the spec says "community packs that passed validation gates" which could include 'inferred' packs that passed their gates.
- **Status:** DIFFERENT. The implementation uses author_agent prefix as a proxy for CORE status, which is a narrow heuristic not described in the spec.

### 3.9 Safety Scanner Pattern Count
- **Spec (line 111):** `9 injection patterns, 11+ privacy patterns`
- **Spec (line 18):** `9 injection patterns, 11 privacy patterns`
- **Code (`safety.py`):** 13 injection patterns, 5 credential patterns, 7 file access patterns, 2 path traversal patterns, 11 privacy patterns (but different set than spec)
- **Status:** DIFFERENT. Pattern counts don't match spec.

### 3.10 Reputation System — Not Wired In
- **Spec (Section 2):** Full Beta reputation, EigenTrust, SybilGuard, quality scoring. Access tiers gate pack visibility.
- **Code (`reputation.py`):** Exists as a standalone computation engine but is NEVER called from `publish.py`, `apply.py`, or `search.py`. No access restrictions are enforced based on reputation.
- **Status:** UNWIRED. The reputation engine computes scores but has zero effect on the system.

### 3.11 URI Resolution
- **Spec (line 241-246):** `guild://domain/name → GitHub raw URL`, retry once after 5s on network failure
- **Code (`uri.py`):** `guild://` resolves to `https://raw.githubusercontent.com/bensargotest-sys/guild-packs/main/packs/{name}.workflow.yaml` — but the spec says `packs/{name}.yaml` not `.workflow.yaml`. Retry sleep is 1s, 2s... (exponential) not "5s once" as spec states.
- **Status:** DIFFERENT.

### 3.12 MCP Tool Names in Spec vs Code
| Spec (line 505-513) | Code (MCP Server) |
|---------------------|-------------------|
| guild_try | guild_try ✓ |
| guild_pull | guild_pull ✓ |
| guild_apply | guild_apply ✓ |
| guild_publish | guild_publish ✓ |
| guild_submit | guild_feedback ✗ |
| guild_init | guild_init ✓ |
| guild_search | guild_search ✓ |

The spec calls it `guild_submit` but the code uses `guild_feedback`.

---

## PART 4: REAL COMPLETION PERCENTAGE BY SECTION

### Phase 1: PROVE THE LOOP
| Deliverable | Status | Notes |
|------------|--------|-------|
| 4 working packs with full lifecycle | PARTIAL | Packs exist but 4 may be optimistic; full lifecycle works in tests |
| 162 passing tests | OUTDATED | 603 tests now |
| Coordinator agent managing pack development | NOT STARTED | No automated coordinator exists |
| Discord #ai-guild channel live | DON'T KNOW | Can't verify |
| 1 external tester completing full loop | NOT STARTED | Zero external users per context |

**Phase 1 Status: ~40% DONE** — core engine works, coordinator/discord/external tester are gaps.

### Phase 2: OPEN THE DOOR
| Deliverable | Status | Notes |
|-------------|--------|-------|
| guild-mcp-server on PyPI | DON'T KNOW | Can't verify pip install |
| Works with Claude Code | UNVERIFIED | Not tested externally |
| Works with Cursor | UNVERIFIED | Not tested externally |
| 20 seed packs | PARTIAL | ~21 packs on GitHub per context |
| guild_search with keyword matching | DONE ✓ | Implemented in search.py |
| Auto-suggest prototype | PARTIAL | Stub exists, not production-ready |
| 30-second setup README | DON'T KNOW | Can't verify |
| Demo video | DON'T KNOW | Can't verify |

**Phase 2 Status: ~50% DONE** — MCP server works, search works, pack count adequate, but auto-suggest and cross-platform verification are incomplete.

### Phase 3: SCALE THE TRUST
| Deliverable | Status | Notes |
|-------------|--------|-------|
| PyPI package ai-guild with CLI | NOT STARTED | No CLI commands |
| Python SDK | NOT STARTED | No SDK |
| npm package (TypeScript SDK) | NOT STARTED | No TS SDK |
| Three-tier trust system | PARTIAL | Computed but not enforced in UI/display |
| Confidence decay | PARTIAL | TTL values differ from spec; advisory only |
| guild convert tool | NOT STARTED | Partial via guild_init --from-skill only |
| Risk-proportional approval | NOT STARTED | No differentiation |

**Phase 3 Status: ~20% DONE** — core pieces exist but nothing shipped as a package/SDK.

### Phase 4: BUILD THE NETWORK
| Deliverable | Status | Notes |
|-------------|--------|-------|
| Reputation scores (Bayesian) | PARTIAL | Engine exists but not wired to permissions |
| Contribution tracking | PARTIAL | Tracks publications; doesn't gate access |
| Semantic search | DONE ✓ | Implemented in semantic_search.py |
| Agent auto-discovery | NOT STARTED | No auto-suggest worth calling this |
| Pack analytics dashboard | NOT STARTED | analytics.py exists but no dashboard |
| Private guild support | NOT STARTED | No multi-tenant anything |
| Guild-to-guild sharing | NOT STARTED | No federation |
| Community showcase | NOT STARTED | No UI for this |

**Phase 4 Status: ~15% DONE** — semantic search done, rest is theory.

---

## OVERALL SPEC COMPLETION: ~35%

**Breakdown:**
- Core infrastructure (apply, publish, pull, try, safety, privacy, proof gates, session): ~80% complete
- MCP transport: ~90% complete (7 tools, proper handlers)
- Coordinator/Discord/CLI: ~15% complete
- Reputation/economics engine: ~20% complete (exists on paper, not wired)
- Supply-side (guild convert, 20 seed packs): ~40% complete
- Demand-side (auto-suggest, analytics dashboard): ~15% complete
- Phase 3+ (SDK, CLI, packages): ~10% complete

---

## ARCHITECTURE ASSESSMENT: Is This The Right Approach?

### Honest Answer: **Over-Engineered Infrastructure, Starved for Users**

The "npm for agent workflows" pitch is compelling and the proof gate + feedback loop + safety scanning combination is genuinely unique. The technical implementation is solid — the core engine, session management, safety scanning, and proof gates all work. But several fundamental problems exist:

**1. The spec describes a Ferrari; the code is a working engine on blocks.**
The 88K spec describes an elaborate system with game-theoretic incentive models (6-layer incentive stack, Beta reputation, EigenTrust, SybilGuard, Bayesian Truth Serum, Shapley attribution), but the actual implementation that users would interact with is a basic MCP server that can pull packs and execute them. The infrastructure-to-user-value ratio is extremely poor.

**2. The reputation system is not wired in AT ALL.**
The entire economic mechanism design (Section 2 of spec, ~450 lines of game theory) exists as code but has zero effect on the system. Access tiers aren't enforced. Free-rider detection doesn't block anyone. The "six layers of incentives" that are supposed to make sharing dominant over hoarding do nothing because they're never called.

**3. Zero external users is the existential problem.**
With 0 current external users and ~21 packs on GitHub, the feedback loop that is supposed to make packs "get smarter with every use" is completely non-functional. The spec acknowledges this as the chicken-and-egg problem but doesn't adequately address it. The architecture is designed for scale that hasn't happened.

**4. The coordinator bot is the missing piece for external adoption.**
The spec's entire external agent strategy depends on a coordinator bot that doesn't exist. Without it, only agents with direct `gh` CLI access can publish. This is a fundamental blocker for the "npm for agent workflows" vision.

**5. Auto-suggest (the growth engine) is a stub.**
The single most important feature for adoption — the agent detecting struggle and suggesting a relevant pack — is not implemented. Without it, users have to manually know about guild and type commands. This defeats the "zero-friction entry" vision.

**6. The "npm" analogy breaks down when you look at what users actually do.**
npm's aha moment is `npm install something` and it immediately works in your project. The guild's aha moment requires: (1) knowing about the guild, (2) finding a relevant pack, (3) pulling it, (4) applying it with operator approval, (5) going through phases, (6) generating feedback, (7) publishing feedback. That's 7 steps with human approval gates. This is not npm. This is more like getting a peer review published in an academic journal.

### What Should Happen:
1. Ship the coordinator bot — it's the #1 blocker for external adoption
2. Wire the reputation system OR admit it's over-engineered and simplify
3. Implement auto-suggest — it's the difference between 0 and viral
4. Get the "aha moment" down to 2 steps, not 7
5. Update the spec to match reality (603 tests, not 162)

### The One Thing Going For It:
The code quality is genuinely high. 603 tests, clean module separation, zero imports from `tools.*`, good error handling. If users ever arrive, the system will work. The problem is purely on the distribution/adoption side.

---

## FILES ANALYZED
- `/root/hermes-workspace/specs/ai-guild-design-doc-v2.0.md` — full spec (1540 lines)
- `/root/hermes-workspace/guild-v2/guild/core/apply.py` — 1027 lines
- `/root/hermes-workspace/guild-v2/guild/core/publish.py` — 559 lines
- `/root/hermes-workspace/guild-v2/guild/core/proof_gates.py` — 369 lines
- `/root/hermes-workspace/guild-v2/guild/core/safety.py` — 267 lines
- `/root/hermes-workspace/guild-v2/guild/core/privacy.py` — 144 lines
- `/root/hermes-workspace/guild-v2/guild/core/session.py` — 323 lines
- `/root/hermes-workspace/guild-v2/guild/core/uri.py` — 228 lines
- `/root/hermes-workspace/guild-v2/guild/core/search.py` — 803 lines
- `/root/hermes-workspace/guild-v2/guild/core/schema.py` — 285 lines
- `/root/hermes-workspace/guild-v2/guild/core/semantic_search.py` — 514 lines
- `/root/hermes-workspace/guild-v2/guild/db/store.py` — 1034 lines
- `/root/hermes-workspace/guild-v2/guild/db/reputation.py` — 462 lines
- `/root/hermes-workspace/guild-v2/guild/db/analytics.py` — analyzed
- `/root/hermes-workspace/guild-v2/guild/integrations/mcp_server.py` — 828 lines
- All test files — 569 test functions total
- Pytest run: **603 tests passing**
