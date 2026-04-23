# Claude CLI onboarding deep review (2026-04-23 15:40 UTC)

## scope
review the onboarding failures hit in live claude cli usage, ship permanent fixes (not workarounds), and define what remains before safe 10/100/1000 distribution.

---

## 1) what failed in the live path (root causes)

### RC1 — `BORG_HOME=~/.borg` is fragile in manual mcp json
- symptom: claude accepted config but borg mcp runtime failed/behaved inconsistently.
- cause: `~` expansion depends on shell launch path; claude mcp spawn path may not expand it.
- impact: nondeterministic onboarding, hard to diagnose.

### RC2 — config could be written before runtime was actually importable
- symptom: user gets “added” state but runtime still fails at tool load (`No module named borg` style class of failures).
- cause: verification was optional and happened after config mutation.
- impact: false-positive onboarding success.

### RC3 — failure messages were not prescriptive enough
- symptom: users/agents loop through retries/manual edits.
- cause: verification failure had generic error output without exact remediation command.
- impact: support overhead + repeated dead-end attempts.

---

## 2) permanent fixes now implemented

## code changes (`borg/cli.py`)

### fix A — verify before config write
`setup-claude` now runs handshake verification before mutating claude config, preventing broken config state.

### fix B — verification default-on
- `--verify` now defaults to enabled.
- `--no-verify` added for explicit bypass only.

### fix C — actionable remediation hints
new helper: `_setup_claude_verify_hints(detail, borg_entry)`
- detects import/runtime class failures (e.g., missing borg module)
- prints exact remediation (`python -m pip install agent-borg` class guidance)
- prints deterministic rerun command: `borg setup-claude --scope user --verify --fix`

### fix D — preserve absolute `BORG_HOME` invariant
existing absolute-path behavior retained and now reinforced in tests/docs.

---

## 3) test coverage added/expanded

file: `borg/tests/test_cli.py`

added:
- `test_setup_claude_verify_enabled_by_default`
- `test_setup_claude_no_verify_skips_handshake`
- `test_setup_claude_verify_failure_shows_install_hint_and_does_not_write_config`
- `test_borg_mcp_entry_writes_absolute_borg_home`

also added fixture to avoid external mcp process spawn in unit tests unless explicitly patched.

---

## 4) docs updated (canonical path + anti-pattern ban)

updated:
- `docs/TRYING_BORG.md`
- `docs/MCP_SETUP.md`
- `docs/ONBOARDING.md`

key doc shifts:
- canonical command standardized: `borg setup-claude --scope user --verify --fix`
- explicit anti-pattern warning against manual `~/.borg` env entries
- explicit note that `--verify` is default-on, `--no-verify` is exceptional
- recommended scope clarified as `user` (`~/.claude.json`)

---

## 5) distribution readiness gates (onboarding-specific)

## gate O1 — deterministic install+setup path
- status: **implemented in code/docs**
- proof target: fresh-machine runbook pass (linux/mac)

## gate O2 — binary pass/fail test suite green
- status: **pending final run evidence in this session**
- required: pytest run output attached to release artifact

## gate O3 — supportability
- status: **improved** (direct remediation output)
- required: first-user transcripts show <1 retry median

## gate O4 — anti-pattern suppression
- status: **documented**
- required: onboarding templates/snippets across docs and bot responses all use canonical command only

---

## 6) remaining work to call onboarding “holy-shit done”

1. run full cli test suite and attach green proof log to docs artifact.
2. run fresh-environment onboarding e2e matrix:
   - pip install path
   - pipx install path
   - `borg-mcp` present / absent
   - mac + linux
3. publish `ONBOARDING_SLO.md` with hard SLOs:
   - p50 time-to-first-borg-tool
   - failure rate by install method
   - retries per user
4. wire CI job that fails if docs drift from canonical command.

---

## verdict right now
onboarding architecture is now materially stronger and closer to deterministic.
**distribution for 10 users is likely viable once O2 evidence is attached.**
100/1000 should wait for fresh-machine matrix + SLO instrumentation, otherwise support debt compounds.
