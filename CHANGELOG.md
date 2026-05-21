# Changelog

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
