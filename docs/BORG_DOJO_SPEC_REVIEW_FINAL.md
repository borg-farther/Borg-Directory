# Borg + Dojo Integration Specification — Final Adversarial Review

**Review Date:** 2026-03-29
**Reviewer:** Adversarial Sub-agent (multi-angle deep analysis)
**Spec Reference:** docs/BORG_DOJO_SPEC.md (v1.0 DRAFT, 1038 lines)
**Prior Review:** docs/BORG_DOJO_SPEC_REVIEW.md (P0/P1 findings)

---

## Executive Summary

The spec has improved significantly from the prior review — it now addresses PII redaction, pagination, rollback, interface versioning, and false positive mitigation. However, **the spec is a design document, not an implementation**. Every section contains gaps between the design intent and what actual code would do. Many P0s from the prior review are addressed in prose but not in the pseudo-code. The spec must be treated as a starting point, not a finished design.

The spec also introduces new issues that weren't in the prior review: role_filter inconsistency between prose and SQL, rollback mechanism mismatch between spec and code, HMAC salt lifecycle undefined, and test architecture that's overly optimistic about fixture management.

---

## 1. ARCHITECTURE REVIEW

### 1.1 Module Boundaries

**CONCERN A: The `SessionAnalysis` dataclass is the only interface contract, but it's a garbage-can design.**
- `SessionAnalysis` bundles 7 conceptually distinct outputs: `tool_metrics`, `failure_reports`, `skill_gaps`, `retry_patterns`, `user_corrections`, `weakest_tools`, plus summary stats. These have wildly different shapes, update frequencies, and consumers.
- Adding a new field is safe (versioned). But what about adding a new **variant** of an existing field? If `failure_reports` gains a new `sub_category` sub-field, is that a schema bump? The spec doesn't define granularity.
- **Severity: P1**

**CONCERN B: `borg/dojo/__init__.py` is the load-bearing facade.**
- All 6+ consuming borg modules (`aggregator.py`, `nudge.py`, `search.py`, `apply.py`, `reputation.py`, `analytics.py`) import from `borg.dojo`. If `__init__.py` changes, all 6+ modules can break silently.
- The spec doesn't specify what `__init__.py` exports. Is it a lazy facade? A direct passthrough? This is the most critical file in the integration and it's unspecified.
- **Severity: P1**

**CONCERN C: Feature flag creates untested code paths.**
- `BORG_DOJO_ENABLED` env var gates all integration. In CI (disabled by default), the code paths are never exercised. A developer who breaks the lazy import in `__init__.py` won't know until production.
- The spec says "existing tests MUST continue passing — CI gate" — but it doesn't require dojo-specific tests to pass in CI. The 75+ tests exist but aren't gated.
- **Severity: P2**

### 1.2 Dependency Direction

**CONCERN D: dojo is a pure library with no awareness of borg.**
- dojo generates `SessionAnalysis` but doesn't know which borg modules will consume it. If borg/packs fills a skill gap, dojo's next run still sees the gap until its next analysis cycle. This is a classic stale-data feedback loop.
- The spec acknowledges this in passing (Section 4.9) but provides no mechanism for borg to notify dojo that a gap was filled.
- **Severity: P1**

### 1.3 Recommendations

1. Define a **stable ABI contract** for `SessionAnalysis`: exactly which fields, their types, and what constitutes a breaking (version-bumped) vs non-breaking change.
2. Specify `__init__.py` exports explicitly — which classes/functions are public API vs internal.
3. Add a CI job that runs with `BORG_DOJO_ENABLED=true` to exercise integration code paths in every PR.
4. Consider a pub/sub or callback mechanism so borg can notify dojo when a gap is filled externally.

---

## 2. SECURITY REVIEW

### 2.1 PII Pipeline — Does It Actually Work?

