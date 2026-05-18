# CLAUDE.md

This file is for Claude Code instances working in this repo. The full
contributor contract lives in AGENTS.md — read that first.

This file only adds Claude-Code-specific notes that aren't in AGENTS.md.

## Identity

Commits must be authored as borg-farther <admin@borg.directory>.
A pre-commit hook enforces this. Install it once after cloning:

    bash scripts/install-hooks.sh

Do not bypass the hook with `--no-verify`. If the hook rejects your
commit, fix your git config — don't go around it.

## Runtime facts not in AGENTS.md

- borg.core.uri.DEFAULT_REPO points at bensargotest-sys/guild-packs,
  which is LIVE RUNTIME. Do not rename or repoint without a coordinated
  migration.
- The Hermes gateway on the dev VPS runs as a system systemd service
  (not --user). Restart with sudo systemctl restart hermes-gateway.
- Canonical working tree on the dev VPS: /root/hermes-workspace/borg.
  Traces DB: ~/.borg/traces.db.

## When in doubt

Read AGENTS.md. If something there is wrong or missing, fix AGENTS.md
in the same PR — don't add competing guidance here.
