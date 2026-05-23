# CLAUDE.md

This file is for Claude Code instances working in this repo. The full
contributor contract lives in AGENTS.md — read that first.

This file only adds Claude-Code-specific notes that aren't in AGENTS.md.

## Identity

Borg is failure memory for AI coding agents. Users install `agent-borg` and run `borg`, `borg-mcp`, and `borg-doctor` from the canonical repo `borg-farther/Borg-Directory`. Current public boundary: first-10 controlled beta; do not claim public self-serve launch until row-derived external-user evidence passes.

Commits must be authored as borg-farther <admin@borg.directory>.
A pre-commit hook enforces this. Install it once after cloning:

    bash scripts/install-hooks.sh

Do not bypass the hook with `--no-verify`. If the hook rejects your
commit, fix your git config — don't go around it.

## Runtime facts not in AGENTS.md

- borg.core.uri.DEFAULT_REPO points at borg-farther/Borg-Directory,
  which is LIVE RUNTIME. Do not rename or repoint without a coordinated
  migration.
- The Hermes gateway on the dev VPS is operator-managed. Do not restart,
  kill, signal, or reload it from Claude Code. If served MCP proof is needed,
  write the fingerprint/canary commands and wait for an operator-approved
  reload window.
- Canonical working tree on the dev VPS: /root/hermes-workspace/borg.
  Traces DB: ~/.borg/traces.db.

## When in doubt

Read AGENTS.md. If something there is wrong or missing, fix AGENTS.md
in the same PR — don't add competing guidance here.
