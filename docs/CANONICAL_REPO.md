# Borg canonical repo and no-loss policy

Rev: `20260518-1427`
Canonical public repo: `https://github.com/borg-farther/Borg-Directory`
Canonical local working tree: `/root/hermes-workspace/borg`
Install package: `agent-borg`
CLI: `borg`
MCP server command: `borg-mcp`

## Decision

`borg-farther/Borg-Directory` is the only active public product repo for Borg's local AI-agent memory package.

This does **not** mean the older Borg/Guild repos are worthless or safe to delete. They contain separate experiments, services, installers, schemas, benchmark fixtures, and unpublished local work. Treat them as **legacy/prototype/source-history repositories** until their unique material is either migrated, deliberately archived, or deliberately kept as a separate component.

## Non-destructive rule

Before any repo is deleted, archived, privatized, branch-pruned, force-pushed, or cleaned:

1. capture a git bundle for committed history;
2. capture a working-tree snapshot for uncommitted/untracked source files;
3. record the repo in `docs/repo-manifest/`;
4. decide whether each unique asset is migrated, kept as a separate repo, or archived read-only;
5. verify the canonical `agent-borg` package still builds, installs, and exposes `borg` plus `borg-mcp`.

Do **not** use `git clean`, branch pruning, destructive GitHub settings, or repo deletion as a first step.

## Same-run preservation snapshot

A local operator snapshot was created before this policy change:

`/root/hermes-workspace/borg-no-loss-snapshots/20260518-1427/`

It contains, where applicable:

- `*.git.bundle` — committed history from each inspected git repo;
- `*.working-tree.no-git.tar.gz` — source working-tree snapshot excluding `.git`, build caches, virtualenvs, node_modules, common secret files, and generated caches;
- `*.tracked-files.txt`, `*.untracked-files.txt`, `*.status-porcelain.txt`, `*.diffstat.txt`;
- `SHA256SUMS.txt`.

This snapshot is local/operator evidence, not a public release artifact.

## Repository map

### Keep as canonical product repo

- `borg-farther/Borg-Directory`
  - Local path: `/root/hermes-workspace/borg`
  - Role: public package/docs/tests for `agent-borg`.
  - Owns: `borg`, `borg-mcp`, `borg-doctor`, local MCP tools, current README/install/setup docs, CI/security gates.

### Public adjunct, not canonical

- `borg-farther/borg-init`
  - Local path: `/root/hermes-workspace/borg-init`
  - Role: NPM/NPX onboarding installer prototype for hosted Borg Collective.
  - Public surface status: README/package metadata now identifies this as an installer adjunct and points users to `borg-farther/Borg-Directory` as canonical.
  - Unique material: multi-client config detection/wiring for Claude Desktop, Claude Code, Cursor, Cline, Continue; atomic JSON config merge; `~/.borg/config.toml` bootstrap; hosted federation registration flow.
  - Preserve/decide: keep as installer adjunct or import under canonical `packages/`; do not treat it as replacement for `agent-borg`.

### Private service / SDK prototypes, not superseded by canonical

- `borg-farther/borg-collective-v1`
  - Local path: `/root/hermes-workspace/borg-collective-v1`
  - Role: Cloudflare Worker + D1 hosted failure-trace federation registry.
  - Unique material: hosted REST API, D1 migrations, feedback funnel, hybrid search, metrics/status endpoints, public trace views, MCP discovery/card endpoints, transfer route, Worker security/rate-limit/auth code.
  - Preservation warning: local worktree has modified and untracked files; do not archive from GitHub HEAD alone.

- `borg-farther/borg-collective-py`
  - Local path: `/root/hermes-workspace/borg-collective-py`
  - Role: Python SDK/CLI/MCP client for the hosted federation.
  - Unique material: sync/async clients, `borg-collective` CLI, hosted-federation MCP server, offline queue, redaction, Ed25519 signing, transport retries, integration docs, closure tests, outreach/friction journals.
  - Preservation warning: local worktree has modified/untracked files and branch-local commits; do not archive from GitHub HEAD alone.

### Legacy codebase / old runtime line with unique experiments

- `guild-v2` / old `guild-tools`
  - Local path: `/root/hermes-workspace/guild-v2`
  - Role: older Borg/Guild runtime predecessor.
  - Unique material found by audit:
    - `borg/wiki/` knowledge layer;
    - `borg/extraction.py` / extraction pipeline;
    - `borg/mutation/` with `PackMutator`, `MutationPlan`, adapters, validators;
    - `borg/meta_mcp/` Harbor-style BorgAgent/hillclimber;
    - old MCP tools such as `borg_extract` and `borg_wiki`;
    - wiki/mutation/meta-MCP tests and docs.
  - Preservation warning: canonical `borg/core/mutation_engine.py` is **not** a lossless replacement for the old `borg/mutation/` package.

### Legacy registry and benchmark assets

- `guild-packs`
  - Local path: `/root/hermes-workspace/guild-packs`
  - Role: original machine-readable workflow pack registry.
  - Unique material: `packs/*.yaml`, `patterns/*.arp.yaml`, schema v2 files, `index.json`, provenance/sybil scripts, old validation scripts.
  - Preservation warning: OpenClaw markdown examples are **not** lossless replacements for the YAML registry and ARP schemas.

- `guild-benchmark`
  - Local path: `/root/hermes-workspace/guild-benchmark`
  - Role: A/B benchmark harness and executable broken-project fixtures.
  - Unique material: challenge source trees, `verify.sh` scripts, `runner.py`, `run_benchmark.py`, `analyze.py`, metrics contract tests.
  - Preserve/decide: migrate executable challenge fixtures into canonical eval assets or keep as private benchmark repo.

- `guild-mcp-package`
  - Local path: `/root/hermes-workspace/guild-mcp-package`
  - Role: standalone legacy `guild_*` MCP package.
  - Unique material: old `guild_*` tool-name compatibility and a simple stdio `GuildMCPClient`.
  - Preservation warning: not a git repo; snapshot local tree before any cleanup.

## Public confusion fixes

Current public user path must say:

- install package: `agent-borg`;
- command: `borg`;
- MCP server: `borg-mcp`;
- canonical repo: `borg-farther/Borg-Directory`;
- do not install unrelated `borg` / `borgbackup` packages.

Public docs and shipped seed skills must not point users at stale public homes such as `punkrocker/agent-borg` or `<OLD_ACCT>/agent-borg`, and must not advertise non-shipped daemons such as `borgd` unless that daemon exists in the package.

## Guardrails for AI agents

When asked to work on Borg:

1. edit `/root/hermes-workspace/borg` by default;
2. verify `git remote -v` points at `borg-farther/Borg-Directory` before committing;
3. do not edit legacy/prototype repos unless the user explicitly asks for that component;
4. if a legacy repo appears relevant, preserve or document the unique material first;
5. never assume old Guild naming (`guild-packs`, `guildpacks`, `guild_*`) is current first-user setup;
6. run the package/docs/security gates before declaring a public-facing change complete.

## Remaining operator-gated choices

These are **not** automatically done by this policy:

- whether `borg-init` stays public as an installer adjunct, becomes private, or is imported into the canonical repo;
- whether hosted federation service repos become public products later;
- whether old private Guild repos are archived read-only;
- whether branch protection/rulesets are enabled on GitHub `main`;
- whether historical/stale docs are further archived or bannered.

Until those are explicitly decided, the safe state is: **one canonical public product repo, no destructive cleanup of the others.**
