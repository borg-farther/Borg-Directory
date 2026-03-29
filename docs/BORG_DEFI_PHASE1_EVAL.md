# Borg DeFi Phase 1 — Success Criteria, Evals, Verification

## Eval Philosophy

Every module must be testable WITHOUT real API keys or real money. We use:
1. **Fixture-based unit tests** — mock API responses from saved JSON
2. **Contract tests** — verify API response schemas match expectations
3. **Integration tests** — real API calls (free tier, read-only) gated by env var
4. **Property tests** — invariants that must hold regardless of input
5. **Smoke tests** — end-to-end pipeline with real data

---

## Module 1: API Clients

### Success Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC1 | DeFiLlama client returns valid pool data | Parse response, verify fields: pool, apy, tvl, chain |
| AC2 | DexScreener client returns pair data | Parse response, verify: pairAddress, priceUsd, volume |
| AC3 | Helius client returns transaction data | Parse enhanced tx format, verify: type, fee, accounts |
| AC4 | Birdeye client returns token prices | Parse response, verify: price > 0, timestamp recent |
| AC5 | All clients handle rate limits gracefully | Return RateLimitError, respect retry-after |
| AC6 | All clients handle network errors | Timeout → retry 3x, then raise |
| AC7 | All clients handle malformed JSON | JSONDecodeError caught, logged, None returned |
| AC8 | No API key leakage in logs or errors | Grep all log output for key patterns |

### Eval Tests (24 tests)

```
test_defillama_pools_schema          — mock response → verify dataclass fields
test_defillama_pools_empty           — empty response → empty list, no crash
test_defillama_pools_real            — [INTEGRATION] real API call, verify >1000 pools
test_dexscreener_pairs_schema        — mock response → verify fields
test_dexscreener_search              — mock search → verify results
test_dexscreener_real                — [INTEGRATION] real API, verify SOL pairs exist
test_helius_transactions_schema      — mock response → verify enhanced tx fields
test_helius_rate_limit               — mock 429 → verify retry behavior
test_birdeye_price_schema            — mock response → verify price > 0
test_birdeye_ohlcv_schema            — mock response → verify candle fields
test_client_timeout_retry            — mock timeout → verify 3 retries
test_client_network_error            — mock ConnectionError → verify graceful fail
test_client_malformed_json           — mock bad JSON → verify None return
test_client_no_key_in_logs           — capture logs → grep for API key patterns
test_client_base_url_configurable    — verify URL override works
test_client_session_reuse            — verify aiohttp session created once
```

---

## Module 2: Whale Tracker

### Success Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| WT1 | Detects whale swaps > $50K | Feed mock tx data, verify alert generated |
| WT2 | Filters below threshold | Feed $1K swap, verify NO alert |
| WT3 | Cooldown prevents spam | Same wallet 2x in 1 min → only 1 alert |
| WT4 | Signal scoring works | Whale with history scores higher than unknown |
| WT5 | Telegram format is valid | Output contains emoji, USD amount, explorer link |
| WT6 | Discord format is valid | Output uses discord markdown |
| WT7 | Multi-chain support | ETH + Solana whales both detected |
| WT8 | Wallet labels applied | Known wallet → shows label not just address |
| WT9 | New wallet discovery | Unknown wallet with >$500K move → flagged for tracking |
| WT10 | No PII in alerts | Wallet addresses truncated in collective sharing |

### Eval Tests (20 tests)

```
test_whale_alert_dataclass           — verify all fields populated
test_whale_swap_above_threshold      — $100K swap → alert generated
test_whale_swap_below_threshold      — $1K swap → no alert
test_whale_transfer_detected         — large transfer → alert
test_whale_cooldown_enforced         — 2 alerts same wallet < 5min → 1 emitted
test_whale_cooldown_expired          — 2 alerts same wallet > 5min → 2 emitted
test_whale_signal_scoring_known      — whale with 70% win rate → score > 0.7
test_whale_signal_scoring_unknown    — new wallet → score = 0.5 (neutral)
test_whale_telegram_format           — verify emoji, amount, link present
test_whale_discord_format            — verify markdown formatting
test_whale_solana_parsing            — mock Helius tx → correct WhaleAlert
test_whale_evm_parsing               — mock Alchemy tx → correct WhaleAlert
test_whale_label_applied             — known address → label shown
test_whale_label_unknown             — unknown address → truncated address
test_whale_discovery_large_move      — unknown + $500K → flagged
test_whale_no_pii_in_collective      — shared alert has hashed wallet
test_whale_multi_chain_scan          — scan both chains → combined results
test_whale_empty_response            — no txs → empty list, no crash
test_whale_concurrent_scan           — parallel scans don't interfere
test_whale_cron_integration          — simulate cron trigger → alerts generated
```

---

## Module 3: Yield Scanner

