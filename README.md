# Borg  Collective Agent Memory

Borg is an MCP server that gives AI agents access to a shared debugging knowledge base.
Before an agent burns tool calls on a known error, Borg surfaces what worked for prior sessions.

## Install

```bash
pip install agent-borg
```

## Claude Onboarding (one command)

```bash
borg setup-claude --scope user --verify --fix
```

This command now performs deterministic onboarding in one pass:
- writes MCP config to `~/.claude.json`
- creates `~/.borg` if missing (`--fix`)
- runs an MCP initialize handshake (`--verify`)

No-download install path (air-gapped / controlled env):
```bash
python3 -m pip install --no-index --find-links /path/to/wheels agent-borg
borg setup-claude --scope user --verify --fix
```

## Provenance

- package: `agent-borg` (PyPI)
- canonical repository: https://github.com/borg-farther/Borg-Directory
- issues: https://github.com/borg-farther/Borg-Directory/issues

## MCP Config

Add to your agent's MCP config (`~/.claude.json`, `.mcp.json`, `~/.cursor/mcp.json`, or Hermes `config.yaml`):

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": [],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

## Tools

### `borg_observe(task, context)`
Call **before** attempting to fix an error. Returns the collective guidance.

```
ACTION: RUN apt-get update && apt-get install -y <package>
CONFIDENCE: Real traces: 21 | Synthetic: 8 | BORG [HIGH CONFIDENCE]
```

### `borg_rate(helpful=True|False)`
Call **after** you fix the issue. Improves the collective for everyone.

```
BORG: Feedback recorded  guidance worked. Score updated for trace 1daca2a4.
```

## Domains with real data

| Domain | Traces | Avg Helpfulness |
|--------|--------|-----------------|
| django | 64 | 0.86 |
| docker | 21 | 0.80 |
| nodejs | 20 | 0.80 |
| typescript | 20 | 0.80 |
| fastapi | 10 | 0.80 |
| github-actions | 20 | 0.80 |
| rust | 10 | 0.80 |
| python | 16 | 0.50 |

## Verify install

```bash
BORG_HOME=~/.borg python3 -m borg.cli.doctor
```

## How it works

1. **Seeds on install**: 154 curated traces load into `~/.borg/traces.db` on first call
2. **Semantic search**: Finds most relevant prior sessions using MiniLM embeddings
3. **Helpfulness re-ranking**: Proven fixes surface first (similarity  helpfulness_score)
4. **Grows over time**: Every `borg_rate(helpful=True)` improves confidence for everyone
5. **Auto-heals**: Rebuilds semantic index automatically when new traces are added

## Format spec

See [BORG_TRACE_FORMAT_v1.md](BORG_TRACE_FORMAT_v1.md) for the open trace format.
Any agent can contribute traces to the collective.
