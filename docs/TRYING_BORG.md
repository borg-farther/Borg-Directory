# Trying Borg — Quick Setup Guide

**agent-borg** is a federated knowledge exchange for AI agents. It ships a CLI and MCP server that gives your agent access to battle-tested debugging workflows.

**agent-borg 3.3.0** | GitHub: `bensargotest-sys/agent-borg` | CLI: `borg` | MCP: `borg-mcp`

---

## 1. INSTALLATION

Borg requires Python 3.10+.

```bash
# Install via pip (one of these methods)
pip install agent-borg                    # system-wide (may need --break-system-packages)
pipx install agent-borg                   # recommended — isolated environment
pip install --user agent-borg             # user-local
```

**Verify installation:**
```bash
borg version
# Expected output: agent-borg 3.3.0
```

If `borg: command not found`, your pipx/bin directory may not be in PATH. Add it:
```bash
export PATH="$HOME/.local/bin:$PATH"      # Linux/macOS
# or find it: python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

---

## 2. CLAUDE CODE SETUP (MCP)

Borg works as an MCP server, giving Claude Code access to borg tools.

### Step 1: Configure MCP

Run the automated setup:
```bash
borg setup-claude
```

This writes the correct MCP configuration to `~/.config/claude/claude_desktop_config.json` using `borg-mcp` (the CLI entry point) or your current Python interpreter.

**Config file location:** `~/.config/claude/claude_desktop_config.json`

After running `borg setup-claude`, your config should contain:
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

Or if `borg-mcp` is not in PATH, the setup uses your Python executable directly:
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

### Step 2: Restart Claude Code

After editing the config, **fully restart Claude Code** (not just the chat). The borg MCP tools will appear in your available tools.

### What you get:

| Tool | Description |
|------|-------------|
| `borg_search` | Search borg packs by keyword |
| `borg_observe` | Proactive guidance at task start |
| `borg_try` | Preview a pack before applying |
| `borg_apply` | Execute a pack (start / advance / complete) |
| `borg_feedback` | Record outcome after a pack |
| `borg_suggest` | Get pack suggestions after failures |
| `borg_debug` | Get structured debugging guidance |

---

## 3. CURSOR SETUP

Add to `~/.cursor/mcp.json`:

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

Or using explicit Python:
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

### Verify Cursor sees borg

Restart Cursor. Ask: "What MCP tools do you have available from borg?"

---

## 4. MANUAL MCP CONFIGURATION

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

## 5. CLI QUICK REFERENCE

```bash
# Search for relevant packs
borg search debugging
borg search "null pointer"
borg search django migration

# Get debugging guidance for an error
borg debug 'TypeError: NoneType object has no attribute get'

# List all available packs
borg list

# Show a specific pack
borg show systematic-debugging

# Preview a pack before applying
borg try borg://systematic-debugging

# Apply a pack to your current task
borg apply systematic-debugging --task "Fix login bug where users get 401"

# Record what worked (helps future agents)
borg feedback-v3 --pack systematic-debugging --success yes

# Export pack for your editor
borg generate systematic-debugging --format claude
borg generate systematic-debugging --format cursor
```

---

## 6. TROUBLESHOOTING

### "borg: command not found" after install

```bash
# Check where borg was installed
pip show agent-borg | grep Location

# Try running via python module
python3 -m borg.cli --version

# Or use the full path
~/.local/bin/borg version
```

### "command not found" or server not responding (MCP)

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

3. Use absolute path in your MCP config.

### "ModuleNotFoundError: No module named 'borg'"

This usually means your Python environment is different from where borg was installed.

```bash
# Check which python/pip you're using
which python3
python3 --version

# Reinstall in the correct environment
pipx install agent-borg   # recommended
# or
python3 -m pip install agent-borg --user
```

### Claude Code / Cursor don't show borg tools after setup

1. **Fully restart** the IDE (not just the chat session)
2. Check the IDE's MCP logs (usually in dev tools or console)
3. Verify JSON syntax is valid in the config file
4. Try with absolute path to `borg-mcp` or `python3`

### Still stuck?

```bash
# Run the CLI directly to see errors
borg search "test" 2>&1

# Check version
borg --version
```

For more help, open an issue at: https://github.com/bensargotest-sys/agent-borg/issues

---

## 7. COLD START

On a fresh install, borg ships with a built-in seed corpus so `borg search` returns results immediately — no network required.

If you have `BORG_DISABLE_SEEDS=1` set, seeds are disabled. Unset it to use the built-in corpus.
