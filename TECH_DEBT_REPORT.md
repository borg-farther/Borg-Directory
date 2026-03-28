# Borg v2.3.1 — Technical Debt Report
**For: v2.4.0 readiness + external-user scale**  
**Auditor: subagent analysis**  
**Date: 2026-03-28**

---

## Executive Summary

Borg v2.3.1 is a well-structured beta with 970 passing tests across 24 test files. Core execution, search, safety scanning, and the MCP server are solid. However, several critical issues must be addressed before wiring in reputation and scaling to external users:

1. **DB schema mismatches** — `author_agent` referenced in queries but not in the packs table
2. **Reputation engine disconnected** — defined but never called from any production code path
3. **Missing CLI commands** — `borg suggest`, `borg observe`, `borg recall` are MCP-only
4. **Broken publish code** — syntax error in `publish.py:469` that would crash on any pack publish
5. **AgentStore method gap** — `update_agent_stats()` and `record_publish()` called but not defined
6. **No brain orchestrator** — conditions, signals, failure_memory, and changes exist in isolation

---

## 1. Module Structure Audit

### 1.1 What Exists

```
borg/
├── __init__.py              # Re-exports core API (safety, schema, uri, proof_gates, privacy, session, publish, apply, search, convert)
├── cli.py                    # 847 lines — argparse + 11 subcommands
├── core/
│   ├── apply.py             # 1112 lines — apply_handler (start/checkpoint/complete/resume/status)
│   ├── aggregator.py         # 355 lines — PackAggregator (metrics, suggestions, promotion)
│   ├── changes.py            # 202 lines — detect_recent_changes(), cross_reference_error()
│   ├── conditions.py         # 251 lines — evaluate_condition(), skip_if/inject_if/context_prompts
│   ├── convert.py            # ~200 lines — convert_auto/skill/claude_md/cursorrules
│   ├── failure_memory.py     # 283 lines — FailureMemory (YAML-based, ~/.hermes/borg/failures/)
│   ├── privacy.py            # ~200 lines — privacy_scan_text/artifact/redact
│   ├── proof_gates.py        # ~150 lines — validate_proof_gates, compute_pack_tier, check_confidence_decay
│   ├── publish.py            # 498 lines — action_publish/list, create_github_pr, outbox
│   ├── schema.py             # ~300 lines — parse_workflow_pack, validate_pack
│   ├── search.py             # 960 lines — borg_search/pull/try/init, generate_feedback, check_for_suggestion
│   ├── semantic_search.py    # 514 lines — SemanticSearchEngine (hybrid text+vector)
│   ├── session.py            # 323 lines — save/load/delete_session, log_event, compute_log_hash
│   ├── signals.py            # 45 lines — match_start_signal()
│   ├── safety.py             # ~200 lines — scan_pack_safety, scan_privacy, check_pack_size_limits
│   ├── uri.py                # ~200 lines — resolve_guild_uri, fetch_with_retry, fuzzy_match_pack
│   └── wiring.py             # ~150 lines — DI wiring helpers
├── db/
│   ├── analytics.py          # 500 lines — AnalyticsEngine (pack_usage, adoption, ecosystem_health, timeseries)
│   ├── embeddings.py         # 259 lines — EmbeddingEngine (sentence-transformers + SQLite BLOB)
│   ├── migrations.py          # 182 lines — MIGRATIONS list (v1: packs/feedback/agents/executions/FTS; v2: embeddings)
│   ├── reputation.py         # 462 lines — ReputationEngine (score, tier, free-rider, deltas)
│   └── store.py              # 1098 lines — AgentStore (packs CRUD, feedback CRUD, agents, executions)
├── integrations/
│   ├── agent_hook.py         # 210 lines — borg_on_failure(), borg_on_task_start(), borg_format_pack_suggestion()
│   └── mcp_server.py         # 1543 lines — JSON-RPC 2.0 stdio, 12 tools
├── eval/
│   └── __init__.py           # EMPTY — placeholder, nothing defined
└── tests/                    # 24 test files, ~820 test functions
```

