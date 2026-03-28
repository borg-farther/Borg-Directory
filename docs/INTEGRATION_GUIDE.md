# Borg MCP Integration Guide

**Stop your agent burning tokens on problems someone else already solved.**

Borg gives your AI agent a memory of solved problems. When your agent hits an error, it calls `borg_observe` — and if someone has already faced that error and published a fix pack, your agent applies it in seconds instead of spending tokens debugging.

This guide covers setup for three platforms: Hermes/Claude Code, Cursor, and Cline.

---

## QUICKSTART (All Platforms)

These steps work regardless of which platform you use.

### 1. Install the Package

```bash
pip install agent-borg
```

### 2. Configure Your MCP Server

Copy the appropriate config block for your platform (see the platform-specific sections below).

### 3. Test the Connection

```bash
python -m borg.integrations.mcp_server
```

Press Ctrl+C to exit. If it starts without import errors, the server is ready.

### 4. Verify Tools Are Registered

Your agent should now have access to these 13 tools:

| Tool | Purpose |
|------|---------|
| `borg_search` | Search the pack index by query |
| `borg_pull` | Download and install a pack by URI |
| `borg_try` | Attempt to apply a pack to current project |
| `borg_observe` | Record a task/situation; get pack suggestions |
| `borg_suggest` | Get pack suggestions for an error message |
| `borg_recall` | Look up a previously observed error |
| `borg_context` | Get relevant files/changes from the last N hours |
| `borg_publish` | List or publish packs to the registry |
| `borg_feedback` | Submit feedback on a pack |
| `borg_init` | Create a new pack from your current session |
| `borg_convert` | Convert a markdown doc to a pack |
| `borg_reputation` | Query agent/pack reputation scores |
| `borg_apply` | Apply a published pack to the current session |

### 5. Run an Example Workflow

When your agent encounters an error:

1. Agent calls `borg_observe(task="fix authentication bug in Django")`
2. Borg searches the index for matching packs
3. If a pack is found, returns `{ success: true, pack: {...} }`
4. Agent calls `borg_apply(pack_uri="gh:org/pack-name@v1.2.3")`
5. Fix is applied — no token burn on debugging

---

## Platform: Hermes / Claude Code

**Config file:** `~/.hermes/config.yaml`

### Add This Config

```yaml
mcp_servers:
  borg-mcp:
    enabled: true
    command: python
    args:
      - -m
      - borg.integrations.mcp_server
    env:
      PYTHONPATH: /root/hermes-workspace/guild-v2
```

### Verify It Works

Start a Claude Code session and run:

```
/mcp list
```

You should see `borg-mcp` listed as an available server.

Or in a Claude Code prompt, try:

```
Call borg_search with query "Django authentication error"
```

Expected response:
```json
{
  "success": true,
  "results": [
    {
      "uri": "gh:halford4d/django-auth-fix@v1.0.0",
      "name": "Django Auth Bug Fix Pack",
      "description": "Fixes a common TypeError in Django.contrib.auth import",
      "relevance_score": 0.94
    }
  ]
}
```

### What Tools Become Available

All 13 tools listed above are available to any Claude Code agent through the MCP protocol. The `mcp_servers` block in `~/.hermes/config.yaml` makes them available system-wide.

### Example Workflow in Claude Code

```
You: fix the authentication bug in my Django project

Agent: *encounters error*
Agent: calling borg_observe(task="fix authentication bug in Django project")

Response: {
  "success": true,
  "suggestions": [
    {
      "uri": "gh:halford4d/django-auth-fix@v1.0.0",
      "name": "Django Auth Bug Fix Pack",
      "relevance_score": 0.94,
      "description": "Patches TypeError when django.contrib.auth is imported incorrectly"
    }
  ]
}

Agent: calling borg_apply(action="apply", pack_uri="gh:halford4d/django-auth-fix@v1.0.0")

Response: {
  "success": true,
  "message": "Pack applied successfully. Modified: auth/decorators.py, auth/middleware.py"
}

Agent: *fix applied* — continuing with your request
```

