# Borg External Tester Evaluation Guide

This guide is for evaluating the borg system from an external tester perspective. You have deep experience with agents, web3, and FHE cryptography. The system consists of:

- **CLI**: `borg`
- **Python API**: `import borg`
- **MCP Server**: `borg-mcp`
- **Repo**: `agent-borg`

Estimated time: **20-30 minutes**

---

## SUCCESS CRITERIA

All items below must pass. Check each box as you verify it.

### Installation
- [ ] `pip install agent-borg` installs without errors

### CLI Basic Commands
- [ ] `borg version` shows a version number
- [ ] `borg search debugging` returns results
- [ ] `borg try borg://systematic-debugging` shows pack preview
- [ ] `borg pull borg://systematic-debugging` saves locally
- [ ] `borg apply systematic-debugging --task 'fix a bug'` starts a session

### MCP Server (borg-mcp)
- [ ] `borg-mcp` responds to `tools/list` with 10 tools

### Agent Integration (Claude Code or Cursor)
- [ ] Agent can call `borg_search` via MCP
- [ ] Agent can call `borg_try` via MCP
- [ ] Agent can call `borg_apply` via MCP and get phase instructions
- [ ] Agent can call `borg_feedback` after completing phases
- [ ] Agent can call `borg_suggest` when stuck

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
pip install agent-borg
```

**Expected output**: No errors, ends with `Successfully installed agent-borg-X.X.X`

**What to check**:
- No `ModuleNotFoundError` or `ERROR`
- If you see `WARNING: scripts are not installed with --user...`, use `--break-system-packages` flag

**If it fails**: Try `pip install --break-system-packages agent-borg`

---

### Step 2: Verify CLI Works

```bash
borg version
```

**Expected output**: Something like `borg 2.0.2`

**If it fails**: The CLI binary might not be in PATH. Try:
```bash
pip show agent-borg | grep Location
# Then check <Location>/../bin/borg
```

---

### Step 3: Search for Packs

```bash
borg search debugging
```

**Expected output**: JSON with `success: true` and a `matches` array containing pack entries like:
```json
{
  "success": true,
  "matches": [
    {
      "id": "borg://converted/systematic-debugging",
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
borg try borg://systematic-debugging
```

**Expected output**: 
- Full pack content with all phases
- Safety scan results (may show 0 threats)
- Trust tier and confidence level
- Required inputs and proof gate status

**If it fails with "Safety threats detected"**: This is a known false positive issue — the safety scanner is overly strict. Use `borg try` anyway to preview the pack content.

---

### Step 5: Pull a Pack (download locally)

```bash
borg pull borg://systematic-debugging
```

**Expected output**: Success message confirming the pack was saved to `~/.hermes/borg/systematic-debugging/pack.yaml`

**If it fails**: Check that `~/.hermes/borg/` is writable

---

### Step 6: Apply a Pack

```bash
borg apply systematic-debugging --task 'fix a bug'
```

**Expected output**:
- An approval summary showing confidence and tier
- A `session_id` for tracking
- Phase instructions for the first phase

**If it fails**: Make sure you pulled the pack first (`borg pull`)

---

### Step 7: MCP Server — Count Tools

Test the MCP server responds correctly with all 10 tools:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | borg-mcp
```

Then call `tools/list`:
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | borg-mcp
```

**Expected output**: JSON-RPC response containing 10 tools:
1. `borg_search`
2. `borg_pull`
3. `borg_try`
4. `borg_init`
5. `borg_apply`
6. `borg_feedback`
7. `borg_publish`
8. `borg_convert`
9. `borg_suggest`
10. `borg_list`

**If it fails**: The MCP binary might not be in PATH. Find it with:
```bash
pip show agent-borg | grep Location
ls <Location>/../bin/borg-mcp
```

---

### Step 8: MCP Integration with Claude Code

**Configure Claude Code MCP**:

Add to `~/.config/claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp"
    }
  }
}
```

**Restart Claude Code** and verify the borg tools appear in your available tools.

**Test each tool via Claude Code**:

1. **borg_search**: Ask Claude Code to search for a debugging pack
2. **borg_try**: Ask it to preview a specific pack
3. **borg_apply**: Ask it to start applying a pack to a task
4. **borg_feedback**: After completing phases, ask it to submit feedback
5. **borg_suggest**: When stuck, ask for a pack suggestion

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
   borg version
   pip show agent-borg
   ```

---

## KNOWN LIMITATIONS

### Requires gh CLI (GitHub CLI)
The following features require `gh` to be installed and authenticated:
- `borg publish` — creates GitHub PRs
- `borg search` — fetches remote pack index (falls back to local-only without gh)

To check: `gh auth status`

### Requires numpy for Semantic Search
Semantic (vector) search requires the `embeddings` extra:
```bash
pip install agent-borg[embeddings]
```
Without it, `borg_search` falls back to text matching.

### Safety Scan False Positives
The safety scanner sometimes blocks legitimate packs with false positives on:
- Code blocks containing words like "ignore", "forget", "system"
- Markdown with specific patterns

Workaround: Use `borg try <uri>` to preview any pack — `try` still shows content even when the scanner triggers.

### MCP Server Requires stdio
The MCP server communicates over stdin/stdout. Some Claude Code configurations may have issues with this. If the server doesn't respond:
1. Try using the absolute path to `borg-mcp`
2. Ensure no other program is reading from stdin

### Pack Directory Structure
Packs must be in `~/.hermes/borg/<pack-name>/pack.yaml`. If you manually create packs, ensure this directory structure is followed.

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
cd /root/hermes-workspace/borg
python -m pytest borg/tests/ -v --tb=short
```

---

## QUICK COMMAND REFERENCE

```bash
# Installation
pip install agent-borg

# CLI commands
borg version                     # Show version
borg search <query>              # Search packs
borg try borg://<pack>           # Preview pack
borg pull borg://<pack>          # Download pack
borg list                        # List local packs
borg apply <pack> --task '<task>' # Execute pack
borg feedback <session_id>       # Generate feedback
borg publish <path>              # Publish to GitHub
borg convert <file> [--format]   # Convert existing files

# MCP server
borg-mcp                         # Run MCP server (stdio)
```
