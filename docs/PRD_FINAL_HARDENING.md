# PRD: Final Hardening — Benchmark, Lean Skills, Circuit Breaker, V2 Brief

**Status:** APPROVED FOR BUILD
**Date:** 2026-03-30
**Basis:** Honest assessment of gaps after 1,123 tests and ~40K LOC

---

## Problem Statement

We have a large, well-tested codebase but zero evidence borg helps agents make better decisions. We have 200-line YAML packs that no agent will fully parse. We have a circuit breaker in the README but not in the code. We have paused cron jobs with no replacement.

---

## WI-1: Benchmark Suite — Does Borg Actually Help?

**Problem:** Zero quantitative evidence borg improves agent outcomes.

**Deliverables:**
- `borg/benchmarks/` directory
- `borg/benchmarks/tasks.py` — 10 realistic tasks spanning:
  - 3 coding/debugging tasks (Docker networking, API auth, database migration)
  - 3 DeFi tasks (yield selection, rug detection, portfolio allocation)
  - 2 ops tasks (deploy config, monitoring setup)
  - 2 research tasks (API comparison, architecture decision)
- `borg/benchmarks/runner.py` — BenchmarkRunner class:
  - `run_without_borg(task) -> TaskResult` — agent solves with no borg access
  - `run_with_borg(task) -> TaskResult` — agent solves with borg packs loaded
  - `compare(baseline, treatment) -> BenchmarkReport`
  - TaskResult: success (bool), time_seconds, quality_score (0-10), approach_taken
- `borg/benchmarks/scorer.py` — score task outputs:
  - Did it solve the problem? (binary)
  - How long? (seconds)
  - Quality: did it follow best practices? (rubric per task)
  - Did it avoid known anti-patterns? (from borg packs)
- `borg/benchmarks/report.py` — generate markdown report:
  - Per-task comparison table
  - Aggregate: success rate delta, time delta, quality delta
  - Statistical significance (paired t-test if n >= 10)

**Success Criteria:**
- [ ] 10 tasks defined with clear rubrics
- [ ] Runner executes both modes (simulated — mock agent responses)
- [ ] Report shows delta between with/without borg
- [ ] Tests verify runner, scorer, and report generation
- [ ] Honest result: if borg doesn't help, the benchmark shows it

**Verification:**
- `python -m pytest borg/benchmarks/tests/ -v` — all pass
- `python -m borg.benchmarks.runner --report` — generates comparison report

---

## WI-2: Lean Skill Rewrite — 5 Core Skills

**Problem:** Current packs are too long. Claude reads the first line and skims. Need: trigger (1 line), principles (not steps), example output, one edge case.

**Format per skill:**
```yaml
---
name: skill-name
description: ONE LINE that tells Claude WHEN to fire this skill
---

# Skill Name

## Principles
1. [WHY not WHAT — reasoning helps Claude generalise]
2. [Max 5 principles]

## Output Format
[Exactly what the output should look like — fields, sections, structure]

## Example
[One complete input→output example Claude can pattern-match]

## Edge Cases
- Normal: [what the typical case looks like]
- Edge: [the tricky case that trips agents up]
- Mess: [what bad input looks like, what to do]

## Recovery
[If it goes wrong, do THIS]
```

**Deliverables:**
- Rewrite 5 skills in `~/.hermes/skills/`:
  1. `systematic-debugging` — trigger: "agent is stuck on a bug"
  2. `code-review` — trigger: "reviewing code changes"
  3. `test-driven-development` — trigger: "implementing a feature"
  4. `defi-yield-strategy` — trigger: "choosing a yield strategy"
  5. `defi-risk-check` — trigger: "before executing a DeFi trade"
- Each under 50 lines (body, excluding frontmatter)
- Each has example output and edge case

**Success Criteria:**
- [ ] Each skill < 50 lines body
- [ ] First line of description is a clear trigger condition
- [ ] Principles, not steps
- [ ] One complete example per skill
- [ ] Edge cases documented
- [ ] Tested: agent with lean skill solves task faster than agent with verbose pack (benchmark WI-1)

---

## WI-3: Circuit Breaker — Safety for Real Users

**Problem:** README says "2 consecutive losses disables pack" but the code doesn't enforce this.

