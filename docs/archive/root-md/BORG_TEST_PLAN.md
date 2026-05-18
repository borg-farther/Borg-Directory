# BORG COMPREHENSIVE TEST PLAN
## Multi-Agent Validation & Go/No-Go Readiness
## Date: 2026-03-31 | Version: 1.0

---

# EXECUTIVE SUMMARY

This plan validates agent-borg v2.5.2 across 5 parallel agent domains with 67 test cases.
Every critical user flow is tested by at least 2 independent methods.
A go/no-go scorecard gates release. One end-to-end value demonstration proves
the product delivers measurable benefit to real users.

**Existing state:** 2,432 unit tests pass. This plan tests what unit tests CANNOT:
real installations, real CLI flows, real MCP interactions, real user journeys,
and real value delivery.

---

# 1. ARCHITECTURE — AGENT ASSIGNMENTS

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│         Aggregates results → Go/No-Go Scorecard         │
└────┬──────────┬──────────┬──────────┬──────────┬────────┘
     │          │          │          │          │
   ┌─▼──┐   ┌──▼──┐   ┌──▼──┐   ┌──▼──┐   ┌──▼──┐
   │ A1  │   │ A2  │   │ A3  │   │ A4  │   │ A5  │
   │FUNC │   │INTG │   │EDGE │   │PERF │   │ UX  │
   │     │   │     │   │     │   │     │   │VALUE│
   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘
