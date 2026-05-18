# Borg MCP integration guide

Use this current guide for Claude Code, Cursor, Cline, Continue, Goose, Codex-style CLIs, or any stdio MCP client.

## 1. Install the right package

Borg is the product name. Install package `agent-borg`; it provides:

- `borg` — CLI
- `borg-mcp` — MCP server command
- `borg-doctor` — diagnostics

Do **not** install `borg`, `borgbackup`, `brew install borgbackup`, `apt install borgbackup`, `dnf install borgbackup`, or `pacman -S borg`; those are unrelated.

Use the OS-specific install guide first: [`INSTALL.md`](INSTALL.md).

## 2. Verify the CLI

macOS/Linux:

```bash
command -v borg
command -v borg-mcp
borg version
borg-doctor --json
```

Windows PowerShell:

```powershell
where.exe borg
where.exe borg-mcp
borg version
borg-doctor --json
```

## 3. Claude Code setup

```bash
borg setup-claude --scope user --verify --fix
```

Expected output includes:

```text
Verify: PASS (initialize handshake ok)
```

Then fully quit and restart Claude Code. In a new session, ask:

```text
what MCP tools do you have from Borg?
```

Expected: Claude lists Borg tools such as `borg_rescue`, `borg_observe`, and `borg_search`, or `/mcp list` shows a `borg` server.

## 4. Generic MCP config

```json
{
  "mcpServers": {
    "borg": {
      "command": "borg-mcp",
      "args": [],
      "env": { "BORG_HOME": "/absolute/path/to/.borg" }
    }
  }
}
```

If your MCP client cannot find `borg-mcp`, use an absolute path.

macOS/Linux:

```bash
command -v borg-mcp
```

Windows PowerShell:

```powershell
where.exe borg-mcp
```

Avoid bare `python` or `python3` in MCP configs unless you know that exact interpreter has `agent-borg` installed.

## 5. Core first-user MCP tools

- `borg_rescue` — ACTION / STOP / VERIFY packet for concrete failures.
- `borg_observe` — guidance before technical fixes.
- `borg_search` — search packs and traces.
- `borg_try` — preview a pack.
- `borg_apply` — start/checkpoint/complete pack execution.
- `borg_feedback` — generate feedback from a completed session.
- `borg_suggest` — suggest after repeated failures.
- `borg_first_10` — first-10 beta gates and smoke path.

Advanced/admin tools may also be exposed, but first users should start with the tools above.

## 6. Prime the agent

```text
Before attempting technical fixes for errors, bugs, installs, configs, deployments, or tests, call Borg first. Prefer borg_rescue(input="<exact error or failing command output>") when there is a concrete failure; use borg_observe(task="<exact task or error>", context="<tech stack>") at task start. Treat Borg output as advisory: follow ACTION when relevant, avoid STOP/AVOID patterns, disclose NO_CONFIDENT_MATCH or weak guidance, and record the outcome with borg_rate(helpful=True/False).
```