**CONCERN A (P0): `privacy.redact_pii()` is referenced but its implementation is unspecified.**
- The spec says "graceful fallback to basic regex if unavailable" — but the fallback behavior is not defined. What patterns does the fallback use? If it misses a pattern class (e.g., Telegram bot tokens `\d+:[\w-]+`), PII leaks silently.
- The spec adds `CREDENTIAL_PATTERNS` (OpenAI, ElevenLabs, GitHub, Bearer, passwords) but misses:
  - AWS keys (`AKIA[0-9A-Z]{16}`)
  - Telegram bot tokens (`\d+:[\w-]+`)
  - Discord tokens (`[A-Za-z0-9]{24}\.[A-Za-z0-9]{6}\.[A-Za-z0-9_-]{27}`)
  - Generic API keys (`[a-zA-Z0-9_-]{32,64}`)
- **Severity: P0**

**CONCERN B (P0): HMAC salt lifecycle is undefined.**
- `user_id` → HMAC-SHA256 with "per-install salt". But:
  - Where is the salt stored? (`~/.hermes/config`? Environment variable?)
  - How is it generated? (What if two installs use the same default?)
  - How is it rotated? (If compromised, can old session_ids be re-linked?)
- If the salt is in an env var `HERMES_DOJO_SALT`, it's in the process environment and visible in `/proc/<pid>/environ`. If it's in a config file, it's on disk.
- **Severity: P0**

**CONCERN C (P1): The SQL JOIN for `get_tool_calls()` ignores `role` entirely.**
- The spec's prose says patterns are applied with `role_filter="tool"`. But the SQL:
  ```sql
  FROM messages m1
  JOIN messages m2 ON m2.session_id = m1.session_id
                   AND m2.tool_call_id IS NOT NULL
  WHERE m1.session_id = ? AND m1.role = 'assistant'
        AND m1.tool_calls IS NOT NULL
  ```
  Only filters `m1.role = 'assistant'` — not `m2.role = 'tool'`. The result includes `m2` rows regardless of role. The role filter is applied in Python after fetching, but if `m2.role = 'user'` or `m2.role = 'system'` contains an error-like string, it enters classification.
- **Severity: P1**

**CONCERN D (P1): `system_prompt` is "never read" — but session_id is a joinable key.**
- The spec says `system_prompt` is never read. But `sessions.id` (the session_id) is stored in `messages.session_id`. If `sessions.user_id` can be joined via `sessions.id = messages.session_id`, then a borg module that receives a `session_id` can in theory look it up in `sessions` and get `user_id`. The "never read" protection is only as strong as the database isolation.
- With `PRAGMA query_only = ON`, direct SELECT on `sessions` is still allowed. A borg module that bypasses `SessionReader` and reads directly from `state.db` would get `user_id`.
- **Severity: P1**

**CONCERN E (P2): `result_snippet` truncation doesn't account for multi-byte encodings.**
- "First 200 chars" — if content is UTF-8 with non-ASCII characters, 200 bytes != 200 characters. A PII field (e.g., a Chinese name) could be truncated mid-character, creating invalid output. Also, if `redact_pii()` replaces "john@gmail.com" with "[EMAIL]", the 200-char cap could cut `[EMAIL` mid-word.
- **Severity: P2**

### 2.2 Credential Scrubbing

**CONCERN F (P1): API key passed to subprocess — still present in fix_content.**
- The spec's Section 8.2 adds credential patterns to `CREDENTIAL_PATTERNS`, but `fix_content` (the generated patch text) is built from `FIX_STRATEGIES[error_category].skill_addition` — template strings, not raw error content. The credential scrubbing applies to `content` going into `FailureReport.error_snippet`, but `fix_content` uses the **generic** skill addition template, not the specific error text.
- However: `FixAction.reason` is described as "the patch text or new skill content" — if this embeds actual error text, credentials could enter `Skill.md` files.
- **Severity: P1**

### 2.3 Recommendations

1. Specify the **exact regex patterns** for `redact_pii()` fallback (not just "basic regex"). Add Telegram bot tokens, AWS keys, Discord tokens, generic API key formats.
2. Define HMAC salt lifecycle: generation method, storage location, rotation procedure, and what happens if the salt is compromised.
3. Fix the SQL JOIN to explicitly filter `m2.role = 'tool'`, not just `m1.role = 'assistant'`.
4. Add a SQL view or trigger that enforces `query_only` at the DB level, preventing even direct session_id lookups from returning user_id.
5. Use `len(content.encode('utf-8'))[:200]` for byte-aware truncation, and validate that `[REDACTED]` replacements don't create truncated placeholders.