### Success Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| YS1 | Returns valid yield opportunities | DeFiLlama data → YieldOpportunity dataclass |
| YS2 | Filters by min TVL | Set min 1M → no pools below 1M |
| YS3 | Filters by max risk | Set max 0.5 → no high-risk pools |
| YS4 | Ranks by risk-adjusted yield | Higher APY + lower risk = higher rank |
| YS5 | Detects yield changes | Yesterday 10%, today 50% → alert |
| YS6 | Detects yield drops | Yesterday 30%, today 5% → warning |
| YS7 | Chain filtering works | Filter Solana only → no EVM results |
| YS8 | Stablecoin filtering | Filter stablecoin pools → only USDC/USDT/DAI |
| YS9 | IL risk flagged | LP pools flagged, single-asset pools not |
| YS10 | Telegram format valid | Contains APY, TVL, risk, protocol link |

### Eval Tests (18 tests)

```
test_yield_opportunity_dataclass     — verify all fields
test_yield_scan_defillama            — mock response → valid opportunities
test_yield_filter_min_tvl            — filter 1M → only large pools
test_yield_filter_max_risk           — filter 0.5 → only safe pools
test_yield_filter_chain              — filter solana → no EVM
test_yield_filter_stablecoin         — filter stable → USDC/USDT only
test_yield_ranking                   — verify rank order correct
test_yield_risk_adjusted_score       — verify score formula
test_yield_change_detection_spike    — 5x APY increase → alert
test_yield_change_detection_drop     — 80% APY drop → warning
test_yield_il_risk_flagging          — LP pool → il_risk=True
test_yield_single_asset_no_il        — lending pool → il_risk=False
test_yield_telegram_format           — verify formatting
test_yield_empty_response            — no pools → empty list
test_yield_dedup                     — same pool 2x → 1 result
test_yield_historical_comparison     — compare current vs previous scan
test_yield_cron_integration          — simulate hourly scan
test_yield_real_defillama            — [INTEGRATION] real API call
```

---

## Module 4: Portfolio Monitor

### Success Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| PM1 | Returns all token holdings | Mock wallet → all tokens listed |
| PM2 | Calculates PnL correctly | Entry $100, current $120 → +$20, +20% |
| PM3 | Risk: concentration alert | Single token >30% → warning |
| PM4 | Risk: health factor alert | Lending position HF<1.5 → critical |
| PM5 | Risk: drawdown alert | Position down >20% → warning |
| PM6 | Daily report format | Contains total value, top positions, alerts |
| PM7 | Multi-chain aggregation | Solana + ETH positions combined |
| PM8 | Historical tracking | Store daily snapshots for trend |

### Eval Tests (16 tests)

```
test_position_dataclass              — verify all fields
test_portfolio_solana                — mock Helius → positions listed
test_portfolio_evm                   — mock Alchemy → positions listed
test_pnl_calculation_profit          — +20% → correct PnL
test_pnl_calculation_loss            — -15% → correct PnL
test_pnl_calculation_zero            — flat → $0 PnL
test_risk_concentration              — 40% in SOL → warning
test_risk_health_factor              — HF 1.2 → critical alert
test_risk_drawdown                   — -25% → warning
test_risk_no_alert                   — balanced portfolio → no warnings
test_daily_report_format             — verify sections present
test_multi_chain_aggregation         — SOL + ETH → combined total
test_historical_snapshot             — save + load → data preserved
test_empty_wallet                    — no tokens → empty portfolio, no crash
test_unknown_token                   — unpriced token → excluded from total
test_portfolio_cron_integration      — simulate daily report
```

---

## Module 5: Security Layer

### Success Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| SEC1 | Keystore encrypts with AES-256 | Encrypted file unreadable without password |
| SEC2 | Keys never in plaintext logs | Grep all log output |
| SEC3 | Spending limit enforced | Over limit → TransactionBlocked error |
| SEC4 | Daily limit tracked | Multiple trades → cumulative check |
| SEC5 | Contract whitelist works | Unknown contract → rejected |
| SEC6 | Rug detection catches honeypots | Known honeypot patterns → blocked |

### Eval Tests (12 tests)

```
test_keystore_encrypt_decrypt        — roundtrip key storage
test_keystore_wrong_password         — wrong password → DecryptionError
test_keystore_no_plaintext_log       — capture logs → no key material
test_spending_limit_under            — $50 trade, $100 limit → allowed
test_spending_limit_over             — $150 trade, $100 limit → blocked
test_spending_limit_daily            — cumulative check
test_spending_limit_reset            — new day → reset
test_contract_whitelist_allowed      — Jupiter router → allowed
test_contract_whitelist_blocked      — random contract → blocked
test_rug_check_honeypot              — mock honeypot → blocked
test_rug_check_normal_token          — normal token → allowed
test_human_approval_threshold        — >$1000 → requires approval
```

---

## TOTAL: 90 eval tests across 5 modules

## Verification Pipeline

```
# 1. Unit tests (no API keys needed)
pytest borg/defi/tests/ -m "not integration" --tb=short

# 2. Integration tests (needs API keys, read-only)
BORG_DEFI_INTEGRATION=true pytest borg/defi/tests/ -m integration --tb=short

# 3. Smoke test (full pipeline with mock data)
python -m borg.defi.smoke_test

# 4. Security audit
grep -r "api_key\|secret\|password\|private_key" borg/defi/ --include="*.py" | grep -v "test_\|\.pyc\|__pycache__"
```