**Deliverables:**
- `borg/defi/v2/circuit_breaker.py` — class CircuitBreaker:
  - `check_before_recommend(pack) -> Tuple[bool, Optional[str]]`
    Returns (allowed, reason). Blocked if:
    - 2+ consecutive losses on this pack
    - Pack reputation < 0.3 with >= 4 outcomes
    - Active warning exists
    - Any single loss > 20% of position
  - `record_outcome(pack_id, profitable, loss_pct) -> Optional[str]`
    Returns warning message if circuit breaker trips
  - `get_tripped_packs() -> List[str]`
  - `reset(pack_id)` — manual reset by trusted agent
  - Persistence: `~/.hermes/borg/defi/circuit_breaker.json`
- Wire into `recommender.py` — recommend() calls check_before_recommend()
- Wire into `record_outcome()` — auto-check after every outcome
- Telegram alert on every trip via delivery.py

**Success Criteria:**
- [ ] 2 consecutive losses → pack excluded from recommendations
- [ ] Single >20% loss → immediate pack suspension
- [ ] Tripped state persists across restarts (JSON file)
- [ ] Manual reset requires trusted tier agent
- [ ] Alert sent on every trip
- [ ] Tests cover: trip, persist, reload, reset, edge cases
- [ ] Existing V2 tests still pass

---

## WI-4: V2 Daily Brief — Replace Paused Crons

**Problem:** 4 V1 data firehose crons paused. User gets nothing. Need portfolio-first daily brief.

**Deliverables:**
- `borg/defi/v2/daily_brief.py` — async function generate_daily_brief(config_path) -> str:
  - Reads user config (wallets, risk tolerance, preferences)
  - Section 1: "Your Portfolio" — wallet balances via free APIs (or "connect wallets to enable")
  - Section 2: "Borg Recommends" — top 3 recommendations from V2 recommender for idle capital
  - Section 3: "Active Warnings" — any collective warnings relevant to user's chains/tokens
  - Section 4: "Market Pulse" — 3-line summary (total DeFi TVL, biggest mover, stablecoin status)
  - Section 5: "Collective Stats" — how many outcomes recorded, packs active, confidence levels
  - Entire message < 2000 chars (Telegram friendly, no chunking needed)
- `borg/defi/v2/alert_engine.py` — real-time alerts (only fires when something matters):
  - depeg > 0.5%
  - circuit breaker trip
  - new collective warning
  - position approaching recommended exit time
- One cron job: daily brief at user's configured time
- One cron job: alert engine every 15 min (only sends if there's something to say)
- Tests with mocked data

**Success Criteria:**
- [ ] Daily brief < 2000 chars
- [ ] Brief works with zero wallet config ("connect wallets to enable portfolio tracking")
- [ ] Brief includes V2 recommendations with collective evidence
- [ ] Alert engine is silent when nothing notable (no spam)
- [ ] Alert fires immediately on depeg or circuit breaker trip
- [ ] Cron jobs registered and delivering to Telegram
- [ ] Tests cover: full brief, empty portfolio, warnings present, alert triggers

---

## WI-5: Publish v2.5.2

**Deliverables:**
- Bump version to 2.5.2
- Build and upload to PyPI
- Fresh venv E2E verification (extend test_e2e_pypi.py)

---

## Execution Plan

**Batch 1 (parallel, no deps):**
- WI-1: Benchmark suite
- WI-2: Lean skill rewrite
- WI-3: Circuit breaker

**Batch 2 (depends on WI-3):**
- WI-4: Daily brief + alert engine + cron jobs

**Batch 3:**
- WI-5: Publish v2.5.2
- Full test suite
- Run benchmark, report results honestly

---

## Test Targets

| Work Item | New Tests | Total After |
|-----------|----------|-------------|
| WI-1 Benchmark | 25+ | — |
| WI-2 Lean Skills | 5 (one per skill, validates format) | — |
| WI-3 Circuit Breaker | 20+ | — |
| WI-4 Daily Brief | 15+ | — |
| **Total** | **65+** | **~1,190+** |

---

## Definition of Done

- [ ] Benchmark proves (or disproves) borg helps agents
- [ ] 5 lean skills under 50 lines each, with examples
- [ ] Circuit breaker wired and enforced in recommender
- [ ] Daily brief delivering to Telegram
- [ ] Alert engine only fires when something matters
- [ ] v2.5.2 on PyPI, E2E verified
- [ ] All tests passing
- [ ] Benchmark report committed to docs/