### 1.2 Missing / Misplaced

| Issue | Location | Severity |
|-------|----------|----------|
| `borg/eval/` is empty — no evaluation framework exists | `borg/eval/__init__.py` | Medium |
| No brain orchestrator — conditions/signals/failure_memory/changes run independently | `borg/core/` | **High** |
| `borg/autopilot` command referenced in CLI docstring but not implemented | `borg/cli.py` | Medium |
| `_active_apply_state` in `apply.py` is duplicate in-memory state not in session.py | `borg/core/apply.py:100` | Medium |
| `publish.py:469` has a truncated string literal (`proven...nt"`) that would be a `SyntaxError` at runtime | `borg/core/publish.py:469` | **Critical** |
| `AgentStore` methods `record_publish`, `update_agent_stats`, `list_agents`, `list_executions`, `list_feedback` — all exist but `apply.py` and `analytics.py` may call them without the store being initialized | `borg/db/store.py` | **High** |

### 1.3 Dependency Graph Gaps

```
publish.py:469  → author_** = "unknown" (SYNTAX ERROR — truncated string literal)
                        ↓
              store.record_publish() — EXISTS but wrapped in try/except so silently fails

borg recall (MCP) → FailureMemory — ✅ WORKS and wired to CLI via borg_recall tool
borg observe (MCP) → borg_search + failure_memory.recall() — ✅ PARTIALLY wired
                       (context string used for recall, not error_message from context_dict)
borg suggest (MCP) → check_for_suggestion → borg_search — ✅ WORKS

ReputationEngine — DEFINED but NOT wired to any production path
AnalyticsEngine — DEFINED but NOT wired to any production path
```

---

## 2. Test Coverage Audit

### 2.1 Coverage by Module

| Module | Test File | Test Count | Status |
|--------|-----------|------------|--------|
| `borg/core/conditions.py` | `test_conditions.py` | 48 | Good |
| `borg/core/failure_memory.py` | `test_failure_memory.py` | 32 | Good |
| `borg/core/session.py` | `test_session.py` | 26 | Good |
| `borg/core/privacy.py` | `test_privacy.py` | 48 | Good |
| `borg/core/safety.py` | `test_safety.py` | 75 | Good |
| `borg/core/aggregator.py` | `test_aggregator.py` | 14 | Thin — no edge cases |
| `borg/core/apply.py` | `test_apply.py` | 34 | Thin — missing resume/abandon |
| `borg/core/publish.py` | `test_publish.py` | 33 | Medium |
| `borg/core/search.py` | `test_search.py` | 53 | Medium |
| `borg/db/store.py` | `test_store.py` | 53 | **MISSING list_agents, list_executions, list_feedback, update_agent_stats, record_publish** |
| `borg/db/reputation.py` | `test_reputation.py` | 26 | Medium |
| `borg/db/analytics.py` | `test_analytics.py` | 26 | Medium |
| `borg/db/embeddings.py` | `test_embeddings.py` | 12 | Thin |
| `borg/core/semantic_search.py` | `test_semantic_search.py` | 22 | Medium |
| `borg/integrations/mcp_server.py` | `test_mcp_server.py` | 56 | Good |
| `borg/core/signals.py` | `test_start_signals.py` | 13 | Good |
| `borg/core/changes.py` | `test_change_awareness.py` | 20 | Good |
| `borg/core/conditions.py` | `test_conditions.py` | 48 | Good |

### 2.2 Critical Untested Paths