```

| Agent | Domain | Scope | Inputs | Outputs |
|-------|--------|-------|--------|---------|
| **A1 — Functional** | Core features work correctly | CLI commands, MCP tools, pack lifecycle, DeFi commands | Fresh venv, seed packs, mock APIs | Per-test PASS/FAIL + output logs |
| **A2 — Integration** | Components work together | MCP server ↔ CLI, pack search → apply → feedback loop, DeFi V2 recommender pipeline | Running MCP server, SQLite DB, API stubs | Cross-component trace logs, data flow verification |
| **A3 — Edge Cases** | Boundaries, errors, adversarial | Malformed input, missing deps, corrupt DB, huge packs, concurrent access, network failures | Deliberately broken inputs, resource constraints | Error messages captured, crash/no-crash status |
| **A4 — Performance** | Speed, resource usage, scale | Latency benchmarks, memory profiling, large pack corpus, concurrent MCP calls | Timer instrumentation, 1000-pack corpus | Latency p50/p95/p99, memory peak, throughput |
| **A5 — UX & Value** | Real user journey, measurable value | First-user install-to-value, before/after comparison, documentation accuracy | Clean machine (Docker), zero prior knowledge | Time-to-first-value, token savings measured, user journey friction log |

---

# 2. TEST COVERAGE TABLE

## Legend
- **Priority:** P0 = must pass for release, P1 = should pass, P2 = nice to have
- **Method 1 / Method 2:** Two independent validation approaches per test
- **Agent:** Which agent owns execution

---

## DOMAIN A1: FUNCTIONAL (Core Features)

| Test ID | Test Name | Priority | Method 1 | Method 2 | Steps | Expected Result | Pass/Fail Criteria | Agent |
|---------|-----------|----------|----------|----------|-------|-----------------|-------------------|-------|
| F-001 | Fresh pip install | P0 | `pip install agent-borg` in clean venv | `pip install agent-borg[all]` in separate clean venv | 1. Create venv 2. pip install 3. `borg version` 4. `borg --help` | Installs without error, version shows 2.5.2, help lists all commands | PASS: exit code 0 + version string matches. FAIL: any error | A1 |
| F-002 | borg search (keyword) | P0 | CLI: `borg search "debugging"` | MCP: call borg_search via JSON-RPC | 1. Run search 2. Check output format 3. Verify results contain pack names | Returns list of matching packs with names, descriptions, scores | PASS: ≥1 result returned with valid pack schema. FAIL: 0 results or malformed output | A1 |
| F-003 | borg search (semantic) | P1 | CLI: `borg search "fix broken tests" --semantic` | Python API: SemanticSearchEngine.search() | 1. Install embeddings extra 2. Run semantic search 3. Compare to keyword results | Returns semantically relevant results, may differ from keyword | PASS: results returned with similarity scores >0. FAIL: crash or no results | A1 |
| F-004 | borg pull | P0 | CLI: `borg pull borg://hermes/systematic-debugging` | MCP: call borg_pull with same URI | 1. Pull pack 2. Verify local storage 3. Check pack schema validity | Pack downloaded, validated, stored in local DB | PASS: pack exists in local store + schema validates. FAIL: download error or invalid schema | A1 |
| F-005 | borg try (preview) | P0 | CLI: `borg try borg://hermes/systematic-debugging` | MCP: call borg_try | 1. Try pack 2. Verify output shows phases 3. Confirm NOT stored locally | Pack content displayed with phases, not persisted | PASS: phases displayed + pack NOT in local store. FAIL: stored locally or no output | A1 |
| F-006 | borg init (scaffold) | P1 | CLI: `borg init my-test-pack` | MCP: call borg_init | 1. Init new pack 2. Check file created 3. Validate YAML schema | Pack YAML created with required fields | PASS: valid YAML with name, phases, anti-patterns sections. FAIL: invalid schema | A1 |
| F-007 | borg apply (start) | P0 | CLI: `borg apply --action start --pack systematic-debugging --task "test task"` | MCP: call borg_apply action=start | 1. Start session 2. Check session created 3. Verify first phase returned | Active session with session_id, first phase instructions | PASS: session_id returned + phase 1 content. FAIL: no session or empty phase | A1 |
| F-008 | borg apply (checkpoint) | P0 | CLI: borg apply --action checkpoint | MCP: call borg_apply action=checkpoint | 1. Start session (F-007) 2. Complete phase 1 3. Checkpoint 4. Get phase 2 | Advances to next phase, logs checkpoint | PASS: phase increments + checkpoint logged. FAIL: stuck on same phase | A1 |
| F-009 | borg apply (complete) | P0 | CLI: borg apply --action complete | MCP: call borg_apply action=complete | 1. Complete all phases 2. Mark complete 3. Check session status | Session marked complete, outcome recorded | PASS: session status = completed. FAIL: session still active | A1 |
| F-010 | borg feedback | P0 | CLI: `borg feedback <session_id>` | MCP: call borg_feedback | 1. Complete a session 2. Generate feedback 3. Check report content | Feedback report generated with metrics | PASS: report contains success/fail assessment + metrics. FAIL: empty or error | A1 |
| F-011 | borg publish | P1 | CLI: `borg publish <pack>` | MCP: call borg_publish | 1. Create pack 2. Publish to outbox 3. Check outbox contents | Pack saved to outbox, rate limit checked | PASS: pack in outbox + no rate limit violation. FAIL: error or rate limited incorrectly | A1 |
| F-012 | borg suggest | P0 | MCP: call borg_suggest with frustration context | Python: check_for_suggestion() direct call | 1. Simulate stuck agent context 2. Call suggest 3. Check recommendation | Returns relevant pack suggestion based on context | PASS: suggestion includes pack name + relevance reason. FAIL: no suggestion or irrelevant | A1 |
| F-013 | borg observe | P0 | MCP: call borg_observe at task start | Python: direct function call | 1. Provide task description 2. Call observe 3. Check guidance output | Returns structural guidance (file signals, anti-patterns) | PASS: guidance returned with actionable content. FAIL: empty or generic | A1 |
| F-014 | borg convert (SKILL.md) | P1 | CLI: `borg convert skill.md` | MCP: call borg_convert | 1. Provide SKILL.md file 2. Convert 3. Validate output pack | Converted to valid borg pack YAML | PASS: valid pack schema output. FAIL: invalid YAML or missing phases | A1 |
| F-015 | borg convert (.cursorrules) | P1 | CLI with .cursorrules input | MCP with same input | 1. Provide .cursorrules 2. Convert 3. Validate | Converted to borg pack | PASS: valid schema. FAIL: error or invalid output | A1 |
| F-016 | borg-defi yields | P0 | CLI: `borg-defi yields` | Python: yield_scanner direct call | 1. Run yields command 2. Check output format 3. Verify data source | Yield data from DeFiLlama displayed | PASS: ≥1 yield result with APY + pool name. FAIL: no data or crash | A1 |
| F-017 | borg-defi tokens | P1 | CLI: `borg-defi tokens` | Python API direct | 1. Run tokens command 2. Check for new token data | New token launches displayed | PASS: token data returned. FAIL: empty or error | A1 |
| F-018 | borg-defi tvl | P1 | CLI: `borg-defi tvl` | Python API direct | 1. Run TVL command 2. Verify protocol data | TVL rankings displayed | PASS: protocol names + TVL values. FAIL: error | A1 |
| F-019 | borg-defi stablecoins | P1 | CLI: `borg-defi stablecoins` | Python API | 1. Run stablecoins 2. Check depeg detection | Stablecoin data with peg status | PASS: stablecoin list with price data. FAIL: error | A1 |
| F-020 | borg-defi scan-all | P1 | CLI: `borg-defi scan-all` | Sequential: yields + tokens + tvl + stablecoins | 1. Run scan-all 2. Verify all sections present | All 4 data sections in output | PASS: all 4 sections present with data. FAIL: any section missing | A1 |

