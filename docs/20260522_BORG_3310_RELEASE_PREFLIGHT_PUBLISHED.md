# Borg 3.3.10 production PyPI release preflight and verification

Rev: 2026-05-22

## Verdict

`agent-borg==3.3.10` is live on production PyPI and passed the fresh-install / MCP stdio canary.

This is a docs-only PyPI presentation sync release: it publishes the GitHub PR #25 public README/docs hardening to the PyPI long description. Runtime behavior is unchanged from 3.3.9.

Public self-serve remains **NO-GO** because first-10 external-user evidence is still missing.

## Release identity

- Package: `agent-borg`
- Version: `3.3.10`
- CLI: `borg`
- MCP command: `borg-mcp`
- GitHub merge commit: `ef91225c1355582684d53f4e3ec12eaa6e4353ca`
- Tag: `v3.3.10`
- PyPI release: https://pypi.org/project/agent-borg/3.3.10/

## Pre-upload gates

Passed before upload:

- Version uniqueness: `agent-borg==3.3.10` did not exist on PyPI before upload.
- Version consistency: `pyproject.toml == borg.__version__ == 3.3.10`.
- GitHub PR #26 checks: CI, security gates, and account-reference firewall all passed before merge.
- GitHub `main` post-merge checks: CI, security gates, and account-reference firewall all passed on `ef91225c1355582684d53f4e3ec12eaa6e4353ca`.
- Targeted docs/readiness tests: `69 passed`.
- Security gate: PASS.
- `python -m build --wheel --sdist`: PASS.
- `python -m twine check dist/*`: PASS.
- Built files:
  - `agent_borg-3.3.10-py3-none-any.whl`
  - `agent_borg-3.3.10.tar.gz`
- Artifact inspection: wheel/sdist metadata contains version `3.3.10`, the 60-second `borg rescue --short` README path, absolute GitHub docs links, and no guarded statistical-lift phrase.

## Post-upload canary

The post-upload canary installed `agent-borg==3.3.10` from production PyPI in a clean venv with isolated `HOME` / `BORG_HOME`, then verified:

- `borg --version` returns `borg 3.3.10`.
- `borg --help` exposes the expected command set.
- `borg rescue "ModuleNotFoundError: No module named flask" --json` returns matched ACTION / STOP / VERIFY guidance.
- `borg-doctor --json` returns `success: true` and package version `3.3.10`.
- `borg-mcp` initializes over stdio.
- MCP `serverInfo`: `borg-mcp-server` / `3.3.10`.
- Required MCP tools present: `borg_observe`, `borg_rescue`, `borg_runtime_fingerprint`, `error_lookup`.
- PyPI JSON reports latest version `3.3.10` with both wheel and sdist files.
- PyPI long description includes the PR #25 first-user value path and docs links.

## Remaining reality gate

This release does **not** authorize public self-serve launch, 100-user rollout, served remote MCP claims, or adoption/lift claims.

Remaining external evidence gate:

- 10 consented external users.
- At least 8 successful installs.
- At least 6 useful rescue moments.
- 0 critical privacy/security incidents.

Until that row-derived evidence passes, Borg is ready for controlled first-10 beta only.
