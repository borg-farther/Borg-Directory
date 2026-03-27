# Guild-v2 External Tester Evaluation Guide

This guide is for evaluating the guild-v2 system from an external tester perspective. You have deep experience with agents, web3, and FHE cryptography. The system consists of:

- **CLI**: `guildpacks` (renamed from `guild` to avoid conflicts)
- **Python API**: `import guild`
- **MCP Server**: `guild-mcp`
- **Repo**: `bensargotest-sys/guild-packs`

Estimated time: **20-30 minutes**

---

## SUCCESS CRITERIA

All items below must pass. Check each box as you verify it.

### Installation
- [ ] `pip install guild-packs` installs without errors

### CLI Basic Commands
- [ ] `guildpacks version` shows a version number
- [ ] `guildpacks search debugging` returns results
- [ ] `guildpacks try guild://systematic-debugging` shows pack preview
- [ ] `guildpacks pull guild://systematic-debugging` saves locally
- [ ] `guildpacks apply systematic-debugging --task 'fix a bug'` starts a session

### MCP Server (guild-mcp)
- [ ] `guild-mcp` responds to `tools/list` with 9 tools

### Agent Integration (Claude Code or Cursor)
- [ ] Agent can call `guild_search` via MCP
- [ ] Agent can call `guild_try` via MCP
- [ ] Agent can call `guild_apply` via MCP and get phase instructions
- [ ] Agent can call `guild_feedback` after completing phases
- [ ] Agent can call `guild_suggest` when stuck

---

## VERIFICATION STEPS

### Prerequisites

You need:
- Python 3.10+
- pip or pipx
- GitHub CLI (`gh`) authenticated (for publishing only)
- Claude Code or Cursor IDE with MCP support

---

### Step 1: Installation

```bash
pip install guild-packs
```

**Expected output**: No errors, ends with `Successfully installed guild-packs-X.X.X`

**What to check**:
- No `ModuleNotFoundError` or `ERROR`
- If you see `WARNING: scripts are not installed with --user...`, use `--break-system-packages` flag

**If it fails**: Try `pip install --break-system-packages guild-packs`

---

### Step 2: Verify CLI Works

```bash
guildpacks version
```

**Expected output**: Something like `guildpacks 2.0.2`

**If it fails**: The CLI binary might not be in PATH. Try:
```bash
pip show guild-packs | grep Location
# Then check <Location>/../bin/guildpacks
```

---

### Step 3: Search for Packs

```bash
guildpacks search debugging
```

**Expected output**: JSON with `success: true` and a `matches` array containing pack entries like:
```json
{
  "success": true,
  "matches": [
    {
      "id": "guild://converted/systematic-debugging",
      "name": "systematic-debugging",
      "problem_class": "Use when encountering any bug...",
      "tier": "COMMUNITY",
      "phase_count": 8
    }
  ]
}
```

**If it fails**: 
- Network issue — check your internet connection
- GitHub rate limit — run `gh auth status` to check authentication

---

### Step 4: Preview a Pack (try)

```bash
guildpacks try guild://systematic-debugging
```

**Expected output**: 
- Full pack content with all phases
- Safety scan results (may show 0 threats)
- Trust tier and confidence level
- Required inputs and proof gate status

**If it fails with "Safety threats detected"**: This is a known false positive issue — the safety scanner is overly strict. Use `guildpacks try` anyway to preview the pack content.

---

### Step 5: Pull a Pack (download locally)

```bash
guildpacks pull guild://systematic-debugging
```

**Expected output**: Success message confirming the pack was saved to `~/.hermes/guild/systematic-debugging/pack.yaml`

**If it fails**: Check that `~/.hermes/guild/` is writable

---

### Step 6: Apply a Pack

```bash
guildpacks apply systematic-debugging --task 'fix a bug'
```

**Expected output**:
- An approval summary showing confidence and tier
- A `session_id` for tracking
- Phase instructions for the first phase

**If it fails**: Make sure you pulled the pack first (`guildpacks pull`)

---

