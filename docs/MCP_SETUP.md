# Borg MCP setup

Prerequisite: install package `agent-borg`; it provides the `borg` CLI and the `borg-mcp` MCP server command. If you have not installed it yet, use [`INSTALL.md`](INSTALL.md).

Do **not** install `borg` or `borgbackup`; those are unrelated to this AI-agent tool.

## Recommended Claude Code setup

Run this after `borg version` and `borg-doctor --json` pass:

```bash
borg setup-claude --scope user --verify --fix
```

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code. In the new session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## What the setup command proves

- `borg-mcp` can be launched.
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

If `borg-mcp` is not on PATH, locate it first and use its absolute path.

macOS/Linux:

```bash
command -v borg-mcp
```

Windows PowerShell:

```powershell
where.exe borg-mcp
```

Avoid bare `python` or `python3` in MCP config unless you are certain that exact interpreter has `agent-borg` installed.
Use absolute paths in MCP env blocks. Do not rely on `~` expansion inside MCP clients.

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

Install the correct package and refresh PATH:

```bash
pipx install --force agent-borg
pipx ensurepath
exec "$SHELL" -l
command -v borg-mcp
```

Windows PowerShell:

```powershell
py -m pipx install --force agent-borg
py -m pipx ensurepath
```

Then close and reopen PowerShell and run:

```powershell
where.exe borg-mcp
```

### MCP tools do not appear

1. Fully restart the agent host/IDE.
2. Confirm the JSON config is valid.
3. Confirm the configured `BORG_HOME` path is absolute.
4. Run `borg-doctor --json` and fix any failed check.
5. Rerun `borg setup-claude --scope user --verify --fix`.
