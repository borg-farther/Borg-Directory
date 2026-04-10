# Borg Quickstart Guide

**agent-borg** is collective intelligence for AI agents — a CLI and MCP server that gives your agent access to battle-tested debugging and workflow knowledge. This guide gets you from zero to running your first pack in under 2 minutes.

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

If `borg: command not found`, your pipx/bin directory may not be in PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"      # Linux/macOS
# or find it: python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

---

## 2. CLAUDE CODE SETUP (MCP)

Run the automated setup:
```bash
borg setup-claude
```

This writes the correct MCP configuration to `~/.config/claude/claude_desktop_config.json`.

After `borg setup-claude`, your config contains:
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

**Then fully restart Claude Code** (not just the chat). The borg MCP tools will appear in your available tools.

### What you get:

| Tool | Description |
|------|-------------|
| `borg_search` | Find packs by keyword or semantic similarity |
| `borg_observe` | Proactive guidance at task start |
| `borg_try` | Preview a pack without saving |
| `borg_pull` | Download and save a pack locally |
| `borg_apply` | Execute a pack with phase tracking |
| `borg_feedback` | Record outcome after a pack |
| `borg_publish` | Share packs via GitHub |
| `borg_convert` | Convert SKILL.md / CLAUDE.md / .cursorrules |
| `borg_suggest` | Auto-suggest pack based on frustration signals |
| `borg_debug` | Get structured debugging guidance |

---

## 3. CURSOR SETUP (MCP)

Run the automated setup:
```bash
borg setup-cursor
```

Or configure manually in `~/.cursor/mcp.json`:
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

Restart Cursor. Ask: "What MCP tools do you have from borg?"

---

## 4. YOUR FIRST PACK (search -> try -> apply -> feedback)

### Step 1: Search for packs

```bash
borg search debugging
borg search "null pointer"
borg search django migration
```

On a cold install, borg ships with a built-in seed corpus so search returns results immediately — no network required.

### Step 2: Get debugging guidance for an error

```bash
borg debug 'TypeError: NoneType object has no attribute get'
```

### Step 3: Preview a pack before applying

```bash
borg try borg://systematic-debugging
```

This shows all phases, checkpoints, anti-patterns, and known failure cases.

### Step 4: Apply to your task

```bash
borg apply systematic-debugging --task "Fix login bug where users get 401 after OAuth redirect"
```

### Step 5: Record what worked

```bash
borg feedback-v3 --pack systematic-debugging --success yes
```

This feedback improves future pack suggestions for all agents.

---

## 5. CLI REFERENCE

```bash
# Search
borg search <keywords>                   # Search packs by keyword
borg search ""                            # List all available packs

# Debugging
borg debug 'your error message'           # Get structured debugging guidance
borg debug 'TypeError' --classify         # Just classify the error type

# Packs
borg list                                 # Show local packs
borg show <pack-name>                     # Show pack details
borg try <pack-uri>                       # Preview without saving
borg pull <pack-uri>                      # Download to ~/.hermes/guild/
borg apply <pack-name> --task "<task>"   # Execute pack

# Feedback
borg feedback-v3 --pack <pack> --success yes   # Record success
borg feedback-v3 --pack <pack> --success no    # Record failure

# Export for your editor
borg generate systematic-debugging --format claude    # CLAUDE.md format
borg generate systematic-debugging --format cursor    # .cursorrules format
borg generate systematic-debugging --format windsurf   # .windsurfrules format
borg generate systematic-debugging --format all        # All formats

# Convert existing files to packs
borg convert ./CLAUDE.md
borg convert ./my-skill/SKILL.md --format skill

# Version
borg version
```

---

## 6. COLD START

On a fresh install, borg returns results immediately from its built-in seed corpus (10 packs covering Django errors, Python stdlib, Docker, Git, pytest, and more).

If you want to disable seeds:
```bash
BORG_DISABLE_SEEDS=1 borg search debugging    # Seeds disabled
```

To re-enable: unset `BORG_DISABLE_SEEDS`.

---

## 7. TROUBLESHOOTING

### `borg: command not found` after install

```bash
# Check where borg was installed
pip show agent-borg | grep Location

# Try running via python module
python3 -m borg.cli --version

# Or use the full path
~/.local/bin/borg version
```

### `borg-mcp` not found in Claude Code / Cursor

The `borg-mcp` binary is in your pip bin directory. Find it:
```bash
pip show agent-borg | grep Location
# Then: <Location>/../bin/borg-mcp
```

Use the absolute path in your MCP config:
```json
{
  "mcpServers": {
    "borg": {
      "command": "/home/user/.local/bin/borg-mcp",
      "args": []
    }
  }
}
```

Or use Python directly (the setup-claude command does this automatically):
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

### `ModuleNotFoundError: No module named 'borg'`

Your Python environment is different from where borg was installed.

```bash
pipx install agent-borg   # recommended
# or
python3 -m pip install agent-borg --user
```

### Claude Code / Cursor don't show borg tools after setup

1. Fully restart the IDE (not just the chat session)
2. Check the IDE's MCP logs
3. Verify JSON syntax in the config file
4. Try with absolute path to borg-mcp or python3

### Search returns no matches

```bash
borg search ""    # List ALL available packs
```

If you have `BORG_DISABLE_SEEDS=1` set, unset it. If the remote index is unreachable, the seed corpus still works offline.

---

## 8. MCP TOOL REFERENCE

Full JSON-RPC 2.0 interface over stdio:

### `borg_search`
```json
{"query": "debugging", "mode": "text"}
```
- `mode`: "text" (keyword) | "semantic" (vector, requires agent-borg[embeddings]) | "hybrid"

### `borg_observe`
```json
{"task": "Fix the login bug", "context": "Django + OAuth"}
```
Proactive guidance at task start from proven approaches.

### `borg_try`
```json
{"uri": "borg://systematic-debugging"}
```
Preview without saving to disk.

### `borg_pull`
```json
{"uri": "borg://systematic-debugging"}
```
Download, validate, save to `~/.hermes/guild/`.

### `borg_apply`
```json
{"action": "start", "pack_name": "systematic-debugging", "task": "fix login bug"}
{"action": "advance", "session_id": "...", "phase_name": "trace_error"}
{"action": "complete", "session_id": "...", "outcome": "Fixed"}
```

### `borg_feedback`
```json
{"session_id": "abc123", "outcome": "success", "notes": "Phase 3 was the key"}
```

### `borg_debug`
```json
{"error": "TypeError: 'NoneType' object has no attribute 'foo'"}
```

### `borg_convert`
```json
{"path": "./CLAUDE.md", "format": "auto"}
```
- `format`: "auto" | "skill" | "claude" | "cursorrules" | "cursor" | "cline" | "windsurf"

### `borg_suggest`
```json
{"context": "The agent tried 3 times to fix the OAuth bug", "failure_count": 3}
```
Auto-suggests a pack after repeated failures.

---

## 9. QUICK REFERENCE CARD

```
borg search <query>              Search packs
borg debug <error>               Get debugging guidance
borg list                        Show local packs
borg try <pack-uri>              Preview without saving
borg pull <pack-uri>             Download pack
borg apply <pack> --task <task> Execute pack
borg feedback-v3 --pack <pack> --success yes   Record success
borg feedback-v3 --pack <pack> --success no    Record failure
borg convert <path> [--format]   Convert CLAUDE.md / SKILL.md / .cursorrules
borg generate <pack> --format all             Export pack to all formats
borg version                     Show version
```
