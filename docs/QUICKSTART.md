# Guild-Packs Quickstart Guide

Guild-packs are **proven AI agent workflows** — execution-tested, safety-scanned, and feedback-improving. This guide gets you from zero to running your first pack in under 2 minutes.

**guild-packs 2.0.0** | GitHub: `bensargotest-sys/guild-packs` | CLI: `guildpacks` | MCP: `guild-mcp`

---

## 1. INSTALLATION

Guild-packs requires Python 3.10+.

```bash
# Install via pip (one of these methods)
pip install guild-packs                    # system-wide (may need --break-system-packages)
pipx install guild-packs                   # recommended — isolated environment
pip install --user guild-packs             # user-local
```

**Verify installation:**
```bash
guildpacks version
# Expected output: guildpacks 2.0.0
```

If `guildpacks: command not found`, your pipx/bin directory may not be in PATH. Add it:
```bash
export PATH="$HOME/.local/bin:$PATH"      # Linux/macOS
# or find it: python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

---

## 2. CLAUDE CODE SETUP (MCP)

Guild-packs works as an MCP server, giving Claude Code access to guild tools.

### Step 1: Configure MCP

Add this to your Claude Code MCP settings file:

**Location:** `~/.config/claude/claude_desktop_config.json`

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

### Step 2: Restart Claude Code

After editing the config, restart Claude Code. The guild tools will appear in your available tools.

### What you get:

| Tool | Description |
|------|-------------|
| `guild_search` | Find packs by keyword or semantic similarity |
| `guild_pull` | Download and save a pack locally |
| `guild_try` | Preview a pack without saving |
| `guild_init` | Scaffold a new pack |
| `guild_apply` | Execute a pack with phase tracking |
| `guild_feedback` | Generate feedback from a session |
| `guild_publish` | Share packs via GitHub |
| `guild_convert` | Convert SKILL.md / CLAUDE.md / .cursorrules to a pack |
| `guild_suggest` | Auto-suggest a pack based on frustration signals |

---

## 3. CURSOR SETUP (MCP)

Cursor IDE supports MCP servers natively.

### Step 1: Configure MCP

Create or edit `~/.cursor/mcp.json`:

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

### Step 2: Restart Cursor

After restarting, guild tools are available in Cursor's AI context.

---

## 4. YOUR FIRST PACK (search → try → pull → apply)

### Step 1: Search for packs

```bash
guildpacks search debugging
```

Example output:
```json
{
  "success": true,
  "matches": [
    {
      "id": "guild://converted/systematic-debugging",
      "name": "systematic-debugging",
      "problem_class": "Use when encountering any bug, test failure, or unexpected behavior",
      "tier": "COMMUNITY",
      "phase_count": 8
    }
  ]
}
```

### Step 2: Preview without saving (try)

```bash
guildpacks try guild://hermes/systematic-debugging
```

This shows:
- All phases and their descriptions
- Safety scan results
- Trust tier and confidence level
- Required inputs
- Proof gate status

### Step 3: Pull to local storage

```bash
guildpacks pull guild://hermes/systematic-debugging
```

Packs are saved to `~/.hermes/guild/<pack-name>/pack.yaml`.

> **Note:** Some packs may fail the safety scan (false positives on code/markdown patterns). This is a known issue — the safety scanner is overly strict on certain content. You can still use `guildpacks try` to preview any pack.

### Step 4: Apply to your task

```bash
guildpacks apply systematic-debugging --task "Fix login bug where users get 401 after OAuth redirect"
```

The apply command:
1. Loads the pack
2. Returns an approval summary
3. Tracks phases as you execute

### List your local packs

```bash
guildpacks list
```

---

## 5. GIVE FEEDBACK

After applying a pack, generate feedback to improve it:

```bash
# After completing a pack execution, note the session_id from apply output
guildpacks feedback <session_id>
```

Feedback helps:
- Validate which phases worked/didn't work
- Update confidence scores
- Improve future pack versions

---

## 6. CREATE YOUR OWN (convert existing CLAUDE.md or skill)

### Convert a CLAUDE.md

```bash
guildpacks convert ./CLAUDE.md
```

### Convert a SKILL.md

```bash
guildpacks convert ./my-skill/SKILL.md --format skill
```

### Convert a .cursorrules file

```bash
guildpacks convert ./.cursorrules --format cursorrules
```

### Convert automatically (auto-detects format)

```bash
guildpacks convert ./path/to/CLAUDE.md --format auto
```

The converter outputs a `pack.yaml` — review it, edit the phases, then publish.

---

## 7. PUBLISH (share with the community)

### Prerequisites
- GitHub CLI authenticated: `gh auth status`
- Your pack lives in `~/.hermes/guild/<pack-name>/pack.yaml`

### Publish

```bash
guildpacks publish ~/.hermes/guild/my-pack/pack.yaml
```

This creates a GitHub PR to `bensargotest-sys/guild-packs` with:
- Proof gate validation
- Safety scan
- Pack review

### What gets published

- Workflow packs (`pack.yaml`)
- Feedback artifacts from pack executions

---

## 8. TROUBLESHOOTING

### `guildpacks: command not found`

```bash
# Check if pipx is installed and in PATH
which pipx || echo "pipx not installed"
pipx ensurepath   # adds ~/.local/bin to PATH

