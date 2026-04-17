# Borg  The Read-Through Cache for Agent Reasoning

Borg is an MCP server that gives AI coding agents a shared cache of debugging traces. Before an agent burns tool calls on an error, Borg surfaces what worked in prior sessions.

## Status (2026-04-16, Phase 0 complete)

- 172 organic agent-authored traces in `traces`
- 293 non-organic traces (seed pack + golden seed + curated sprint) in `seed_traces`
- 465 total corpus entries
- Tiered retrieval: organic first, synthetic fallback, each result labelled with `source_tier`
- 4 live invariant tests (I3 real/synthetic separation at read + write; I4 PII gate; source-tier retrieval contract)
- Not yet ready for public launch. See `Borg_PRD_v4.md` 11 for launch gates.

## Install (private beta)

Requires repo access  ask the maintainer.

```bash
pip install git+ssh://git@github.com/bensargotest-sys/borg.git
```

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for full setup (MCP config for Claude Desktop / Cursor / Claude Code / Cline).

MCP config (Claude Desktop / Cursor / Cline / Claude Code):

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": { "BORG_HOME": "~/.borg" }
    }
  }
}
```

## How it works

Agent calls `borg_observe(task, context)` before attempting a fix. Borg returns up to 5 results, each with a `source_tier`:

- `real`  organic agent-authored trace from live sessions
- `synthetic`  seed-pack / golden-seed / curated coverage (fallback when no real match)

After the fix, `borg_rate(helpful=True/False)` updates helpfulness scoring.

## What's real vs what's not

Phase 0 (this commit) enforces a hard separation:

- `traces` table  only agent-authored organic data. Write path (`save_trace`) rejects `source` in `seed_pack`/`golden_seed`/`curated` and raises `ValueError`.
- `seed_traces` table  synthetic and scripted-sprint coverage. Retrieval falls back here only when organic yields fewer than `limit` results.

## Performance claims

**None yet.** Public performance numbers require `borg-bench` (Phase 1) running on a held-out benchmark dataset. See `Borg_PRD_v4.md` 7 for the metrics contract and 11 for launch gates.

Prior materials that cited "27% fewer tool calls" and "67% higher success rate" were computed on synthetic seed packs and are not reproducible on real traffic. Those claims are withdrawn pending Phase 1 measurement.

## Trace format

Open format documented in `BORG_TRACE_FORMAT_v1.md`. Any agent framework that writes Borg-compatible traces can contribute.

## Invariants (CI-enforced)

| # | Invariant | Status |
|---|---|---|
| I1 | First query hits in <30s on fresh install | Pending Phase 1 harness |
| I2 | README performance numbers reproducible from `borg-bench` | Pending Phase 1 |
| I3 | `traces` and `seed_traces` architecturally separate | LIVE |
| I4 | PII never ships | LIVE |
| I5 | Exported traces validate against `BORG_TRACE_FORMAT_v1` | Pending JSON schema |

## Verification

```bash
BORG_HOME=~/.borg python3 -m pytest borg/tests/test_invariants.py -v
```

Expected: 4 passed, 3 skipped.

## Roadmap

- **Phase 0 (done):** data hygiene, real/synthetic separation, invariant tests, honest claims
- **Phase 1:** `borg-bench` with WILD-200 held-out dataset, dead-end re-ranker, MCP tool rename (`borg_observe`  `error_lookup`), invited beta (5 users)
- **Phase 2+:** public launch, trace format adoption by other agent frameworks, governance

## License

MIT (code) / CC0 (trace format specification)

## Maintainer

Single-maintainer project. Not affiliated with any company. Issues and PRs welcome but response time is best-effort.
