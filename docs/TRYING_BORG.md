# Trying Borg

Welcome to **agent-borg** — collective memory for AI coding agents.

## Quick Start

### Installation

```bash
pip install agent-borg
```

### Basic Commands

```bash
# Show all available commands
borg --help

# Configure the Borg MCP server for Claude Code
borg setup-claude

# Search for relevant workflow packs
borg search <query>
borg search systematic-debugging
borg search auth bug

# Observe a task for later searchability
borg observe 'fix django authentication bug' --context 'TypeError on login'
```

## MCP Server Setup

The `borg setup-claude` command configures the Borg MCP server for Claude Code,
enabling tools like `borg_observe`, `borg_search`, and `borg_suggest`.

After running `borg setup-claude`:
1. Restart Claude Code (or reload the MCP server config)
2. Borg MCP tools will be available in your agent session

## Common Troubleshooting

### "python: command not found" or MCP server won't start

If the MCP server fails to start, verify your Python path:

```bash
which python
pip show agent-borg | grep Location
```

Ensure `PYTHONPATH` is set correctly in your MCP config at `~/.config/claude/claude_desktop_config.json`.

### Pack not found

```bash
# Update the local pack index
borg pull <uri>

# List available packs
borg list
```

### Need help?

- GitHub: https://github.com/bensargotest-sys/agent-borg
- Report issues at: https://github.com/bensargotest-sys/agent-borg/issues
