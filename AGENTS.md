# Borg repo guidance for AI agents

This is the canonical Borg product repo.

- Canonical local path: `/root/hermes-workspace/borg`
- Canonical GitHub repo: `https://github.com/borg-farther/Borg-Directory`
- Package users install: `agent-borg`
- Commands users run: `borg`, `borg-mcp`, `borg-doctor`

## Before editing

1. Confirm you are in this repo and not a legacy/prototype repo:
   `git remote -v` must point to `borg-farther/Borg-Directory`.
2. Read `docs/CANONICAL_REPO.md` before any repo consolidation, cleanup, archival, or migration task.
3. Do not edit `/root/hermes-workspace/guild-v2`, `borg-init`, `borg-collective-v1`, `borg-collective-py`, `guild-packs`, `guild-benchmark`, or `guild-mcp-package` unless the user explicitly asks for that component.

## No-loss rule

Do not delete, archive, privatize, prune branches, run `git clean`, or force-push any Borg/Guild repo until its committed history and working tree have been snapshotted and its unique material is recorded in `docs/repo-manifest/`.

Legacy repos contain unique material: hosted federation, SDK, installer, wiki/extraction/mutation experiments, ARP schemas, benchmark fixtures, and `guild_*` compatibility. Treat them as sources to preserve, not trash.

## Public docs rule

Public first-user docs must point to:

- install package: `agent-borg`
- CLI: `borg`
- MCP server: `borg-mcp`
- repo: `borg-farther/Borg-Directory`

Do not reintroduce stale setup names such as `pip install guild-packs`, `guildpacks`, stale `guild_*` user instructions, `punkrocker/agent-borg`, `bensargotest-sys/agent-borg`, or non-shipped `borgd` daemon instructions in current public setup docs.