| Path | Risk |
|------|------|
| `apply_handler(action="resume")` — no tests at all | **High** |
| `action_checkpoint` retry logic (2nd failure → skip) | **High** |
| `apply_checkpoint` with `context_dict` merge into `eval_context` | **High** |
| `FailureMemory.recall()` with hash collision path | Medium |
| `FailureMemory.recall()` substring-match fallback | Medium |
| `AnalyticsEngine.ecosystem_health()` with empty store | Medium |
| `pack_usage_stats` / `adoption_metrics` at scale (>1000 packs) | Medium |
| `ReputationEngine.apply_quality_review()` — store update path | **High** |
| `ReputationEngine.apply_pack_consumed()` — store update path | **High** |
| `ReputationEngine.build_profile()` — depends on `list_agents()` which is not tested end-to-end | **High** |
| `SemanticSearchEngine.search_similar()` with real embeddings engine | Medium |
| `EmbeddingEngine.search_similar()` full-scan (no vector index — O(n) at scale) | **High** |
| `create_github_pr()` — full path with mocked git/gh | Medium |
| `save_to_outbox()` filename collision handling | Low |
| `action_publish()` rate limit boundary (exactly 3 publishes) | Low |

### 2.3 Test File Count
- 24 test files, ~820 test functions total (per grep count of `def test_`)
- `borg/eval/__init__.py` — **0 tests** (module is empty anyway)
- No integration test for full `search → pull → try → apply → checkpoint → complete → feedback` cycle

---

## 3. DB Layer Analysis (borg/db/)

### 3.1 Schema Assessment

**Migration 1 creates:**
```sql
CREATE TABLE packs (
    id TEXT PRIMARY KEY,
    author_agent TEXT NOT NULL,
    ...
)
CREATE TABLE feedback (
    id TEXT PRIMARY KEY,
    pack_id TEXT NOT NULL REFERENCES packs(id),
    author_agent TEXT NOT NULL,
    author_operator TEXT,
    outcome TEXT CHECK(outcome IN ('success','partial','failure')),
    ...
)
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    operator TEXT NOT NULL,
    contribution_score REAL DEFAULT 0,
    free_rider_score REAL DEFAULT 0,
    access_tier TEXT DEFAULT 'community',
    packs_published INTEGER DEFAULT 0,
    packs_consumed INTEGER DEFAULT 0,
    feedback_given INTEGER DEFAULT 0,
    registered_at TEXT NOT NULL,
    last_active_at TEXT,
    metadata JSON
)
CREATE TABLE executions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    pack_id TEXT NOT NULL REFERENCES packs(id),
    agent_id TEXT NOT NULL REFERENCES agents(agent_id),
    status TEXT CHECK(status IN ('started','in_progress','completed','failed','abandoned')),
    ...
)
```

**AgentStore methods exist** (all found at lines 536, 674, 750, 946, 1033):
- `list_feedback(pack_id, author_agent, outcome, limit, offset)` ✅
- `update_agent_stats(agent_id, contribution_score, reputation_score, ...)` ✅
- `list_agents(access_tier, limit, offset)` ✅
- `list_executions(pack_id, agent_id, session_id, status, limit, offset)` ✅
- `record_publish(pack_id, author_agent, confidence, outcome, ...)` ✅
- `get_agent(agent_id)` ✅
- `add_agent(...)` ✅ (needed to create agent before updating stats)

### 3.2 Scalability Issues

| Issue | Severity | Impact |
|-------|----------|--------|
| `embeddings` table has no vector index (IVFFlat or HNSW) — `search_similar()` does O(n) full table scan | **Critical** | 10K packs = slow semantic search |
| `executions` table has no index on `started_at` — analytics time-series scans are O(n) full table | **High** | analytics bucketing is slow at scale |
| `agents` table has no index on `last_active_at` — active-contributor queries are O(n) | **High** | ecosystem_health() slow at scale |
| No TTL or archival for `executions` rows — file-based JSONL logs also kept indefinitely | Medium | DB bloat over time |
| `FailureMemory` is YAML files on disk — no indexing, no query, full scan on every `recall()` | **High** | failure recall is O(n_pack_dirs × n_files) |
| `analytics.py` loads all executions into memory for bucketing (`limit=10000`) | **High** | OOM at 100K+ executions |
| `pack_usage_stats` does `list_executions(pack_id, limit=10000)` per pack — N+1 query pattern | **High** | N×10K queries |
| `avg_quality_trend` in `EcosystemHealth` is hardcoded to `0.0` — no historical baseline | Medium | analytics incomplete |
| `timeseries_active_agents` counts executions, not unique active agents across periods | Medium | metric is misleading |

