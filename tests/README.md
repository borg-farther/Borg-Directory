# Test suite layout

The Borg test suite is grouped by product surface instead of keeping every file in one flat package directory.

- `cli/` — command-line entrypoints and first-user CLI contracts.
- `core/` — core library behavior: search, store, schemas, URI handling, conversion, rescue.
- `learning/` — collective-learning, telemetry, traces, selectors, nudges, and feedback loops.
- `mcp/` — MCP server, observe wrapper, runtime fingerprint, and MCP hardening.
- `security/` — privacy, prompt-injection, atom-policy, safety, and security fixture tests.
- `packaging/` — release, version, compatibility, OpenClaw, and distribution checks.
- `publishing/` — publish/pull/reputation flows and related integrations.
- `readiness/` — confidence gates and first-10 beta readiness contracts.
- `e2e/` — long-form end-to-end verification harnesses.
- `fixtures/` — static data used by tests.

Default run:

```bash
python -m pytest tests/ --tb=short -q
```
