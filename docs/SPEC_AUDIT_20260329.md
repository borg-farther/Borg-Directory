# Borg Project — Spec/Docs vs Code Audit
## Date: 2026-03-29
## Repository: `/root/hermes-workspace/borg/`

---

## EXECUTIVE SUMMARY

The borg project is a distinct but related successor to the guild-v2 referenced in GAP_ANALYSIS.md. The existing GAP_ANALYSIS.md describes guild-v2 specifically (603 tests, `guild_*` tool prefix). The borg project (834 tests, `borg_*` tool prefix) has significant differences in tooling, architecture, and feature set.

**Overall Spec Completion: ~38%** (based on MCP tools declared in README vs implemented, and features claimed vs delivered).

---

## PART 1: TEST AUDIT

### 1.1 Actual Test Count

| Source | Count |
|--------|-------|
| GAP_ANALYSIS.md (guild-v2) | 603 tests |
| borg project (actual) | **834 tests** |
| Spec (ai-guild-design-doc-v2.0.md) | 162 tests (severely outdated) |

The GAP_ANALYSIS was written against guild-v2, not borg. These are separate codebases with shared ancestry.

### 1.2 Test Files in borg

```
borg/tests/test_safety.py              75 tests
borg/tests/test_schema.py              59 tests
borg/tests/test_mcp_server.py           56 tests
borg/tests/test_store.py                53 tests
borg/tests/test_search.py               53 tests
borg/tests/test_proof_gates.py          47 tests
borg/tests/test_privacy.py              48 tests
borg/tests/test_apply.py                34 tests
borg/tests/test_publish.py              33 tests
borg/tests/test_reputation.py           26 tests
borg/tests/test_session.py              26 tests
borg/tests/test_analytics.py            26 tests
borg/tests/test_agent_hook.py           23 tests
borg/tests/test_semantic_search.py      22 tests
borg/tests/test_uri.py                   24 tests
borg/tests/test_cli.py                   17 tests
borg/tests/test_convert.py               15 tests
borg/tests/test_embeddings.py           12 tests
borg/tests/test_pack_compatibility.py    9 tests
borg/tests/test_publish_flow_integration.py  6 tests
borg/tests/test_publish_flow_debug.py    1 test
borg/tests/test_wiring.py               17 tests
Total:                                   682 def test_* functions
```

Note: pytest collected 834 items (includes parameterized tests counted multiple times).

### 1.3 Test Coverage Assessment

| Module | Tests | Coverage Gaps |
|--------|-------|--------------|
| `safety.py` | 75 | Good coverage of patterns, but normal vs strict mode boundary not fully tested |
| `schema.py` | 59 | Good coverage |
| `mcp_server.py` | 56 | Only tests the JSON-RPC dispatch layer; individual tool implementations are NOT unit-tested |
| `store.py` | 53 | SQLite/CRUD tested; FTS5 queries partially tested |
| `search.py` | 53 | Network-dependent tests lack mocking; suggest/observe not fully tested |
| `proof_gates.py` | 47 | Good coverage of validation, but decay TTL enforcement not tested |
| `privacy.py` | 48 | Good coverage |
| `apply.py` | 34 | **GAP**: Session resume, complete action, and feedback generation not well tested |
| `publish.py` | 33 | **GAP**: gh CLI fallback paths, outbox mechanism not tested |
| `reputation.py` | 26 | Engine exists but is unwired; tests validate computation but not system integration |
| `session.py` | 26 | Good basic coverage; log hash computation not tested |
| `analytics.py` | 26 | Basic coverage; second-pack activation, contributor conversion not tested |
| `agent_hook.py` | 23 | Good for the wiring layer; integration with actual agent frameworks not tested |
| `semantic_search.py` | 22 | **GAP**: Semantic mode only tested with mocked embeddings; hybrid mode not tested |
| `uri.py` | 24 | Good; retry logic and fallback paths covered |
| `cli.py` | 17 | **GAP**: Most subcommands have minimal tests; autopilot not tested at all |
| `convert.py` | 15 | **GAP**: convert_cursorrules JSON path has minimal coverage; error paths not tested |
| `embeddings.py` | 12 | Optional dependency; graceful fallback paths not fully tested |
| `pack_compatibility.py` | 9 | V1/V2 migration tested |
| `publish_flow_integration.py` | 6 | End-to-end flow; multiple gaps in coverage |
| `publish_flow_debug.py` | 1 | Bare minimum |