---

## DOMAIN A2: INTEGRATION (Cross-Component)

| Test ID | Test Name | Priority | Method 1 | Method 2 | Steps | Expected Result | Pass/Fail Criteria | Agent |
|---------|-----------|----------|----------|----------|-------|-----------------|-------------------|-------|
| I-001 | MCP server starts and lists tools | P0 | Start borg-mcp, send tools/list JSON-RPC | Start via subprocess, parse stdout | 1. `borg-mcp` starts 2. Send initialize 3. Send tools/list 4. Count tools | Server responds, lists 14+ tools | PASS: 14 tools listed with valid schemas. FAIL: server crash or <14 tools | A2 |
| I-002 | MCP search → pull → apply → feedback pipeline | P0 | Full MCP JSON-RPC sequence | CLI equivalent sequence | 1. Search "debugging" 2. Pull top result 3. Apply start 4. Checkpoint through 5. Complete 6. Feedback | Full lifecycle completes without error | PASS: each step returns valid response, feedback generated. FAIL: any step errors | A2 |
| I-003 | V2 Recommender pipeline | P0 | Python: StrategyQuery → recommend → record outcome | CLI: borg-defi integrated flow | 1. Create recommender 2. Query USDC/base 3. Get recommendations 4. Record outcome 5. Query again 6. Verify updated scores | Recommendations change after outcome recorded | PASS: second query reflects recorded outcome (score change >0). FAIL: scores unchanged | A2 |
| I-004 | Circuit breaker triggers on losses | P0 | Record 2 consecutive losses, check pack disabled | Record 1 win + 2 losses, verify threshold | 1. Record loss 1 for pack X 2. Record loss 2 3. Query pack X status 4. Verify disabled | Pack disabled after 2 consecutive losses | PASS: pack.is_disabled = True after loss 2. FAIL: pack still active | A2 |
| I-005 | Warning propagation across agents | P0 | Agent A records rug, agent B queries and sees warning | Direct warning store + query | 1. Agent A: record rug warning for token X 2. Agent B: recommend for token X 3. Check warning flag | Warning appears in agent B's recommendation | PASS: recommendation contains warning flag. FAIL: no warning shown | A2 |
| I-006 | Pack search → conditions evaluation | P1 | Apply pack with skip_if conditions | Apply pack with inject_if conditions | 1. Start pack with conditions 2. Provide context matching skip_if 3. Verify phase skipped | Conditional logic correctly skips/injects phases | PASS: phase skipped when condition matches. FAIL: phase executed anyway | A2 |
| I-007 | Session persistence across restarts | P1 | Start session, restart process, resume | Start session, check SQLite directly, resume | 1. Start apply session 2. Kill process 3. Restart 4. Resume session | Session state recovered from DB | PASS: resume returns correct phase. FAIL: session lost | A2 |
| I-008 | Failure memory write → recall | P1 | borg_feedback writes failure → borg_recall retrieves it | Direct FailureMemory API | 1. Complete session with failure 2. Generate feedback 3. Recall failures for same error type | Failure pattern retrievable | PASS: recall returns the recorded failure. FAIL: empty results | A2 |
| I-009 | Pack signing and verification | P0 | Sign pack → verify succeeds | Sign pack → tamper → verify fails | 1. Generate key 2. Sign pack 3. Verify (should pass) 4. Modify pack 5. Verify (should fail) | Signing works, tampered pack rejected | PASS: valid sig verifies, tampered sig rejects. FAIL: either case wrong | A2 |
| I-010 | Reputation tracking on contributions | P1 | Publish pack → check reputation increased | Give feedback → check reputation increased | 1. Check initial reputation 2. Publish pack 3. Check reputation again | Reputation score increases | PASS: score after > score before. FAIL: no change | A2 |
| I-011 | DeFi API client fallback chain | P1 | Disable primary API → verify fallback | Rate limit primary → verify retry | 1. Mock primary API failure 2. Call yield scanner 3. Check secondary source used | Graceful fallback to alternative data source | PASS: data returned from fallback. FAIL: crash or empty | A2 |
| I-012 | Dojo pipeline end-to-end | P1 | DojoPipeline.analyze_recent_sessions() | CLI: run cron_runner | 1. Create mock sessions with failures 2. Run pipeline 3. Check report | Analysis report generated with failure classification | PASS: report contains classified failures + suggestions. FAIL: empty report | A2 |