### Step 7: MCP Server — Count Tools

Test the MCP server responds correctly with all 9 tools:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | guild-mcp
```

Then call `tools/list`:
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | guild-mcp
```

**Expected output**: JSON-RPC response containing 9 tools:
1. `guild_search`
2. `guild_pull`
3. `guild_try`
4. `guild_init`
5. `guild_apply`
6. `guild_feedback`
7. `guild_publish`
8. `guild_convert`
9. `guild_suggest`

**If it fails**: The MCP binary might not be in PATH. Find it with:
```bash
pip show guild-packs | grep Location
ls <Location>/../bin/guild-mcp
```

---

### Step 8: MCP Integration with Claude Code

**Configure Claude Code MCP**:

Add to `~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "guild-packs": {
      "command": "guild-mcp"
    }
  }
}
```

**Restart Claude Code** and verify the guild tools appear in your available tools.

**Test each tool via Claude Code**:

1. **guild_search**: Ask Claude Code to search for a debugging pack
2. **guild_try**: Ask it to preview a specific pack
3. **guild_apply**: Ask it to start applying a pack to a task
4. **guild_feedback**: After completing phases, ask it to submit feedback
5. **guild_suggest**: When stuck, ask for a pack suggestion

**Expected**: Claude Code should be able to call these tools and return structured JSON responses.

---

## HOW TO REPORT ISSUES

When you find something that doesn't work:

1. **Capture the exact command and output**
2. **Note your environment**:
   - OS and version
   - Python version (`python3 --version`)
   - pip/pipx installation method
3. **Note whether gh CLI is authenticated** (`gh auth status`)
4. **Check if it's reproducible** — try twice to confirm
5. **Report to**: The project maintainers with the output from:
   ```bash
   guildpacks version
   pip show guild-packs
   ```

---

## KNOWN LIMITATIONS

### Requires gh CLI (GitHub CLI)
The following features require `gh` to be installed and authenticated:
- `guildpacks publish` — creates GitHub PRs
- `guildpacks search` — fetches remote pack index (falls back to local-only without gh)

To check: `gh auth status`

### Requires numpy for Semantic Search
Semantic (vector) search requires the `embeddings` extra:
```bash
pip install guild-packs[embeddings]
```
Without it, `guild_search` falls back to text matching.

### Safety Scan False Positives
The safety scanner sometimes blocks legitimate packs with false positives on:
- Code blocks containing words like "ignore", "forget", "system"
- Markdown with specific patterns

Workaround: Use `guildpacks try <uri>` to preview any pack — `try` still shows content even when the scanner triggers.

### MCP Server Requires stdio
The MCP server communicates over stdin/stdout. Some Claude Code configurations may have issues with this. If the server doesn't respond:
1. Try using the absolute path to `guild-mcp`
2. Ensure no other program is reading from stdin

### Pack Directory Structure
Packs must be in `~/.hermes/guild/<pack-name>/pack.yaml`. If you manually create packs, ensure this directory structure is followed.

### Privacy Scanning
The privacy scanner automatically redacts:
- Email addresses
- API keys (sk-, ak-, etc.)
- Potential secrets in text

This is by design — published packs will have this data redacted.

---

## TEST SUITE

To run the internal test suite:
```bash
cd /root/hermes-workspace/guild-v2
python -m pytest guild/tests/ -v --tb=short
```

**Expected**: All tests pass (669 tests as of this writing)

---

## QUICK COMMAND REFERENCE

```bash
# Installation
pip install guild-packs

# CLI commands
guildpacks version                     # Show version
guildpacks search <query>               # Search packs
guildpacks try guild://<pack>           # Preview pack
guildpacks pull guild://<pack>         # Download pack
guildpacks list                         # List local packs
guildpacks apply <pack> --task '<task>' # Execute pack
guildpacks feedback <session_id>        # Generate feedback
guildpacks publish <path>               # Publish to GitHub
guildpacks convert <file> [--format]   # Convert existing files

# MCP server
guild-mcp                              # Run MCP server (stdio)
```
