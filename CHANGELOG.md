# Changelog

## 3.3.15 — 2026-05-28

- First-user channel completeness release: `borg generate systematic-debugging --format all --output ...` now works from a clean wheel/PyPI install with empty `BORG_HOME`, using bundled seed packs instead of maintainer-only registry paths.
- Release gates now exercise the previously missing export/mix paths: platform rules generation, OpenClaw conversion, Python API import, CLI rescue/search/try, stdio MCP tools/value response, and setup commands.
- Documentation now has an explicit channel/install-method matrix so GitHub visitors can distinguish verified local CLI/stdio MCP paths from NO-GO served/remote channels.

## 3.3.11 — 2026-05-23

- Production hardening release: publishes the failure-memory package summary/keywords so PyPI no longer presents Borg as vague collective memory.
- MCP stdio hardening: `borg-mcp` now accepts standard `Content-Length` framed JSON-RPC while preserving newline-delimited compatibility.
- HTTP MCP hardening: adds explicit `borg-http`/`agent-borg[http]` packaging, loopback default, bearer-token enforcement for `/mcp`, and a fail-closed advisory tool allowlist.
- Public-surface cleanup: removes stale collective-intelligence/OpenClaw/autopilot wording from shipped seeds, examples, and generator output.
- Release boundary unchanged: controlled first-10 beta only; public self-serve and served remote MCP remain blocked until their separate evidence/runtime gates pass.

## 3.3.10 — 2026-05-22

- Docs-only PyPI presentation sync release: publishes the PR #25 GitHub README/public-doc hardening to the PyPI long description.
- Keeps runtime behavior unchanged from 3.3.9.

## 3.3.9 — 2026-05-22

- Public presentation patch: ships the sharpened README to PyPI so first users see the 60-second `borg rescue` path and absolute GitHub documentation links.
- Claims discipline: removes guarded statistical-lift phrasing from the package long description and keeps public self-serve / served-MCP / 100-user claims blocked until real evidence passes.
- Tests: extends public-presentation regression coverage for README overclaim language and first-10 readiness wording.

## 3.3.8 — 2026-05-22

- Public self-serve hardening: added row-derived first-10 evidence validation, PyPI fresh-install/MCP stdio canary, and a single fail-closed public self-serve launch gate.
- Claims discipline: updated first-10 invite/closure docs to `agent-borg==3.3.8`, replaced unsupported lift/SHIP copy with controlled-beta/no-go wording, and added CI coverage for public-readiness fail-closed tests.
- Release status: `agent-borg==3.3.8` is published on production PyPI; the post-upload fresh-install/MCP stdio canary passed. Public self-serve still fails closed until first-10 external evidence passes.

## 3.3.7 — 2026-05-21

- MCP: added `error_lookup` as a plain-English alias for `borg_rescue`, keeping the same ACTION / STOP / VERIFY rescue contract for concrete failures.
- First-user UX: updated README, install, MCP setup, quickstart, trying-Borg, first-10 readiness, and bundled skills so concrete failures use `error_lookup` / `borg rescue` before broader `borg_observe` or pack search.
- Tests: added first-user MCP alias regressions for tool discovery, dispatcher parity, JSON-RPC response shape, duplicate tool names, trace-capture privacy, and readiness contract docs.

## 3.3.6 — 2026-05-20

- Firewall: scrubbed residual deprecated account-name references from public docs and tracked eval artifacts.
- Fix: `DEFAULT_REPO` now defaults to `borg-farther/Borg-Directory` for pack publish/discovery paths.
- Fix: remote pack fallback URLs now point at `borg/seeds_data/packs/`, the path that actually exists in the public repo.
- CI: widened the account-reference firewall to scan all tracked files.

## 3.3.5 — 2026-05-18

- Fix: `borg/__init__.py` now derives `__version__` from package metadata (importlib.metadata.version) instead of a hardcoded string. CLI banners (`borg version`, `borg-mcp`, `borg-doctor`) will always match the installed version going forward.

## 3.3.3

- Tightened first-user docs around `borg rescue`, `borg first-10`, and MCP setup.
- Clarified that Borg is ready for controlled first-10 beta sharing, not public self-serve launch.
- Kept security, privacy, prompt-injection, and CI gates visible from the public README.
- Moved historical root-level audit, experiment, strategy, and marketing notes into `docs/archive/root-md/` so the repo root stays focused.

## Historical notes

Older detailed/internal changelog entries are archived at `docs/archive/root-md/CHANGELOG.md`.
