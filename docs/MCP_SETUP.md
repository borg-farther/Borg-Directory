# Borg MCP Setup Guide

This guide provides exact copy-paste MCP configurations for Claude Code, Cursor, and generic MCP clients.

**The recommended setup is:**
```bash
borg setup-claude   # automated setup for Claude Code
```

The config below is what `borg setup-claude` writes automatically. You only need this if you're configuring manually.

---

## Claude Code

**Config file:** `~/.config/claude/claude_desktop_config.json`

> Note: Claude Code stores MCP settings in a JSON file. The default location is `~/.config/claude/claude_desktop_config.json` on Linux/macOS.

### Single borg server (recommended: use borg-mcp)

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": []
    }
  }
}
```

### Using explicit Python interpreter

If `borg-mcp` is not in PATH, use your Python executable directly:

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"]
    }
  }
}
```

### Multiple MCP servers (merge existing)

If you already have other MCP servers configured, merge the borg entry:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": []
    },
    "your-other-server": {
      "command": "your-other-mcp-server",
      "args": []
    }
  }
}
```

### Verify Claude Code sees borg

After restarting Claude Code, ask:
> "What MCP tools do you have available from borg?"

You should see tools like `borg_search`, `borg_observe`, `borg_try`, `borg_apply`, `borg_feedback`, `borg_suggest`, and `borg_debug`.

---

## Cursor

**Config file:** `~/.cursor/mcp.json`

Create the file if it doesn't exist:

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": []
    }
  }
}
```

Or with explicit Python:
```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"]
    }
  }
}
```

### Multiple MCP servers

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": []
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

### Verify Cursor sees borg

Restart Cursor. Ask: "Search borg packs for a code review workflow."

---

## Generic MCP Client

Any MCP client that supports stdio-based servers can use borg.

### Basic stdio configuration

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": []
    }
  }
}
```

### With explicit Python interpreter

```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-m", "borg.integrations.mcp_server"]
    }
  }
}
```

Or with inline Python path resolution:
```json
{
  "mcpServers": {
    "borg": {
      "command": "python3",
      "args": ["-c", "import sys; sys.path.insert(0, '/path/to/site-packages'); from borg.integrations.mcp_server import main; main()"]
    }
  }
}
```

### Manual JSON-RPC 2.0 over stdio

borg-mcp speaks JSON-RPC 2.0 over stdin/stdout. You can test it manually:

```bash
# Initialize
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | borg-mcp

# List tools
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | borg-mcp

# Call borg_search
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"borg_search","arguments":{"query":"debugging"}}}' | borg-mcp
```

---

## Protocol Details

- **Protocol version:** 2024-11-05
- **Transport:** stdio (stdin/stdout JSON-RPC 2.0)
- **Server name:** borg-mcp-server
- **Server version:** 3.3.0

### Available Tools

| Tool | Description |
|------|-------------|
| `borg_search` | Search packs by keyword or semantic similarity |
| `borg_observe` | Proactive guidance at task start |
| `borg_try` | Preview pack without saving |
| `borg_pull` | Download and save pack locally |
| `borg_apply` | Execute pack (start/checkpoint/complete) |
| `borg_feedback` | Generate feedback from session |
| `borg_publish` | Publish pack or feedback to GitHub |
| `borg_convert` | Convert SKILL.md/CLAUDE.md/.cursorrules |
| `borg_suggest` | Auto-suggest pack from frustration signals |
| `borg_debug` | Get structured debugging guidance |

---

## Troubleshooting

### "command not found" or server not responding

1. Verify borg-mcp is installed:
```bash
which borg-mcp
borg-mcp --version 2>&1 || echo "borg-mcp not in PATH"
```

2. Find the correct path:
```bash
pip show agent-borg | grep Location
# borg-mcp is at: <Location>/../../../bin/borg-mcp
```

3. Use absolute path in config, or use `python3 -m borg.integrations.mcp_server`.

### macOS: "borg-mcp cannot be opened because the developer is not verified"

Go to System Preferences → Security & Privacy → General → allow "borg-mcp" (or use `xattr -d com.apple.quarantine /path/to/borg-mcp`).

### Windows: borg-mcp closes immediately

On Windows, specify python explicitly:
```json
{
  "mcpServers": {
    "borg": {
      "command": "python",
      "args": ["-m", "borg.integrations.mcp_server"]
    }
  }
}
```

### Claude Code / Cursor don't show borg tools after setup

1. Restart the IDE completely (not just the chat)
2. Check the IDE's MCP logs (usually in dev tools or console)
3. Verify JSON syntax is valid in config file
4. Try with absolute path to borg-mcp or python

### Linux: ~/.config directory doesn't exist

```bash
mkdir -p ~/.config/claude
mkdir -p ~/.cursor
```