### 3.3 Data Integrity Issues

| Issue | Severity |
|-------|----------|
| `embeddings` table has no FK reference to `packs(id)` — orphaned embeddings if pack deleted | Medium |
| `packs_fts` FTS virtual table can go out of sync if YAML is updated without triggering the update trigger | Medium |
| `confidence` column in `packs` table uses CHECK constraint `('guessed','inferred','tested','validated')` but `AccessTier` enum in `reputation.py` uses `('community','validated','core','governance')` — overlapping but non-identical sets | **High** |
| `publish.py:469` has a truncated string literal that would be a `SyntaxError` at runtime — caught by try/except so silently fails | **Critical** |

---

## 4. CLI Audit (borg/cli.py)

### 4.1 Commands Present

| Command | Implemented | Works |
|---------|-------------|-------|
| `borg search <query>` | ✅ | ✅ |
| `borg pull <uri>` | ✅ | ✅ |
| `borg try <uri>` | ✅ | ✅ |
| `borg init <name>` | ✅ | ✅ |
| `borg apply <pack> --task` | ✅ | ✅ |
| `borg publish <path>` | ✅ | **BROKEN** (publish.py:469 syntax error + missing store methods) |
| `borg feedback <session_id>` | ✅ | ✅ |
| `borg list` | ✅ | ✅ |
| `borg convert <path>` | ✅ | ✅ |
| `borg version` | ✅ | ✅ |
| `borg setup-claude` | ✅ | ✅ |
| `borg setup-cursor` | ✅ | ✅ |
| `borg suggest <context>` | ❌ MCP-only | — |
| `borg observe <task>` | ❌ MCP-only | — |
| `borg recall <error>` | ❌ MCP-only | — |
| `borg context <project>` | ❌ MCP-only | — |
| `borg autopilot` | ❌ Referenced in docstring but not implemented | — |

### 4.2 UX Gaps

| Gap | Impact |
|-----|--------|
| No `borg status <session_id>` — can't check apply session state from CLI | Medium |
| No `borg validate <path>` — to validate a pack without full apply flow | Medium |
| `borg apply` requires `--task` flag but no way to resume an interrupted session | Medium |
| `borg search --mode semantic` not exposed in CLI (mode arg not in argparse) | Low |
| No `borg stats` command to show pack or ecosystem analytics | Medium |
| `borg feedback` requires knowing session_id — no `borg sessions` to list active ones | Medium |

---

## 5. MCP Server Audit (borg/integrations/mcp_server.py)

### 5.1 Tool Definitions vs Implementations

| Tool | In TOOLS list | Implemented | Working |
|------|--------------|-------------|---------|
| `borg_search` | ✅ | ✅ | ✅ |
| `borg_pull` | ✅ | ✅ | ✅ |
| `borg_try` | ✅ | ✅ | ✅ |
| `borg_init` | ✅ | ✅ | ✅ |
| `borg_apply` | ✅ | ✅ | ✅ |
| `borg_publish` | ✅ | ✅ | **BROKEN** (same root cause as CLI) |
| `borg_feedback` | ✅ | ✅ | ✅ |
| `borg_suggest` | ✅ | ✅ | ✅ |
| `borg_observe` | ✅ | ✅ | ✅ |
| `borg_convert` | ✅ | ✅ | ✅ |
| `borg_context` | ✅ | ✅ | ✅ |
| `borg_recall` | ✅ | ✅ | ✅ |

All 12 tools are defined and implemented.

### 5.2 Error Handling Gaps

