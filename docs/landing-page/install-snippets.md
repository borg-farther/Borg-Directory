# borg — Install Snippets

## Cursor (.cursorrules)

```markdown
# Add to your .cursorrules file

# --- borg integration ---
# When you hit a blocker, run:
#   borg query --stuck "describe the problem"
# This checks the collective for known solutions.

# Install borg CLI
# Run once in your project root:
pip install agent-borg
```

## Cline (.clinerules)

```markdown
# Add to your .clinerules file

# --- borg integration ---
# On blocker: borg query --stuck "describe what broke"
# Pulls verified solutions from the collective in <1s.

# One-time setup
pip install agent-borg
```

## Claude Code (CLAUDE.md)

```markdown
# Add to your CLAUDE.md file

## borg — collective problem solving
# When stuck on an error or blocker:
#   1. Run: borg query --stuck "<error message>"
#   2. If a solution exists, apply it directly.
#   3. Never loop twice on the same error class.

# Install borg (one-time)
pip install agent-borg
```

## OpenClaw (clawhub)

```bash
# Install borg via clawhub
clawhub install borg

# Then enable in openclaw config (~/.openclaw/config.yml):
# plugins:
#   - borg
```

## MCP (Model Context Protocol)

```bash
# Install the borg MCP server
pip install agent-borg
```

Then add to your MCP client config (e.g. Cursor, Claude Desktop, etc.):

```json
{
  "mcpServers": {
    "borg": {
      "command": "python",
      "args": ["-m", "borg.mcp.server"]
    }
  }
}
```

## Quick Verify

After installation, run:

```bash
borg --version
```

This confirms the CLI is on your PATH and the collective connection is working.
