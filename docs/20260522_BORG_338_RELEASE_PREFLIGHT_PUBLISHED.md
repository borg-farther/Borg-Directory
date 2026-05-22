# Borg 3.3.8 production PyPI release preflight and verification

Generated: 2026-05-22T12:12:12Z
Rev: final post-upload verification

## Verdict

**PUBLISHED_AND_VERIFIED** for the package release.

`agent-borg==3.3.8` is live on production PyPI and passed the fresh-install/MCP canary.

This does **not** make Borg public self-serve GO. Public self-serve remains blocked only by real first-10 external-user evidence.

## Release provenance

- Repo: `borg-farther/Borg-Directory`
- PR: https://github.com/borg-farther/Borg-Directory/pull/20
- Merged main commit: `928dc43faa23a75c1245300ef747755d9eb4b6f3`
- Tag: `v3.3.8`
- Tag type: annotated, unsigned
- Tag peels to commit: `928dc43faa23a75c1245300ef747755d9eb4b6f3`
- PyPI release: https://pypi.org/project/agent-borg/3.3.8/

## CI proof

- PR checks before merge: all required checks passed.
- Main push checks after merge:
  - Account Reference Firewall: pass
  - Borg Security Gates: pass
  - CI Python 3.10: pass
  - CI Python 3.11: pass
  - CI Python 3.12: pass

## Artifact proof

- `agent_borg-3.3.8-py3-none-any.whl`
  - sha256: `12adeffbf6773ec6f06cfb3454a5fa7e3ffd7abd5bbb4f1b17128afcd33a6e77`
- `agent_borg-3.3.8.tar.gz`
  - sha256: `d6fc4435e8c9c50e0d8f3716957a5446d78bfbc4779e5f70c62e0ad9bde17d14`
- `twine check`: pass
- PyPI JSON now lists both files for version `3.3.8`.

## Post-release package verification

`python eval/run_pypi_fresh_install_canary.py`: **PASS**

The canary installed `agent-borg==3.3.8` from production PyPI in a clean venv with isolated `HOME`/`BORG_HOME`, then verified:

- `borg --version` returns `borg 3.3.8`
- `borg --help` works
- `borg rescue ... --json` works
- `borg-doctor --json` works
- `borg-mcp` stdio initialize works
- MCP `serverInfo`: `borg-mcp-server` / `3.3.8`

## Current launch status

- Supervised local/source first-user path: **GO**
- PyPI first-10 controlled-beta infrastructure: **GO**
- Public self-serve launch: **NO-GO**
- 100-real-user rollout: **NO-GO**
- Served remote MCP: **NO-GO until separate runtime cutover/canary**
- External adoption/lift: **unproven; verified external users = 0**

## Remaining non-fakeable blocker

Collect row-derived first-10 external-user evidence:

- 10 consented external users
- at least 8 install successes
- at least 6 useful rescue moments
- 0 critical privacy/security incidents

Only after that evidence passes should `eval/public_self_serve_launch_gate.py` become GO.