---

## DOMAIN A3: EDGE CASES & ERROR HANDLING

| Test ID | Test Name | Priority | Method 1 | Method 2 | Steps | Expected Result | Pass/Fail Criteria | Agent |
|---------|-----------|----------|----------|----------|-------|-----------------|-------------------|-------|
| E-001 | Search with empty query | P0 | CLI: `borg search ""` | MCP: borg_search query="" | 1. Search empty string 2. Check response | Graceful error message, no crash | PASS: helpful error message returned. FAIL: crash/traceback | A3 |
| E-002 | Pull nonexistent pack | P0 | CLI: `borg pull borg://fake/doesntexist` | MCP equivalent | 1. Pull fake URI 2. Check error | Clear error: pack not found | PASS: "not found" error message. FAIL: crash or misleading message | A3 |
| E-003 | Apply without active session | P0 | CLI: `borg apply --action checkpoint` (no start) | MCP equivalent | 1. Checkpoint with no active session | Error: no active session | PASS: clear error. FAIL: crash or silent failure | A3 |
| E-004 | Malformed pack YAML | P0 | Feed invalid YAML to parse_workflow_pack | Feed YAML missing required fields | 1. Parse garbage YAML 2. Parse valid YAML missing 'phases' | Validation error with specific field info | PASS: SchemaValidationError with field name. FAIL: crash or accepts bad input | A3 |
| E-005 | Corrupt SQLite database | P1 | Truncate DB file, then search | Write random bytes to DB, then search | 1. Corrupt local store DB 2. Attempt search | Graceful recovery or clear error | PASS: error message + suggestion to reinit. FAIL: unhandled exception | A3 |
| E-006 | Network timeout on pack pull | P1 | Mock 30s timeout on GitHub fetch | Mock DNS failure | 1. Set timeout to 1ms 2. Pull pack | Timeout error with retry suggestion | PASS: timeout error message. FAIL: hangs indefinitely or crash | A3 |
| E-007 | Pack with 1000 phases | P1 | Generate 1000-phase pack, apply | Generate deeply nested conditions | 1. Create oversized pack 2. Validate 3. Attempt apply | Size limit enforced or handles gracefully | PASS: size limit error OR successful processing. FAIL: OOM or crash | A3 |
| E-008 | Concurrent MCP calls | P1 | 10 simultaneous borg_search calls | 5 search + 5 apply calls simultaneously | 1. Fire concurrent requests 2. Check all responses | All responses valid, no data corruption | PASS: all 10 responses valid. FAIL: any corrupt response or deadlock | A3 |
| E-009 | Unicode/emoji in pack content | P1 | Create pack with emoji in phases | Search for unicode pack name | 1. Init pack with 🧠 in name 2. Pull pack with CJK characters | Handles unicode throughout | PASS: pack stored and retrievable. FAIL: encoding error | A3 |
| E-010 | Publish rate limiting | P1 | Publish 10 packs in 1 second | Publish same pack twice rapidly | 1. Rapid-fire publishes 2. Check rate limit kicks in | Rate limit enforced after threshold | PASS: rate limit error after N publishes. FAIL: no limit or crash | A3 |
| E-011 | Missing API keys for DeFi | P0 | Run `borg-defi yields` with no API keys | Run with invalid API key | 1. Unset all API keys 2. Run yields | Works with free APIs, clear error for paid-only features | PASS: free data returns, paid features show "key required". FAIL: crash | A3 |
| E-012 | Signing with missing crypto deps | P1 | Call sign_pack without nacl installed | Call verify without key | 1. Remove nacl 2. Attempt sign | Clear error about missing optional dependency | PASS: ImportError caught with install instruction. FAIL: raw traceback | A3 |
| E-013 | SQL injection in search query | P0 | Search: `'; DROP TABLE packs; --` | Search: `" OR 1=1 --` | 1. Search with injection payload 2. Check DB integrity | Query sanitized, DB intact | PASS: returns 0 results, DB still works. FAIL: DB corrupted or error | A3 |
| E-014 | Privacy scanner catches secrets | P0 | Pack with AWS key in content | Pack with private key in phases | 1. Create pack with secret 2. Run safety scan 3. Attempt publish | Secret detected, publish blocked | PASS: safety scan flags secret. FAIL: secret passes through | A3 |
| E-015 | GoPlus security scan blocking bad token | P1 | Mock GoPlus returning honeypot=true | Mock GoPlus returning is_rug=true | 1. Query token safety 2. Check warning flag | Warning issued, swap blocked | PASS: warning generated + tx not built. FAIL: swap proceeds | A3 |

