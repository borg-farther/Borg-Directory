# Borg MCP setup

Recommended Claude Code setup:

```bash
borg setup-claude --scope user --verify --fix
```

Then fully restart Claude Code.

## What the setup command proves

- `borg-mcp` or `python -m borg.integrations.mcp_server` can be launched.
- Borg home storage exists or is created.
- The MCP server responds to `initialize`.
- Config is merged instead of overwriting unrelated MCP servers.
- `BORG_HOME` is written as an absolute path, not `~`.

## Manual config

Use this for Claude Code, Cursor, Cline, Continue, Goose, Codex-style CLIs, or any stdio MCP client that accepts `mcpServers` JSON.

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

If `borg-mcp` is not on PATH:

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

## Core first-user MCP tools

- `borg_rescue` — ACTION / STOP / VERIFY packet for concrete failures.
- `borg_observe` — guidance before technical fixes.
- `borg_search` — search packs and traces.
- `borg_try` — preview a pack.
- `borg_apply` — start/checkpoint/complete pack execution.
- `borg_feedback` — generate feedback from a completed session.
- `borg_suggest` — suggest after repeated failures.
- `borg_first_10` — first-10 beta gates and smoke path.

Advanced/admin tools may also be exposed by the server, but first users should start with the tools above.

## Verify manually

```bash
borg-doctor --json
```

For raw JSON-RPC stdio testing:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | borg-mcp
```

## Troubleshooting

### `borg-mcp` not found

```bash
python3 -m pip install agent-borg
python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

Use the printed scripts directory to build an absolute command path if your MCP client cannot find `borg-mcp`.

### MCP tools do not appear

1. Fully restart the agent host/IDE.
2. Confirm the JSON config is valid.
3. Confirm the configured `BORG_HOME` path is absolute.
4. Run `borg-doctor --json` and fix any failed check.
