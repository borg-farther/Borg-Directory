# borg readiness verdict (2026-04-23 14:50 utc)

## scope
- onboarding hardening (`borg setup-claude --scope user --verify --fix`)
- regression confidence
- github home cutover hygiene
- distribution gates for 10 / 100 / 1,000 users

## hard evidence captured

### 1) test execution evidence (cron session)
source: `/root/.hermes/sessions/session_cron_4cc61cba4554_20260423_144234.json`

- command: `pytest -q borg/tests/test_cli.py`
- output pattern: `....F.F...........F...F......FF.FFFFFF [100%]`
- inferred result: **12 failed, 26 passed** (38 total), exit code non-zero
- first failing test shown: `test_apply_dispatches_to_apply_handler`

- command: `pytest -q borg/tests/test_search.py`
- result: `53 passed in 8.20s`
- exit code: 0

### 2) ecosystem telemetry evidence
source: `mcp_guild_borg_dashboard` and `mcp_guild_borg_analytics`

- `total_outcomes`: 2
- `success_rate`: 1.0 (but tiny sample)
- `timeseries.executions (30d daily)`: empty
- `timeseries.active_agents (30d daily)`: empty

interpretation: telemetry is currently too sparse to justify claims for 100+ or 1,000+ rollout confidence.

### 3) cutover hygiene edits completed locally
- updated runtime/doc links from legacy owner to new home in key files:
  - `borg/core/pack_taxonomy.py`
  - `borg/core/convert.py`
  - `borg/core/openclaw_converter.py`
  - `openclaw-skill/SKILL.md`
  - `docs/QUICKSTART.md`
  - `docs/TRYING_BORG.md`
- fixed workflow test path drift:
  - `.github/workflows/test.yml` changed `guild/tests/` -> `borg/tests/`

## verdict by rollout tier

### 10 users: **not ready yet**
blocked by failing `test_cli.py` suite (core CLI reliability gate red).

### 100 users: **not ready**
blocked by red tests + insufficient telemetry sample depth.

### 1,000 users: **not ready**
blocked by all above + no demonstrated sustained execution/active-agent time series.

## required closure checklist (must be green)
1. make `pytest -q borg/tests/test_cli.py` green (0 failed).
2. run full regression subset and record artifacts:
   - `pytest -q borg/tests/test_search.py`
   - `pytest -q borg/tests/test_convert_openclaw.py`
3. generate and store one signed proof artifact in docs with command outputs + exit codes.
4. execute github cutover proof with authenticated `gh` and confirm old home visibility = private.
5. rerun telemetry collection until non-empty daily points support stated rollout tier.

## final status
this is improved and materially closer, but not shippable to 10/100/1000 tiers yet under hard-proof standards.