---

## DOMAIN A4: PERFORMANCE

| Test ID | Test Name | Priority | Method 1 | Method 2 | Steps | Expected Result | Pass/Fail Criteria | Agent |
|---------|-----------|----------|----------|----------|-------|-----------------|-------------------|-------|
| P-001 | borg search latency (local) | P0 | Time 100 searches, compute p95 | Benchmark with pytest-benchmark | 1. Seed 50 packs 2. Run 100 keyword searches 3. Measure latency | p95 < 200ms for local search | PASS: p95 < 200ms. FAIL: p95 ≥ 200ms | A4 |
| P-002 | borg search latency (semantic) | P1 | Time 50 semantic searches, compute p95 | Profile with cProfile | 1. Load embeddings 2. Run 50 semantic searches 3. Measure | p95 < 500ms for semantic search | PASS: p95 < 500ms. FAIL: p95 ≥ 500ms | A4 |
| P-003 | MCP server response time | P0 | Time 100 tool calls via JSON-RPC | Profile server handler | 1. Start MCP server 2. Send 100 borg_search requests 3. Measure round-trip | p95 < 300ms per tool call | PASS: p95 < 300ms. FAIL: p95 ≥ 300ms | A4 |
| P-004 | Pack apply memory usage | P1 | tracemalloc during 10-phase apply | /proc/self/status RSS tracking | 1. Start tracemalloc 2. Apply 10-phase pack 3. Measure peak | Peak < 100MB for standard pack | PASS: peak < 100MB. FAIL: peak ≥ 100MB | A4 |
| P-005 | Large corpus search (1000 packs) | P1 | Generate 1000 packs, search, measure | FTS5 EXPLAIN QUERY PLAN analysis | 1. Seed 1000 packs 2. Search various queries 3. Measure latency | Search still < 500ms with 1000 packs | PASS: p95 < 500ms. FAIL: p95 ≥ 500ms | A4 |
| P-006 | V2 Recommender throughput | P1 | 1000 recommend() calls, measure ops/sec | Profile Thompson Sampling computation | 1. Seed 100 strategies 2. Run 1000 recommendations 3. Measure throughput | ≥ 100 recommendations/sec | PASS: ≥ 100 ops/sec. FAIL: < 100 ops/sec | A4 |
| P-007 | pip install time | P0 | Time `pip install agent-borg` (cold) | Time `pip install agent-borg[all]` (cold) | 1. Clean venv 2. Time install 3. Record | Install < 60 seconds | PASS: install < 60s. FAIL: ≥ 60s | A4 |
| P-008 | CLI startup time | P0 | Time `borg version` (cold) | Time `borg --help` (cold) | 1. Clear module cache 2. Time CLI startup 3. Record | CLI responds in < 2 seconds | PASS: < 2s. FAIL: ≥ 2s | A4 |
| P-009 | SQLite WAL mode under concurrent writes | P1 | 10 threads writing outcomes simultaneously | 5 writers + 5 readers simultaneously | 1. Open DB in WAL mode 2. Concurrent operations 3. Check integrity | No corruption, no lock timeouts | PASS: all operations succeed, PRAGMA integrity_check passes. FAIL: any failure | A4 |
| P-010 | DeFi API client response caching | P1 | Call yields twice, measure second call latency | Check cache hit rate after 10 calls | 1. First call (cold) 2. Second call (cached) 3. Compare latency | Cached call ≥ 10x faster | PASS: cached < cold/10. FAIL: no speedup | A4 |

