# PRD: Borg DeFi Stack Hardening & Completion

**Status:** ACTIVE
**Date:** 2026-03-30
**Author:** Hermes Agent
**Version:** 1.0

---

## 1. Executive Summary

The Borg DeFi stack (v2.5.0) has 603 tests across 22 modules, 4 live cron jobs, and a working pip package. However, the critical review identified 7 actionable gaps that prevent world-class engineering quality. This PRD specs each fix with formal success criteria and verification.

---

## 2. Work Items

### WI-1: Unit Tests for 4 Untested Modules

**Problem:** `data_models.py`, `api_clients/base.py`, `security/keystore.py`, `security/tx_guard.py` have no dedicated test files. They are exercised indirectly but edge cases, error paths, and boundary conditions are untested.

**Deliverables:**
- `borg/defi/tests/test_data_models.py` — dataclass construction, defaults, field validation, serialization, edge cases (empty strings, negative values, None fields)
- `borg/defi/tests/test_base_client.py` — BaseAPIClient init, session management, retry logic, timeout handling, rate limit response, API key sanitization in logs
- `borg/defi/tests/test_keystore.py` — encrypt/decrypt round-trip, wrong password, corrupted data, key rotation, empty plaintext, large payloads, file permissions
- `borg/defi/tests/test_tx_guard.py` — spending limits (at limit, over limit, reset), contract whitelist (allow, deny, empty list), check_token with GoPlus integration, check_token_security mock, concurrent spend tracking

**Success Criteria:**
- [ ] Each module has dedicated test file
- [ ] ≥90% line coverage per module (measure with pytest-cov)
- [ ] All error paths tested (exception types, messages)
- [ ] Edge cases: empty input, None, negative numbers, Unicode, max int
- [ ] 0 new test failures in full suite

**Verification:**
- Formal: `pytest --cov=borg/defi/data_models --cov=borg/defi/api_clients/base --cov=borg/defi/security --cov-report=term-missing`
- Informal: Reviewer confirms each test name describes a real scenario

---

### WI-2: Fix AsyncMock Warnings in swap_executor Tests

**Problem:** 2 tests produce `RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited`. This happens because the mock's `__aenter__` raises before the coroutine can be awaited.

**Deliverables:**
- Fix mock setup in `test_swap_executor.py` for `test_get_quote_error` (Jupiter) and `test_get_quote_api_error` (1inch)
- Suppress or properly handle the coroutine lifecycle

**Success Criteria:**
- [ ] 0 warnings in `pytest -W error::RuntimeWarning borg/defi/tests/test_swap_executor.py`
- [ ] All 39 swap_executor tests still pass
- [ ] No behavioral change — tests still verify the same error paths

**Verification:**
- Formal: `pytest -W error borg/defi/tests/test_swap_executor.py` exits 0
- Informal: Diff review confirms only mock setup changed, not assertions

---

### WI-3: Keystore PBKDF2 Key Derivation

**Problem:** `keystore.py` uses SHA256 for key derivation (marked "not production-safe" in code comments). This is vulnerable to brute force. Need PBKDF2 with ≥600,000 iterations or Argon2id.

**Deliverables:**
- Replace SHA256 fallback with PBKDF2-HMAC-SHA256 (600k iterations) using `cryptography` library
- Add migration path: if existing keystore detected with old format, re-encrypt on next unlock
- Update tests to verify iteration count and key derivation time (should take 100-500ms)

**Success Criteria:**
- [ ] `hashlib.sha256` no longer used for key derivation
- [ ] PBKDF2 with ≥600,000 iterations (OWASP 2024 recommendation)
- [ ] Existing keystores auto-migrate on first unlock
- [ ] Key derivation takes 100-500ms (not instant = not brute-forceable, not slow = usable)
- [ ] Round-trip encrypt/decrypt still works
- [ ] All existing keystore tests pass

**Verification:**
- Formal: `grep -r "sha256" borg/defi/security/keystore.py` returns 0 results (excluding comments)
- Formal: Test measures derivation time, asserts ≥100ms
- Informal: Code review confirms PBKDF2 parameters match OWASP guidance

