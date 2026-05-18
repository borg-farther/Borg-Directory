# Borg archive

This directory contains historical audits, experiments, generated PDFs, marketing drafts, dogfood fixtures, root-level one-off scripts, and ad hoc tests preserved for provenance.

These files are not the current first-user product surface and should not be treated as installation instructions, release claims, or active CI targets.

Current public docs remain listed in [`../README.md`](../README.md). The canonical first-user path starts at the root [`README.md`](../../README.md).

## Buckets

- `root-pdfs/` — old generated PDF reports formerly shown in the repository root.
- `root-scripts/` — one-off debug/audit/check/replay scripts formerly shown in the repository root.
- `root-tests/` — ad hoc root `test_*.py` files kept out of the default pytest suite.
- `django-constraint-fixture/` — old Django constraint experiment fixture that should not shadow real `django` imports from the repo root.
- `dogfood/`, `autoresearch/`, `marketing/` — historical experiment and marketing workspaces.