---

## Platform: Cursor

**Config file:** `<your-project>/.cursor/mcp.json`

Cursor uses project-level MCP configuration. Create the file in your project root if it does not exist.

### Add This Config

```json
{
  "mcp_servers": {
    "borg-mcp": {
      "command": "python",
      "args": [
        "-m",
        "borg.integrations.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/root/hermes-workspace/guild-v2"
      }
    }
  }
}
```

### Verify It Works

1. Open Cursor and go to **Settings → MCP** (or search for "MCP" in settings)
2. You should see `borg-mcp` listed with a green "connected" status
3. In any chat, try using `Cmd+K` / `Ctrl+K` to invoke an MCP tool

Alternatively, use the Cursor terminal:

```bash
cd /path/to/your/project
python -m borg.integrations.mcp_server
```

If it starts without import errors, the connection is ready.

### What Tools Become Available

All 13 tools are available in Cursor's AI Chat and Agent modes. Look for the MCP tool picker (hammer icon or `Cmd+K`).

### Example Workflow in Cursor

```
You (in Cursor Chat): Fix the Django authentication error

Cursor Agent: *detects the error*
Cursor Agent: → calls borg_observe(task="Django authentication TypeError")
  ← { success: true, suggestions: [{ uri: "gh:halford4d/django-auth-fix", score: 0.94 }] }

Cursor Agent: → calls borg_apply(action="apply", pack_uri="gh:halford4d/django-auth-fix@v1.0.0")
  ← { success: true, modified: ["auth/decorators.py"] }

Cursor Agent: Fixed. The pack patched the incorrect import in auth/decorators.py.
```

---

## Platform: Cline

**Config file:** VS Code Settings (`settings.json`) or `.vscode/mcp.json` in the workspace

Cline uses VS Code's MCP configuration. You can configure it in:

- **Global:** `~/.config/Code/User/settings.json` (Linux) or equivalent
- **Workspace:** `<project>/.vscode/mcp.json`

### Add This Config (Global)

Open your VS Code settings JSON (`Cmd+,` or `Ctrl+,` then "Open Settings JSON"):

```json
{
  "mcp.servers": {
    "borg-mcp": {
      "command": "python",
      "args": [
        "-m",
        "borg.integrations.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/root/hermes-workspace/guild-v2"
      }
    }
  }
}
```

### Add This Config (Workspace-Level)

Create or edit `<project>/.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "borg-mcp": {
      "command": "python",
      "args": [
        "-m",
        "borg.integrations.mcp_server"
      ],
      "env": {
        "PYTHONPATH": "/root/hermes-workspace/guild-v2"
      }
    }
  }
}
```

### Verify It Works

1. Open VS Code with Cline extension installed
2. Run the **Cline: MCP Servers** command from the command palette
3. You should see `borg-mcp` listed with a status indicator

Or test from terminal:

```bash
cd /path/to/your/project
python -m borg.integrations.mcp_server
```

Press Ctrl+C — if no import errors, it works.

### What Tools Become Available

All 13 `borg_*` tools appear in Cline's tool picker when you start a new task. Look for tools prefixed with `borg_`.

### Example Workflow in Cline

```
Task: fix the authentication bug in my Django project

Cline: *detects error during task execution*
Cline: → borg_observe({ task: "fix authentication bug in Django" })
  ← { success: true, suggestions: [{ uri: "gh:halford4d/django-auth-fix@v1.0.0", score: 0.94 }] }

Cline: → borg_apply({ action: "apply", pack_uri: "gh:halford4d/django-auth-fix@v1.0.0" })
  ← { success: true, modified: ["auth/decorators.py"] }

Cline: ✅ Pack applied. Task complete.
```

---

## Example Workflow: Problem → Pack Found → Applied