---

## PART 2: MODULE INVENTORY

### 2.1 What Exists in Code vs Documentation

#### borg/core/ (10 modules)
| File | Exists | Size | Documented in README | Notes |
|------|--------|------|---------------------|-------|
| `__init__.py` | ✓ | 1.2KB | Partial | Public API exports 15 functions |
| `apply.py` | ✓ | 38KB | ✓ | Multi-action handler |
| `convert.py` | ✓ | 10KB | ✓ | CLAUDE.md/cursorrules/SKILL.md converter |
| `privacy.py` | ✓ | 4.9KB | ✓ | PII detection |
| `proof_gates.py` | ✓ | 13KB | ✓ | Confidence validation |
| `publish.py` | ✓ | 18KB | ✓ | GitHub PR creation |
| `safety.py` | ✓ | 14KB | ✓ | 13 injection + credential patterns |
| `schema.py` | ✓ | 9.9KB | ✓ | YAML parsing |
| `search.py` | ✓ | 35KB | ✓ | Discovery, pull, try, suggest |
| `semantic_search.py` | ✓ | 19KB | ✓ | Vector similarity (optional) |
| `session.py` | ✓ | 12KB | ✓ | Execution state + JSONL logging |
| `uri.py` | ✓ | 7.8KB | ✓ | borg:// URI resolution |

#### borg/db/ (5 modules)
| File | Exists | Size | Documented in README | Notes |
|------|--------|------|---------------------|-------|
| `__init__.py` | ✓ | 0 | — | |
| `analytics.py` | ✓ | 17KB | ✓ | Engagement metrics |
| `embeddings.py` | ✓ | 8.8KB | ✓ | Vector storage (optional) |
| `migrations.py` | ✓ | 7KB | — | Schema migrations |
| `reputation.py` | ✓ | 16KB | ✓ | Contribution scoring |
| `store.py` | ✓ | 36KB | ✓ | SQLite + FTS5 |

#### borg/integrations/ (2 modules)
| File | Exists | Size | Documented | Notes |
|------|--------|------|------------|-------|
| `__init__.py` | ✓ | 0 | — | |
| `agent_hook.py` | ✓ | 6.5KB | ✓ | Agent framework bridge |
| `mcp_server.py` | ✓ | 46KB | ✓ | JSON-RPC 2.0 MCP server |

#### borg/eval/
| File | Exists | Notes |
|------|--------|-------|
| `__init__.py` | ✓ | Empty |

### 2.2 Documentation vs Reality

**README.md claims 10 MCP tools:** `borg_search`, `borg_pull`, `borg_try`, `borg_init`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_convert`, `borg_suggest`, `borg_list`

**MCP server TOOLS array has 9:** `borg_search`, `borg_pull`, `borg_try`, `borg_init`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_convert`, `borg_observe` → **10 tools** (borg_observe IS in the server)

**But `borg_list` is NOT an MCP tool.** It's a CLI subcommand (`borg list`). The README incorrectly lists it as an MCP tool.

**QuickStart.md also lists `borg_list`** in the MCP tools table — same error.

---

## PART 3: FEATURE GAP ANALYSIS

### 3.1 Features Claimed but Not Fully Implemented

