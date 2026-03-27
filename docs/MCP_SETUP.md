# Guild-Packs MCP Setup Guide

This guide provides exact copy-paste MCP configurations for Claude Code, Cursor, and generic MCP clients.

---

## Claude Code

**Config file:** `~/.config/claude/claude_desktop_config.json`

> Note: Claude Code stores MCP settings in a JSON file. The default location is `~/.config/claude/claude_desktop_config.json` on Linux/macOS.

### Single guild-packs server

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp",
      "args": []
    }
  }
}
```

### Multiple MCP servers (merge existing)

If you already have other MCP servers configured, merge the guild-packs entry:

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp",
      "args": []
    },
    "your-other-server": {
      "command": "your-other-mcp-server",
      "args": []
    }
  }
}
```

### Using absolute path (if `guild-mcp` not in PATH)

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "/home/YOUR_USER/.local/bin/guild-mcp",
      "args": []
    }
  }
}
```

Find your guild-mcp path with:
```bash
which guild-mcp
# or
find ~ -name "guild-mcp" -type f 2>/dev/null
```

### Verify Claude Code sees guild-packs

After restarting Claude Code, ask:
> "What MCP tools do you have available from guild-packs?"

You should see tools like `guild_search`, `guild_pull`, `guild_try`, `guild_apply`, etc.

---

## Cursor

**Config file:** `~/.cursor/mcp.json`

Create the file if it doesn't exist:

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp",
      "args": []
    }
  }
}
```

### Multiple MCP servers

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp",
      "args": []
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

### Using absolute path

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "/Users/YOUR_USER/.local/bin/guild-mcp",
      "args": []
    }
  }
}
```

### Verify Cursor sees guild-packs

In Cursor, try asking:
> "Search guild packs for a code review workflow"

---

## Generic MCP Client

Any MCP client that supports stdio-based servers can use guild-packs.

### Basic stdio configuration

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp",
      "args": []
    }
  }
}
```

### With explicit Python interpreter

Some clients need the Python interpreter specified:

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "python3",
      "args": ["-m", "guild.integrations.mcp_server"]
    }
  }
}
```

Or with explicit path:
```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "python3",
      "args": ["-c", "import sys; sys.path.insert(0, '/path/to/guild-v2'); from guild.integrations.mcp_server import main; main()"]
    }
  }
}
```

### Manual JSON-RPC 2.0 over stdio

guild-mcp speaks JSON-RPC 2.0 over stdin/stdout. You can test it manually:

```bash
# Initialize
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | guild-mcp

# List tools
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | guild-mcp

# Call guild_search
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"guild_search","arguments":{"query":"debugging"}}}' | guild-mcp
```

---

## Protocol Details

- **Protocol version:** 2024-11-05
- **Transport:** stdio (stdin/stdout JSON-RPC 2.0)
- **Server name:** guild-mcp-server
- **Server version:** 1.0.0

### Available Tools

| Tool | Description |
|------|-------------|
| `guild_search` | Search packs by keyword or semantic similarity |
| `guild_try` | Preview pack without saving |
| `guild_pull` | Download and save pack locally |
| `guild_init` | Scaffold a new pack |
| `guild_apply` | Execute pack (start/checkpoint/complete) |
| `guild_feedback` | Generate feedback from session |
| `guild_publish` | Publish pack or feedback to GitHub |
| `guild_convert` | Convert SKILL.md/CLAUDE.md/.cursorrules |
| `guild_suggest` | Auto-suggest pack from frustration signals |

---

## Troubleshooting

### "command not found" or server not responding

1. Verify guild-mcp is installed:
```bash
which guild-mcp
guild-mcp --version 2>&1 || echo "guild-mcp not in PATH"
```

2. Find the correct path:
```bash
pip show guild-packs | grep Location
# guild-mcp is at: <Location>/../../../bin/guild-mcp
```

3. Use absolute path in config.

### macOS: "guild-mcp cannot be opened because the developer is not verified"

Go to System Preferences → Security & Privacy → General → allow "guild-mcp" (or use `xattr -d com.apple.quarantine /path/to/guild-mcp`).

### Windows: guild-mcp closes immediately

On Windows, you may need to specify python explicitly:
```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "python",
      "args": ["-m", "guild.integrations.mcp_server"]
    }
  }
}
```

### Claude Code / Cursor don't show guild tools after setup

1. Restart the IDE completely (not just the chat)
2. Check the IDE's MCP logs (usually in dev tools or console)
3. Verify JSON syntax is valid in config file
4. Try with absolute path to guild-mcp

### Linux: ~/.config directory doesn't exist

Create it:
```bash
mkdir -p ~/.config/claude
mkdir -p ~/.cursor
```