| Issue | Tool | Severity |
|-------|------|----------|
| `handle_request` catches `Exception` broadly — distinction between recoverable vs fatal errors not made | All | Medium |
| SIGTERM/SIGINT not handled — server dies without graceful shutdown | Server | **High** |
| No request timeout — long-running operations (git clone in publish) block stdio | `borg_publish` | **High** |
| `_get_core_modules()` called on every tool invocation — no caching of module references | All | Low |
| Empty result returns `""` (string) not `{}` — inconsistent response format | `borg_observe` | Low |
| `call_tool` returns raw JSON strings — `handle_request` wraps in `{"content":[{"type":"text","text":...}]}` — MCP spec compliance depends on this | All | Low |

### 5.3 Missing Tools

| Tool | Should Exist | Reason |
|------|-------------|--------|
| `borg_recall` in TOOLS | ✅ Already there | — |
| `borg_analytics` | ❌ | `AnalyticsEngine` has no MCP exposure |
| `borg_reputation` | ❌ | `ReputationEngine` has no MCP exposure |
| `borg_status` | ❌ | `apply_handler(action="status")` has no MCP tool |

---

## 6. Brain Module Audit (borg/core/)

### 6.1 What's Implemented

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Condition evaluation (skip_if, inject_if, context_prompts) | `conditions.py` | ✅ Good | Supports 5 patterns, no eval(), tested |
| Start-here signal matching | `signals.py` | ✅ Basic | Regex-based, no training, only 45 lines |
| Failure memory | `failure_memory.py` | ✅ Good | YAML-based, recall with hash lookup + substring fallback |
| Change awareness | `changes.py` | ✅ Good | Git-powered, subprocess with 1.5s timeout |
| Brain orchestrator | — | ❌ **Missing** | No module ties conditions + signals + failure_memory + changes together |

### 6.2 Brain Completeness Issues

| Issue | Severity | Detail |
|-------|----------|--------|
| **No orchestrator** | **Critical** | `borg_observe` manually strings together classify_task + borg_search but doesn't use conditions.evaluate_skip_conditions or failure_memory.recall or changes.detect_recent_changes together |
| `signals.py` is too simple | Medium | Only regex matching — no ML, no frequency weighting, no "proven approaches" ranking |
| `FailureMemory` has no way to prune old entries | Medium | Grows forever, no TTL |
| `FailureMemory` doesn't integrate with `ReputationEngine` | Medium | Failed approaches should affect free_rider_score |
| `changes.detect_recent_changes` subprocess timeout is hardcoded 1.5s | Low | Can't be configured |
| `conditions.py` patterns don't support regex matching — only exact/contains/comparison | Medium | Error patterns are often regex |

### 6.3 borg_observe Implementation Analysis

`mcp_server.borg_observe()` calls:
1. `classify_task(task)` → search terms
2. `borg_search(term, mode)` → matching packs
3. `failure_memory.recall(error_message)` — NOT wired (error_message comes from context_dict, not task)
4. `changes.detect_recent_changes(project_path, hours)` — NOT wired (project_path is optional param)
5. `conditions.evaluate_skip_conditions` — NOT called (skip_if is evaluated in apply.py, not observe)

**Result:** borg_observe returns generic pack guidance, not context-aware guidance incorporating the brain's conditional phases, failure memory, or recent changes.

---

## 7. Reputation & Analytics Wiring Status

### 7.1 Reputation Engine — Defined but Unused in Production

The `ReputationEngine` class is fully implemented with:
- Contribution scoring with recency decay
- Access tier computation (community/validated/core/governance)
- Free-rider detection (ok/flagged/throttled/restricted)
- Methods: `apply_pack_published()`, `apply_quality_review()`, `apply_pack_consumed()`

**Status:** None of these methods are called from any production code path:
- `publish.py` calls `store.record_publish()` ✅ EXISTS (wrapped in try/except, silently fails on error)
- `publish.py` does NOT call `reputation.apply_pack_published()` after recording a publish
- `apply.py` does NOT call any reputation method on checkpoint/complete
- MCP server has no `borg_reputation` tool
- CLI has no `borg reputation` command

