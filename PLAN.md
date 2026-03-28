# BORG MASTER PLAN
## From Demo to Dominant Agent Workflow Ecosystem
### Generated: 2026-03-28 | Status: DRAFT — requires AB approval

---

## HONEST ASSESSMENT

### What we have:
- Well-architected core logic (reputation, search, safety, proof gates, failure memory)
- Good pack schema with provenance/confidence tiers
- 23 packs (quality unverified)
- 970 tests passing
- Zero external users

### What we don't have:
- Production-ready infrastructure (single-agent, single-process assumptions everywhere)
- Working MCP tools (3 of 12 are `NameError` stubs: `borg_reputation`, `borg_context`, `borg_recall`)
- External validation of any kind
- A distribution strategy beyond "test GitHub org"

### The core tension:
Building more features on a foundation that can't handle >1 user is premature optimization.
Getting users before the foundation works is reputation suicide.
**The plan must thread this needle.**

---

## PHASE 0: STOP THE BLEEDING (1-2 days)
**Goal:** No broken tools, no false advertising

### 0.1 Fix or remove broken MCP tools
- `borg_reputation` — implement (reputation.py is ready, just needs wiring)
- `borg_context` — implement or remove from TOOLS schema
- `borg_recall` — implement or remove from TOOLS schema
- **Eval:** `borg-mcp` starts, every declared tool can be called without `NameError`
- **Test:** Call every tool via stdio, verify JSON response (not crash)

### 0.2 Wire reputation into core flows
- `apply.py` — record pack usage events
- `publish.py` — record publication events
- `search.py` — reputation-aware ranking (partially done)
- `feedback.py` — record feedback as reputation signal
- **Eval:** `ReputationEngine` import count in core/ goes from 0 to 4+
- **Test:** Integration test: publish → use → feedback → check reputation changed

### 0.3 Fix the README
- Remove unverifiable claims ("reduces 12 iterations to 4")
- Add architecture diagram (text-based)
- Link to real pack examples
- Add API reference for all 12+ MCP tools
- **Eval:** A developer reading README can understand what borg does in 2 minutes

### Definition debt:
- [ ] What exactly does `borg_context` do? (underspecified)
- [ ] What exactly does `borg_recall` do vs `borg_observe`? (overlapping)

---

## PHASE 1: SINGLE-AGENT PRODUCTION QUALITY (1 week)
**Goal:** One agent can use borg reliably for real work, end to end

### 1.1 SQLite hardening
- Enable WAL mode
- Add connection pooling
- Handle SQLITE_BUSY with retry
- **Eval:** 10 concurrent threads can read/write without errors
- **Test:** Stress test with threading

### 1.2 Session persistence
- Sessions survive process restart
- Orphaned session cleanup on startup
- **Eval:** Kill borg-mcp mid-session, restart, session recoverable
- **Test:** Integration test with process kill

### 1.3 Configurable BORG_DIR
- `BORG_DIR` env var override
- Per-agent namespace support
- **Eval:** Two agents on same machine don't collide
- **Test:** Run two borg-mcp instances with different BORG_DIR, verify isolation

### 1.4 Pack quality audit
- Read all 23 packs
- Score each against pack schema requirements
- Fix or remove packs that don't meet spec
- **Eval:** Every pack has: provenance, confidence level, at least 1 example, safety scan passes
- **Autoresearch candidate:** YES — automated pack quality scoring against schema

### 1.5 CLI completeness
- `borg reputation <agent_id>` command
- `borg status` — show local state, sessions, reputation
- **Eval:** Every MCP tool has a CLI equivalent
- **Test:** CLI integration tests

### Definition debt:
- [ ] What's the upgrade path when pack schema changes? (versioning)
- [ ] How do packs handle dependencies on other packs? (composition)
- [ ] What's the security model for pack execution? (sandboxing depth)

---

## PHASE 2: FIRST EXTERNAL USER (2 weeks)
**Goal:** One real agent framework integrates borg and uses it for real work

### 2.1 Integration target selection
- **Research needed:** Which framework has the lowest integration barrier?
  - Hermes (we control it — easiest but not external validation)
  - Cline (VS Code extension, large user base, MCP support)
  - OpenClaw (open source, community-driven)
  - Cursor (largest user base but hardest to influence)
- **Eval criteria for target selection:**
  - Integration effort (days)
  - User reach (agents using it)
  - Feedback quality (will they report issues?)
  - Strategic value (does this unlock others?)

### 2.2 Integration guide
- Step-by-step for chosen framework
- "Hello world" pack usage tutorial
- Troubleshooting guide
- **Eval:** A developer unfamiliar with borg can integrate in <30 minutes
- **Test:** Have someone follow the guide cold

### 2.3 Telemetry (opt-in)
- Track: search queries, pack pull counts, apply success/failure rates
- No PII, no pack content
- **Eval:** Dashboard showing real usage patterns
- **Verification:** Privacy review of telemetry data

### 2.4 Feedback loop
- `borg_feedback` must be trivially easy to call
- Aggregate feedback into pack improvements
- **Eval:** Feedback → aggregator → improved pack, end-to-end automated
- **Autoresearch candidate:** YES — measure pack improvement quality over feedback cycles

### Definition debt:
- [ ] What's the SLA for pack availability? (uptime)
- [ ] What happens when GitHub is down? (offline mode)
- [ ] How do we handle pack conflicts between versions? (resolution)

---