---

## 3. RELIABILITY REVIEW

### 3.1 Does Rollback Actually Work?

**CONCERN A (P0): Rollback mechanism mismatch — spec says "staging + atomic rename" but code shows direct copy.**
- The spec's Reliability section (4.5) says: "Write to staging, atomic rename on success, rollback on failure." This is the correct pattern.
- But the pseudo-code shows:
  ```python
  shutil.copy2(backup_path, skill_path / "SKILL.md")  # direct write
  ```
  Not a staging file + `os.rename()`. The difference matters:
  - `shutil.copy2()` is not atomic — if it fails mid-copy, the destination file is partially written.
  - `os.rename()` is atomic on POSIX systems (the rename is synchronous and either fully succeeds or fully fails).
  - If the skill file is 100KB and the disk fills at 50KB during copy, the file is corrupted. Rollback from backup would help, but the backup itself might be incomplete.
- **Severity: P0**

**CONCERN B (P0): Pipeline applies fixes sequentially with no all-or-nothing semantics.**
- In `DojoPipeline.run()`:
  ```python
  fixes = [fixer.apply_fix(r) for r in recommendations[:3]]
  ```
  If `apply_fix(recommendations[0])` succeeds, `apply_fix(recommendations[1])` fails with disk full, fix[0] stays applied. The pipeline continues and `_feed_aggregator()` runs with partial fixes applied.
  - The spec's error handling table (Section 7) says "mark fix as failed, continue with next" — which is exactly what happens, but the prior fixes are not rolled back.
  - A partial pipeline run (2 of 3 fixes applied) produces inconsistent state that won't be self-correcting.
- **Severity: P0**

**CONCERN C (P1): Backup path collision on rapid re-runs.**
- `backup_path = self.BACKUP_DIR / f"{fix.target_skill}_{int(time.time())}.md"` — `int(time.time())` is second-resolution. If two cron runs happen within the same second (e.g., manual trigger + scheduled), both writes go to the same backup path. The second run's backup overwrites the first's backup.
- If both runs try to fix the same skill, rollback from run[2] would restore from a backup created by run[1], not the original skill content.
- **Severity: P1**

### 3.2 State.db Schema Changes

**CONCERN D (P1): `schema_version` in `MetricSnapshot` (v1) vs schema_version in `SessionAnalysis` (v1) — are they the same?**
- The spec has two versioned things: `SessionAnalysis.schema_version` (Section 5.1) and `MetricSnapshot.schema_version` (Section 4.6). Are they the same version space? If `SessionAnalysis` bumps to v2 but `MetricSnapshot` stays at v1, does that break anything?
- The spec's Open Question OQ7 asks "How to handle hermes version differences in state.db schema?" — but the answer ("Check schema_version in state.db, support v5+") refers to SQLite schema, not the `SessionAnalysis` dataclass schema.
- **Severity: P1**

**CONCERN E (P1): WAL checkpoint assumption may not hold under load.**
- The spec says "WAL mode enables concurrent reads" — this is true. But `PRAGMA quick_check` only checks the freelist integrity, not the WAL. A corrupted WAL header (e.g., from an OOM-killed writer) will pass `quick_check` but produce garbage rows on read.
- **Severity: P1**

**CONCERN F (P2): `PRAGMA query_only = ON` is not a security boundary.**
- `PRAGMA query_only = ON` tells SQLite to refuse writes, but it's advisory — a misconfigured connection string or a bug in the code could open a write-capable connection. The spec relies on this as a PII safety mechanism (Section 8.1 rule #6: "0 write operations to state.db").
- If the connection string is misconfigured to `?mode=rw`, writes are allowed and PII could be modified.
- **Severity: P2**

### 3.3 Recommendations

