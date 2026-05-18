# Changelog

## 3.3.5 — 2026-05-18

- Fix: `borg/__init__.py` now derives `__version__` from package metadata (importlib.metadata.version) instead of a hardcoded string. CLI banners (`borg version`, `borg-mcp`, `borg-doctor`) will always match the installed version going forward.

## 3.3.3

- Tightened first-user docs around `borg rescue`, `borg first-10`, and MCP setup.
- Clarified that Borg is ready for controlled first-10 beta sharing, not public self-serve launch.
- Kept security, privacy, prompt-injection, and CI gates visible from the public README.
- Moved historical root-level audit, experiment, strategy, and marketing notes into `docs/archive/root-md/` so the repo root stays focused.

## Historical notes

Older detailed/internal changelog entries are archived at `docs/archive/root-md/CHANGELOG.md`.