---

### WI-4: MCP Tool Registration + CLI Entry Point

**Problem:** No way for Hermes agents to invoke DeFi functions via MCP tools or CLI. Users must write raw Python.

**Deliverables:**
- `borg/defi/mcp_tools.py` — MCP tool definitions:
  - `borg_defi_yields` — scan yield opportunities (wraps yield_hunter)
  - `borg_defi_tokens` — scan new tokens (wraps token_radar)
  - `borg_defi_tvl` — TVL pulse (wraps tvl_pulse)
  - `borg_defi_stablecoins` — stablecoin watch (wraps stablecoin_watch)
  - `borg_defi_risk` — portfolio risk check (wraps risk_engine)
  - `borg_defi_whale` — whale scan (wraps whale_tracker, needs API key)
- `borg/defi/cli.py` — CLI subcommands:
  - `borg defi yields [--min-apy N] [--min-tvl N]`
  - `borg defi tokens [--limit N]`
  - `borg defi tvl [--limit N]`
  - `borg defi stablecoins [--depeg-threshold N]`
  - `borg defi scan-all` — run all free scans
- Register in pyproject.toml entry points
- Guard with defi dep check — clear error if aiohttp not installed

**Success Criteria:**
- [ ] MCP tools callable from Hermes agent via tool invocation
- [ ] CLI commands work: `borg defi yields` outputs formatted results
- [ ] `borg defi scan-all` runs all 4 free scans
- [ ] Graceful error when defi deps not installed
- [ ] Each tool has docstring with parameter descriptions
- [ ] Tests verify tool registration and output format

**Verification:**
- Formal: `borg defi yields` returns non-empty output with APY data
- Formal: `borg defi scan-all` completes in <30s
- Informal: Agent can invoke `borg_defi_yields` via MCP and get formatted results

---

### WI-5: Dojo Feedback Loop — Nudges → Strategy Selection

**Problem:** `dojo_bridge.py` generates nudge text but nothing acts on it. The learning loop is one-directional: outcomes are recorded but don't influence future decisions.

**Deliverables:**
- `borg/defi/strategy_selector.py` — class StrategySelector:
  - `get_best_strategy(context: str) -> str` — returns highest-reputation strategy for given context (yield farming, swap routing, LP management)
  - `should_avoid(strategy: str) -> Tuple[bool, str]` — checks if strategy is on cooldown due to recent losses
  - `get_active_nudges() -> List[str]` — returns all unacted nudges
  - `apply_nudge(nudge_id: str)` — mark nudge as applied, adjust strategy weights
  - Reads from dojo_bridge YAML files (strategy metadata, warnings)
  - Weights strategies by: win_rate * 0.4 + sharpe_ratio * 0.3 + recency * 0.2 + collective_score * 0.1
- Wire into swap_executor: before executing, consult strategy_selector for routing preference
- Wire into yield_scanner: rank results influenced by strategy reputation
- Tests with mock YAML data

**Success Criteria:**
- [ ] StrategySelector reads existing dojo YAML files
- [ ] Strategies with <30% win rate auto-avoided with reason
- [ ] Strategies with ≥3 consecutive losses enter cooldown
- [ ] get_best_strategy returns strategies sorted by composite score
- [ ] Nudges from dojo_bridge can be consumed and applied
- [ ] swap_executor checks strategy_selector before routing (when available)
- [ ] Full round-trip test: record bad outcome → generate nudge → selector avoids strategy

**Verification:**
- Formal: Test creates trade outcomes via dojo_bridge, then verifies strategy_selector ranks them correctly
- Formal: Test verifies cooldown: 3 losses → strategy avoided for configured period
- Informal: Code review confirms selector weights match spec

---

### WI-6: E2E Integration Tests Against Real Free APIs

**Problem:** All 603 tests use mocks. We've never verified the actual API response schemas match our parsing code. DeFiLlama could change their JSON structure and we'd never know.