1. Implement staging + `os.rename()` for all skill file writes, not `shutil.copy2()`.
2. Add an explicit pipeline-level transaction log: if any fix fails, rollback all applied fixes before continuing.
3. Use microsecond timestamps (`int(time.time() * 1_000_000)`) or UUIDs for backup file names.
4. Separate `SessionAnalysis` schema version from `MetricSnapshot` schema version into distinct version constants with independent increment rules.
5. Replace `PRAGMA quick_check` with `PRAGMA integrity_check` (full check, not just freelist) before any read.
6. Add a SQLite user-version check (`PRAGMA user_version`) as a schema fingerprint, separate from the application-level `schema_version` dataclass field.

---

## 4. PERFORMANCE REVIEW

### 4.1 Regex Scaling

**CONCERN A (P1): The performance estimates are optimistic by 10-100x.**
- The spec claims:
  - "Classify 1 message (50 patterns): ~0.1ms"
  - "Full analysis (7 days, ~100 sessions): ~2-5 seconds"
- Testing the math: 100 sessions × ~31 messages/session (22,349/715 from Section 2.3) = ~3,100 messages. 3,100 × 50 patterns × 0.1ms = 15.5 seconds just for classification. That's more than the full analysis budget.
- Python's `re` module has overhead per `search()` call (pattern compilation cache hit, frame setup, match engine invocation). 0.1ms per message per pattern is optimistic; real-world measurement is likely 0.5-2ms per pattern per message.
- **Severity: P1**

**CONCERN B (P1): Pagination doesn't reduce total work, just peak memory.**
- Page size = 100 sessions. For 7 days, that's ~3-4 page reads. Each page read fetches all messages for those sessions. The work done is O(total messages × patterns) regardless of pagination. Pagination only limits how many rows are in memory at once.
- The spec conflates memory efficiency with computational efficiency. Pagination helps memory but not CPU.
- **Severity: P1**

**CONCERN C (P2): Compiled regex cache is process-global but not thread-safe during refresh.**
- The spec mentions "compiled regex cache" but doesn't specify whether the cache is per-SessionReader instance or a global module-level dict. If it's global, and the patterns are ever hot-reloaded, concurrent analysis runs (e.g., hermes-plugin + cron pipeline simultaneously) could cause cache thrashing.
- **Severity: P2**

### 4.2 Pagination Adequacy

**CONCERN D (P1): Page size of 100 sessions is arbitrary.**
- Why 100? If average session has 200 messages, a page reads 20,000 message rows. If the average session has 2,000 messages (long conversations), a page reads 200,000 rows. The spec provides no upper bound on messages per session.
- The pagination is on sessions (LIMIT/OFFSET on `sessions` table), but `get_tool_calls()` does a JOIN that could produce many rows per session. There's no pagination on the messages themselves.
- **Severity: P1**

### 4.3 Cache Invalidation

**CONCERN E (P2): 1-hour cache with no invalidation signal.**
- `analyze_recent_sessions()` result is cached for 1 hour. If `state.db` is updated (new sessions, new messages), the cache serves stale data for up to 1 hour. For hermes-plugin's nudge engine making real-time decisions, this is a significant staleness window.
- **Severity: P2**

### 4.4 Recommendations

1. Benchmark actual classification throughput on real data before committing to performance targets.
2. Combine all 50+ patterns into a single compiled automaton using the `regex` library (which supports combined patterns) or Aho-Corasick for multi-pattern matching — this would reduce 50 `re.search()` calls to 1.
3. Add a hard upper bound on messages per session page (e.g., if a session has >1,000 messages, paginate within the session).
4. Add cache invalidation: if `state.db` modification time changes, invalidate the cache regardless of TTL.
5. Add a streaming mode that yields results incrementally instead of building the full `SessionAnalysis` in memory.

---

## 5. TESTABILITY REVIEW

### 5.1 Are 75+ Tests Actually Achievable?

**CONCERN A (P1): The spec's test architecture requires maintaining a production-representative `sample_state.db`.**
- The fixture `tests/fixtures/sample_state.db` must be kept current with the evolving schema. If the schema changes (Section 5, Open Question OQ7), all fixture DBs must be regenerated. This is a maintenance burden that typically causes test rot.
- A `sample_state.db` with 715 sessions and 22,349 messages (mirroring production from Section 2.3) would be ~10-50MB of fixture data. This doesn't belong in a code repo.
- The labeled_messages.json fixture (100 manually labeled tool results for SC1 verification) is also a maintenance burden. Who updates it when the classification logic changes?
- **Severity: P1**

