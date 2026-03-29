# Borg Quickstart Guide

Borg are **proven AI agent workflows** — execution-tested, safety-scanned, and feedback-improving. This guide gets you from zero to running your first pack in under 2 minutes.

**agent-borg** | CLI: `borg` | MCP: `borg-mcp`

---

## 1. INSTALLATION

Borg requires Python 3.10+.

```bash
# Install via pip (one of these methods)
pip install agent-borg                    # system-wide (may need --break-system-packages)
pipx install agent-borg                  # recommended — isolated environment
pip install --user agent-borg            # user-local
```

**Verify installation:**
```bash
borg version
# Expected output: borg 2.0.0
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

Add this to your Claude Code MCP settings file:

**Location:** `~/.config/claude/claude_desktop_config.json`

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

### Step 2: Restart Claude Code

After editing the config, restart Claude Code. The borg tools will appear in your available tools.

### What you get:

| Tool | Description |
|------|-------------|
| `borg_search` | Find packs by keyword or semantic similarity |
| `borg_pull` | Download and save a pack locally |
| `borg_try` | Preview a pack without saving |
| `borg_init` | Scaffold a new pack |
| `borg_apply` | Execute a pack with phase tracking |
| `borg_feedback` | Generate feedback from a session |
| `borg_publish` | Share packs via GitHub |
| `borg_convert` | Convert SKILL.md / CLAUDE.md / .cursorrules to a pack |
| `borg_suggest` | Auto-suggest a pack based on frustration signals |
| `borg_list` | List local packs |

---

## 3. CURSOR SETUP (MCP)

Cursor IDE supports MCP servers natively.

### Step 1: Configure MCP

Create or edit `~/.cursor/mcp.json`:

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

### Step 2: Restart Cursor

After restarting, borg tools are available in Cursor's AI context.

---

## 4. YOUR FIRST PACK (search → try → pull → apply)

### Step 1: Search for packs

```bash
borg search debugging
```

Example output:
```json
{
  "success": true,
  "matches": [
    {
      "id": "borg://converted/systematic-debugging",
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
borg try borg://hermes/systematic-debugging
```

This shows:
- All phases and their descriptions
- Safety scan results
- Trust tier and confidence level
- Required inputs
- Proof gate status

### Step 3: Pull to local storage

```bash
borg pull borg://hermes/systematic-debugging
```

Packs are saved to `~/.hermes/borg/<pack-name>/pack.yaml`.

> **Note:** Some packs may fail the safety scan (false positives on code/markdown patterns). This is a known issue — the safety scanner is overly strict on certain content. You can still use `borg try` to preview any pack.

### Step 4: Apply to your task

```bash
borg apply systematic-debugging --task "Fix login bug where users get 401 after OAuth redirect"
```

The apply command:
1. Loads the pack
2. Returns an approval summary
3. Tracks phases as you execute

### List your local packs

```bash
borg list
```

---

## 5. GIVE FEEDBACK

After applying a pack, generate feedback to improve it:

```bash
# After completing a pack execution, note the session_id from apply output
borg feedback <session_id>
```

Feedback helps:
- Validate which phases worked/didn't work
- Update confidence scores
- Improve future pack versions

---

## 6. CREATE YOUR OWN (convert existing CLAUDE.md or skill)

### Convert a CLAUDE.md

```bash
borg convert ./CLAUDE.md
```

### Convert a SKILL.md

```bash
borg convert ./my-skill/SKILL.md --format skill
```

### Convert a .cursorrules file

```bash
borg convert ./.cursorrules --format cursorrules
```

### Convert automatically (auto-detects format)

```bash
borg convert ./path/to/CLAUDE.md --format auto
```

The converter outputs a `pack.yaml` — review it, edit the phases, then publish.

---

## 7. PUBLISH (share with the community)

### Prerequisites
- GitHub CLI authenticated: `gh auth status`
- Your pack lives in `~/.hermes/borg/<pack-name>/pack.yaml`

### Publish

```bash
borg publish ~/.hermes/borg/my-pack/pack.yaml
```

This creates a GitHub PR with:
- Proof gate validation
- Safety scan
- Pack review

### What gets published

- Workflow packs (`pack.yaml`)
- Feedback artifacts from pack executions

---

## 8. TROUBLESHOOTING

### `borg: command not found`

```bash
# Check if pipx is installed and in PATH
which pipx || echo "pipx not installed"
pipx ensurepath   # adds ~/.local/bin to PATH

# Or use full path
~/.local/bin/borg version
```

### `borg-mcp` not found in Claude Code / Cursor

The `borg-mcp` binary is installed to your pip bin directory. Find it:

```bash
python3 -c "import sys; print([p for p in sys.path if 'dist-packages' in p][0] + '/../../../bin/borg-mcp')"
# Or:
pip show agent-borg | grep Location
# Then: <Location>/../bin/borg-mcp
```

Use the absolute path in your MCP config:

```json
{
  "mcpServers": {
    "borg": {
      "command": "/home/user/.local/bin/borg-mcp"
    }
  }
}
```

### Safety scan blocks a pack (false positive)

**Symptom:** `borg pull` or `borg apply` returns `"Safety threats detected: Prompt injection detected"`

**Cause:** The safety scanner is overly strict on code blocks and markdown patterns. Many legitimate packs trigger this.

**Workaround:** Use `borg try <uri>` to preview any pack — `try` still performs the safety scan but doesn't block you from seeing the content. The `pull` and `apply` commands are affected by this known issue.

### MCP server doesn't respond

The MCP server uses stdio (stdin/stdout). If Claude Code or Cursor shows "MCP server not responding":

1. Test the MCP server manually:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | borg-mcp
```

2. If no output, check Python path:
```bash
borg-mcp  # Should output JSON-RPC responses on stdio
```

### Python path issues with borg module

If you see `ModuleNotFoundError: No module named 'borg'` when using the CLI directly, this is a pipx/pip installation quirk. Using `borg` via the installed bin wrapper should work. If not:

```bash
pipx run borg version   # runs in isolated venv
# or
python3 -m borg.cli version
```

### Search returns no matches

```bash
borg search ""    # List ALL available packs
```

The index is fetched from GitHub on first use. If you have network issues, you may see fewer packs.

---

## MCP Tool Reference

Full JSON-RPC 2.0 interface over stdio:

### `borg_search`
```json
{"query": "debugging", "mode": "text"}
```
- `mode`: "text" (keyword) | "semantic" (vector, requires embeddings) | "hybrid"

### `borg_try`
```json
{"uri": "borg://hermes/systematic-debugging"}
```
Preview without saving.

### `borg_pull`
```json
{"uri": "borg://hermes/systematic-debugging"}
```
Download, validate, save to `~/.hermes/borg/`.

### `borg_init`
```json
{"pack_name": "my-workflow", "problem_class": "reasoning", "mental_model": "slow-thinker"}
```

### `borg_apply`
```json
{"action": "start", "pack_name": "systematic-debugging", "task": "fix login bug"}
{"action": "checkpoint", "session_id": "...", "phase_name": "phase_1", "status": "passed", "evidence": "..."}
{"action": "complete", "session_id": "...", "outcome": "Fixed successfully"}
```

### `borg_convert`
```json
{"path": "./CLAUDE.md", "format": "auto"}
```
- `format`: "auto" | "skill" | "claude" | "cursorrules"

### `borg_publish`
```json
{"action": "publish", "pack_name": "my-pack"}
{"action": "list"}
```

### `borg_feedback`
```json
{"session_id": "abc123", "what_changed": "Added phase for edge cases", "where_to_reuse": "API debugging scenarios"}
```

---

## Quick Reference Card

```
borg search <query>              Search packs
borg try <uri>                   Preview without saving
borg pull <uri>                  Download pack
borg list                        Show local packs
borg apply <pack> --task <task>  Execute pack
borg feedback <session_id>       Generate feedback
borg convert <path> [--format]   Convert CLAUDE.md / SKILL.md / .cursorrules
borg publish <path>              Share on GitHub
borg version                     Show version
```