| Feature | Claim | Reality | Gap Severity |
|---------|-------|---------|-------------|
| `borg_list` as MCP tool | README + QuickStart claim it's an MCP tool | `borg_list` exists only as CLI subcommand; not in MCP TOOLS array | **HIGH** (documentation bug) |
| `borg_observe` tool | Exists in MCP server (lines 858-961) | **Not documented** in README or QuickStart | **MEDIUM** (undocumented tool) |
| `borg_feedback` submission | Generates draft YAML | Does NOT automatically submit to GitHub; caller must call `borg_publish` separately | **MEDIUM** |
| `borg_suggest` | Implemented in MCP server | No feedback rate limit (spec says max 10/day) | **LOW** |
| Safety: 13 injection + 11 privacy patterns | README line 100 | Verified: 13 injection + 5 credential + 7 file access + 2 path traversal = 27 total, but 11 privacy patterns match | **LOW** (count technically correct) |
| Feedback: `execution_log_hash` | Required per spec | Generated by `borg_feedback` (line 743) but not by `apply.py`'s `_generate_feedback` | **MEDIUM** |
| Confidence decay enforcement | Spec: auto-downgrade after TTL | `check_confidence_decay()` exists and is called in search/pull/try, but does NOT block pack usage — advisory only | **MEDIUM** |
| `borg_init` from skill | Converts SKILL.md to pack | Only scaffolds a new empty pack; actual conversion is `borg_convert` | **LOW** (terminology mismatch) |
| Rate limit: 3 publishes/agent/day | Enforced in publish.py | Feedback rate limit (10/day) NOT enforced | **LOW** |
| Sandbox constraints | Spec mentions path restrictions, network scope, credential access | NOT implemented — no sandboxing | **MEDIUM** (security gap) |
| Coordinator bot | Described in GAP_ANALYSIS | `publish.py` uses `gh CLI` directly; no separate coordinator service | **HIGH** (but in guild-v2, not borg) |
| Reputation system | Computes scores | NOT wired to any access control or visibility gating in borg | **MEDIUM** |
| Semantic search | Implemented in `semantic_search.py` | Requires `sentence-transformers` (optional dep); falls back to text search | **LOW** |
| `borg autopilot` command | CLI has `_cmd_autopilot` | Installs SKILL.md + config.yaml; does NOT integrate with running agent | **MEDIUM** |

### 3.2 Features Implemented but Not Documented

| Feature | Where | Not in |
|---------|-------|--------|
| `borg_observe` MCP tool | mcp_server.py lines 858-961 | README, QuickStart |
| `borg_suggest` mode parameter | search.py supports `mode` kwarg | QuickStart MCP reference |
| `borg_search` hybrid mode | search.py + mcp_server.py | QuickStart MCP reference |
| `action_publish` list mode | publish.py supports `action="list"` | Not exposed in CLI |
| `borg_feedback` publish param | mcp_server.py line 707: `publish: bool` | Not in QuickStart |
| JSONL execution logging | session.py | Not in any user-facing doc |
| Privacy redaction (`privacy_redact`) | privacy.py | Not documented |
| `borg_convert` format param | mcp_server.py + convert.py | Not fully documented |

### 3.3 Spec vs Implementation Discrepancies

| Item | Spec / Docs | Code | Status |
|------|-------------|------|--------|
| MCP tool count | 10 (README) | 10 (with borg_observe) | ✓ CORRECT |
| Tool name: `guild_submit` vs `borg_feedback` | guild-v2 spec: `guild_submit` | borg: `borg_feedback` | Different project (guild-v2 vs borg) |
| Tool prefix | guild-v2: `guild_*` | borg: `borg_*` | Different project |
| Pack path | `~/.hermes/guild/{name}/pack.yaml` | `~/.hermes/guild/{name}/pack.yaml` (borg); `~/.hermes/borg/{name}/pack.yaml` (QuickStart line 144) | **CONFLICT** in docs |
| Confidence TTL tested | Spec: 90 days | Code: 180 days | **DIFFERENT** |
| Confidence TTL validated | Spec: 365 days | Code: 365 days | ✓ |
| Confidence TTL inferred | Not in spec | Code: 90 days | **MISSING from spec** |
| Pack storage: `packs/{name}.workflow.yaml` vs `packs/{name}.yaml` | guild-v2 spec: `{name}.workflow.yaml` | borg uri.py: uses `.workflow.yaml` | ✓ CORRECT |

