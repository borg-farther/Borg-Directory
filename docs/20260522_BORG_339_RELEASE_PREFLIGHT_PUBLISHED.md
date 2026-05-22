# Borg 3.3.9 production PyPI release preflight and verification

> **Historical/internal — not current product documentation.**
> Current release proof is [`20260522_BORG_3310_RELEASE_PREFLIGHT_PUBLISHED.md`](20260522_BORG_3310_RELEASE_PREFLIGHT_PUBLISHED.md).

Rev: 2026-05-22

## Verdict

`agent-borg==3.3.9` is live on production PyPI and passed the fresh-install / MCP stdio canary.

This is a public-presentation patch release. It ships the sharpened README to PyPI so first users see the 60-second `borg rescue` value path and absolute GitHub documentation links instead of stale PyPI-relative docs links.

## Proven release target

- Package: `agent-borg`
- Version: `3.3.9`
- CLI: `borg`
- MCP server: `borg-mcp`
- Main release commit: `fe44e91225c7d29a95795c8ba4a290ca5a342fae`
- Tag: `v3.3.9`
- PyPI release: https://pypi.org/project/agent-borg/3.3.9/

## Pre-upload gates

- Version uniqueness: `agent-borg==3.3.9` did not exist on PyPI before upload.
- Version consistency: `pyproject.toml == borg.__version__ == 3.3.9`.
- Targeted docs/readiness tests: `67 passed`.
- Full suite: `2177 passed, 40 skipped, 4 xfailed, 1 xpassed`.
- Security gate: PASS.
- GitHub PR #23 checks: PASS on CI, security gates, secret scan, and account-reference firewall.
- Main branch checks after merge: PASS on CI, security gates, and account-reference firewall.
- Build: `python -m build --wheel --sdist` produced:
  - `agent_borg-3.3.9-py3-none-any.whl`
  - `agent_borg-3.3.9.tar.gz`
- `python -m twine check dist/*`: PASS.
- Built artifact inspection: wheel/sdist metadata contains version `3.3.9`, the 60-second README path, absolute GitHub docs links, and no guarded statistical-lift phrase.
- Fresh local wheel smoke: `borg --version`, `borg rescue --json`, `borg-doctor --json`, and `borg-mcp` initialize all passed with version `3.3.9`.

## Post-upload gates

The post-upload canary installed `agent-borg==3.3.9` from production PyPI in a clean venv with isolated `HOME` / `BORG_HOME`, then verified:

- `borg --version` returns `borg 3.3.9`.
- `borg --help` exposes first-user commands.
- `borg rescue "ModuleNotFoundError: No module named flask" --json` returns ACTION / STOP / VERIFY with `success=true`.
- `borg-doctor --json` passes.
- `borg-mcp` stdio JSON-RPC initialize passes.
- MCP `serverInfo`: `borg-mcp-server` / `3.3.9`.
- MCP tool list includes `borg_observe`, `borg_rescue`, `error_lookup`, and `borg_runtime_fingerprint`.
- PyPI JSON reports latest version `3.3.9` with both wheel and sdist files.
- PyPI JSON long description includes `Try Borg in 60 seconds`, absolute GitHub documentation links, and no guarded statistical-lift phrase.

## Remaining honest blockers

- Public self-serve remains **NO-GO** until first-10 row-derived evidence passes: 10 consented external users, at least 8 successful installs, at least 6 useful rescue moments, and 0 critical privacy/security incidents.
- 100-real-user rollout remains **NO-GO** until first-10 external evidence passes and follow-on real-user gates are satisfied.
- Served remote MCP remains **NO-GO** until a separate runtime cutover proves the live served process path, version, hash, and realistic `borg_observe` behavior.
- Real external lift remains unproven; no adoption/lift claim is made from this release.
