# Borg repo guidance for AI agents

This is the canonical Borg product repo. Borg is failure memory for AI coding agents.

- Canonical local path: `/root/hermes-workspace/borg`
- Canonical GitHub repo: `https://github.com/borg-farther/Borg-Directory`
- Package users install: `agent-borg`
- Commands users run: `borg`, `borg-mcp`, `borg-doctor`
- Day-one value path: `pipx install agent-borg` then `borg rescue "<real error>" --short`.
- Current rollout boundary: GitHub exact-SHA source install is canary-green for local CLI/API/stdio MCP/generated-rules/OpenClaw at the proven PR head. Published PyPI `agent-borg==3.3.18` is not package-current for this source line and its full package canary is red because the immutable package still fails clean-install OpenClaw registry conversion; a new immutable release is required. Controlled first-10 beta remains **NO-GO** until package proof, served-runtime freshness, ops/watchdog/proof-dashboard gates, and first-10 external-user evidence are green. GitHub `main` release governance is enforced. Do not claim public self-serve, 100-user rollout, served remote MCP, or measured external lift until row-derived external-user evidence passes.

## Before editing

1. Confirm you are in this repo and not a legacy/prototype repo:
   `git remote -v` must point to `borg-farther/Borg-Directory`.
2. Read `docs/CANONICAL_REPO.md` before any repo consolidation, cleanup, archival, or migration task.
3. Do not edit `/root/hermes-workspace/guild-v2`, `borg-init`, `borg-collective-v1`, `borg-collective-py`, `guild-packs`, `guild-benchmark`, or `guild-mcp-package` unless the user explicitly asks for that component.

## Operations safety

Do not restart, kill, signal, or reload the Hermes gateway from an agent session.
Do not edit operator `.env` or Hermes config files from this repo. Live served-MCP
cutovers are operator-supervised actions; agents may only produce the exact
fingerprint/canary commands and record the results.

## No-loss rule

Do not delete, archive, privatize, prune branches, run `git clean`, or force-push any Borg/Guild repo until its committed history and working tree have been snapshotted and its unique material is recorded in `docs/repo-manifest/`.

Legacy repos contain unique material: hosted federation, SDK, installer, wiki/extraction/mutation experiments, ARP schemas, benchmark fixtures, and `guild_*` compatibility. Treat them as sources to preserve, not trash.

## Public docs rule

Public first-user docs must point to:

- install package: `agent-borg`
- CLI: `borg`
- MCP server: `borg-mcp`
- repo: `borg-farther/Borg-Directory`

Never reference deprecated or personal account names; canonical identity is `borg-farther`. Do not reintroduce stale setup names such as `pip install guild-packs`, `guildpacks`, stale `guild_*` user instructions, or non-shipped `borgd` daemon instructions in current public setup docs.

## Verification before readiness claims

Run the executable gates, not just static review:

```bash
python eval/run_first_user_release_gate.py
python eval/run_readiness_gates.py
python eval/real_user_rollout_gate.py  # expected nonzero until first-10 rows pass
python -m pytest -q tests/packaging/test_distribution_readiness.py tests/packaging/test_public_repo_surface.py
```