## PHASE 3: NETWORK EFFECTS (1-2 months)
**Goal:** Multiple agents contributing packs, reputation system creating quality signals

### 3.1 Coordinator service
- Accept pack submissions without requiring git CLI
- Automated quality gates (safety scan, schema validation, test execution)
- **Eval:** External agent can publish a pack via MCP tool only (no git)
- **Test:** End-to-end: agent creates pack → submits → quality gate → published

### 3.2 Aggregator automation
- Cron/CI trigger for improvement loop
- Auto-PR for improved packs
- Human approval gate for confidence promotions
- **Eval:** Aggregator runs weekly, produces measurable pack improvements
- **Autoresearch candidate:** YES — measure aggregator output quality

### 3.3 Benchmark suite
- Define 10 standard agent tasks
- Measure: with borg vs without borg
- Publish results publicly
- **Eval:** Statistically significant improvement on ≥7/10 tasks
- **Autoresearch candidate:** YES — this IS autoresearch

### 3.4 Pack ecosystem growth
- Target: 50 packs (from 23)
- Categories: debugging, code review, TDD, planning, deployment, data, security, testing
- **Eval:** Search query → relevant pack found for 80%+ of common agent tasks

### 3.5 Distribution beyond GitHub
- CDN for pack index
- Fallback mirrors
- Offline pack bundles
- **Eval:** Pack fetch latency <500ms p95

### Definition debt:
- [ ] Governance model for pack acceptance (who decides?)
- [ ] Dispute resolution for conflicting packs
- [ ] Licensing model (MIT? Apache? CLA?)
- [ ] Monetization strategy (if any)

---

## PHASE 4: SCALE (3-6 months)
**Goal:** Borg is the default workflow source for AI agents

### 4.1 Multi-agent infrastructure
- Replace SQLite with Postgres (or keep SQLite + proper locking)
- Distributed session store
- Rate limiting
- Auth (API keys per agent)
- **Eval:** 100 concurrent agents, <1% error rate

### 4.2 MiniMax format conversion
- Import MiniMax YAML+markdown into borg pack format
- Automated conversion pipeline
- **Eval:** 80%+ of MiniMax content converts without manual intervention

### 4.3 Reputation as competitive moat
- Public reputation scores
- Leaderboard
- Verified publisher program
- **Eval:** Reputation score correlates with pack quality (measured by user feedback)

### 4.4 Cross-framework compatibility
- Works with: Claude Code, Cursor, Cline, OpenClaw, AutoGPT, CrewAI
- Framework-specific adapters where needed
- **Eval:** Same pack works across 3+ frameworks without modification

---

## RESOURCE ALLOCATION MATRIX

| Phase | Research % | Implementation % | Testing % | Outreach % |
|-------|-----------|------------------|-----------|------------|
| 0     | 10        | 60               | 30        | 0          |
| 1     | 20        | 50               | 30        | 0          |
| 2     | 30        | 30               | 20        | 20         |
| 3     | 20        | 30               | 20        | 30         |
| 4     | 10        | 40               | 30        | 20         |

---

## AUTORESEARCH CANDIDATES (ranked by impact)

1. **Benchmark suite** (Phase 3.3) — directly proves borg's value proposition
2. **Pack quality scoring** (Phase 1.4) — automated quality gates
3. **Aggregator output quality** (Phase 3.2) — measures self-improvement loop
4. **Feedback → improvement cycle** (Phase 2.4) — measures learning rate

---

## ASSUMPTIONS REQUIRING VALIDATION

| # | Assumption | Risk if wrong | Validation method |
|---|-----------|---------------|-------------------|
| A1 | AI agents benefit from shared workflows | Fatal — no product | Benchmark suite (Phase 3.3) |
| A2 | MCP is the winning standard | High — wrong protocol | Monitor adoption metrics quarterly |
| A3 | Pack quality matters more than quantity | Medium — wrong priority | A/B test curated vs uncurated |
| A4 | Reputation systems drive quality | Medium — overhead without benefit | Measure correlation after Phase 3 |
| A5 | GitHub is sufficient for distribution | Low short-term, high long-term | Monitor fetch latency and availability |
| A6 | SQLite is sufficient for Phase 1-2 | Low — can migrate later | Stress test at Phase 1.1 |

---

## KILL CRITERIA

Stop and pivot if:
- Phase 2 completes and zero external agents adopt voluntarily
- Benchmark suite shows no measurable improvement from using borg
- Pack feedback is consistently "not useful" or "too generic"
- MCP adoption stalls or a competing standard emerges with >10x traction

---

## WHAT'S STILL UNDERSPECIFIED (definition debt backlog)

### Critical (blocks Phase 1):
1. `borg_context` tool — what does it actually do?
2. `borg_recall` vs `borg_observe` — overlapping purpose, need to resolve
3. Pack versioning strategy — what happens when a pack changes?

### Important (blocks Phase 2):
4. Offline mode behavior
5. Telemetry privacy spec
6. Integration guide structure

### Future (blocks Phase 3+):
7. Governance model
8. Dispute resolution
9. Monetization
10. Multi-region distribution

---

## NEXT ACTION

Before implementing anything: AB reviews this plan and answers:
1. Is the phase ordering right? (fix foundation → single-agent quality → first user → network effects → scale)
2. Which integration target for Phase 2? (Hermes dogfood first, or go external?)
3. Kill criteria — are these the right signals?
4. Definition debt items 1-3 — can you spec these now or do they need research?
