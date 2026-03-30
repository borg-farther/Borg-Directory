# DeFi Module Coverage Report

Generated: 2026-03-30

## Summary

| Module | Statements | Missing | Coverage |
|--------|-----------|---------|----------|
| `borg.defi.data_models` | 182 | 5 | 97% |
| `borg.defi.api_clients.base` | 105 | 52 | 50% |
| `borg.defi.security.keystore` | 216 | 41 | 81% |
| `borg.defi.security.tx_guard` | 178 | 67 | 62% |
| **Subtotal (newly-tested)** | **681** | **165** | **76%** |

| Module | Statements | Missing | Coverage |
|--------|-----------|---------|----------|
| `borg.defi.strategy_selector` | 273 | 68 | 75% |
| `borg.defi.mcp_tools` | 31 | 2 | 94% |
| `borg.defi.cli` | 69 | 26 | 62% |
| **Subtotal** | **373** | **96** | **74%** |

---

## Module Details

### borg.defi.data_models (97%)

**File:** `borg/defi/data_models.py`

Data classes covered: `WhaleAlert`, `YieldOpportunity`, `Position`, `DeFiPackMetadata`, `TokenPrice`, `OHLCV`, `Transaction`, `DexPair`

Missing lines: 177-181 (5 lines)

### borg.defi.api_clients.base (50%)

**File:** `borg/defi/api_clients/base.py`

Base API client with retry logic, rate limiting, and error handling.

Missing lines: 125-192 (68 lines) —这部分未被测试覆盖

### borg.defi.security.keystore (81%)

**File:** `borg/defi/security/keystore.py`

Key management, signing, and wallet security features.

Missing lines: 24-25, 30-31, 91-92, 108-115, 166-169, 180-183, 189-192, 198-201, 273-274, 318-320, 365, 377-378, 418-422, 470, 507, 514-516

### borg.defi.security.tx_guard (62%)

**File:** `borg/defi/security/tx_guard.py`

Transaction validation, guardrails, and safety checks.

Missing lines: 136-138, 142-143, 239-241, 285-344, 424-430, 435, 519, 530-543, 564-578

### borg.defi.strategy_selector (75%)

**File:** `borg/defi/strategy_selector.py`

Missing lines: 140-141, 150-151, 178-179, 201-210, 307, 354-364, 472, 494-496, 528-564, 644-647, 668-698, 702

### borg.defi.mcp_tools (94%)

**File:** `borg/defi/mcp_tools.py`

Missing lines: 26-27

### borg.defi.cli (62%)

**File:** `borg/defi/cli.py`

Missing lines: 24-25, 30-31, 36-43, 48-51, 56-59, 64-70, 75-78, 157, 161

---

## Test Execution Notes

- All 155 DeFi unit tests pass with no RuntimeWarnings
- All 39 swap_executor tests pass (no RuntimeWarnings — prior fix successful)
- Core borg tests: **1 failure** (`test_collect_text_fields_includes_context_prompts`) — pre-existing, unrelated to DeFi modules

## RuntimeWarning Status

**FIXED** — No RuntimeWarnings in `test_swap_executor.py`. All 39 tests pass under `pytest -W error::RuntimeWarning`.