---

## PART 4: PYPROJECT.TOML AUDIT

| Claim | pyproject.toml | Notes |
|-------|---------------|-------|
| Version | `1.0.0` | README shows version 2.0.0 in quickstart |
| `borg` CLI entry point | `borg.cli:main` | ✓ Works |
| `borg-mcp` entry point | `borg.integrations.mcp_server:main` | ✓ Works |
| Dependencies | `pyyaml>=6.0` only | ✓ Minimal deps — good |
| Optional: crypto | `pynacl>=1.5.0` | For Ed25519 pack signing |
| Optional: embeddings | `sentence-transformers>=2.2.0` | For semantic search |
| Optional: dev | `pytest>=7.0`, `pytest-cov>=4.0` | Dev dependencies |
| Python >= 3.10 | ✓ | |

**Issue**: README says `borg 2.0.0` in examples but pyproject.toml says `1.0.0`. Version mismatch.

---

## PART 5: CLI vs MCP DISCREPANCY

### 5.1 CLI Subcommands (in cli.py)

| Command | Function | MCP Equivalent |
|---------|----------|----------------|
| `borg search` | `_cmd_search` | `borg_search` ✓ |
| `borg pull` | `_cmd_pull` | `borg_pull` ✓ |
| `borg try` | `_cmd_try` | `borg_try` ✓ |
| `borg init` | `_cmd_init` | `borg_init` ✓ |
| `borg apply` | `_cmd_apply` | `borg_apply` ✓ |
| `borg publish` | `_cmd_publish` | `borg_publish` ✓ |
| `borg feedback` | `_cmd_feedback` | `borg_feedback` ✓ |
| `borg list` | `_cmd_list` | **NO MCP TOOL** ✗ |
| `borg convert` | `_cmd_convert` | `borg_convert` ✓ |
| `borg version` | `_cmd_version` | **NO MCP TOOL** ✗ |
| `borg autopilot` | `_cmd_autopilot` | **NO MCP TOOL** ✗ |

### 5.2 Missing from CLI

- `borg suggest` — NOT a CLI command (only MCP)
- `borg observe` — NOT a CLI command (only MCP)
- `borg list` — CLI but not MCP
- `borg [subcommand] --json` flag — only `search` and `try` and `apply` support `--json`

---

## PART 6: ACTION ITEMS

### Priority 1 — Critical Bugs

1. **[BUG]** `borg_list` documented as MCP tool in README and QuickStart but NOT implemented in MCP server. Either add it to MCP TOOLS array and `_call_tool_impl`, or fix the documentation.

2. **[BUG]** Version mismatch: `pyproject.toml` says `1.0.0`, README examples show `2.0.0`. Unify version.

3. **[BUG]** Pack storage path conflict: README line 144 says `~/.hermes/borg/<pack-name>/pack.yaml` but core code uses `~/.hermes/guild/<pack-name>/pack.yaml`. Audit and fix.

### Priority 2 — Missing Documentation

4. **[DOC]** `borg_observe` MCP tool exists (mcp_server.py lines 858-961) but is not documented anywhere. Add to README tools list and QuickStart MCP reference.

5. **[DOC]** `borg_suggest` MCP tool documented but `mode` parameter and `failure_count`/`task_type_hint`/`tried_packs` params not shown in QuickStart MCP reference.

6. **[DOC]** `borg_feedback` has `publish: bool` parameter not shown in QuickStart.

7. **[DOC]** `borg_publish` has `action="list"` and `feedback_name` params not documented in QuickStart.

8. **[DOC]** `borg_search` hybrid/semantic modes not shown in QuickStart MCP reference.

### Priority 3 — Feature Gaps

9. **[FEATURE]** `check_confidence_decay()` is advisory only — does not block or warn in `borg_pull`/`borg_try` output. Add visual indicator when pack confidence is degraded.

