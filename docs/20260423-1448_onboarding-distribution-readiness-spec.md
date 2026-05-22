> **Historical/internal — not current product documentation.**
> Current public docs start at [the root README](https://github.com/borg-farther/Borg-Directory/blob/main/README.md) and [docs index](https://github.com/borg-farther/Borg-Directory/blob/main/docs/README.md). Do not treat old commands, credentials, metrics, version numbers, repo names, or launch claims in this file as current.

# 2026-04-23 14:48 UTC — Borg onboarding + distribution readiness spec

## mission
make onboarding + first-use production-grade with one human command:

```bash
borg setup-claude --scope user --verify --fix
```

and establish binary go/no-go gates for staged distribution: 10 -> 100 -> 1,000 users.

---

## adversarial multi-team synthesis (red / blue / green)

### red team (failure/security)
- onboarding fails silently when MCP command wiring is wrong (`borg-mcp` with `-m` args bug).
- config paths are fragmented (`~/.config/claude/...` vs `~/.claude.json`) causing user confusion.
- `BORG_HOME` often missing or using `~`, which some clients do not expand.
- no deterministic runtime proof that MCP server actually initializes.
- risky overwrites of user config without backup.

### blue team (usability/reliability)
- one command must complete setup + remediation + verification.
- output must state exactly what changed and where.
- behavior must be idempotent.
- preserve unrelated MCP servers.

### green team (cost/ops/scale)
- defaults should avoid expensive support loops and repeated manual setup.
- staged rollout must be blocked by hard evidence, not optimism.
- telemetry/quality signal volume currently insufficient for 100+ user confidence.

---

## implemented in this change

1. **new setup scopes**
   - `--scope user` -> `~/.claude.json`
   - `--scope project` -> `./.mcp.json`
   - `--scope desktop` -> `~/.config/claude/claude_desktop_config.json` (legacy compatibility)

2. **one-command remediation**
   - `--fix` creates `BORG_HOME` when absent.

3. **runtime verification gate**
   - `--verify` performs MCP initialize handshake and returns PASS/FAIL.

4. **command resolution fixed**
   - if `borg-mcp` exists: use direct command with empty args.
   - otherwise fallback to `python -m borg.integrations.mcp_server`.

5. **config safety**
   - backup file created before overwriting existing config (`*.bak`).
   - merge semantics preserve non-borg MCP servers.

6. **side-effect containment**
   - `CLAUDE.md` project mutations only for `project`/`desktop` scopes.
   - `user` scope avoids editing repo files.

7. **docs updated**
   - README and QUICKSTART now document one-command onboarding and scope behavior.
   - added `docs/ONBOARDING.md` as deterministic runbook.

---

## hard rollout gates (distribution)

### gate set A — onboarding quality (must pass before 10 users)
- A1: >= 95% successful setup runs on clean environments (linux/mac baseline).
- A2: >= 95% successful verify handshake on first run.
- A3: median time-to-first-working-tools <= 5 minutes.
- A4: zero destructive config overwrite incidents.

### gate set B — product readiness (must pass before 100 users)
- B1: observed 14-day success rate >= 90% for real sessions.
- B2: top 10 failure modes documented + auto-remediated or actionable.
- B3: oncall/playbook + rollback documented and tested.
- B4: telemetry pipeline stable with daily reconciliation.

### gate set C — scale readiness (must pass before 1,000 users)
- C1: sustained active agents and executions trend data exists (not empty series).
- C2: statistically meaningful quality score distribution by pack and task type.
- C3: trust/reputation and abuse controls validated under load.
- C4: release governance supports incident response under multi-tenant churn.

---

## current evidence snapshot (from local dashboard/analytics)
- total outcomes: 2
- success rate: 100% (sample size too small)
- executions timeseries: empty
- active agents timeseries: empty

**verdict:** not ready for 100 or 1,000-user distribution. can proceed to controlled 10-user pilot only after A-gates are proven with real onboarding telemetry.

---

## github home cutover / old-home privatization checklist

precondition: local git remote already points to new home (`borg-farther/Borg-Directory`).

1. ensure CI/CD and package publishing point only to new home.
2. verify docs badges/links all target new home.
3. lock old home:
   - archive old repo or set private
   - add final README redirect if kept public briefly
4. enforce branch protections + CODEOWNERS on new home.
5. run migration proof script and keep artifact in `docs/` and `eval/`.

go/no-go for old-home privatization:
- no required automation references old remote
- no production webhook points to old remote
- all public docs point to new home

---

## test plan for this change

- unit tests added/updated in `borg/tests/test_cli.py` for:
  - user scope path behavior
  - preflight failure without `--fix`
  - verify handshake invocation
  - `borg-mcp` command arg correctness
- regression target: existing setup-claude and setup-cursor test paths.

(see session output for latest run status.)