This walkthrough shows the full `borg_observe` → `borg_search` → `borg_apply` cycle.

### Scenario

Your agent is working on a Python project and hits:

```
TypeError: cannot import name 'auth' from 'django.contrib'
```

### Step 1: Observe the Problem

The agent calls `borg_observe`:

```json
{
  "tool": "borg_observe",
  "arguments": {
    "task": "fix Django authentication import error"
  }
}
```

Response:
```json
{
  "success": true,
  "suggestions": [
    {
      "uri": "gh:halford4d/django-auth-fix@v1.0.0",
      "name": "Django Auth Bug Fix Pack",
      "relevance_score": 0.94,
      "description": "Patches the incorrect django.contrib.auth import pattern"
    }
  ],
  "pack_id": "pkg-8823"
}
```

### Step 2: Pull the Pack

The agent calls `borg_pull`:

```json
{
  "tool": "borg_pull",
  "arguments": {
    "uri": "gh:halford4d/django-auth-fix@v1.0.0"
  }
}
```

Response:
```json
{
  "success": true,
  "message": "Pack pulled and cached locally",
  "pack_path": "/root/.borg/packs/gh/halford4d/django-auth-fix@v1.0.0"
}
```

### Step 3: Apply the Fix

The agent calls `borg_apply`:

```json
{
  "tool": "borg_apply",
  "arguments": {
    "action": "apply",
    "pack_uri": "gh:halford4d/django-auth-fix@v1.0.0"
  }
}
```

Response:
```json
{
  "success": true,
  "message": "Pack applied successfully",
  "modified": ["auth/decorators.py", "auth/middleware.py"],
  "summary": "Replaced 'from django.contrib import auth' with 'from django.contrib.auth import get_user_model'"
}
```

**Result:** The fix was applied in seconds, tokens saved, agent continues with original task.

---

## Configuration Reference

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `PYTHONPATH` | Must point to the directory containing the `borg` package | `/root/hermes-workspace/guild-v2` |

### Server Details

| Property | Value |
|----------|-------|
| Server module | `borg.integrations.mcp_server` |
| Protocol | JSON-RPC 2.0 via stdin/stdout |
| Tools count | 13 |
| Package | `agent-borg` (PyPI) |

### Hermes Config Location

```
~/.hermes/config.yaml
```

### Cursor Config Location

```
<project-root>/.cursor/mcp.json
```

### Cline Config Location

```
~/.config/Code/User/settings.json      # global
<project>/.vscode/mcp.json             # workspace-level
```

---

## Troubleshooting

### "Module not found: borg"

- Ensure `PYTHONPATH` is set to the directory **containing** `borg/`, not inside `borg/`
- Verify the package is installed: `pip show agent-borg`
- Check the path: `/root/hermes-workspace/guild-v2` should contain `borg/`

### "No MCP server found" in Cursor/Cline

- Restart the IDE completely
- Verify the JSON is valid: use a JSON linter
- Check that `mcp_servers` (Cursor) or `mcpServers` (Cline) is spelled correctly

### Tools not appearing

- Run the smoke test: `python /root/hermes-workspace/guild-v2/test_mcp_server.py`
- All 13 tools should return `PASS`
- Check that the server starts without errors in a standalone terminal first

### Hermes config not loading

- Verify `~/.hermes/config.yaml` exists and is valid YAML
- Run: `python -c "import yaml; yaml.safe_load(open('~/.hermes/config.yaml'))"`
- Ensure `mcp_servers:` is at the correct indentation level

---

## Files Reference

| File | Purpose |
|------|---------|
| `borg/integrations/mcp_server.py` | The MCP server implementation |
| `test_mcp_server.py` | Smoke test for all 13 tools |
| `MCP_SMOKE_TEST_RESULTS.md` | Latest smoke test output |
| `PACK_AUDIT_RESULTS.md` | Audit of available packs |
| `guild-v2/docs/INTEGRATION_GUIDE.md` | This document |