---

## DOMAIN A5: UX & VALUE DEMONSTRATION

| Test ID | Test Name | Priority | Method 1 | Method 2 | Steps | Expected Result | Pass/Fail Criteria | Agent |
|---------|-----------|----------|----------|----------|-------|-----------------|-------------------|-------|
| V-001 | First user: install to first search (< 5 min) | P0 | Fresh Docker container, clock the journey | Fresh venv, follow README only | 1. Start clean 2. pip install 3. borg search "debugging" 4. Read result 5. Record time | Value in under 5 minutes | PASS: meaningful search result in < 5 min from zero. FAIL: > 5 min or confusing | A5 |
| V-002 | First user: search → try → apply a pack | P0 | Follow docs only, no prior knowledge | Follow CLI --help only, no docs | 1. Search 2. Try top result 3. Apply to a real task 4. Record friction points | User can complete full cycle | PASS: workflow completes with ≤ 2 friction points. FAIL: blocked or > 5 friction points | A5 |
| V-003 | Documentation accuracy | P1 | Execute every command in README | Execute every command in CLI --help | 1. Run each documented command exactly 2. Compare output to docs | Docs match reality | PASS: 100% of documented commands work. FAIL: any command fails or differs | A5 |
| V-004 | Error message clarity | P1 | Trigger 10 known errors, rate messages | Show error messages to non-expert, ask if actionable | 1. Trigger errors (missing pack, bad YAML, etc) 2. Rate each message: clear/unclear/misleading | All error messages are actionable | PASS: ≥ 8/10 rated "clear". FAIL: < 8/10 | A5 |
| V-005 | MCP integration with Claude Code | P0 | Add borg to claude code MCP config, use it | Add borg to cursor MCP config, use it | 1. Configure MCP 2. Start agent 3. Agent uses borg_search 4. Agent applies pack | Agent successfully uses borg tools | PASS: agent calls borg tools and gets useful response. FAIL: tools fail or agent confused | A5 |
| V-006 | **VALUE DEMO: Before/After debugging task** | P0 | Agent debugs WITHOUT borg (measure tokens + time) | SAME agent debugs WITH borg (measure tokens + time) | See detailed spec below | Measurable improvement with borg | PASS: borg reduces tokens by ≥ 30% OR time by ≥ 30%. FAIL: no measurable improvement | A5 |
| V-007 | **VALUE DEMO: DeFi safety — rug detection** | P0 | Agent enters pool WITHOUT borg warnings | Agent enters SAME pool WITH borg collective warning | See detailed spec below | Borg prevents loss | PASS: borg-equipped agent avoids rugged pool. FAIL: agent enters anyway | A5 |
| V-008 | DeFi CLI zero-config value | P1 | Run `borg-defi yields` with no setup | Run `borg-defi scan-all` with no setup | 1. Fresh install 2. No API keys 3. Run command 4. Get useful data | Useful DeFi data with zero configuration | PASS: actionable yield/TVL data displayed. FAIL: "no API key" error or empty | A5 |
| V-009 | Pack quality — does following a pack improve outcomes? | P0 | Complete coding task following borg pack phases | Complete same task without pack | 1. Define test task 2. Run with pack 3. Run without 4. Compare quality scores | Pack-guided work scores higher | PASS: pack-guided score ≥ 1.5x baseline. FAIL: no improvement | A5 |
| V-010 | Collective learning loop proof | P0 | Agent A fails → Agent B avoids same failure | 3 agents sequential, measure failure rate decrease | 1. Agent A hits problem, records failure 2. Agent B starts same task, gets borg_suggest 3. Agent B avoids failure | Failure propagation works | PASS: Agent B avoids Agent A's mistake. FAIL: Agent B repeats it | A5 |