**CONCERN B (P1): Auto-fixer rollback tests require actual filesystem state.**
- `test_fixer_rollback`: "apply fix → verify → rollback → verify original" — this requires:
  1. A real skill directory with a real `SKILL.md` file
  2. A real backup file written to `~/.hermes/borg/dojo_backups/`
  3. The test must clean up after itself (remove backup, restore original skill)
- This is an integration test masquerading as a unit test. It can't run in parallel with other tests (filesystem state pollution). It requires teardown logic.
- **Severity: P1**

**CONCERN C (P1): The `privacy.redact_pii()` test coverage can't be verified.**
- The spec says `redact_pii()` is "graceful fallback to basic regex if unavailable." But the fallback behavior is unspecified — so tests for the fallback can't be written. How do you assert "fallback works correctly" when the fallback is undefined?
- If `borg.core.privacy` is the real implementation and the test environment has it, tests pass. If it's missing in test, the fallback silently kicks in and produces different results.
- **Severity: P1**

**CONCERN D (P2): Integration tests for `_feed_aggregator`, `_feed_nudge`, `_feed_reputation` require borg module mocking.**
- These methods are called in `DojoPipeline.run()` but their implementations are in other borg modules. Testing them requires mocking `aggregator`, `nudge`, `reputation` — which are themselves complex modules. This creates a mocking web that tests behavior but not integration.
- **Severity: P2**

**CONCERN E (P2): The E2E "pipeline with seeded data" test is fragile.**
- `test_pipeline_with_seeded_data`: seed state.db → run pipeline → verify report + snapshot. This requires either:
  - A separate test SQLite database that the test creates, populates, analyzes, then tears down
  - Pollution of the test runner's own `~/.hermes/state.db`
- Both options are fragile. The test should use an in-memory SQLite database (`:memory:`) with a known schema.
- **Severity: P2**

### 5.2 Untestable Components

**CONCERN F (P2): The correction detection recall measurement (SC2) requires manual labeling.**
- SC2: ">85% recall on correction signals" — verification requires "50 sessions with known user corrections." This must be manually labeled by a human. It's not automatable in CI.
- The spec proposes this as a one-time verification ("compare against manually labeled 100-message sample") but doesn't specify how the 100-message sample is maintained.
- **Severity: P2**

**CONCERN G (P2): The 75+ test count is not CI-gated.**
- The spec says "CI gate" but doesn't specify `pytest borg/dojo/tests/ --tb=short` must pass. The current CI (Section 2.1, 1083 passing tests) is for existing borg modules. There's no mention of adding dojo tests to CI.
- Without CI enforcement, the 75 tests are aspirational.
- **Severity: P2**

### 5.3 Recommendations

1. Use `fakeredis` or an in-memory SQLite for all integration tests. Keep `sample_state.db` small (<100 sessions) and regenerate it programmatically from a schema factory.
2. Separate rollback E2E tests into a dedicated test class with explicit setup/teardown that can run in isolation.
3. Specify the exact `redact_pii()` fallback implementation — write the fallback code, then write tests for it, rather than leaving it undefined.
4. Add dojo tests to CI with `BORG_DOJO_ENABLED=true` as a required gate.
5. For SC2 recall measurement, build a labeled correction dataset once and commit it as a fixture. Accept that it will drift and schedule periodic re-labeling.

---

## Summary: Concerns by Severity