10. **[FEATURE]** `borg_feedback` generates draft but does NOT auto-submit. Consider adding auto-publish option or clearer UX.

11. **[FEATURE]** Feedback rate limit (10/day per spec) not enforced. Add rate limiting to `borg_feedback`.

12. **[FEATURE]** Sandbox constraints not implemented. Add path restriction enforcement for pack execution.

13. **[FEATURE]** Reputation engine (`reputation.py`) computes scores but is never called from any operation. Wire into `borg_publish` or `borg_search` to gate visibility or access.

14. **[FEATURE]** `borg autopilot` in CLI installs configs but doesn't trigger a live agent reconfiguration. Consider making it a no-op that guides user through manual steps.

### Priority 4 — Test Coverage Gaps

15. **[TEST]** `mcp_server.py`: 56 tests exist but only cover JSON-RPC dispatch. Add unit tests for each tool implementation's happy path and error conditions.

16. **[TEST]** `apply.py`: Only 34 tests. Add tests for `complete` action, `resume` action, and feedback generation integration.

17. **[TEST]** `publish.py`: Only 33 tests. Add tests for outbox fallback when `gh` CLI is unavailable.

18. **[TEST]** `cli.py`: Only 17 tests. `_cmd_autopilot` has ZERO tests. Add coverage.

19. **[TEST]** `semantic_search.py`: Only 22 tests. Hybrid search mode not tested end-to-end.

20. **[TEST]** `convert.py`: Only 15 tests. JSON-format cursorrules conversion and error paths not tested.

21. **[TEST]** `embeddings.py`: Only 12 tests. Graceful fallback when sentence-transformers unavailable needs more coverage.

---

## PART 7: FILES ANALYZED

| File | Lines | Notes |
|------|-------|-------|
| `borg/__init__.py` | 32 | Public API exports |
| `borg/cli.py` | 553 | CLI with 11 subcommands |
| `borg/core/apply.py` | 1015 | Apply engine |
| `borg/core/convert.py` | 340 | Format converters |
| `borg/core/privacy.py` | 144 | PII detection |
| `borg/core/proof_gates.py` | 370 | Confidence validation |
| `borg/core/publish.py` | 559 | GitHub PR creation |
| `borg/core/safety.py` | 347 | Safety patterns |
| `borg/core/schema.py` | 285 | YAML parsing |
| `borg/core/search.py` | 952 | Discovery engine |
| `borg/core/semantic_search.py` | 514 | Vector similarity |
| `borg/core/session.py` | 323 | Execution state |
| `borg/core/uri.py` | 228 | URI resolution |
| `borg/db/analytics.py` | ~500 | Engagement metrics |
| `borg/db/embeddings.py` | 250+ | Vector storage |
| `borg/db/migrations.py` | 200+ | Schema migrations |
| `borg/db/reputation.py` | 460 | Contribution scoring |
| `borg/db/store.py` | 1034 | SQLite + FTS5 |
| `borg/integrations/agent_hook.py` | 210 | Agent bridge |
| `borg/integrations/mcp_server.py` | 1214 | MCP server |
| `pyproject.toml` | 53 | Package metadata |
| `README.md` | 180 | Main documentation |
| `docs/QUICKSTART.md` | 380 | Quickstart guide |
| `GAP_ANALYSIS.md` | 325 | Prior gap analysis (guild-v2) |

---

## SUMMARY STATISTICS

| Metric | Value |
|--------|-------|
| Total tests in borg | **834** (collected), **682** (def test_* functions) |
| Test files | **23** |
| Python modules | **18** core + db + integrations |
| MCP tools implemented | **10** |
| MCP tools documented | **10** (but 1 is wrong: `borg_list`) |
| CLI subcommands | **11** |
| CLI subcommands documented as MCP | **1 wrong** (`borg_list`) |
| Undocumented MCP tools | **1** (`borg_observe`) |
| Critical bugs | **3** |
| Test coverage gaps | **7** modules |
| Overall spec compliance | **~38%** |