# Or use full path
~/.local/bin/guildpacks version
```

### `guild-mcp` not found in Claude Code / Cursor

The `guild-mcp` binary is installed to your pip bin directory. Find it:

```bash
python3 -c "import sys; print([p for p in sys.path if 'dist-packages' in p][0] + '/../../../bin/guild-mcp')"
# Or:
pip show guild-packs | grep Location
# Then: <Location>/../bin/guild-mcp
```

Use the absolute path in your MCP config:

```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "/home/user/.local/bin/guild-mcp"
    }
  }
}
```

### Safety scan blocks a pack (false positive)

**Symptom:** `guildpacks pull` or `guildpacks apply` returns `"Safety threats detected: Prompt injection detected"`

**Cause:** The safety scanner is overly strict on code blocks and markdown patterns. Many legitimate packs trigger this.

**Workaround:** Use `guildpacks try <uri>` to preview any pack — `try` still performs the safety scan but doesn't block you from seeing the content. The `pull` and `apply` commands are affected by this known issue.

### MCP server doesn't respond

The MCP server uses stdio (stdin/stdout). If Claude Code or Cursor shows "MCP server not responding":

1. Test the MCP server manually:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | guild-mcp
```

2. If no output, check Python path:
```bash
guild-mcp  # Should output JSON-RPC responses on stdio
```

### Python path issues with guild module

If you see `ModuleNotFoundError: No module named 'guild'` when using the CLI directly, this is a pipx/pip installation quirk. Using `guildpacks` via the installed bin wrapper should work. If not:

```bash
pipx run guildpacks version   # runs in isolated venv
# or
python3 -m guild.cli version
```

### Search returns no matches

```bash
guildpacks search ""    # List ALL available packs
```

The index is fetched from GitHub on first use. If you have network issues, you may see fewer packs.

---

## MCP Tool Reference

Full JSON-RPC 2.0 interface over stdio:

### `guild_search`
```json
{"query": "debugging", "mode": "text"}
```
- `mode`: "text" (keyword) | "semantic" (vector, requires embeddings) | "hybrid"

### `guild_try`
```json
{"uri": "guild://hermes/systematic-debugging"}
```
Preview without saving.

### `guild_pull`
```json
{"uri": "guild://hermes/systematic-debugging"}
```
Download, validate, save to `~/.hermes/guild/`.

### `guild_init`
```json
{"pack_name": "my-workflow", "problem_class": "reasoning", "mental_model": "slow-thinker"}
```

### `guild_apply`
```json
{"action": "start", "pack_name": "systematic-debugging", "task": "fix login bug"}
{"action": "checkpoint", "session_id": "...", "phase_name": "phase_1", "status": "passed", "evidence": "..."}
{"action": "complete", "session_id": "...", "outcome": "Fixed successfully"}
```

### `guild_convert`
```json
{"path": "./CLAUDE.md", "format": "auto"}
```
- `format`: "auto" | "skill" | "claude" | "cursorrules"

### `guild_publish`
```json
{"action": "publish", "pack_name": "my-pack"}
{"action": "list"}
```

### `guild_feedback`
```json
{"session_id": "abc123", "what_changed": "Added phase for edge cases", "where_to_reuse": "API debugging scenarios"}
```

---

## Quick Reference Card

```
guildpacks search <query>              Search packs
guildpacks try <uri>                   Preview without saving
guildpacks pull <uri>                  Download pack
guildpacks list                        Show local packs
guildpacks apply <pack> --task <task>  Execute pack
guildpacks feedback <session_id>       Generate feedback
guildpacks convert <path> [--format]   Convert CLAUDE.md / SKILL.md / .cursorrules
guildpacks publish <path>              Share on GitHub
guildpacks version                     Show version
```