---

# 3. VALUE DEMONSTRATION — DETAILED SPECS

## V-006: Before/After Debugging Task

### Setup
- Repository: a prepared Python project with 3 intentional bugs
- Bug types: TypeError (NoneType), import cycle, race condition
- Each bug has a known fix and a known wrong-approach (that wastes tokens)

### Before (no borg)
1. Agent gets task: "Fix the failing tests in this repo"
2. Agent uses standard tools only (terminal, file read/write)
3. Measure: total tokens consumed, time to fix all 3, number of wrong approaches tried

### After (with borg)
1. Same agent, same repo (reset), same task
2. Agent has borg MCP tools available
3. Agent calls borg_search on first error → gets "start here" signal
4. Agent calls borg_suggest when stuck → gets anti-pattern warning
5. Measure: total tokens consumed, time to fix all 3, number of wrong approaches tried

### Success Metric
| Metric | Without Borg | With Borg | Improvement Required |
|--------|-------------|-----------|---------------------|
| Tokens consumed | Baseline | Target | ≥ 30% reduction |
| Time to fix all 3 | Baseline | Target | ≥ 20% reduction |
| Wrong approaches tried | Baseline | Target | ≥ 50% reduction |

---

## V-007: DeFi Safety — Rug Detection

### Setup
- Mock DeFi environment with 5 pools
- Pool 3 is a honeypot (GoPlus returns honeypot=true)
- Pool 5 has 2 prior agent losses recorded in borg (circuit breaker should trip)

### Without Borg
1. Agent evaluates all 5 pools
2. Agent has no safety data
3. Agent selects pool 3 (highest APY) → gets rugged

### With Borg
1. Agent evaluates all 5 pools
2. Agent calls borg V2 recommender
3. Pool 3 flagged by GoPlus integration
4. Pool 5 flagged by circuit breaker (2 losses)
5. Agent selects pool 1 or 2 (safe, lower APY, no loss)

### Success Metric
| Metric | Without Borg | With Borg |
|--------|-------------|-----------|
| Entered honeypot? | YES | NO |
| Entered circuit-broken pool? | YES | NO |
| Capital preserved? | NO | YES |

---

# 4. GO/NO-GO READINESS SCORECARD

## Scoring

| Dimension | Weight | Tests | Required | Go Threshold |
|-----------|--------|-------|----------|-------------|
| **Functional (P0)** | 30% | F-001 to F-013, F-016 | 100% pass | ALL P0 pass |
| **Integration (P0)** | 25% | I-001 to I-005, I-009 | 100% pass | ALL P0 pass |
| **Edge Cases (P0)** | 15% | E-001 to E-004, E-011, E-013, E-014 | 100% pass | ALL P0 pass |
| **Performance (P0)** | 15% | P-001, P-003, P-007, P-008 | 100% pass | ALL P0 pass |
| **UX & Value (P0)** | 15% | V-001, V-002, V-005 to V-007, V-009, V-010 | 100% pass | ALL P0 pass |

## Decision Rules

```
IF all P0 tests PASS:
  → GO (ship it)

IF any P0 test FAILS:
  → NO-GO (fix and re-test)

P1 tests:
  → ≥ 90% pass required for GO
  → < 90% = conditional GO with documented known issues

P2 tests:
  → Informational only, do not block release
```

