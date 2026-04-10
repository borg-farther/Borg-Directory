# Borg — Cache Layer for Agent Reasoning

**pip install agent-borg | CLI: `borg` | MCP: `borg-mcp`**

Borg is a workflow cache for AI agents. When your agent gets stuck, it can reach into the borg for a proven approach that another agent already worked out — and write back what it learned so the next agent doesn't repeat the same failed attempts.

Think of it as connective brain tissue for agents: not a magic oracle, but a shared cache of approaches that worked.

---

## Installation

```bash
pip install agent-borg                    # core only
pip install agent-borg[embeddings]        # semantic search
pip install agent-borg[crypto]            # Ed25519 pack signing
pip install agent-borg[all]              # everything
pipx install agent-borg                  # recommended — isolated
```

Requires Python 3.10+.

## Quick Start

### CLI

```bash
# Search for a relevant pack
borg search debugging

# Preview without committing
borg try borg://hermes/systematic-debugging

# Pull to local storage
borg pull borg://hermes/systematic-debugging

# Apply it to your task
borg apply systematic-debugging --task "Fix login 401 after OAuth redirect"

# After completing, generate feedback
borg feedback <session_id>
```

### MCP Server

Add to your Claude Code, Cursor, or OpenClaw MCP config:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp"
    }
  }
}
```

Available tools: `borg_search`, `borg_pull`, `borg_try`, `borg_init`, `borg_apply`, `borg_publish`, `borg_feedback`, `borg_suggest`, `borg_observe`, `borg_convert`.

### Python API

```python
from borg import borg_search, borg_pull, borg_try

results = borg_search("debugging")
borg_try("borg://hermes/systematic-debugging")
borg_pull("borg://hermes/systematic-debugging")
```

---

## What It Actually Does

Borg manages **workflow packs** — YAML files that encode how to approach a problem class. A pack contains:

- **Problem class**: what kind of task this pack addresses
- **Mental model**: how to think about it (e.g., "slow-thinker" vs "fast-thinker")
- **Phases**: ordered steps with descriptions, checkpoints, and anti-patterns
- **Provenance**: confidence level (guessed → inferred → tested → validated)
- **Safety scan results**: injection and privacy pattern checks

The core loop:

```
Agent hits a problem
  → borg_search finds relevant packs
    → borg_try previews phases and safety scan
      → borg_pull downloads to ~/.hermes/borg/
        → borg_apply executes phase by phase
          → borg_feedback generates a structured artifact
            → next agent gets a better starting point
```

This is a cache, not a magic box. Packs encode what worked before. They get better as feedback accumulates. No packs have been externally validated yet — that's the gap between what's built and what's useful at scale.

---

## Architecture

```
borg/
├── core/                    # Engine — zero external deps beyond PyYAML
│   ├── search.py            # borg_search, borg_pull, borg_try, borg_init
│   ├── apply.py             # Phase-by-phase pack execution
│   ├── publish.py           # GitHub PR creation via gh CLI
│   ├── safety.py            # 13 injection + 11 privacy pattern scanner
│   ├── proof_gates.py       # Confidence tier validation
│   ├── schema.py            # YAML parsing and pack validation
│   ├── privacy.py           # PII detection and redaction
│   ├── session.py           # Execution state and JSONL logging
│   ├── uri.py               # borg:// URI resolution and fetch
│   ├── semantic_search.py   # Vector similarity (optional, requires embeddings)
│   └── convert.py           # SKILL.md / CLAUDE.md / .cursorrules converter
├── db/
│   ├── store.py             # SQLite with FTS5 full-text search
│   ├── reputation.py        # Contribution scoring (computed but not enforced)
│   ├── analytics.py         # Engagement metrics
│   └── embeddings.py        # Vector storage (optional)
└── integrations/
    ├── mcp_server.py        # JSON-RPC 2.0 MCP server over stdio
    └── agent_hook.py        # borg_on_failure, borg_on_task_start entry points
```

**Core dependency: PyYAML only.** Embeddings, crypto, and SQLite are optional.

---

## What Exists vs What Doesn't

### What Exists (Phases 0-3 complete)

- Full CLI with 11 subcommands: search, pull, try, init, apply, publish, feedback, convert, list, autopilot, version
- MCP server with 10 tools wired to core modules
- Pack lifecycle: search → try → pull → apply → feedback
- Safety scanner (13 injection patterns, 11 privacy patterns)
- Proof gate validation with 4 confidence tiers (guessed/inferred/tested/validated)
- Privacy scanning and redaction
- Session logging with JSONL
- SQLite persistence with FTS5 full-text search
- Semantic search (optional, requires embeddings)
- SKILL.md / CLAUDE.md / .cursorrules converter
- Zero-config autopilot for Hermes
- 682+ unit tests across core modules
- OpenClaw integration docs

### What Doesn't Exist Yet

- **No external users.** Zero. The feedback loop that improves packs with real usage hasn't run.
- **No coordinator bot.** Pack publishing requires direct `gh` CLI access. The spec describes an automated coordinator — it doesn't exist in code.
- **Reputation engine is unwired.** `reputation.py` computes scores but nothing enforces access based on them.
- **Auto-suggest is minimal.** `borg_suggest` and `borg_on_task_start` exist as stubs; they're not production-quality suggestion engines.
- **No PyPI-hosted MCP server package.** The `agent-borg` package is on PyPI but only as a Python library. The MCP server runs via `borg-mcp` entry point.
- **Confidence decay is advisory only.** Packs don't get blocked based on age.
- **Safety scanner has false positives.** Known issue — code-heavy packs trigger injection pattern matches.

---

## Contributing

### Create a pack from a skill

```bash
borg init my-workflow
```

### Convert an existing CLAUDE.md / SKILL.md / .cursorrules

```bash
borg convert ./CLAUDE.md --format auto
```

### Publish a pack

```bash
# Requires GitHub CLI authenticated: gh auth status
borg publish ~/.hermes/borg/my-workflow/pack.yaml
```

### Run tests

```bash
pip install agent-borg[dev]
pytest borg/tests/
```

---

## Status

v2.4.0 — Phases 0-3 infrastructure is complete. The core engine works, the MCP transport is solid, and the safety/proof gate systems are functional. The gap is adoption: no external users means no feedback loop, which means packs haven't been battle-tested by the community yet.

The architecture is over-engineered for its current user count (zero external users). If you want to help prove it out, try the autopilot and file feedback on any packs that don't work for your use case.
