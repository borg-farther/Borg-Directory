# Borg public GitHub presentation audit

> Historical/internal — not current product documentation. Superseded by current readiness gates and release snapshots.

Rev: 2026-05-22

## Verdict

**Ready for controlled first-10 beta presentation.**

The public GitHub path now says what Borg is in one screen, shows the first value command, names the exact install package, distinguishes Borg from BorgBackup, and keeps public self-serve / lift claims blocked until real first-10 evidence exists.

## What a first-time evaluator should understand

1. Borg is failure memory for AI coding agents, not a generic backup tool or vague “AI knowledge base.”
2. The first useful command is:

   ```bash
   pipx install agent-borg
   borg rescue "ModuleNotFoundError: No module named flask"
   ```

3. Useful output must contain `ACTION`, `STOP`, `VERIFY`, and confidence/no-match language.
4. The package is `agent-borg`; the installed CLI is `borg`; the MCP server command is `borg-mcp`.
5. Public launch is not claimed yet. Current public claim is controlled first-10 beta readiness.

## What was fixed in this pass

- Reworked the README opening around a concrete 60-second rescue path instead of broad marketing language.
- Converted internal/status docs to current `agent-borg==3.3.10` reality: PyPI is live and fresh-install/stdin MCP canary passes.
- Replaced stale roadmap language from the old `guild-packs` / `guildpacks` era.
- Moved stale demo docs out of the live docs surface into `docs/archive/stale-public/`.
- Added regression tests that prevent reintroducing unsupported external-lift claims, stale PyPI blockers, and first-screen README ambiguity.
- Marked synthetic benchmark docs as scaffold only, not external efficacy proof.
- Updated packaged Borg skill examples and seed skill copy so they do not claim unsupported “thousands of sessions” proof.

## Current evidence

- PyPI latest: `agent-borg==3.3.10` after the docs-only patch release.
- Fresh PyPI install canary: PASS.
- MCP stdio canary: PASS, `serverInfo.version == 3.3.10` after the docs-only patch release.
- Public docs claim guard: PASS.
- Security policy gate: PASS.
- Full sanitized pytest run: PASS.
- Public self-serve gate: expected NO-GO, blocked only by first-10 external-user evidence.

## Remaining honest blockers

- `eval/first_10_user_scoreboard.json` still has zero verified external users.
- Public self-serve needs 10 consented external users, at least 8 successful installs, at least 6 useful rescue moments, and 0 critical privacy/security incidents.
- Served remote MCP remains a separate runtime-cutover channel; local PyPI/stdin MCP proof does not prove the served gateway runtime.

## Standard going forward

Do not let Borg look like AI slop:

- first screen must show real value, not vague “collective intelligence” copy;
- no fake adoption or unsupported lift numbers;
- every public claim needs a gate or evidence file;
- every stale release blocker must be either removed or explicitly archived;
- public self-serve stays blocked until real-user evidence says otherwise.