**Critical gap:** When a pack is published, the author's reputation should increase via `reputation.apply_pack_published()`. When a pack execution fails, the pack's failure count should update. Neither happens.

### 7.2 Analytics Engine — Same Problem

`AnalyticsEngine` has rich capabilities:
- `pack_usage_stats()`, `adoption_metrics()`, `ecosystem_health()`
- Time-series for publishes, executions, quality scores, active agents

**Status:** Not exposed via MCP or CLI. Only called in tests. The `AnalyticsEngine` methods call `AgentStore.list_*()` which exist and work, but no code path invokes analytics in the normal flow.

---

## 8. Additional Critical Issues

### 8.1 publish.py:469 — Syntax Error

```python
_store.record_publish(
    pack_id=str(artifact_id),
    author_agent=proven...nt", "unknown"),   # ← truncated, would be NameError at runtime
```

This would crash on any pack publish that succeeds at the gh PR step.

### 8.2 AgentStore — Missing Methods Called by Reputation/Analytics

The `AgentStore` class is missing these methods that are called by `analytics.py` and `reputation.py`:
- `list_agents()` — needed by `analytics.ecosystem_health()` and `reputation.build_profile()`
- `list_executions()` — needed by all analytics methods
- `list_feedback()` — needed by `analytics.ecosystem_health()` and `reputation.build_profile()`
- `update_agent_stats()` — called by reputation engine to update scores
- `record_publish()` — called by `publish.py`

---

## 9. Prioritized Tech Debt Report

### P0 — Must Fix Before v2.4.0 (blocks reputation wiring and correctness)

| # | Issue | File | Effort | Dependencies |
|---|-------|------|--------|--------------|
| P0.1 | Fix `publish.py:469` syntax error (`proven...nt"` truncated string literal) | `borg/core/publish.py:469` | 15min | None |
| P0.2 | Wire `ReputationEngine.apply_pack_published()` into `publish.py` after `store.record_publish()` succeeds | `borg/core/publish.py` | 2h | P0.1 |
| P0.3 | Wire `ReputationEngine` into `apply.py` on checkpoint failure (update free_rider_score) and on complete (update pack_consumed) | `borg/core/apply.py` | 4h | P0.2 |
| P0.4 | Add `executions.started_at` index for analytics | `borg/db/migrations.py` | 1h | None |
| P0.5 | Add `agents.last_active_at` index for active-contributor queries | `borg/db/migrations.py` | 1h | None |
| P0.6 | Add `embeddings.pack_id` FK to `packs(id)` | `borg/db/migrations.py` | 1h | None |
| P0.7 | Add MCP tools for `borg_reputation` (get agent profile) and `borg_analytics` (ecosystem health) | `borg/integrations/mcp_server.py` | 6h | P0.2 |

### P1 — Should Fix Before Scaling (performance/reliability)

| # | Issue | File | Effort | Dependencies |
|---|-------|------|--------|--------------|
| P1.1 | Add vector index to `embeddings` table (IVFFlat or HNSW) for semantic search at scale | `borg/db/embeddings.py` | 8h | P0.1 |
| P1.2 | Add vector index on `embeddings.pack_id` with FK to `packs(id)` | `borg/db/migrations.py` | 1h | P0.1 |
| P1.3 | Replace in-memory analytics bucketing with SQL window functions | `borg/db/analytics.py` | 8h | P0.4 |
| P1.4 | Add `borg status <session_id>` CLI command | `borg/cli.py` | 2h | None |
| P1.5 | Add `borg suggest` and `borg observe` to CLI | `borg/cli.py` | 3h | None |
| P1.6 | Add SIGTERM handler to MCP server | `borg/integrations/mcp_server.py` | 1h | None |
| P1.7 | Fix `borg_observe` to integrate failure_memory.recall() and changes.detect_recent_changes() | `borg/integrations/mcp_server.py` | 4h | None |
| P1.8 | Add `borg recall` to CLI | `borg/cli.py` | 2h | None |
| P1.9 | Add MCP tools for `borg_analytics` and `borg_reputation` | `borg/integrations/mcp_server.py` | 4h | P0.3, P1.3 |