**Deliverables:**
- `borg/defi/tests/test_e2e_live.py` — marked with `@pytest.mark.integration` (skipped by default):
  - `test_defillama_yields_schema` — hit real API, verify response has `data` list, each pool has: project, chain, symbol, apy, tvlUsd
  - `test_defillama_protocols_schema` — verify: name, tvl, chain, change_1d, change_7d
  - `test_defillama_stablecoins_schema` — verify: peggedAssets list, each has: name, symbol, circulating.peggedUSD, price
  - `test_dexscreener_latest_schema` — verify: list of tokens with chainId, tokenAddress
  - `test_jupiter_quote_schema` — GET real quote for SOL→USDC, verify: inAmount, outAmount, routePlan
  - `test_yield_hunter_e2e` — run full yield_hunter(), verify output contains "YIELD HUNTER", has at least 5 results
  - `test_tvl_pulse_e2e` — run tvl_pulse(), verify contains "TVL PULSE", "Total DeFi TVL"
  - `test_stablecoin_watch_e2e` — run stablecoin_watch(), verify contains USDT, USDC
  - `test_token_radar_e2e` — run token_radar(), verify contains "TOKEN RADAR"
- Run with: `pytest -m integration borg/defi/tests/test_e2e_live.py`

**Success Criteria:**
- [ ] All 9+ e2e tests pass against live APIs
- [ ] Response schema validation catches any field renames/removals
- [ ] Tests are idempotent — can run anytime without side effects
- [ ] Tests timeout gracefully (10s per test, not hanging)
- [ ] Skipped by default in normal test runs (only run with -m integration)

**Verification:**
- Formal: `pytest -m integration borg/defi/tests/test_e2e_live.py -v` — all pass
- Formal: Each test asserts specific schema keys exist
- Informal: Run at different times of day to verify API consistency

---

## 3. Non-Goals (This Sprint)

- PyPI publish (blocked on token — user action required)
- Discord H4D bot fix (admin access required)
- Real wallet swap execution (needs funded wallet)
- Arkham/GoPlus/Alchemy API key setup (user config)

---

## 4. Test Matrix

| Module | Current Tests | Target Tests | Coverage Target |
|--------|--------------|-------------|-----------------|
| data_models.py | 0 (indirect) | 20+ | ≥95% |
| api_clients/base.py | 0 (indirect) | 15+ | ≥90% |
| security/keystore.py | 0 (indirect) | 20+ | ≥95% |
| security/tx_guard.py | 0 (indirect) | 15+ | ≥90% |
| swap_executor.py | 39 | 39 (fix warnings) | maintained |
| strategy_selector.py | 0 (new) | 25+ | ≥90% |
| mcp_tools.py | 0 (new) | 10+ | ≥90% |
| cli.py | 0 (new) | 10+ | ≥90% |
| test_e2e_live.py | 0 (new) | 9+ | N/A (integration) |
| **TOTAL** | 603 | ~730+ | — |

---

## 5. Execution Plan

**Batch 1 (parallel, no dependencies):**
- WI-1: Unit tests for 4 modules
- WI-2: Fix AsyncMock warnings
- WI-3: Keystore PBKDF2

**Batch 2 (parallel, depends on batch 1):**
- WI-4: MCP tools + CLI
- WI-5: Strategy selector + feedback loop
- WI-6: E2E integration tests

**Batch 3:**
- Full test suite run
- Coverage report
- Commit + push

---

## 6. Definition of Done

- [ ] All existing 603 tests still pass
- [ ] All new tests pass (target: 730+)
- [ ] 0 pytest warnings (RuntimeWarning, DeprecationWarning)
- [ ] Coverage ≥90% for all modified/new modules
- [ ] E2E tests pass against live APIs
- [ ] MCP tools callable from Hermes
- [ ] CLI `borg defi yields` returns real data
- [ ] Strategy selector influences swap routing
- [ ] Keystore uses PBKDF2 with ≥600k iterations
- [ ] All changes committed and pushed
- [ ] Skill updated with new patterns