| # | Angle | Severity | Concern |
|---|-------|----------|---------|
| 1 | Security | P0 | `privacy.redact_pii()` fallback is unspecified; credential pattern set is incomplete |
| 2 | Security | P0 | HMAC salt lifecycle undefined (generation, storage, rotation) |
| 3 | Reliability | P0 | Rollback uses `shutil.copy2()` not staging+atomic-rename |
| 4 | Reliability | P0 | Pipeline applies fixes sequentially with no all-or-nothing rollback |
| 5 | Security | P1 | SQL JOIN in `get_tool_calls()` doesn't filter `m2.role = 'tool'` |
| 6 | Security | P1 | `system_prompt` "never read" is bypassable via session_id join |
| 7 | Architecture | P1 | `SessionAnalysis` dataclass is a garbage can of 7 unrelated outputs |
| 8 | Architecture | P1 | `borg/dojo/__init__.py` (the critical facade) is unspecified |
| 9 | Architecture | P1 | dojo has no mechanism to learn when borg fills a detected gap |
| 10 | Reliability | P1 | Backup path collision on sub-second re-runs |
| 11 | Reliability | P1 | Two independent schema_version fields (SessionAnalysis vs MetricSnapshot) |
| 12 | Reliability | P1 | `PRAGMA quick_check` doesn't catch WAL header corruption |
| 13 | Performance | P1 | Performance estimates (0.1ms/message, 2-5s full run) are 10-100x optimistic |
| 14 | Performance | P1 | Pagination reduces memory but not computational work |
| 15 | Performance | P1 | Page size (100 sessions) has no upper bound on message rows |
| 16 | Testability | P1 | `sample_state.db` fixture maintenance burden; test rot risk |
| 17 | Testability | P1 | Rollback tests require real filesystem state, can't run in parallel |
| 18 | Testability | P1 | `redact_pii()` fallback behavior undefined, can't test |
| 19 | Security | P2 | `result_snippet` truncation may produce invalid UTF-8 or truncated redaction placeholders |
| 20 | Security | P2 | `PRAGMA query_only = ON` is advisory, not a hard security boundary |
| 21 | Architecture | P2 | Feature flag creates permanently untested code paths in CI |
| 22 | Performance | P2 | Compiled regex cache thread-safety unspecified |
| 23 | Performance | P2 | 1-hour cache with no invalidation on `state.db` modification |
| 24 | Testability | P2 | SC2 recall measurement requires manual labeling, can't CI-verify |
| 25 | Testability | P2 | 75+ tests not CI-gated — aspirational |
| 26 | Testability | P2 | E2E pipeline tests require non-in-memory state.db |

---

## Prior Review P0s: Are They Addressed?

| P0 from Prior Review | Spec Addressed? | Verdict |
|---------------------|-----------------|---------|
| PII flows unreduced (user_id = Telegram chat IDs) | Section 8.1: user_id → HMAC-SHA256, system_prompt never read | **Partially** — design is sound but implementation gaps (HMAC salt undefined, role filter bypass in SQL) |
| No credential scrubbing in error text | Section 8.2: CREDENTIAL_PATTERNS defined | **Partially** — patterns incomplete (missing Telegram tokens, AWS keys) |
| No state.db corruption handling | Section 7: `PRAGMA quick_check` + skip on failure | **Partially** — quick_check doesn't catch WAL corruption; error path returns empty analysis which is safe but silent |
| No rollback on partial fix application | Section 4.5: `apply_fix()` with backup + rollback | **Partially** — rollback mechanism exists but uses wrong primitive (`shutil.copy2` vs atomic rename); pipeline has no all-or-nothing semantics |

---

## Top 5 Priority Fixes for Next Version

1. **[P0] Specify `redact_pii()` fallback and expand `CREDENTIAL_PATTERNS`** — add Telegram bot tokens, AWS keys, Discord tokens, generic API key patterns. Define the fallback explicitly.

2. **[P0] Implement atomic skill writes** — replace `shutil.copy2()` with staging file + `os.rename()`. Add pipeline-level all-or-nothing fix application with rollback on any failure.

3. **[P0] Define HMAC salt lifecycle** — specify storage, generation, and rotation. Store in a file with `0600` permissions, not in env vars.

4. **[P1] Fix SQL JOIN role filter** — add `AND m2.role = 'tool'` to the JOIN in `get_tool_calls()`, making the role filter explicit at the DB level.

5. **[P1] Benchmark real performance** — run actual classification on the real 22,349-message dataset and measure per-message latency. Revise performance estimates based on measured data.

---

*End of Final Review*