## Rollup Formula

```
Score = (P0_pass_rate × 0.70) + (P1_pass_rate × 0.25) + (P2_pass_rate × 0.05)

GO:     Score ≥ 0.95 AND P0_pass_rate = 1.00
CONDITIONAL GO: Score ≥ 0.85 AND P0_pass_rate = 1.00
NO-GO:  Score < 0.85 OR P0_pass_rate < 1.00
```

---

# 5. EXECUTION PLAN

## Phase 1: Setup (Day 1)
- [ ] Prepare clean Docker images for A5 (UX tests)
- [ ] Prepare mock DeFi environment for V-007
- [ ] Prepare bugged Python repo for V-006
- [ ] Seed 50 test packs for performance baselines
- [ ] Generate 1000-pack corpus for P-005

## Phase 2: Parallel Execution (Day 1-2)
- [ ] A1 (Functional): Run F-001 through F-020
- [ ] A2 (Integration): Run I-001 through I-012
- [ ] A3 (Edge Cases): Run E-001 through E-015
- [ ] A4 (Performance): Run P-001 through P-010
- [ ] A5 (UX & Value): Run V-001 through V-010

## Phase 3: Results & Decision (Day 2)
- [ ] Each agent submits results table
- [ ] Orchestrator computes scorecard
- [ ] GO/NO-GO decision
- [ ] Document all failures with root cause + fix plan

## Agent Execution Commands

```bash
# A1 — Functional
delegate_task(goal="Execute Functional test cases F-001 through F-020 from BORG_TEST_PLAN.md", toolsets=["terminal", "file"])

# A2 — Integration
delegate_task(goal="Execute Integration test cases I-001 through I-012 from BORG_TEST_PLAN.md", toolsets=["terminal", "file"])

# A3 — Edge Cases
delegate_task(goal="Execute Edge Case test cases E-001 through E-015 from BORG_TEST_PLAN.md", toolsets=["terminal", "file"])

# A4 — Performance
delegate_task(goal="Execute Performance test cases P-001 through P-010 from BORG_TEST_PLAN.md", toolsets=["terminal", "file"])

# A5 — UX & Value
delegate_task(goal="Execute UX & Value test cases V-001 through V-010 from BORG_TEST_PLAN.md", toolsets=["terminal", "file", "web"])
```

---

# 6. CRITICAL GAPS IDENTIFIED (from codebase inspection)

These must be addressed BEFORE or DURING test execution:

| Gap | Risk | Action |
|-----|------|--------|
| `core/crypto.py` has ZERO tests | CRITICAL — signing/verification is security core | Write tests before I-009 |
| `defi/v2/daily_brief.py` has 0 tests | HIGH — daily brief is user-facing feature | Write tests or exclude from release |
| `defi/v2/warnings.py` has 0 tests | HIGH — warning propagation is the core value prop | Write tests before I-005 and V-007 |
| `defi/mcp_tools.py` only 14 tests | MEDIUM — DeFi MCP tools undertested | Expand coverage |
| MCP server tested at integration level only | MEDIUM — individual tool functions not unit-tested | Add isolated unit tests |
| Benchmark +50% is simulated, not real | HIGH — marketing claim unverified | V-006 and V-009 must produce REAL numbers |

---

# 7. RESULTS TEMPLATE

Each agent fills this in:

```
## Agent [X] — [Domain] Results
Date: ____
Tests Executed: __/__
P0 Pass: __/__
P1 Pass: __/__
P2 Pass: __/__

| Test ID | Result | Notes |
|---------|--------|-------|
| X-001   | PASS/FAIL | details |
| X-002   | PASS/FAIL | details |
...

### Failures
| Test ID | Root Cause | Fix Required | Severity |
|---------|-----------|-------------|----------|
| X-00N   | description | fix plan | P0/P1/P2 |

### Observations
- (unexpected findings, new risks, recommendations)
```

---

*67 test cases. 5 agents. 2 independent methods per test. Binary PASS/FAIL.*
*No ambiguity. No marketing claims without proof.*
*Resistance is futile.*