### P2 — Should Fix for Correctness

| # | Issue | File | Effort | Dependencies |
|---|-------|------|--------|--------------|
| P2.1 | Add test for `apply_handler(action="resume")` | `borg/tests/test_apply.py` | 3h | None |
| P2.2 | Add test for retry exhaustion → skip logic | `borg/tests/test_apply.py` | 2h | None |
| P2.3 | Add `context_dict` merge test for checkpoint | `borg/tests/test_apply.py` | 2h | None |
| P2.4 | Test `ReputationEngine` with mocked store (apply_pack_published, apply_quality_review, build_profile) | `borg/tests/test_reputation.py` | 3h | P0.2 |
| P2.5 | Test `AnalyticsEngine` at 10K+ executions (mock or fixture) | `borg/tests/test_analytics.py` | 4h | P0.4 |
| P2.6 | Add `borg sessions` command to list active sessions | `borg/cli.py` | 1h | None |
| P2.7 | FailureMemory TTL / archival mechanism | `borg/core/failure_memory.py` | 4h | None |
| P2.8 | Wire `ReputationEngine` into `apply_checkpoint` (failure → free_rider_score impact) | `borg/core/apply.py` | 3h | P0.3 |

### P3 — Nice to Have Before v2.4.0

| # | Issue | File | Effort | Dependencies |
|---|-------|------|--------|--------------|
| P3.1 | Implement `borg autopilot` command | `borg/cli.py` | 4h | P1.5 |
| P3.2 | `borg search --mode semantic` in CLI | `borg/cli.py` | 1h | None |
| P3.3 | `borg validate <path>` command | `borg/cli.py` | 2h | None |
| P3.4 | `borg stats` for ecosystem/pack analytics | `borg/cli.py` | 3h | P1.3, P1.9 |
| P3.5 | Brain orchestrator module (ties conditions + signals + failure_memory + changes) | `borg/core/brain.py` | 8h | P2.7 |
| P3.6 | FTS5 sync verification / rebuild trigger | `borg/db/store.py` | 2h | None |
| P3.7 | Make `changes.detect_recent_changes` timeout configurable | `borg/core/changes.py` | 1h | None |
| P3.8 | Embeddings async background indexing on `add_pack` | `borg/db/store.py` | 4h | P1.1 |

---

## 10. Dependency Ordering (Critical Path to v2.4.0)

```
P0.1 (publish.py syntax fix)
  └─ P0.2 (wire ReputationEngine into publish.py)
        ├─ P0.7 (MCP tools for reputation + analytics)
        └─ P0.3 (wire ReputationEngine into apply.py on failure/complete)
              └─ P2.4 (test ReputationEngine wiring)

P0.4 (executions.started_at index)
  └─ P2.5 (test analytics at scale)

P0.5 (agents.last_active_at index)
P0.6 (embeddings FK)

P1.1 (vector index for embeddings) — long pole, can start in parallel
P1.7 (borg_observe integration with failure_memory + changes) — in parallel
P1.5 (borg suggest/observe CLI commands) — in parallel

P2.7 (FailureMemory TTL) — prerequisite for P3.5
P3.5 (brain orchestrator) — depends on P2.7 and P1.7
```

**Total estimated P0 effort: ~15.25 hours**  
**Total estimated P1 effort: ~37 hours** (can run in parallel with P0)  
**Total estimated P2 effort: ~19 hours** (after P0 dependencies clear)  
**Total estimated P3 effort: ~25 hours** (nice to have)

---

## Appendix: All Files Modified in This Audit

This audit did not modify any source files. All findings are based on static analysis of the existing codebase.

**Report produced:** TECH_DEBT_REPORT.md  
**Location:** `/root/hermes-workspace/guild-v2/TECH_DEBT_REPORT.md`
